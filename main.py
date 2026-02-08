import os
import shutil
import uuid
import subprocess
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ---------- CONFIG ----------
BASE_URL = "https://verifyd-backend.onrender.com"

VIDEOS_DIR = "videos"
CERT_DIR = "certified"
ASSETS_DIR = "assets"
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)

# email usage tracker
usage_db = {}

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- HOME ----------
@app.get("/")
def home():
    return {"status": "VFVid API LIVE"}

# ---------- UPLOAD ----------
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...), email: str = Form(...)):
    cert_id = str(uuid.uuid4())
    input_path = os.path.join(VIDEOS_DIR, f"{cert_id}_{file.filename}")
    output_path = os.path.join(CERT_DIR, f"{cert_id}.mp4")

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ---------- OVERLAY LOGO ----------
    if os.path.exists(LOGO_PATH):
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-i", LOGO_PATH,
            "-filter_complex", "overlay=W-w-20:H-h-20",
            "-codec:a", "copy",
            output_path
        ]
    else:
        shutil.copy(input_path, output_path)
        cmd = None

    if cmd:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---------- USAGE TRACKING ----------
    if email not in usage_db:
        usage_db[email] = 0
    usage_db[email] += 1

    used = usage_db[email]
    free_remaining = max(0, 10 - used)

    return {
        "status": "CERTIFIED",
        "certificate_id": cert_id,
        "verify": f"{BASE_URL}/verify/{cert_id}",
        "download": f"{BASE_URL}/download/{cert_id}",
        "uploads_used": used,
        "free_remaining": free_remaining
    }

# ---------- DOWNLOAD ----------
@app.get("/download/{cert_id}")
def download(cert_id: str):
    path = os.path.join(CERT_DIR, f"{cert_id}.mp4")

    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(path, media_type="video/mp4", filename=f"{cert_id}.mp4")

# ---------- VERIFY ----------
@app.get("/verify/{cert_id}")
def verify(cert_id: str):
    path = os.path.join(CERT_DIR, f"{cert_id}.mp4")

    if not os.path.exists(path):
        return {"status": "not found"}

    return {
        "status": "verified",
        "certificate_id": cert_id
    }























