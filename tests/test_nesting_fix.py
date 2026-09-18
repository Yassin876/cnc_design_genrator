"""
Test nesting functionality
"""
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.nesting import nest_parts, StockSheet, NestablePart

# Test with a simple part
test_part_path = "storage/uploads/test_part.dxf"  # Create a test file if needed

# Create stock sheet
stock_sheets = [
    StockSheet(
        width=1200.0,
        height=600.0,
        thickness=18.0,
        material="Steel",
        name="Stock Sheet 1",
        available_quantity=1,
        unlimited_quantity=True
    )
]

# Test part
parts = [
    {
        "path": os.path.join(project_root, "tests", "fixtures", "butterfly.dxf"),
        "quantity": 1,
        "thickness": 18.0,
        "priority": "Normal",
        "priority_order": 100
    }
]


try:
    result = nest_parts(
        parts=parts,
        stock_sheets=stock_sheets,
        spacing=5.0,
        allow_rotate=True,
        nesting_mode="Finish priority parts first",
        output_dir="storage/outputs/nesting_test"
    )
    print("Nesting successful!")
    print(f"Total parts placed: {result['total_parts_placed']}")
    print(f"Total sheets used: {result['total_sheets_used']}")
    print(f"Utilization: {result['total_utilization']}%")
    
    if result['sheets']:
        for sheet in result['sheets']:
            print(f"Sheet {sheet['sheet_number']}: {sheet['dxf_path']}")
            print(f"  Parts: {len(sheet['placed_parts'])}")
            for p in sheet['placed_parts']:
                print(f"    - {p['part_name']} at ({p['x']}, {p['y']}) rotation {p['rotation']}°")
except Exception as e:
    print(f"Nesting failed: {e}")
    import traceback
    traceback.print_exc()
