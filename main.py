from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import hashlib, os, uuid, subprocess, sqlite3
from datetime import datetime

BASE_DIR = r"C:\Users\RDigiacomo2\VeriFYD"

REVIEW_DIR = os.path.join(BASE_DIR, "review")
CERTIFIED_DIR = os.path.join(BASE_DIR, "certified")
DB_FILE = os.path.join(BASE_DIR, "certificates.db")

FFMPEG_PATH = r"C:\Users\RDigiacomo2\VeriFYD\tools\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"

os.makedirs(REVIEW_DIR, exist_ok=True)
os.makedirs(CERTIFIED_DIR, exist_ok=True)

app = FastAPI(title="VeriFYD Video Certification Authority")

# =====================================================
# DATABASE
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id TEXT PRIMARY KEY,
        filename TEXT,
        fingerprint TEXT,
        status TEXT,
        score INTEGER,
        stored_file TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =====================================================
# HASH
# =====================================================
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(8192):
            h.update(b)
    return h.hexdigest()

# =====================================================
# AUTHENTICITY ENGINE (placeholder)
# =====================================================
def authenticity_score(_):
    # replace later with AI detection
    return 100

# =====================================================
# STAMP VIDEO
# =====================================================
def stamp_video(src, dst, cert_id):
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", src,
        "-metadata", f"VeriFYD-CertID={cert_id}",
        "-metadata", "VeriFYD-Status=CertifiedAuthentic",
        "-c:v","libx264","-preset","fast","-crf","23",
        "-c:a","aac","-b:a","128k",
        dst
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise Exception(r.stderr)

# =====================================================
# UPLOAD
# =====================================================
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    cid = str(uuid.uuid4())
    raw = os.path.join(REVIEW_DIR, f"{cid}_{file.filename}")

    with open(raw, "wb") as f:
        f.write(await file.read())

    fingerprint = sha256(raw)
    score = authenticity_score(raw)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # AUTO CERTIFY IF PASS
    if score >= 80:
        certified_name = f"{cid}_VeriFYD.mp4"
        certified_path = os.path.join(CERTIFIED_DIR, certified_name)

        stamp_video(raw, certified_path, cid)

        c.execute("""
            INSERT INTO certificates
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cid,
            file.filename,
            fingerprint,
            "CERTIFIED",
            score,
            certified_name,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return {
            "status": "CERTIFIED",
            "score": score,
            "certificate_id": cid,
            "download": f"http://127.0.0.1:8000/download/{cid}",
            "verify": f"http://127.0.0.1:8000/verify/{cid}"
        }

    # OTHERWISE SEND TO REVIEW
    c.execute("""
        INSERT INTO certificates
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        cid,
        file.filename,
        fingerprint,
        "REVIEW",
        score,
        os.path.basename(raw),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()

    return {
        "status": "UNDER REVIEW",
        "score": score,
        "certificate_id": cid
    }

# =====================================================
# MANUAL APPROVE
# =====================================================
@app.post("/approve/{cert_id}")
def approve(cert_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT stored_file FROM certificates WHERE id=?", (cert_id,))
    row = c.fetchone()

    if not row:
        raise HTTPException(404)

    src = os.path.join(REVIEW_DIR, row[0])
    dst_name = f"{cert_id}_VeriFYD.mp4"
    dst = os.path.join(CERTIFIED_DIR, dst_name)

    stamp_video(src, dst, cert_id)

    c.execute("""
        UPDATE certificates
        SET status='CERTIFIED', stored_file=?
        WHERE id=?
    """, (dst_name, cert_id))

    conn.commit()
    conn.close()

    return {
        "status": "CERTIFIED",
        "download": f"http://127.0.0.1:8000/download/{cert_id}",
        "verify": f"http://127.0.0.1:8000/verify/{cert_id}"
    }

# =====================================================
# VERIFY
# =====================================================
@app.get("/verify/{cert_id}")
def verify(cert_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM certificates WHERE id=?", (cert_id,))
    r = c.fetchone()
    conn.close()

    if not r:
        return {"status":"NOT FOUND"}

    return {
        "certificate_id": r[0],
        "filename": r[1],
        "status": r[3],
        "score": r[4]
    }

# =====================================================
# DOWNLOAD
# =====================================================
@app.get("/download/{cert_id}")
def download(cert_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT stored_file, status FROM certificates WHERE id=?", (cert_id,))
    r = c.fetchone()
    conn.close()

    if not r or r[1] != "CERTIFIED":
        raise HTTPException(403, "Not certified")

    path = os.path.join(CERTIFIED_DIR, r[0])
    return FileResponse(path, media_type="video/mp4", filename=r[0])
















