import os
import sys
import time
import requests
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import DatabaseManager

MAIN_BACKEND_URL = os.getenv("MAIN_BACKEND_URL", "http://localhost:8000")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class PipelineManager:
    """
    HTTP Client proxy that replaces local execution with API requests
    to the Main Backend Orchestrator Microservice.
    """
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.backend_url = MAIN_BACKEND_URL

    def _poll_job_completion(self, job_id: str, timeout_sec: int = 300) -> Dict[str, Any]:
        """Polls the Main Backend GET /api/jobs/{job_id} until completed or failed."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            resp = requests.get(f"{self.backend_url}/api/jobs/{job_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            
            if status == "completed":
                return data
            elif status == "failed":
                err = data.get("error") or "Job execution failed on microservice"
                raise RuntimeError(f"Microservice job failed: {err}")
            
            time.sleep(2)
        raise TimeoutError(f"Job {job_id} timed out after {timeout_sec} seconds")

    def run_2d_pipeline(self, user_id, project_id, mode, prompt, image_path=None, params=None, output_dir=None):
        """
        Runs the 2D pipeline (Image, Prompt, or Edit) via Main Backend HTTP microservices.
        """
        job_id = self.db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type=mode,
            design_type="2D",
            output_format="DXF",
            text_prompt=prompt,
            input_file_id=None
        )
        
        start_time = datetime.now()
        input_path_for_naming = image_path if mode == "Edit" else None
        output_dxf = self._generate_output_path(prompt, "dxf", output_dir, input_file_path=input_path_for_naming)
        params = params or {}

        try:
            if mode == "Edit":
                payload = {
                    "dxf_url": image_path,  # In real deployment, upload file to storage first or send URL
                    "instruction": prompt
                }
                resp = requests.post(f"{self.backend_url}/api/2d/edit-dxf", json=payload, timeout=30)
                resp.raise_for_status()
                remote_job_id = resp.json()["job_id"]
                
            elif mode == "Prompt":
                payload = {
                    "prompt": prompt,
                    "params": params
                }
                resp = requests.post(f"{self.backend_url}/api/2d/generate-from-prompt", json=payload, timeout=30)
                resp.raise_for_status()
                remote_job_id = resp.json()["job_id"]
                
            else:  # mode == "Image"
                payload = {
                    "image_url": image_path,
                    "prompt": prompt or "object",
                    "params": params
                }
                resp = requests.post(f"{self.backend_url}/api/2d/generate-from-image", json=payload, timeout=30)
                resp.raise_for_status()
                remote_job_id = resp.json()["job_id"]

            # Poll for job completion
            job_res = self._poll_job_completion(remote_job_id)
            result_url_or_path = job_res.get("result_url")
            
            # Download or copy resulting DXF to output_dxf
            if result_url_or_path and result_url_or_path.startswith("http"):
                dl_resp = requests.get(result_url_or_path, timeout=30)
                dl_resp.raise_for_status()
                with open(output_dxf, "wb") as f:
                    f.write(dl_resp.content)
            elif result_url_or_path and os.path.exists(result_url_or_path):
                import shutil
                shutil.copy2(result_url_or_path, output_dxf)

            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            out_file_id = self.db.log_output_file(job_id, os.path.basename(output_dxf), output_dxf, "DXF")
            self.db.update_job_status(job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration)
            return output_dxf

        except Exception as e:
            print(f"2D Pipeline Error: {e}")
            self.db.update_job_status(job_id, "FAILED")
            raise

    def run_3d_pipeline(self, user_id, project_id, mode, prompt, image_path=None, params=None, output_dir=None):
        """
        Runs the 3D pipeline (Local fallback / legacy core integration).
        """
        import shutil

        job_id = self.db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type=mode,
            design_type="3D",
            output_format="STL",
            text_prompt=prompt
        )
        start_time = datetime.now()

        try:
            if params is None:
                params = {}
            h = float(params.get('height', 50.0))
            w = float(params.get('width', 100.0))
            l = float(params.get('length', 100.0))

            if mode == "Text3D":
                from app.core.three_d.text_to_3d import gen_by_text_3d
                source_file = gen_by_text_3d(prompt, h, w, l)
            elif mode == "Image3D":
                from app.core.three_d.upload_image import upload_image_3d
                source_file = upload_image_3d(image_path, h, w, l)
            else:  # Edit3D
                from app.core.three_d.edit_3d import edit_file_3d
                source_file = edit_file_3d(image_path, prompt)

            input_path_for_naming = image_path if mode == "Edit3D" else None
            dest_path = self._generate_output_path(
                prompt,
                os.path.splitext(source_file)[1].lstrip(".") or "stl",
                output_dir,
                input_file_path=input_path_for_naming,
            )
            if os.path.abspath(source_file) != os.path.abspath(dest_path):
                shutil.copy2(source_file, dest_path)
            output_file = dest_path

            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            out_file_id = self.db.log_output_file(job_id, os.path.basename(output_file), output_file, "STL")
            self.db.update_job_status(job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration)
            return output_file

        except Exception as e:
            print(f"3D Pipeline Error: {e}")
            self.db.update_job_status(job_id, "FAILED")
            return None

    def text_to_2d(self, user_prompt: str, params: dict = None, user_id: str = "default_user", project_id: str = None) -> str:
        return self.run_2d_pipeline(user_id=user_id, project_id=project_id, mode="Prompt", prompt=user_prompt, params=params)

    def image_to_2d(self, image_path: str, user_prompt: str = None, params: dict = None, user_id: str = "default_user", project_id: str = None) -> str:
        return self.run_2d_pipeline(user_id=user_id, project_id=project_id, mode="Image", prompt=user_prompt or "Vectorize Image", image_path=image_path, params=params)

    def text_to_3d(self, user_prompt: str, desired_dims: dict = None, user_id: str = "default_user", project_id: str = None) -> str:
        params = desired_dims or {}
        return self.run_3d_pipeline(user_id=user_id, project_id=project_id, mode="Text3D", prompt=user_prompt, params=params)

    def image_to_3d(self, image_path: str, desired_dims: dict = None, user_id: str = "default_user", project_id: str = None) -> str:
        params = desired_dims or {}
        return self.run_3d_pipeline(user_id=user_id, project_id=project_id, mode="Image3D", prompt="Image to 3D", image_path=image_path, params=params)

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
        Pack multiple DXF parts via Nesting Worker microservice.
        """
        if stock_sheets is None:
            stock_sheets = [
                {
                    "name": "Legacy Sheet",
                    "material": "Default",
                    "width": sheet_width if sheet_width is not None else 1200.0,
                    "height": sheet_height if sheet_height is not None else 600.0,
                    "thickness": 1.0,
                    "available_quantity": 1,
                    "unlimited_quantity": True,
                }
            ]
        elif isinstance(stock_sheets, list) and len(stock_sheets) > 0 and not isinstance(stock_sheets[0], dict):
            stock_sheets = [s.__dict__ if hasattr(s, "__dict__") else s for s in stock_sheets]

        job_id = self.db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type="Nest",
            design_type="2D",
            output_format="DXF",
            text_prompt=f"Nest {len(part_paths)} part(s) on stock sheet inventory",
        )

        start_time = datetime.now()
        save_dir = output_dir if output_dir else os.path.join("outputs", "nesting_results", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        os.makedirs(save_dir, exist_ok=True)

        try:
            payload = {
                "part_files_urls": part_paths,
                "stock_sheets": stock_sheets,
                "spacing": spacing,
                "allow_rotate": allow_rotate,
                "nesting_mode": nesting_mode,
                "continue_on_incomplete": continue_on_incomplete
            }
            resp = requests.post(f"{self.backend_url}/api/2d/nest", json=payload, timeout=30)
            resp.raise_for_status()
            remote_job_id = resp.json()["job_id"]

            job_res = self._poll_job_completion(remote_job_id)
            summary_result = job_res.get("result") or {}

            duration = int((datetime.now() - start_time).total_seconds() * 1000)

            first_sheet_path = None
            if summary_result.get("sheets"):
                first_sheet_path = summary_result["sheets"][0].get("dxf_path")
                out_file_id = self.db.log_output_file(
                    job_id, os.path.basename(first_sheet_path), first_sheet_path, "DXF"
                ) if first_sheet_path else None
            else:
                out_file_id = None

            self.db.update_job_status(
                job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration
            )
            return summary_result

        except Exception as e:
            print(f"Nesting Error: {e}")
            self.db.update_job_status(job_id, "FAILED")
            raise

    def _generate_output_path(self, prompt, ext, output_dir=None, input_file_path=None):
        save_dir = output_dir if output_dir else "outputs"
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
