import os
import subprocess
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

app = FastAPI()

# Base mixing folder
MIXING_DIR = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-server\rvc-mixing"
os.makedirs(MIXING_DIR, exist_ok=True)

# Final output folder
FINAL_VOICE_DIR = os.path.join(MIXING_DIR, "final-voice")
os.makedirs(FINAL_VOICE_DIR, exist_ok=True)

MIX_CLI_PATH = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-cli\mix_audio.py"

def get_next_filename(folder, prefix="MARGED", extension=".wav"):
    """Generate a unique filename like MARGED_1.wav, MARGED_2.wav, etc."""
    existing_files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(extension)]
    numbers = [int(f.replace(prefix + "_", "").replace(extension, "")) for f in existing_files if f.replace(prefix + "_", "").replace(extension, "").isdigit()]
    next_number = max(numbers) + 1 if numbers else 1
    return os.path.join(folder, f"{prefix}_{next_number}{extension}")

@app.post("/mix-audio")
async def mix_audio(
    instrument_file: UploadFile = File(...),
    vocal_file: UploadFile = File(...)
):
    # Save uploaded files temporarily
    instrument_path = os.path.join(MIXING_DIR, instrument_file.filename)
    vocal_path = os.path.join(MIXING_DIR, vocal_file.filename)
    with open(instrument_path, "wb") as f:
        f.write(await instrument_file.read())
    with open(vocal_path, "wb") as f:
        f.write(await vocal_file.read())

    # Generate unique output file
    output_file = get_next_filename(FINAL_VOICE_DIR)

    cmd = [
        "python",
        MIX_CLI_PATH,
        "--input-instrument", instrument_path,
        "--input-vocal", vocal_path,
        "--output-audio", output_file
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        # Optionally, delete input files after mixing to save space
        os.remove(instrument_path)
        os.remove(vocal_path)
        return JSONResponse({
            "status": "success",
            "output_file": output_file,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except subprocess.CalledProcessError as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "stdout": e.stdout,
            "stderr": e.stderr
        }, status_code=500)