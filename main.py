from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import os
import uuid
import sqlite3
import shutil

app = FastAPI()

# ===============================
# CORS (ALLOW WEBSITE ACCESS)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vfvid.com",
        "https://www.vfvid.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# FOLDERS
# ===============================
UPLOAD_DIR = "videos"
CERT_DIR = "certified"
REVIEW_DIR = "review"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)
os.makedirs(REVIEW_DIR, exist_ok=True)

DB_FILE = "vfvid.db"

# ===============================
# DATABASE
# ===============================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        uploads_used INTEGER DEFAULT 0,
        subscribed INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id TEXT PRIMARY KEY,
        email TEXT,
        filename TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ===============================
# HASH
# ===============================
def fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

# ===============================
# UPLOAD
# ===============================
@app.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    email: str = Form(...)
):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # create user if not exists
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()

    if not user:
        c.execute("INSERT INTO users (email, uploads_used, subscribed) VALUES (?,0,0)", (email,))
        conn.commit()
        uploads_used = 0
        subscribed = 0
    else:
        uploads_used = user[1]
        subscribed = user[2]

    # free tier check
    if uploads_used >= 10 and subscribed == 0:
        conn.close()
        return {"error": "Free limit reached. Please subscribe."}

    # save video
    cert_id = str(uuid.uuid4())
    filename = f"{cert_id}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # fake AI score (for now)
    score = 100

    if score >= 80:
        status = "CERTIFIED"
        dest = os.path.join(CERT_DIR, filename)
    else:
        status = "UNDER REVIEW"
        dest = os.path.join(REVIEW_DIR, filename)

    shutil.copy(save_path, dest)

    # update DB
    c.execute("INSERT INTO certificates VALUES (?,?,?,?)",
              (cert_id, email, filename, status))

    c.execute("UPDATE users SET uploads_used = uploads_used + 1 WHERE email=?", (email,))
    conn.commit()
    conn.close()

    return {
        "status": status,
        "score": score,
        "certificate_id": cert_id,
        "verify": f"https://verifyd-backend.onrender.com/verify/{cert_id}",
        "download": f"https://verifyd-backend.onrender.com/download/{cert_id}",
        "uploads_used": uploads_used + 1,
        "free_remaining": max(0, 10 - (uploads_used + 1))
    }

# ===============================
# VERIFY
# ===============================
@app.get("/verify/{cert_id}")
def verify(cert_id: str):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT status FROM certificates WHERE id=?", (cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"error": "not found"}

    return {"certificate_id": cert_id, "status": row[0]}

# ===============================
# DOWNLOAD
# ===============================
@app.get("/download/{cert_id}")
def download(cert_id: str):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT filename,status FROM certificates WHERE id=?", (cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"error": "not found"}

    filename, status = row

    if status != "CERTIFIED":
        return {"error": "Not certified"}

    path = os.path.join(CERT_DIR, filename)

    return FileResponse(path, media_type="video/mp4", filename=filename)

# ===============================
# SUBSCRIPTION ACTIVATE
# ===============================
@app.post("/activate-subscription/")
def activate(email: str = Form(...)):

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("UPDATE users SET subscribed=1 WHERE email=?", (email,))
    conn.commit()
    conn.close()

    return {"status": "subscription activated"}

# ===============================
# HOME
# ===============================
@app.get("/")
def home():
    return {"VFVID": "Backend running"}



















