# -*- coding: utf-8 -*-
# app.py — NexusMemoir (Production Ready)
# - Session-based ownership
# - Cloudflare R2 (S3 compatible) media storage
# - SQLite DB
# - QR Code generation
# - Multiple landing pages

import os
import re
import hashlib
import secrets
import sqlite3
import io
import base64
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import traceback

from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

import qrcode
from qrcode.image.svg import SvgPathImage

from fastapi import FastAPI, Request, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


# -------------------------
# Config
# -------------------------
MAX_NOTES = 5
MAX_PHOTOS = 10
MAX_VIDEOS = 1

MAX_PHOTO_BYTES = 10 * 1024 * 1024   # 10MB
MAX_VIDEO_BYTES = 80 * 1024 * 1024   # 80MB

ALLOWED_PHOTO = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO = {"video/mp4", "video/webm", "video/quicktime"}

TZ_TR = ZoneInfo("Europe/Istanbul")


def env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


SECRET_KEY = env_required("SECRET_KEY")
ADMIN_PASSWORD = env_required("ADMIN_PASSWORD")

R2_ENDPOINT = env_required("R2_ENDPOINT")
R2_ACCESS_KEY_ID = env_required("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env_required("R2_SECRET_ACCESS_KEY")
R2_BUCKET = env_required("R2_BUCKET")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "db.sqlite3"))


# -------------------------
# App
# -------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# -------------------------
# DB helpers
# -------------------------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(dt_str: str):
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def is_open(unlock_at: str | None) -> bool:
    dt = parse_iso(unlock_at)
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= dt


def require_capsule_id(request: Request) -> int | None:
    return request.session.get("capsule_id")


def safe_filename(name: str) -> str:
    name = name or "file"
    name = name.replace("\\", "_").replace("/", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:120]


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        unlock_at TEXT,
        title TEXT,
        lat REAL,
        lng REAL,
        location_name TEXT,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capsule_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(capsule_id) REFERENCES capsules(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capsule_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        r2_key TEXT NOT NULL,
        original_name TEXT,
        content_type TEXT,
        size_bytes INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(capsule_id) REFERENCES capsules(id)
    )
    """)

    con.commit()
    con.close()


@app.on_event("startup")
def on_startup():
    init_db()


# -------------------------
# R2 helpers
# -------------------------
def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


def r2_put_bytes(key: str, data: bytes, content_type: str):
    s3 = r2_client()
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except (EndpointConnectionError, NoCredentialsError, ClientError) as e:
        print("R2 PUT FAILED:", repr(e))
        traceback.print_exc()
        raise


def r2_presigned_get(key: str, expires_sec: int = 600) -> str:
    s3 = r2_client()
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": R2_BUCKET, "Key": key},
        ExpiresIn=expires_sec,
    )


# -------------------------
# QR Code Generation
# -------------------------
def generate_qr_code(data: str) -> str:
    """Generate QR code and return as base64 data URL"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


