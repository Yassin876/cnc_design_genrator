import os
import sys
import subprocess
import glob
import shutil
from core import gemini_service

def run_unified_2d_pipeline(image_path: str, output_path: str, prompt: str, params: dict = None) -> str:
    """
    Orchestrates the 2D pipeline:
    1. Classify image with Gemini (CAD vs REGULAR).
    2. Route to correct pipeline:
       - CAD     → Image2CAD-master
       - REGULAR → reglar_image2cad
    """
    if params is None:
        params = {}
        
    api_key = params.get("gemini_key") or os.environ.get("GEMINI_API_KEY", "")
    
    # 1. Classification
    img_type = gemini_service.classify_image(image_path, api_key=api_key)
    print(f"DEBUG: Gemini classified image as: {img_type}")
    
    if img_type == "CAD":
        print("🚀 Routing to Image2CAD pipeline...")
        return _run_image2cad(image_path, output_path)
    else:
        print("🚀 Routing to reglar_image2cad pipeline...")
        return _run_regular_image2cad(image_path, output_path, prompt, params)

def _run_image2cad(image_path: str, output_path: str) -> str:
    # Resolve absolute paths
    image_path = os.path.abspath(image_path)
    output_path = os.path.abspath(output_path)
    
    # Script location
    script_path = os.path.abspath(os.path.join(
        "Image2CAD-master", "Image2CAD-master", "Image2CAD", "Image2CAD_Headless.py"
    ))
    
    # Image2CAD runs in os.path.dirname(image_path) and creates Output/
    image_dir = os.path.dirname(image_path)
    folder_name = os.path.splitext(os.path.basename(image_path))[0]
    
    # Prepare environment with UTF-8 encoding
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    python_exe = sys.executable
    print(f"Running Subprocess: {python_exe} {script_path} {image_path}")
    try:
        # Run process
        result = subprocess.run(
            [python_exe, script_path, image_path],
            cwd=image_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            check=True
        )
        print("Image2CAD execution finished successfully.")
        
        # Locate the output file we need to find in Output/<folder_name>/<timestamp>/<folder_name>.dxf
        output_glob = os.path.join(image_dir, "Output", folder_name, "*", f"{folder_name}.dxf")
        dxf_files = glob.glob(output_glob)
        
        if dxf_files:
            # Get the most recently created file (in case of multiple timestamps)
            latest_dxf = max(dxf_files, key=os.path.getctime)
            print(f"Found generated DXF: {latest_dxf}")
            
            # Copy to target destination
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(latest_dxf, output_path)
            print(f"Copied DXF to: {output_path}")
            return output_path
        else:
            print(f"Error: Could not find generated DXF at glob: {output_glob}")
            print(f"Subprocess stdout: {result.stdout}")
            print(f"Subprocess stderr: {result.stderr}")
            raise FileNotFoundError("Image2CAD produced no DXF output.")
            
    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed with code {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise e

def _run_regular_image2cad(image_path: str, output_path: str, prompt: str, params: dict = None) -> str:
    """
    Routes REGULAR (non-CAD) images to the reglar_image2cad pipeline 
    which uses SAM segmentation + vectorization.
    """
    if params is None:
        params = {}
        
    image_path = os.path.abspath(image_path)
    output_path = os.path.abspath(output_path)
    
    # Entry point: reglar_image2cad/scripts/run_pipeline.py
    script_path = os.path.abspath(os.path.join(
        "reglar_image2cad", "scripts", "run_pipeline.py"
    ))
    script_cwd = os.path.abspath("reglar_image2cad")
    
    python_exe = sys.executable
    cmd = [
        python_exe, script_path,
        "--input", image_path,
        "--output", output_path,
    ]
    
    if prompt:
        cmd.extend(["--prompt", prompt])
    
    part_width = params.get("part_width_mm", 0.0)
    part_height = params.get("part_height_mm", 0.0)
    tool_diameter = params.get("tool_diameter_mm", 0.0)
    
    if part_width > 0:
        cmd.extend(["--part-width-mm", str(part_width)])
    if part_height > 0:
        cmd.extend(["--part-height-mm", str(part_height)])
    if tool_diameter > 0:
        cmd.extend(["--tool-diameter-mm", str(tool_diameter)])
        
    # Prepare environment with UTF-8 encoding
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
        
    print(f"Running Subprocess: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=script_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            check=True
        )
        print("reglar_image2cad execution finished successfully.")
        print(result.stdout)
        
        if os.path.exists(output_path):
            print(f"DXF created at: {output_path}")
            return output_path
        else:
            print("Error: Output path does not exist despite success exit code.")
            print(f"Subprocess stdout: {result.stdout}")
            raise FileNotFoundError("reglar_image2cad produced no output.")
            
    except subprocess.CalledProcessError as e:
        print(f"Subprocess failed with code {e.returncode}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        raise e
