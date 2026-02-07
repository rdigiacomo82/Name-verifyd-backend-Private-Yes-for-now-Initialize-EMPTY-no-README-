from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os

app = FastAPI()

# -------------------------------
# CORS (allow your website)
# -------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Simple in-memory storage
# -------------------------------
USERS = {}
CERTS = {}

# -------------------------------
# ROOT ROUTE (fixes Render hang)
# -------------------------------
@app.get("/")
def home():
    return {"status": "VFVID backend running"}

# -------------------------------
# UPLOAD VIDEO
# -------------------------------
@app.post("/upload/")
async def upload_video(
    file: UploadFile = File(...),
    email: str = Form(...)
):
    # create user if not exists
    if email not in USERS:
        USERS[email] = {
            "uploads_used": 0,
            "free_remaining": 10,
            "subscribed": False
        }

    user = USERS[email]

    # check limits
    if not user["subscribed"] and user["free_remaining"] <= 0:
        return JSONResponse(
            status_code=403,
            content={"error": "Free limit reached. Subscribe."}
        )

    # simulate processing
    cert_id = str(uuid.uuid4())

    CERTS[cert_id] = {
        "email": email,
        "status": "CERTIFIED",
        "score": 100
    }

    user["uploads_used"] += 1
    if not user["subscribed"]:
        user["free_remaining"] -= 1

    return {
        "status": "CERTIFIED",
        "score": 100,
        "certificate_id": cert_id,
        "verify": f"https://verifyd-backend.onrender.com/verify/{cert_id}",
        "download": f"https://verifyd-backend.onrender.com/download/{cert_id}",
        "uploads_used": user["uploads_used"],
        "free_remaining": user["free_remaining"]
    }

# -------------------------------
# VERIFY CERT
# -------------------------------
@app.get("/verify/{cert_id}")
def verify(cert_id: str):
    if cert_id not in CERTS:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return CERTS[cert_id]

# -------------------------------
# DOWNLOAD CERT
# -------------------------------
@app.get("/download/{cert_id}")
def download(cert_id: str):
    if cert_id not in CERTS:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return {"download": "certificate.pdf"}

# -------------------------------
# ACTIVATE SUBSCRIPTION
# -------------------------------
@app.post("/activate-subscription/")
def activate_subscription(email: str = Form(...)):
    if email not in USERS:
        USERS[email] = {
            "uploads_used": 0,
            "free_remaining": 0,
            "subscribed": True
        }
    else:
        USERS[email]["subscribed"] = True

    return {"status": "subscription activated"}




















