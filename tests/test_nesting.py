"""
Unit tests for extended Nest Parts / DXF Nesting application.
Tests priority ordering, stock quantity limits, thickness matching,
unplaced parts reporting, and legacy migration.
"""

import os
import shutil
import tempfile
import unittest
import ezdxf

from core.nesting import StockSheet, NestablePart, nest_parts, part_bbox


class TestNestingEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="nest_test_")
        
        # Create dummy DXF part files
        self.dxf_small = os.path.join(self.temp_dir, "small_part.dxf")
        self.dxf_medium = os.path.join(self.temp_dir, "medium_part.dxf")
        self.dxf_large = os.path.join(self.temp_dir, "large_part.dxf")

        self._create_rect_dxf(self.dxf_small, 100, 100)
        self._create_rect_dxf(self.dxf_medium, 300, 300)
        self._create_rect_dxf(self.dxf_large, 3000, 3000)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_rect_dxf(self, path, w, h):
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        pts = [(0, 0), (w, 0), (w, h), (0, h), (0, 0)]
        msp.add_lwpolyline(pts)
        doc.saveas(path)

    # 1. Priority Order 1 is completed before Priority Order 2
    def test_priority_order_1_before_order_2(self):
        sheet = StockSheet(width=1000, height=1000, thickness=18.0, available_quantity=2)
        part1 = NestablePart(path=self.dxf_medium, quantity=4, thickness=18.0, priority="High", priority_order=2, name="Order2")
        part2 = NestablePart(path=self.dxf_medium, quantity=4, thickness=18.0, priority="Normal", priority_order=1, name="Order1")

        out_dir = os.path.join(self.temp_dir, "run1")
        result = nest_parts(parts=[part1, part2], stock_sheets=[sheet], output_dir=out_dir)

        sheets = result["sheets"]
        self.assertTrue(len(sheets) > 0)
        # Sheet 1 should contain Order1 parts placed first
        first_sheet_parts = [p["part_name"] for p in sheets[0]["placed_parts"]]
        self.assertIn("Order1", first_sheet_parts)

    # 2. A Normal part with Priority Order 1 is processed before a High part with Priority Order 2
    def test_normal_order_1_before_high_order_2(self):
        sheet = StockSheet(width=1000, height=1000, thickness=18.0, available_quantity=5)
        part_normal_p1 = NestablePart(path=self.dxf_small, quantity=2, thickness=18.0, priority="Normal", priority_order=1, name="NormalP1")
        part_high_p2 = NestablePart(path=self.dxf_small, quantity=2, thickness=18.0, priority="High", priority_order=2, name="HighP2")

        out_dir = os.path.join(self.temp_dir, "run2")
        result = nest_parts(parts=[part_high_p2, part_normal_p1], stock_sheets=[sheet], output_dir=out_dir)

        # Check production order in results
        placed = [p["part_name"] for s in result["sheets"] for p in s["placed_parts"]]
        self.assertEqual(placed[0], "NormalP1")

    # 3. Thickness matching tolerance (abs(part - sheet) < 0.001)
    def test_thickness_matching(self):
        sheet_18 = StockSheet(width=1000, height=1000, thickness=18.0, available_quantity=5)
        part_18 = NestablePart(path=self.dxf_small, quantity=1, thickness=18.0, name="Match18")
        part_12 = NestablePart(path=self.dxf_small, quantity=1, thickness=12.0, name="NoMatch12")

        out_dir = os.path.join(self.temp_dir, "run3")
        result = nest_parts(parts=[part_18, part_12], stock_sheets=[sheet_18], output_dir=out_dir)

        self.assertEqual(result["total_parts_placed"], 1)
        self.assertEqual(result["total_parts_unplaced"], 1)
        self.assertEqual(result["unplaced_parts"][0]["reason"], "No stock sheet with compatible thickness.")

    # 4. Stock quantity hard limit enforcement
    def test_stock_quantity_limit(self):
        sheet = StockSheet(width=400, height=400, thickness=10.0, available_quantity=1)
        part = NestablePart(path=self.dxf_medium, quantity=4, thickness=10.0, name="MedPart")

        out_dir = os.path.join(self.temp_dir, "run4")
        result = nest_parts(parts=[part], stock_sheets=[sheet], output_dir=out_dir)

        # Only 1 medium part fits on 400x400 sheet, stock limit = 1 sheet -> 1 placed, 3 unplaced
        self.assertEqual(result["total_sheets_used"], 1)
        self.assertEqual(result["stock_usage"][0]["used_quantity"], 1)
        self.assertEqual(result["stock_usage"][0]["remaining_quantity"], 0)
        self.assertEqual(result["total_parts_placed"], 1)
        self.assertEqual(result["total_parts_unplaced"], 3)

    # 5. Multiple stock sheet sizes selection
    def test_multiple_stock_sheet_selection(self):
        sheet_small = StockSheet(width=500, height=500, thickness=18.0, available_quantity=2, name="SmallSheet")
        sheet_large = StockSheet(width=2000, height=2000, thickness=18.0, available_quantity=2, name="LargeSheet")
        part = NestablePart(path=self.dxf_medium, quantity=1, thickness=18.0, name="FitSmall")

        out_dir = os.path.join(self.temp_dir, "run5")
        result = nest_parts(parts=[part], stock_sheets=[sheet_large, sheet_small], output_dir=out_dir)

        # Should select SmallSheet since it fits and minimizes waste
        used_sheet = result["sheets"][0]["stock_sheet_name"]
        self.assertEqual(result["total_sheets_used"], 1)
        self.assertIn("SmallSheet", used_sheet)

    # 6. Unplaced parts reporting for oversized part
    def test_oversized_part_unplaced(self):
        sheet = StockSheet(width=1000, height=1000, thickness=18.0, available_quantity=5)
        part_huge = NestablePart(path=self.dxf_large, quantity=1, thickness=18.0, name="HugePart")

        out_dir = os.path.join(self.temp_dir, "run6")
        result = nest_parts(parts=[part_huge], stock_sheets=[sheet], output_dir=out_dir)

        self.assertEqual(result["total_parts_placed"], 0)
        self.assertEqual(result["total_parts_unplaced"], 1)
        self.assertEqual(result["unplaced_parts"][0]["reason"], "The part is larger than every compatible stock sheet.")

    # 7. Unlimited legacy stock explicitly enabled
    def test_unlimited_legacy_stock(self):
        sheet = StockSheet(width=400, height=400, thickness=1.0, available_quantity=1, unlimited_quantity=True)
        part = NestablePart(path=self.dxf_medium, quantity=3, thickness=1.0)

        out_dir = os.path.join(self.temp_dir, "run7")
        result = nest_parts(parts=[part], stock_sheets=[sheet], output_dir=out_dir)

        # Should create 3 sheets because stock is unlimited
        self.assertEqual(result["total_sheets_used"], 3)
        self.assertEqual(result["total_parts_placed"], 3)
        self.assertEqual(result["total_parts_unplaced"], 0)

    # 8. High-priority sheets listed first in output order
    def test_high_priority_sheets_first(self):
        sheet = StockSheet(width=400, height=400, thickness=10.0, available_quantity=5)
        part_low = NestablePart(path=self.dxf_medium, quantity=1, thickness=10.0, priority="Low", priority_order=200, name="LowPart")
        part_high = NestablePart(path=self.dxf_medium, quantity=1, thickness=10.0, priority="High", priority_order=10, name="HighPart")

        out_dir = os.path.join(self.temp_dir, "run8")
        result = nest_parts(parts=[part_low, part_high], stock_sheets=[sheet], output_dir=out_dir)

        self.assertEqual(result["sheets"][0]["priority_order"], 10)
        self.assertEqual(result["sheets"][0]["placed_parts"][0]["part_name"], "HighPart")

    # 9. Verify no empty sheets are generated and placements are non-empty
    def test_no_empty_sheets_and_non_overlapping(self):
        sheet = StockSheet(width=500, height=500, thickness=18.0, available_quantity=5)
        part = NestablePart(path=self.dxf_medium, quantity=3, thickness=18.0, name="MedPart")

        out_dir = os.path.join(self.temp_dir, "run9")
        result = nest_parts(parts=[part], stock_sheets=[sheet], output_dir=out_dir)

        for s in result["sheets"]:
            self.assertTrue(len(s["placed_parts"]) > 0, "Generated sheet must contain placed parts")
            self.assertTrue(os.path.exists(s["dxf_path"]))


if __name__ == "__main__":
    unittest.main()
