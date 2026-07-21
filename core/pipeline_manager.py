import os
from datetime import datetime
from core.ai_generator import AIGenerator
from core.database import DatabaseManager

class PipelineManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.ai_gen = None
        self._models_loaded = False

    def _ensure_models_loaded(self):
        if not self._models_loaded:
            self._init_models()
            self._models_loaded = True

    def _init_models(self):
        print("--- Initializing AI Models ---")
        try:
            self.ai_gen = AIGenerator()
        except Exception as e:
            print(f"Error initializing models: {e}")

    def run_2d_pipeline(self, user_id, project_id, mode, prompt, image_path=None, params=None, output_dir=None):
        """
        Runs the 2D pipeline (Image, Prompt, or Edit).
        output_dir: the workspace folder chosen by the user. Falls back to 'outputs/' if None.
        """
        self._ensure_models_loaded()
        # 1. Log Job
        job_id = self.db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type=mode,
            design_type="2D",
            output_format="DXF",
            text_prompt=prompt,
            input_file_id=None # Could log input file here if path provided
        )
        
        start_time = datetime.now()
        output_dxf = self._generate_output_path(prompt, "dxf", output_dir)

        try:
            if mode == "Edit":
                from core.dxf_editor import dxf_to_json, apply_edits
                
                print("📐 Parsing DXF file structure...")
                dxf_json = dxf_to_json(image_path)
                
                print("🤖 Consulting Gemini for structured edits...")
                edits = self.ai_gen.generate_structured_edits(dxf_json, prompt)
                
                print(f"✏️  Applying: {len(edits.get('delete', []))} deletions, {len(edits.get('resize_circles', []))} circle resizes...")
                apply_edits(image_path, edits, output_dxf)
            
            elif mode == "Prompt":
                import tempfile
                from core.unified_pipeline import run_unified_2d_pipeline
                
                print(f"🔍 Identifying main object from: '{prompt}'")
                detect_prompt = self.ai_gen.extract_main_object(prompt)
                print(f"🎨 Generating silhouette for: '{prompt}'")
                image = self.ai_gen.generate_image(prompt)
                
                # Save generated image to a temp file so unified_pipeline can process it
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_image_path = tmp.name
                image.save(tmp_image_path)
                print(f"💾 Saved generated image to temp: {tmp_image_path}")
                
                # Ensure params has gemini_key
                if params is None:
                    params = {}
                if "gemini_key" not in params:
                    params["gemini_key"] = os.environ.get("GEMINI_API_KEY", "")
                
                try:
                    run_unified_2d_pipeline(
                        image_path=tmp_image_path,
                        output_path=output_dxf,
                        prompt=detect_prompt,
                        params=params
                    )
                finally:
                    # Clean up temp file
                    try:
                        os.remove(tmp_image_path)
                    except Exception:
                        pass
            
            else: # mode == "Image"
                print(f"📸 Running unified 2D pipeline on image: '{image_path}'")
                from core.unified_pipeline import run_unified_2d_pipeline
                
                # Ensure params dict has gemini_key
                if params is None:
                    params = {}
                if "gemini_key" not in params:
                    params["gemini_key"] = os.environ.get("GEMINI_API_KEY", "")
                
                run_unified_2d_pipeline(
                    image_path=image_path,
                    output_path=output_dxf,
                    prompt=prompt or "object",
                    params=params
                )

            # 2. Log Success
            duration = int((datetime.now() - start_time).total_seconds() * 1000)
            out_file_id = self.db.log_output_file(job_id, os.path.basename(output_dxf), output_dxf, "DXF")
            self.db.update_job_status(job_id, "COMPLETED", output_file_id=out_file_id, processing_time_ms=duration)
            return output_dxf

        except Exception as e:
            print(f"2D Pipeline Error: {e}")
            self.db.update_job_status(job_id, "FAILED")
            return None

    def run_3d_pipeline(self, user_id, project_id, mode, prompt, image_path=None, params=None, output_dir=None):
        """
        Runs the 3D pipeline.
        output_dir: the workspace folder chosen by the user. Falls back to 'outputs/' if None.
        """
        self._ensure_models_loaded()
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
            if mode == "Text3D":
                from core.three_d.text_to_3d import gen_by_text_3d
                source_file = gen_by_text_3d(prompt, params['height'], params['width'], params['length'])
            elif mode == "Image3D":
                from core.three_d.upload_image import upload_image_3d
                source_file = upload_image_3d(image_path, params['height'], params['width'], params['length'])
            else: # Edit3D
                from core.three_d.edit_3d import edit_file_3d
                source_file = edit_file_3d(image_path, prompt)

            # Copy the generated file to the user workspace (or outputs/ fallback)
            dest_path = self._generate_output_path(prompt, os.path.splitext(source_file)[1].lstrip(".") or "stl", output_dir)
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


    def _generate_output_path(self, prompt, ext, output_dir=None):
        # Use the user-selected workspace folder, or fall back to 'outputs/'
        save_dir = output_dir if output_dir else "outputs"
        os.makedirs(save_dir, exist_ok=True)
        base = "".join([c if c.isalnum() else "_" for c in prompt[:20]]).strip("_") or "output"
        return os.path.join(save_dir, f"{base}_{datetime.now().strftime('%H%M%S')}.{ext}")
