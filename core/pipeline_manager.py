import os
import sys
import math
from datetime import datetime
from core.database import DatabaseManager

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class PipelineManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def text_to_3d(self, user_prompt, desired_dims=None, user_id="default_user", project_id=None, output_dir=None, job_id=None):
        return self.run_3d_pipeline(
            user_id=user_id,
            project_id=project_id,
            mode="Text3D",
            prompt=user_prompt,
            params=desired_dims or {"height": 100, "width": 100, "length": 100},
            output_dir=output_dir,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )

    def image_to_3d(self, image_path, desired_dims=None, user_id="default_user", project_id=None, output_dir=None, job_id=None):
        return self.run_3d_pipeline(
            user_id=user_id,
            project_id=project_id,
            mode="Image3D",
            prompt="Image to 3D",
            image_path=image_path,
            params=desired_dims or {"height": 100, "width": 100, "length": 100},
            output_dir=output_dir,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )

    def edit_3d(self, file_path, prompt, desired_dims=None, user_id="default_user", project_id=None, output_dir=None, job_id=None):
        return self.run_3d_pipeline(
            user_id=user_id,
            project_id=project_id,
            mode="Edit3D",
            prompt=prompt,
            image_path=file_path,
            params=desired_dims or {"height": 100, "width": 100, "length": 100},
            output_dir=output_dir,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )


    def run_3d_pipeline(self, user_id, project_id, mode, prompt, image_path=None, params=None, output_dir=None, job_id=None):
        """
        Runs the 3D pipeline.
        output_dir: the workspace folder chosen by the user. Falls back to 'storage/outputs/' if None.
        job_id: Optional pre-created job ID (to avoid duplicate creation)
        """
        import shutil

        # Only create job_id if not provided (prevents duplicate creation)
        if job_id is None:
            job_id = self.db.create_job(
                user_id=user_id,
                project_id=project_id,
                job_type=mode,
                design_type="3D",
                output_format="STL",
                text_prompt=prompt
            )
            print(f"[PipelineManager] Created new job_id: {job_id}")
        else:
            print(f"[PipelineManager] Using existing job_id: {job_id}")

        start_time = datetime.now()

        try:
            print(f"[PipelineManager] Starting 3D pipeline for job {job_id}, mode: {mode}")
            
            if mode == "Text3D":
                from core.three_d.external_3d_client import text_to_3d
                source_file = text_to_3d(prompt, params['height'], params['width'], params['length'])
            elif mode == "Image3D":
                from core.three_d.external_3d_client import image_to_3d
                source_file = image_to_3d(image_path, params['height'], params['width'], params['length'])
            else: # Edit3D
                from core.three_d.external_3d_client import edit_3d
                source_file = edit_3d(image_path, prompt)

            # ── Unit normalisation: Hunyuan3D outputs in metres, we need mm ──────
            source_file = self._normalise_stl_units(source_file)

            # ── Scale to baseline 100x100x100 (preserve aspect ratio) ─────────────
            source_file = self._scale_to_baseline(source_file, baseline_size=100.0)

            # Copy the generated file to the user workspace (or storage/outputs/ fallback)
            input_path_for_naming = image_path if mode == "Edit3D" else None
            dest_path = self._generate_output_path(
                prompt,
                os.path.splitext(source_file)[1].lstrip(".") or "stl",
                output_dir,
                input_file_path=input_path_for_naming,
                user_id=user_id,
                project_id=project_id
            )
            if os.path.abspath(source_file) != os.path.abspath(dest_path):
                shutil.copy2(source_file, dest_path)
            output_file = dest_path

            # Optimize / decimate high-density Hunyuan3D mesh for smooth 60fps viewport rendering
            try:
                self._simplify_stl_mesh(output_file, max_faces=60000)
            except Exception as dec_err:
                print(f"[PipelineManager] Mesh decimation skipped: {dec_err}")

            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            out_file_id = self.db.log_output_file(job_id, os.path.basename(output_file), output_file, "STL")
            self.db.update_job_status(job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration)
            print(f"[PipelineManager] Pipeline COMPLETED for job {job_id}: {output_file}")
            return output_file

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[PipelineManager] Pipeline ERROR for job {job_id}: {e}")
            print(f"[PipelineManager] Full traceback:\n{error_trace}")
            self.db.update_job_status(job_id, "FAILED")
            raise

    def _normalise_stl_units(self, stl_path: str, threshold: float = 5.0, scale: float = 1000.0) -> str:
        """
        Hunyuan3D exports geometry in metres. This helper detects the unit scale
        by computing the bounding-box longest dimension from the binary STL.
        If it is smaller than `threshold` (i.e. the model fits inside a 5-metre cube),
        every vertex coordinate is multiplied by `scale` (1000 → converts m to mm)
        and the STL is rewritten in-place.

        Returns the (possibly modified) file path unchanged.
        """
        if not stl_path or not os.path.exists(stl_path):
            return stl_path

        # Check if this file has already been normalized (prevent double scaling)
        # Use a marker file approach or check file modification time
        marker_path = stl_path + ".normalized"
        if os.path.exists(marker_path):
            marker_time = os.path.getmtime(marker_path)
            stl_time = os.path.getmtime(stl_path)
            if marker_time >= stl_time:
                print(f"[UnitNorm] INFO: File already normalized (marker exists and is newer) - skipping: {stl_path}")
                return stl_path
        try:
            import struct

            with open(stl_path, "rb") as f:
                header = f.read(80)
                raw_n = f.read(4)
                if len(raw_n) < 4:
                    return stl_path
                n_triangles = struct.unpack("<I", raw_n)[0]
                if n_triangles == 0:
                    return stl_path

                triangles = []
                xs = []
                for _ in range(n_triangles):
                    tri_data = f.read(50)
                    if len(tri_data) < 50:
                        break
                    triangles.append(tri_data)
                    # vertices at bytes 12-48, 3 vertices × 3 floats × 4 bytes each
                    for vi in range(3):
                        offset = 12 + vi * 12
                        x = struct.unpack_from("<f", tri_data, offset)[0]
                        xs.append(abs(x))

            if not xs:
                return stl_path

            # Sample the bounding box via the X-range (fast heuristic)
            # Full check: read all vertices from saved triangles
            all_coords = []
            for tri_data in triangles:
                for vi in range(3):
                    offset = 12 + vi * 12
                    x, y, z = struct.unpack_from("<fff", tri_data, offset)
                    all_coords.append((x, y, z))

            xs_all = [c[0] for c in all_coords]
            ys_all = [c[1] for c in all_coords]
            zs_all = [c[2] for c in all_coords]
            xs_all_max = max(xs_all)
            xs_all_min = min(xs_all)
            ys_all_max = max(ys_all)
            ys_all_min = min(ys_all)
            zs_all_max = max(zs_all)
            zs_all_min = min(zs_all)
            longest = max(
                xs_all_max - xs_all_min,
                ys_all_max - ys_all_min,
                zs_all_max - zs_all_min,
            )

            orig_lx = xs_all_max - xs_all_min
            orig_ly = ys_all_max - ys_all_min
            orig_lz = zs_all_max - zs_all_min

            if longest >= threshold:
                print(f"[UnitNorm] INFO: Already in mm - original dims: lx={orig_lx:.2f}mm ly={orig_ly:.2f}mm lz={orig_lz:.2f}mm (longest={longest:.2f}mm >= {threshold}mm threshold) — no scaling needed.")
                return stl_path

            print(f"[UnitNorm] INFO: Detected unit: METRES | original dims: lx={orig_lx:.6f}m ly={orig_ly:.6f}m lz={orig_lz:.6f}m")
            print(f"[UnitNorm] INFO: Conversion factor: x{scale} (m→mm) | bbox longest={longest:.6f}m < {threshold}m threshold")

            # Rewrite STL with scaled vertices
            with open(stl_path, "wb") as f:
                f.write(header)
                f.write(struct.pack("<I", n_triangles))
                for tri_data in triangles:
                    # Normal (bytes 0-11): normals are unit vectors — do NOT scale them
                    f.write(tri_data[:12])  # write original normal unchanged
                    # Vertices (bytes 12-48): scale each coordinate
                    for vi in range(3):
                        offset = 12 + vi * 12
                        x, y, z = struct.unpack_from("<fff", tri_data, offset)
                        f.write(struct.pack("<fff", x * scale, y * scale, z * scale))
                    # Attribute byte count (bytes 48-49)
                    f.write(tri_data[48:50])

            final_lx = orig_lx * scale
            final_ly = orig_ly * scale
            final_lz = orig_lz * scale
            print(f"[UnitNorm] INFO: Rescaled {n_triangles:,} triangles | final dims: lx={final_lx:.2f}mm ly={final_ly:.2f}mm lz={final_lz:.2f}mm")

            # Create marker file to prevent double normalization
            with open(marker_path, 'w') as f:
                f.write(f"normalized_at={datetime.now().isoformat()}\n")
                f.write(f"original_dims={orig_lx:.6f},{orig_ly:.6f},{orig_lz:.6f}\n")
                f.write(f"final_dims={final_lx:.2f},{final_ly:.2f},{final_lz:.2f}\n")
                f.write(f"scale_factor={scale}\n")
        except Exception as e:
            print(f"[UnitNorm] WARNING: unit normalisation failed ({e}) — file left unchanged")

        return stl_path

    def _scale_to_baseline(self, stl_path: str, baseline_size: float = 100.0) -> str:
        """
        Scale the generated STL to fit within a baseline cube (default 100x100x100mm)
        while preserving the aspect ratio. This ensures all generated models are
        consistently sized and not too large for the viewport.
        
        Logic:
        1. Compute current bounding box dimensions
        2. Find the longest dimension
        3. Calculate scale factor = baseline_size / longest_dimension
        4. Scale all vertices by this factor
        5. This ensures the model fits within baseline cube while maintaining proportions
        """
        if not stl_path or not os.path.exists(stl_path):
            return stl_path

        # Check if already scaled to baseline
        baseline_marker = stl_path + ".baseline_scaled"
        if os.path.exists(baseline_marker):
            marker_time = os.path.getmtime(baseline_marker)
            stl_time = os.path.getmtime(stl_path)
            if marker_time >= stl_time:
                print(f"[BaselineScale] INFO: File already scaled to baseline - skipping: {stl_path}")
                return stl_path

        try:
            import struct

            with open(stl_path, "rb") as f:
                header = f.read(80)
                raw_n = f.read(4)
                if len(raw_n) < 4:
                    return stl_path
                n_triangles = struct.unpack("<I", raw_n)[0]
                if n_triangles == 0:
                    return stl_path

                triangles = []
                all_coords = []
                for _ in range(n_triangles):
                    tri_data = f.read(50)
                    if len(tri_data) < 50:
                        break
                    triangles.append(tri_data)
                    # Extract all vertices
                    for vi in range(3):
                        offset = 12 + vi * 12
                        x, y, z = struct.unpack_from("<fff", tri_data, offset)
                        all_coords.append((x, y, z))

            if not all_coords:
                return stl_path

            # Compute bounding box
            xs = [c[0] for c in all_coords]
            ys = [c[1] for c in all_coords]
            zs = [c[2] for c in all_coords]
            
            orig_lx = max(xs) - min(xs)
            orig_ly = max(ys) - min(ys)
            orig_lz = max(zs) - min(zs)
            
            longest = max(orig_lx, orig_ly, orig_lz)
            
            # If model is already smaller than baseline, don't scale up (avoid tiny models)
            if longest <= baseline_size * 0.5:
                print(f"[BaselineScale] INFO: Model already small enough (longest={longest:.2f}mm <= {baseline_size * 0.5:.2f}mm) - no scaling needed")
                return stl_path
            
            # Calculate scale factor to fit within baseline
            scale_factor = baseline_size / longest
            
            # If scale factor is close to 1, skip
            if 0.95 <= scale_factor <= 1.05:
                print(f"[BaselineScale] INFO: Model already at baseline size (scale_factor={scale_factor:.3f}) - no scaling needed")
                return stl_path

            print(f"[BaselineScale] INFO: Scaling to baseline {baseline_size}x{baseline_size}x{baseline_size}mm")
            print(f"[BaselineScale] INFO: Original dims: lx={orig_lx:.2f}mm ly={orig_ly:.2f}mm lz={orig_lz:.2f}mm (longest={longest:.2f}mm)")
            print(f"[BaselineScale] INFO: Scale factor: {scale_factor:.4f}")

            # Rewrite STL with scaled vertices
            with open(stl_path, "wb") as f:
                f.write(header)
                f.write(struct.pack("<I", n_triangles))
                for tri_data in triangles:
                    # Normals (bytes 0-11): do NOT scale
                    f.write(tri_data[:12])
                    # Vertices (bytes 12-48): scale by factor
                    for vi in range(3):
                        offset = 12 + vi * 12
                        x, y, z = struct.unpack_from("<fff", tri_data, offset)
                        f.write(struct.pack("<fff", x * scale_factor, y * scale_factor, z * scale_factor))
                    # Attribute byte count (bytes 48-50)
                    f.write(tri_data[48:50])

            final_lx = orig_lx * scale_factor
            final_ly = orig_ly * scale_factor
            final_lz = orig_lz * scale_factor
            print(f"[BaselineScale] INFO: Scaled {n_triangles:,} triangles | final dims: lx={final_lx:.2f}mm ly={final_ly:.2f}mm lz={final_lz:.2f}mm")

            # Create marker file
            with open(baseline_marker, 'w') as f:
                f.write(f"baseline_scaled_at={datetime.now().isoformat()}\n")
                f.write(f"original_dims={orig_lx:.2f},{orig_ly:.2f},{orig_lz:.2f}\n")
                f.write(f"final_dims={final_lx:.2f},{final_ly:.2f},{final_lz:.2f}\n")
                f.write(f"scale_factor={scale_factor:.4f}\n")
                f.write(f"baseline_size={baseline_size}\n")

        except Exception as e:
            print(f"[BaselineScale] WARNING: baseline scaling failed ({e}) — file left unchanged")

        return stl_path

    def _simplify_stl_mesh(self, stl_path: str, max_faces: int = 60000) -> str:
        """
        In-place quadric mesh simplification for overly dense Hunyuan3D geometry.
        Reduces triangle count to `max_faces` so the 3D viewport renders smoothly without lag.
        """
        if not stl_path or not os.path.exists(stl_path):
            return stl_path

        try:
            import trimesh
            mesh = trimesh.load(stl_path)
            if not hasattr(mesh, "faces") or len(mesh.faces) <= max_faces:
                print(f"[Mesh Simplification] INFO: Face count {len(mesh.faces):,} <= {max_faces:,} - no simplification needed")
                return stl_path

            original_faces = len(mesh.faces)
            print(f"[Mesh Simplification] INFO: Decimating {os.path.basename(stl_path)} from {original_faces:,} to {max_faces:,} faces...")

            # Try quadric decimation methods
            simplified = None
            if hasattr(mesh, "simplify_quadric_decimation"):
                try:
                    simplified = mesh.simplify_quadric_decimation(face_count=max_faces)
                except Exception as q_err:
                    print(f"[Mesh Simplification] quadric decimation error: {q_err}")

            if simplified is None and hasattr(mesh, "simplify_quadratic_decimation"):
                try:
                    simplified = mesh.simplify_quadratic_decimation(face_count=max_faces)
                except Exception as q2_err:
                    print(f"[Mesh Simplification] quadratic decimation fallback error: {q2_err}")

            if simplified is not None and hasattr(simplified, "faces") and len(simplified.faces) > 0:
                simplified.export(stl_path)
                print(f"[Mesh Simplification] SUCCESS: Reduced from {original_faces:,} to {len(simplified.faces):,} faces.")
            else:
                print(f"[Mesh Simplification] WARNING: Decimation could not produce valid mesh - kept original.")

        except Exception as err:
            print(f"[Mesh Simplification] ERROR during decimation: {err}")

        return stl_path

    def _generate_viewport_preview(self, stl_path: str, max_faces: int = 40000) -> str:
        """
        Creates a decimated lightweight preview STL for smooth 60fps Three.js viewport rendering,
        while preserving the original high-resolution master STL untouched on disk for CAD/CAM export.
        Returns the preview path if generated, otherwise returns the original stl_path.
        """
        if not stl_path or not os.path.exists(stl_path):
            return stl_path

        # Check if a preview already exists and is newer than the source — skip decimation
        preview_path = os.path.splitext(stl_path)[0] + "_preview.stl"
        if os.path.exists(preview_path) and os.path.getmtime(preview_path) >= os.path.getmtime(stl_path):
            print(f"[Mesh Decimation] INFO: Reusing existing preview: {preview_path} ({os.path.getsize(preview_path)} bytes)")
            return preview_path

        # Only decimate if file is > 3 MB
        size_bytes = os.path.getsize(stl_path)
        if size_bytes < 3 * 1024 * 1024:
            print(f"[Mesh Decimation] INFO: File too small to decimate ({size_bytes/1024/1024:.2f}MB < 3MB) — using original")
            return stl_path

        try:
            import trimesh
            mesh = trimesh.load(stl_path)
            if not hasattr(mesh, "faces") or len(mesh.faces) <= max_faces:
                print(f"[Mesh Decimation] INFO: Mesh already has {len(mesh.faces):,} faces (<= {max_faces:,}) — using original")
                return stl_path

            face_count = len(mesh.faces)
            print(f"[Mesh Decimation] INFO: {face_count:,} faces in {os.path.basename(stl_path)} — decimating to {max_faces:,}...")

            # Try fast_simplification first (best quality)
            try:
                decimated = mesh.simplify_quadric_decimation(face_count=max_faces)
                decimated.export(preview_path)
                print(f"[Mesh Decimation] INFO: Preview saved using fast_simplification: {preview_path} ({len(decimated.faces):,} faces, {os.path.getsize(preview_path)} bytes)")
                return preview_path
            except ImportError:
                print("[Mesh Decimation] WARNING: fast_simplification not installed — trying trimesh fallback")
            except Exception as dec_err:
                print(f"[Mesh Decimation] WARNING: fast_simplification failed ({dec_err}) — trying trimesh fallback")

            # Fallback to trimesh's built-in simplification
            try:
                # Use trimesh's simplify_quadratic_decimation as fallback
                decimated = mesh.simplify_quadratic_decimation(face_count=max_faces)
                decimated.export(preview_path)
                print(f"[Mesh Decimation] INFO: Preview saved using trimesh fallback: {preview_path} ({len(decimated.faces):,} faces, {os.path.getsize(preview_path)} bytes)")
                return preview_path
            except Exception as trimesh_err:
                print(f"[Mesh Decimation] WARNING: Trimesh fallback also failed ({trimesh_err}) — using original STL")
                return stl_path

        except Exception as load_err:
            print(f"[Mesh Decimation] ERROR: Could not load mesh for decimation ({load_err}) — using original STL")
            return stl_path


    def run_nesting(
        self,
        user_id,
        project_id,
        part_paths,
        stock_sheets=None,
        sheet_width=1200.0,
        sheet_height=600.0,
        spacing=5.0,
        allow_rotate=True,
        nesting_mode="Finish priority parts first",
        continue_on_incomplete=True,
        output_dir=None,
    ):
        """
        Pack multiple DXF parts onto stock sheets.
        Handles both new multi-sheet inventory/priority signatures and legacy single-sheet calls.
        Returns NestResult summary dictionary.
        """
        from core.nesting import nest_parts, StockSheet, NestablePart

        # ── Legacy Migration Check ──────────────────────────────────────
        if stock_sheets is None:
            stock_sheets = [
                StockSheet(
                    name="Legacy Sheet",
                    material="Default",
                    width=sheet_width if sheet_width is not None else 1200.0,
                    height=sheet_height if sheet_height is not None else 600.0,
                    thickness=1.0,
                    available_quantity=1,
                    unlimited_quantity=True,
                )
            ]

        job_id = self.db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type="Nest",
            design_type="2D",
            output_format="DXF",
            text_prompt=f"Nest {len(part_paths)} part(s) on stock sheet inventory",
        )

        start_time = datetime.now()
        save_dir = output_dir if output_dir else os.path.join("storage/outputs", "nesting_results", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(save_dir, exist_ok=True)

        try:
            summary_result = nest_parts(
                parts=part_paths,
                stock_sheets=stock_sheets,
                spacing=spacing,
                allow_rotate=allow_rotate,
                nesting_mode=nesting_mode,
                continue_on_incomplete=continue_on_incomplete,
                output_dir=save_dir,
            )

            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            # Log primary output sheet DXF if any were generated
            first_sheet_path = None
            if summary_result.get("sheets"):
                first_sheet_path = summary_result["sheets"][0]["dxf_path"]
                out_file_id = self.db.log_output_file(
                    job_id, os.path.basename(first_sheet_path), first_sheet_path, "DXF"
                )
            else:
                out_file_id = None

            self.db.update_job_status(
                job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration
            )
            return summary_result

        except Exception as e:
            print(f"Nesting Error: {e}")
            self.db.update_job_status(job_id, "FAILED")
            return {
                "output_dir": save_dir,
                "total_parts_required": len(part_paths),
                "total_parts_placed": 0,
                "total_parts_unplaced": len(part_paths),
                "total_sheets_used": 0,
                "total_utilization": 0.0,
                "total_waste": 100.0,
                "completed_priority_groups": 0,
                "incomplete_priority_groups": 1,
                "priority_completion": [],
                "production_ready_sheets": [],
                "stock_usage": [],
                "unplaced_parts": [{"reason": str(e)}],
                "sheets": [],
            }

    def _generate_output_path(self, prompt, ext, output_dir=None, input_file_path=None, user_id=None, project_id=None):
        if output_dir:
            save_dir = output_dir
        elif user_id and user_id != "default_user":
            if project_id and project_id != "default_project":
                save_dir = os.path.join("storage", "outputs", "users", user_id, "projects", project_id)
            else:
                save_dir = os.path.join("storage", "outputs", "users", user_id)
        else:
            save_dir = "storage/outputs"

        os.makedirs(save_dir, exist_ok=True)

        if input_file_path:
            stem = os.path.splitext(os.path.basename(input_file_path))[0]
            if stem.endswith("_edit"):
                base = stem
            else:
                base = f"{stem}_edit"
            out_path = os.path.join(save_dir, f"{base}.{ext}")
            if os.path.exists(out_path):
                out_path = os.path.join(save_dir, f"{base}_{datetime.now().strftime('%H%M%S')}.{ext}")
            return out_path

        base = "".join([c if c.isalnum() else "_" for c in prompt[:20]]).strip("_") or "output"
        return os.path.join(save_dir, f"{base}_{datetime.now().strftime('%H%M%S')}.{ext}")