# -------------------------
# Counting
# -------------------------
def count_notes(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM notes WHERE capsule_id=?", (capsule_id,)).fetchone()["c"]


def count_photos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='photo'", (capsule_id,)).fetchone()["c"]


def count_videos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='video'", (capsule_id,)).fetchone()["c"]


# -------------------------
# Landing Pages
# -------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Main landing page - map version"""
    return templates.TemplateResponse("map-landing.html", {"request": request})


@app.get("/landing", response_class=HTMLResponse)
def landing_standard(request: Request):
    """Standard landing page"""
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/globe", response_class=HTMLResponse)
def landing_globe(request: Request):
    """Globe landing page"""
    return templates.TemplateResponse("globe-landing.html", {"request": request})


# -------------------------
# Create Capsule
# -------------------------
@app.get("/create", response_class=HTMLResponse)
def create_page(request: Request):
    """Create capsule wizard page"""
    return templates.TemplateResponse("create-capsule.html", {"request": request})


@app.post("/api/capsules/create")
async def api_create_capsule(
    request: Request,
    lat: float = Form(...),
    lng: float = Form(...),
    title: str = Form(...),
    unlock_at: str = Form(...),
    location_name: str = Form(default="")
):
    """API endpoint to create a new capsule"""
    try:
        # Generate token and PIN
        token = secrets.token_urlsafe(24)
        pin = f"{secrets.randbelow(10**6):06d}"
        
        # Parse unlock date
        try:
            dt_local_naive = datetime.fromisoformat(unlock_at)
            dt_local = dt_local_naive.replace(tzinfo=TZ_TR)
            dt_utc = dt_local.astimezone(timezone.utc)
            unlock_at_utc = dt_utc.isoformat()
        except Exception as e:
            return JSONResponse({
                "success": False,
                "error": f"Invalid date format: {str(e)}"
            }, status_code=400)
        
        # Create capsule
        con = db()
        cur = con.cursor()
        cur.execute(
            """INSERT INTO capsules(token_hash, pin_hash, unlock_at, title, lat, lng, location_name, created_at) 
               VALUES(?,?,?,?,?,?,?,?)""",
            (sha256(token), sha256(pin), unlock_at_utc, title, lat, lng, location_name, now_utc_iso()),
        )
        con.commit()
        capsule_id = cur.lastrowid
        con.close()
        
        # Generate QR code
        base_url = str(request.base_url).rstrip("/")
        claim_url = f"{base_url}/claim?token={token}"
        qr_code = generate_qr_code(claim_url)
        
        return JSONResponse({
            "success": True,
            "capsule_id": capsule_id,
            "token": token,
            "pin": pin,
            "qr_code": qr_code,
            "claim_url": claim_url
        })
        
    except Exception as e:
        print("Error creating capsule:", str(e))
        traceback.print_exc()
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@app.get("/success", response_class=HTMLResponse)
def success_page(
    request: Request,
    token: str = Query(...),
    pin: str = Query(...),
    qr: str = Query(...)
):
    """Success page after capsule creation"""
    return templates.TemplateResponse("success.html", {
        "request": request,
        "token": token,
        "pin": pin,
        "qr_code": qr,
        "title": "Anı Kapsülü",
        "date": "Yakında"
    })


# -------------------------
# Public API
# -------------------------
@app.get("/api/capsules/public")
def api_public_capsules():
    """Get all public capsules for map display"""
    try:
        con = db()
        cur = con.cursor()
        
        capsules = cur.execute("""
            SELECT id, title, lat, lng, location_name, unlock_at, created_at
            FROM capsules
            WHERE lat IS NOT NULL AND lng IS NOT NULL
            ORDER BY created_at DESC
        """).fetchall()
        
        con.close()
        
        result = []
        for cap in capsules:
            unlock_dt = parse_iso(cap["unlock_at"])
            is_unlocked = is_open(cap["unlock_at"])
            
            # Format city name
            city = cap["location_name"] or "Unknown Location"
            if "," in city:
                city = city.split(",")[0].strip()
            
            result.append({
                "id": cap["id"],
                "title": cap["title"] or "Anı Kapsülü",
                "lat": cap["lat"],
                "lng": cap["lng"],
                "city": city,
                "unlock_at": unlock_dt.strftime("%d %B %Y") if unlock_dt else "Belirsiz",
                "status": "open" if is_unlocked else "locked"
            })
        
        return JSONResponse({
            "success": True,
            "capsules": result,
            "total": len(result)
        })
        
    except Exception as e:
        print("Error fetching public capsules:", str(e))
        traceback.print_exc()
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


# -------------------------
# Auth & Claim
# -------------------------
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/claim", response_class=HTMLResponse)
def claim_page(request: Request, token: str = ""):
    return templates.TemplateResponse("claim.html", {"request": request, "token": token, "error": ""})


@app.post("/claim")
def claim_submit(request: Request, token: str = Form(...), pin: str = Form(...)):
    con = db()
    cur = con.cursor()
    row = cur.execute("SELECT * FROM capsules WHERE token_hash=?", (sha256(token),)).fetchone()
    con.close()

    if (not row) or (row["pin_hash"] != sha256(pin)):
        return templates.TemplateResponse(
            "claim.html",
            {"request": request, "token": token, "error": "Token veya PIN hatalı."},
            status_code=400,
        )

    request.session["capsule_id"] = row["id"]
    return RedirectResponse(url="/dashboard", status_code=303)


# -------------------------
# Dashboard
# -------------------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    con = db()
    cur = con.cursor()

    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    open_flag = is_open(cap["unlock_at"])

    notes = cur.execute(
        "SELECT * FROM notes WHERE capsule_id=? ORDER BY id",
        (capsule_id,),
    ).fetchall()

    photos = cur.execute(
        "SELECT * FROM media WHERE capsule_id=? AND kind='photo' ORDER BY id",
        (capsule_id,),
    ).fetchall()

    video = cur.execute(
        "SELECT * FROM media WHERE capsule_id=? AND kind='video' ORDER BY id",
        (capsule_id,),
    ).fetchone()

    notes_c = count_notes(cur, capsule_id)
    photos_c = count_photos(cur, capsule_id)
    videos_c = count_videos(cur, capsule_id)

    con.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "capsule": cap,
            "open": open_flag,
            "notes": notes,
            "photos": photos,
            "video": video,
            "notes_c": notes_c,
            "photos_c": photos_c,
            "videos_c": videos_c,
            "MAX_NOTES": MAX_NOTES,
            "MAX_PHOTOS": MAX_PHOTOS,
            "MAX_VIDEOS": MAX_VIDEOS,
        },
    )


