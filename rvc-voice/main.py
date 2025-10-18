import os
import subprocess
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

app = FastAPI()

# Folder to save converted voices
CONVERTED_DIR = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-server\rvc-voice\converted-voice"
os.makedirs(CONVERTED_DIR, exist_ok=True)

# RVC CLI Python environment
PYTHON_PATH = r"C:\Users\dipan\AppData\Local\Programs\Python\Python313\python.exe"

# RVC CLI script location
RVC_CLI_PATH = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-cli\rvc_cli.py"

# Model and index paths
MODEL_PATH = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-cli\logs\third_model\third_model_exported.pth"
INDEX_PATH = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-cli\logs\third_model\third_model.index"

def generate_unique_filename(original_name: str):
    """Generate a unique filename using UUID"""
    ext = os.path.splitext(original_name)[1]
    unique_name = f"vocals_converted_{uuid.uuid4().hex}{ext}"
    return os.path.join(CONVERTED_DIR, unique_name)

@app.post("/convert-voice")
async def convert_voice(file: UploadFile = File(...), pitch: int = Form(...)):
    # Generate unique output filename
    output_file = generate_unique_filename(file.filename)

    # Save the uploaded file temporarily inside the rvc-cli cwd (required by the CLI)
    temp_input_file = os.path.join(os.path.dirname(RVC_CLI_PATH), f"temp_{uuid.uuid4().hex}.wav")
    with open(temp_input_file, "wb") as f:
        f.write(await file.read())

    cmd = [
        PYTHON_PATH,
        RVC_CLI_PATH,
        "infer",
        "--pitch", str(pitch),
        "--input_path", temp_input_file,
        "--output_path", output_file,
        "--pth_path", MODEL_PATH,
        "--index_path", INDEX_PATH
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True,
                                cwd=os.path.dirname(RVC_CLI_PATH))
        # Remove temporary input file after conversion
        os.remove(temp_input_file)

        return JSONResponse({
            "status": "success",
            "output_file": output_file,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.CalledProcessError as e:
        # Clean up temp file in case of error
        if os.path.exists(temp_input_file):
            os.remove(temp_input_file)
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr
        }, status_code=500)