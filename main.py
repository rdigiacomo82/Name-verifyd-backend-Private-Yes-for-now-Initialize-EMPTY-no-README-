from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
import shutil
import uuid
import os
import sqlite3

app = FastAPI()

# ==============================
# DATABASE SETUP
# ==============================

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    uploads INTEGER DEFAULT 0,
    subscribed INTEGER DEFAULT 0
)
""")
conn.commit()

# ==============================
# HEALTH CHECK
# ==============================

@app.get("/")
def home():
    return {"status": "VeriFYD API LIVE"}

# ==============================
# UPLOAD + CERTIFY VIDEO
# ==============================

@app.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    email: str = Form(...)
):

    # --------------------------
    # CHECK USER IN DATABASE
    # --------------------------
    cursor.execute("SELECT uploads, subscribed FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if user:
        uploads, subscribed = user
    else:
        uploads = 0
        subscribed = 0
        cursor.execute(
            "INSERT INTO users (email, uploads, subscribed) VALUES (?,0,0)",
            (email,)
        )
        conn.commit()

    # --------------------------
    # FREE LIMIT CHECK
    # --------------------------
    if uploads >= 10 and subscribed == 0:
        return {
            "status": "PAYMENT_REQUIRED",
            "message": "Free limit reached. Please subscribe at VFVid.com"
        }

    # --------------------------
    # SAVE VIDEO LOCALLY
    # --------------------------
    cert_id = str(uuid.uuid4())

    os.makedirs("videos", exist_ok=True)
    os.makedirs("certified", exist_ok=True)

    video_path = f"videos/{cert_id}_{file.filename}"

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # --------------------------
    # SIMULATED CERTIFICATION
    # (your AI check goes here later)
    # --------------------------
    score = 100
    status = "CERTIFIED"

    certified_path = f"certified/{cert_id}_{file.filename}"
    shutil.copy(video_path, certified_path)

    # --------------------------
    # UPDATE UPLOAD COUNT
    # --------------------------
    cursor.execute(
        "UPDATE users SET uploads = uploads + 1 WHERE email=?",
        (email,)
    )
    conn.commit()

    # --------------------------
    # RESPONSE
    # --------------------------
    return {
        "status": status,
        "score": score,
        "certificate_id": cert_id,
        "verify": f"https://verifyd-backend.onrender.com/verify/{cert_id}",
        "download": f"https://verifyd-backend.onrender.com/download/{cert_id}",
        "uploads_used": uploads + 1,
        "free_remaining": max(0, 10 - (uploads + 1))
    }

# ==============================
# VERIFY ENDPOINT
# ==============================

@app.get("/verify/{cert_id}")
def verify(cert_id: str):
    return {
        "certificate_id": cert_id,
        "status": "VALID",
        "issuer": "VeriFYD"
    }

# ==============================
# DOWNLOAD ENDPOINT
# ==============================

@app.get("/download/{cert_id}")
def download(cert_id: str):
    folder = "certified"

    for filename in os.listdir(folder):
        if filename.startswith(cert_id):
            path = os.path.join(folder, filename)
            return FileResponse(path)

    return {"error": "file not found"}

# ==============================
# ADMIN: ACTIVATE SUBSCRIPTION
# (PayPal webhook will call this later)
# ==============================

@app.post("/activate-subscription/")
def activate(email: str = Form(...)):
    cursor.execute(
        "UPDATE users SET subscribed = 1 WHERE email=?",
        (email,)
    )
    conn.commit()

    return {"status": "subscription activated"}


















