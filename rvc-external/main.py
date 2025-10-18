import os
import shutil
import httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

app = FastAPI()

# Orchestrator folders
BASE_DIR = r"D:\ZT 130825\Pogramme Files\website\portfolio\spotify Clone\sound remixing\rvc-server\rvc-external"
FINAL_VOICE_DIR = os.path.join(BASE_DIR, "final-voice")
os.makedirs(FINAL_VOICE_DIR, exist_ok=True)

TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Internal API URLs
DEMUSCS_URL = "http://127.0.0.1:8001/separate-vocals"
VOICE_URL = "http://127.0.0.1:8002/convert-voice"
MIX_URL = "http://127.0.0.1:8003/mix-audio"

MAX_TIMEOUT = 300.0  # 5 minutes per internal API call

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...), pitch: int = Form(...)):
    try:
        # Save user upload to temp
        user_file_path = os.path.join(TEMP_DIR, file.filename)
        with open(user_file_path, "wb") as f:
            f.write(await file.read())

        # Step 1: Demucs separation
        async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
            with open(user_file_path, "rb") as f:
                demucs_resp = await client.post(
                    DEMUSCS_URL,
                    files={"file": (file.filename, f)}
                )
        demucs_data = demucs_resp.json()
        if demucs_data.get("status") != "success":
            raise Exception(f"Demucs failed: {demucs_data}")

        # Step 2: Voice conversion
        vocals_path = demucs_data["vocals"]
        instrumental_path = demucs_data["instrumental"]

        # Upload vocals to voice API
        async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
            with open(vocals_path, "rb") as f:
                voice_resp = await client.post(
                    VOICE_URL,
                    files={"file": (os.path.basename(vocals_path), f)},
                    data={"pitch": str(pitch)}
                )
        voice_data = voice_resp.json()
        if voice_data.get("status") != "success":
            raise Exception(f"Voice conversion failed: {voice_data}")

        converted_vocals_path = voice_data["output_file"]

        # Step 3: Mixing
        async with httpx.AsyncClient(timeout=MAX_TIMEOUT) as client:
            with open(converted_vocals_path, "rb") as f_voc:
                with open(instrumental_path, "rb") as f_inst:
                    mix_resp = await client.post(
                        MIX_URL,
                        files={
                            "instrument_file": (os.path.basename(instrumental_path), f_inst),
                            "vocal_file": (os.path.basename(converted_vocals_path), f_voc)
                        }
                    )
        mix_data = mix_resp.json()
        if mix_data.get("status") != "success":
            raise Exception(f"Mixing failed: {mix_data}")

        final_file = mix_data["output_file"]

        # Move final output to final-voice folder
        final_filename = f"final_{os.path.basename(final_file)}"
        final_path = os.path.join(FINAL_VOICE_DIR, final_filename)
        shutil.move(final_file, final_path)

        # Cleanup temp files and Demucs/voice intermediate files
        for path in [user_file_path, vocals_path, instrumental_path, converted_vocals_path, final_file]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        return JSONResponse({
            "status": "success",
            "output_file": final_path
        })

    except Exception as e:
        # Cleanup temp folder if anything left
        for f_name in os.listdir(TEMP_DIR):
            f_path = os.path.join(TEMP_DIR, f_name)
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except Exception:
                    pass

        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)
