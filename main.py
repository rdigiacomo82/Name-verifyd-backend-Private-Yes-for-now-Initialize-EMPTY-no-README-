from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import hashlib
import os
import uuid
import subprocess
import sqlite3
from datetime import datetime

app = FastAPI(title="VeriFYD API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_DIR = os.path.join(BASE_DIR, "videos")
CERTIFIED_DIR = os.path.join(BASE_DIR, "certified")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DB_FILE = os.path.join(BASE_DIR, "certificates.db")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CERTIFIED_DIR, exist_ok=True)

FFMPEG_PATH = "ffmpeg"   # ← Render-safe

# =====================================================
# DB
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id TEXT PRIMARY KEY,
        filename TEXT,
        fingerprint TEXT,
        certified_file TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =====================================================
# HASH
# =====================================================
def fingerprint(path):
    sha = hashlib.sha256()
    with open(path,"rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

# =====================================================
# VIDEO STAMP
# =====================================================
def stamp_video(input_path, output_path, cert_id):

    logo_path = os.path.join(ASSETS_DIR, "logo.png")

    command = [
        FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-i", logo_path,
        "-filter_complex",
        "overlay=W-w-20:H-h-20,"
        "drawtext=text='VeriFYD Certified':fontsize=28:fontcolor=white:x=20:y=H-th-20",
        "-metadata", f"cert_id={cert_id}",
        "-c:v","libx264",
        "-preset","fast",
        "-crf","23",
        "-c:a","aac",
        output_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        print(result.stderr)
        raise Exception("FFmpeg failed")

# =====================================================
# UPLOAD
# =====================================================
@app.post("/upload/")
async def upload_video(file: UploadFile = File(...)):

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".mp4",".mov",".avi",".m4v"]:
        return {"error":"Invalid format"}

    raw_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")

    with open(raw_path,"wb") as f:
        f.write(await file.read())

    fp = fingerprint(raw_path)
    cert_id = str(uuid.uuid4())
    out_name = f"{cert_id}.mp4"
    out_path = os.path.join(CERTIFIED_DIR, out_name)

    stamp_video(raw_path, out_path, cert_id)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    INSERT INTO certificates VALUES (?,?,?,?,?)
    """,(cert_id,file.filename,fp,out_name,datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

    base = "https://verifyd-backend.onrender.com"

    return {
        "status":"CERTIFIED",
        "certificate_id": cert_id,
        "download": f"{base}/download/{cert_id}",
        "verify": f"{base}/verify/{cert_id}"
    }

# =====================================================
# DOWNLOAD
# =====================================================
@app.get("/download/{cert_id}")
def download(cert_id:str):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT certified_file FROM certificates WHERE id=?",(cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"error":"not found"}

    path = os.path.join(CERTIFIED_DIR, row[0])

    return FileResponse(path, media_type="video/mp4", filename=row[0])

# =====================================================
# VERIFY
# =====================================================
@app.get("/verify/{cert_id}")
def verify(cert_id:str):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM certificates WHERE id=?",(cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"status":"not found"}

    return {
        "status":"verified",
        "certificate_id":row[0],
        "file":row[1],
        "fingerprint":row[2]
    }

@app.get("/")
def home():
    return {"status":"VFVid API LIVE"}


























