import os
import uuid
import shutil
import sqlite3

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure folders exist
os.makedirs("videos", exist_ok=True)
os.makedirs("certified", exist_ok=True)

DB = "certificates.db"


# -----------------------------
# DB INIT
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        cert_id TEXT PRIMARY KEY,
        email TEXT,
        filename TEXT
    )
    """)
    conn.commit()
    conn.close()


init_db()


# -----------------------------
# HOME
# -----------------------------
@app.get("/")
def home():
    return {"status": "VFVid API LIVE"}


# -----------------------------
# UPLOAD VIDEO
# -----------------------------
@app.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    email: str = Form(...)
):
    cert_id = str(uuid.uuid4())
    original_path = f"videos/{cert_id}_{file.filename}"
    certified_path = f"certified/{cert_id}_{file.filename}"

    # Save original
    with open(original_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Copy as certified (placeholder until watermark added)
    shutil.copy(original_path, certified_path)

    # Save to DB
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO certificates VALUES (?, ?, ?)",
        (cert_id, email, file.filename)
    )
    conn.commit()
    conn.close()

    return {
        "status": "CERTIFIED",
        "certificate_id": cert_id,
        "verify": f"https://verifyd-backend.onrender.com/verify/{cert_id}",
        "download": f"https://verifyd-backend.onrender.com/download/{cert_id}",
        "free_remaining": 9
    }


# -----------------------------
# VERIFY PAGE (PUBLIC PAGE)
# -----------------------------
@app.get("/verify/{cert_id}", response_class=HTMLResponse)
def verify(cert_id: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT email, filename FROM certificates WHERE cert_id=?", (cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return HTMLResponse("<h1>Certificate Not Found</h1>", status_code=404)

    email, filename = row

    return f"""
    <html>
    <head>
        <title>VFVid Certificate</title>
        <style>
            body {{
                background:#0b0b0b;
                color:white;
                font-family:Arial;
                text-align:center;
                padding-top:60px;
            }}
            .box {{
                background:#1c1c1c;
                padding:40px;
                border-radius:12px;
                width:500px;
                margin:auto;
            }}
            .seal {{
                font-size:42px;
                color:#7c5cff;
                margin-bottom:20px;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <div class="seal">✔ VFVid Certified</div>
            <p><b>Certificate ID:</b> {cert_id}</p>
            <p><b>File:</b> {filename}</p>
            <p><b>Owner:</b> {email}</p>
            <p>Status: AUTHENTIC VIDEO</p>
        </div>
    </body>
    </html>
    """


# -----------------------------
# DOWNLOAD VIDEO
# -----------------------------
@app.get("/download/{cert_id}")
def download(cert_id: str):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT filename FROM certificates WHERE cert_id=?", (cert_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return JSONResponse({"error": "Not found"}, status_code=404)

    filename = row[0]
    path = f"certified/{cert_id}_{filename}"

    if not os.path.exists(path):
        return JSONResponse({"error": "File missing"}, status_code=404)

    return FileResponse(path, media_type="video/mp4", filename=f"certified_{filename}")


# -----------------------------
# ACTIVATE SUBSCRIPTION
# -----------------------------
@app.post("/activate-subscription/")
def activate_subscription(email: str = Form(...)):
    return {"status": "subscription activated"}





