# -------------------------
# Actions
# -------------------------
@app.post("/set-unlock")
def set_unlock(request: Request, unlock_at: str = Form(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    try:
        dt_local_naive = datetime.fromisoformat(unlock_at)
        dt_local = dt_local_naive.replace(tzinfo=TZ_TR)
        dt_utc = dt_local.astimezone(timezone.utc)
    except Exception:
        return HTMLResponse("Tarih formatı hatalı.", status_code=400)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, zaman değiştirilemez.", status_code=400)

    cur.execute("UPDATE capsules SET unlock_at=? WHERE id=?", (dt_utc.isoformat(), capsule_id))
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/add-note")
def add_note(request: Request, text: str = Form(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    txt = (text or "").strip()
    if not txt:
        return HTMLResponse("Boş metin eklenemez.", status_code=400)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık metin eklenemez.", status_code=400)

    if count_notes(cur, capsule_id) >= MAX_NOTES:
        con.close()
        return HTMLResponse("Metin limiti doldu (5/5).", status_code=400)

    cur.execute(
        "INSERT INTO notes(capsule_id, text, created_at) VALUES(?,?,?)",
        (capsule_id, txt, now_utc_iso()),
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/upload/photo")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    if file.content_type not in ALLOWED_PHOTO:
        return HTMLResponse("Geçersiz foto formatı. (jpg/png/webp)", status_code=400)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık foto yüklenemez.", status_code=400)

    if count_photos(cur, capsule_id) >= MAX_PHOTOS:
        con.close()
        return HTMLResponse("Foto limit doldu (10/10).", status_code=400)

    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        con.close()
        return HTMLResponse("Foto çok büyük (max 10MB).", status_code=400)

    ext = ".jpg"
    if file.content_type == "image/png":
        ext = ".png"
    elif file.content_type == "image/webp":
        ext = ".webp"

    original = safe_filename(file.filename)
    key = f"capsules/{capsule_id}/photos/{secrets.token_urlsafe(16)}{ext}"

    try:
        r2_put_bytes(key=key, data=data, content_type=file.content_type)
    except Exception:
        con.close()
        return HTMLResponse(
            "Storage hatası: R2 upload başarısız.",
            status_code=502,
        )

    cur.execute(
        "INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at) VALUES(?,?,?,?,?,?,?)",
        (capsule_id, "photo", key, original, file.content_type, len(data), now_utc_iso()),
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/upload/video")
async def upload_video(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    if file.content_type not in ALLOWED_VIDEO:
        return HTMLResponse("Geçersiz video formatı. (mp4/webm/mov)", status_code=400)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık video yüklenemez.", status_code=400)

    if count_videos(cur, capsule_id) >= MAX_VIDEOS:
        con.close()
        return HTMLResponse("Video limiti doldu (1/1).", status_code=400)

    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        con.close()
        return HTMLResponse("Video çok büyük (max 80MB).", status_code=400)

    ext = ".mp4"
    if file.content_type == "video/webm":
        ext = ".webm"
    elif file.content_type == "video/quicktime":
        ext = ".mov"

    original = safe_filename(file.filename)
    key = f"capsules/{capsule_id}/videos/{secrets.token_urlsafe(16)}{ext}"

    try:
        r2_put_bytes(key=key, data=data, content_type=file.content_type)
    except Exception:
        con.close()
        return HTMLResponse(
            "Storage hatası: R2 upload başarısız.",
            status_code=502,
        )

    cur.execute(
        "INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at) VALUES(?,?,?,?,?,?,?)",
        (capsule_id, "video", key, original, file.content_type, len(data), now_utc_iso()),
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/m/{media_id}")
def open_media(request: Request, media_id: int):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return HTMLResponse("Yetkisiz.", status_code=403)

    con = db()
    cur = con.cursor()

    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap or (not is_open(cap["unlock_at"])):
        con.close()
        return HTMLResponse("Kilitli.", status_code=403)

    m = cur.execute(
        "SELECT * FROM media WHERE id=? AND capsule_id=?",
        (media_id, capsule_id),
    ).fetchone()
    con.close()

    if not m:
        return HTMLResponse("Bulunamadı.", status_code=404)

    url = r2_presigned_get(m["r2_key"], expires_sec=600)
    return RedirectResponse(url=url, status_code=302)


# -------------------------
# Admin (old endpoint compatibility)
# -------------------------
@app.get("/admin/create", response_class=HTMLResponse)
def admin_create(request: Request, p: str = Query(default="")):
    """Legacy admin create endpoint - redirects to new create page"""
    if p != ADMIN_PASSWORD:
        return HTMLResponse(
            """
            <div style="font-family:system-ui;padding:40px">
              <h2>Yetkisiz</h2>
              <p>Kullanım: <code>/admin/create?p=ADMIN_PASSWORD</code></p>
              <p>Yeni sistem: <a href="/create">/create</a> sayfasını kullanın</p>
            </div>
            """,
            status_code=403,
        )
    
    return RedirectResponse(url="/create", status_code=303)
