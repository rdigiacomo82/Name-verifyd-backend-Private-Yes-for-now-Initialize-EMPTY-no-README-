from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
import os
import subprocess

app = FastAPI()

# Allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist (Render resets disk)
os.makedirs("videos", exist_ok=True)
os.makedirs("certified", exist_ok=True)
os.makedirs("review", exist_ok=True)
os.makedirs("assets", exist_ok=True)

LOGO_PATH = "assets/logo.png"


@app.get("/")
def root():
    return {"status": "VFVid API LIVE"}


# ---------------- UPLOAD ----------------
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):
    try:
        cert_id = str(uuid.uuid4())

        input_path = f"videos/{cert_id}_{file.filename}"
        output_path = f"certified/certified_{cert_id}.mp4"

        # Save upload
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # FFmpeg overlay command
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-i", LOGO_PATH,
            "-filter_complex", "overlay=W-w-20:H-h-20",
            "-codec:a", "copy",
            output_path
        ]

        subprocess.run(cmd, check=True)

        return {
            "certificate_id": cert_id,
            "download": f"/download/{cert_id}"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------- DOWNLOAD ----------------
@app.get("/download/{cert_id}")
def download_video(cert_id: str):
    path = f"certified/certified_{cert_id}.mp4"

    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4", filename="certified_video.mp4")

    return JSONResponse(status_code=404, content={"detail": "Not found"})

























