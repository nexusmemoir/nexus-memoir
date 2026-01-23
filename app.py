# -*- coding: utf-8 -*-
# app.py — NexusMemoir - Complete with API
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

try:
    import qrcode
except ImportError:
    print("WARNING: pip install qrcode[pil] --break-system-packages")

from fastapi import FastAPI, Request, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# Config
MAX_NOTES = 5
MAX_PHOTOS = 10
MAX_VIDEOS = 1
MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_VIDEO_BYTES = 80 * 1024 * 1024
ALLOWED_PHOTO = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO = {"video/mp4", "video/webm", "video/quicktime"}
TZ_TR = ZoneInfo("Europe/Istanbul")

def env_required(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing: {name}")
    return v

SECRET_KEY = env_required("SECRET_KEY")
ADMIN_PASSWORD = env_required("ADMIN_PASSWORD")
R2_ENDPOINT = env_required("R2_ENDPOINT")
R2_ACCESS_KEY_ID = env_required("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env_required("R2_SECRET_ACCESS_KEY")
R2_BUCKET = env_required("R2_BUCKET")
DB_PATH = os.getenv("DB_PATH", "db.sqlite3")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None

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
    
    # Capsules table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        unlock_at TEXT
    )
    """)
    
    # Add missing columns (safe migration)
    def add_column_if_missing(table, column, definition):
        try:
            cols = {r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
            if column not in cols:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")
                print(f"[MIGRATION] Added {table}.{column}")
        except Exception as e:
            print(f"[MIGRATION] Skip {table}.{column}: {e}")
    
    # Add new columns to capsules
    add_column_if_missing("capsules", "capsule_number", "capsule_number TEXT")  # No UNIQUE - will add index later
    add_column_if_missing("capsules", "lat", "lat REAL")
    add_column_if_missing("capsules", "lng", "lng REAL")
    add_column_if_missing("capsules", "location_name", "location_name TEXT")
    add_column_if_missing("capsules", "capsule_title", "capsule_title TEXT")
    add_column_if_missing("capsules", "is_public", "is_public INTEGER DEFAULT 0")  # Default 0 - not visible until paid
    add_column_if_missing("capsules", "status", "status TEXT DEFAULT 'draft'")  # draft, locked, paid
    add_column_if_missing("capsules", "created_at", "created_at TEXT")
    
    # Try to create unique index on capsule_number (may fail if duplicates exist)
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_capsule_number ON capsules(capsule_number) WHERE capsule_number IS NOT NULL")
    except Exception as e:
        print(f"[MIGRATION] Index creation skipped: {e}")
    
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
        capsule_id INTEGER,
        kind TEXT,
        r2_key TEXT,
        original_name TEXT,
        content_type TEXT,
        size_bytes INTEGER,
        created_at TEXT,
        FOREIGN KEY(capsule_id) REFERENCES capsules(id)
    )
    """)
    
    con.commit()
    con.close()

@app.on_event("startup")
def on_startup():
    init_db()

# R2
def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )

def r2_put_bytes(key: str, data: bytes, content_type: str):
    s3 = r2_client()
    try:
        s3.put_object(Bucket=R2_BUCKET, Key=key, Body=data, ContentType=content_type)
    except Exception as e:
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

def count_notes(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM notes WHERE capsule_id=?", (capsule_id,)).fetchone()["c"]

def count_photos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='photo'", (capsule_id,)).fetchone()["c"]

def count_videos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='video'", (capsule_id,)).fetchone()["c"]

# Routes
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("map-landing.html", {"request": request})

@app.get("/create", response_class=HTMLResponse)
def create_page(request: Request):
    return templates.TemplateResponse("create-capsule.html", {"request": request})

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
            {"request": request, "token": token, "error": "Token veya PIN hatalı"},
            status_code=400,
        )
    
    request.session["capsule_id"] = row["id"]
    return RedirectResponse(url="/dashboard", status_code=303)

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
    notes = cur.execute("SELECT * FROM notes WHERE capsule_id=? ORDER BY id", (capsule_id,)).fetchall()
    photos = cur.execute("SELECT * FROM media WHERE capsule_id=? AND kind='photo' ORDER BY id", (capsule_id,)).fetchall()
    video = cur.execute("SELECT * FROM media WHERE capsule_id=? AND kind='video' ORDER BY id", (capsule_id,)).fetchone()
    notes_c = count_notes(cur, capsule_id)
    photos_c = count_photos(cur, capsule_id)
    videos_c = count_videos(cur, capsule_id)
    con.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "capsule": cap, "open": open_flag,
        "notes": notes, "photos": photos, "video": video,
        "notes_c": notes_c, "photos_c": photos_c, "videos_c": videos_c,
        "MAX_NOTES": MAX_NOTES, "MAX_PHOTOS": MAX_PHOTOS, "MAX_VIDEOS": MAX_VIDEOS,
    })

# Helper: Generate unique 6-digit capsule number
def generate_capsule_number(cur) -> str:
    """Generate a unique 6-digit capsule number"""
    for _ in range(100):  # Max 100 attempts
        num = f"{secrets.randbelow(900000) + 100000}"  # 100000-999999
        try:
            existing = cur.execute("SELECT id FROM capsules WHERE capsule_number=?", (num,)).fetchone()
            if not existing:
                return num
        except Exception:
            # Column might not exist yet, just return the number
            return num
    raise RuntimeError("Could not generate unique capsule number")

# API Routes

# Step 1: Create draft capsule (after location selection + date)
@app.post("/api/capsules/create-draft")
async def api_create_draft_capsule(
    request: Request,
    lat: float = Form(...),
    lng: float = Form(...),
    title: str = Form(...),
    unlock_at: str = Form(...),
    location_name: str = Form(...)
):
    """Create a draft capsule - user will add content, then pay to publish"""
    try:
        token = secrets.token_urlsafe(24)
        pin = f"{secrets.randbelow(10**6):06d}"
        token_hash = sha256(token)
        pin_hash = sha256(pin)
        
        # Parse date
        dt_local_naive = datetime.fromisoformat(unlock_at)
        dt_local = dt_local_naive.replace(tzinfo=TZ_TR)
        dt_utc = dt_local.astimezone(timezone.utc)
        
        con = db()
        cur = con.cursor()
        
        # Check if capsule_number column exists
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(capsules)").fetchall()}
        has_capsule_number = "capsule_number" in cols
        has_status = "status" in cols
        has_created_at = "created_at" in cols
        
        # Generate unique 6-digit capsule number
        capsule_number = generate_capsule_number(cur) if has_capsule_number else str(secrets.randbelow(900000) + 100000)
        
        # Build dynamic INSERT based on available columns
        if has_capsule_number and has_status and has_created_at:
            cur.execute("""
                INSERT INTO capsules(capsule_number, token_hash, pin_hash, unlock_at, lat, lng, location_name, capsule_title, is_public, status, created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (capsule_number, token_hash, pin_hash, dt_utc.isoformat(), lat, lng, location_name, title, 0, 'draft', now_utc_iso()))
        else:
            # Fallback for old schema
            cur.execute("""
                INSERT INTO capsules(token_hash, pin_hash, unlock_at, lat, lng, location_name, capsule_title, is_public)
                VALUES(?,?,?,?,?,?,?,?)
            """, (token_hash, pin_hash, dt_utc.isoformat(), lat, lng, location_name, title, 0))
        
        capsule_id = cur.lastrowid
        con.commit()
        con.close()
        
        # Set session so user can access dashboard
        request.session["capsule_id"] = capsule_id
        
        return JSONResponse({
            "success": True,
            "capsule_id": capsule_id,
            "capsule_number": capsule_number,
            "token": token,
            "pin": pin,
            "redirect": "/dashboard"
        })
    except Exception as e:
        print(f"Error creating draft: {e}")
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Step 2: Pay and lock capsule (makes it visible on map)
@app.post("/api/capsules/pay-and-lock")
async def api_pay_and_lock(request: Request):
    """Process payment and lock capsule - makes it visible on map"""
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return JSONResponse({"success": False, "error": "Oturum bulunamadı"}, status_code=401)
    
    try:
        con = db()
        cur = con.cursor()
        
        # Check which columns exist
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(capsules)").fetchall()}
        has_status = "status" in cols
        has_capsule_number = "capsule_number" in cols
        
        cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
        if not cap:
            con.close()
            return JSONResponse({"success": False, "error": "Kapsül bulunamadı"}, status_code=404)
        
        # Check if already paid (if status column exists)
        if has_status and cap["status"] == "paid":
            con.close()
            return JSONResponse({"success": False, "error": "Kapsül zaten ödenmiş"}, status_code=400)
        
        # TODO: Real payment integration here
        # For now, simulate successful payment
        
        # Update capsule: mark as paid and make public
        if has_status:
            cur.execute("""
                UPDATE capsules 
                SET status='paid', is_public=1 
                WHERE id=?
            """, (capsule_id,))
        else:
            cur.execute("""
                UPDATE capsules 
                SET is_public=1 
                WHERE id=?
            """, (capsule_id,))
        
        con.commit()
        
        # Get capsule number (if exists)
        capsule_number = cap["capsule_number"] if has_capsule_number else str(capsule_id)
        
        con.close()
        
        return JSONResponse({
            "success": True,
            "message": "Ödeme başarılı! Kapsülünüz haritada görünür.",
            "capsule_number": capsule_number
        })
    except Exception as e:
        print(f"Error in payment: {e}")
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Delete unpaid capsule (cleanup)
@app.post("/api/capsules/delete-draft")
async def api_delete_draft(request: Request):
    """Delete an unpaid draft capsule and all its content"""
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return JSONResponse({"success": False, "error": "Oturum bulunamadı"}, status_code=401)
    
    try:
        con = db()
        cur = con.cursor()
        
        # Check which columns exist
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(capsules)").fetchall()}
        has_status = "status" in cols
        
        cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
        if not cap:
            con.close()
            return JSONResponse({"success": False, "error": "Kapsül bulunamadı"}, status_code=404)
        
        # Check if paid (if status column exists)
        if has_status and cap["status"] == "paid":
            con.close()
            return JSONResponse({"success": False, "error": "Ödenmiş kapsül silinemez"}, status_code=400)
        
        # Delete media from R2
        media_items = cur.execute("SELECT r2_key FROM media WHERE capsule_id=?", (capsule_id,)).fetchall()
        s3 = r2_client()
        for item in media_items:
            try:
                s3.delete_object(Bucket=R2_BUCKET, Key=item["r2_key"])
            except Exception as e:
                print(f"Failed to delete R2 object {item['r2_key']}: {e}")
        
        # Delete from database
        cur.execute("DELETE FROM media WHERE capsule_id=?", (capsule_id,))
        cur.execute("DELETE FROM notes WHERE capsule_id=?", (capsule_id,))
        cur.execute("DELETE FROM capsules WHERE id=?", (capsule_id,))
        
        con.commit()
        con.close()
        
        # Clear session
        request.session.clear()
        
        return JSONResponse({"success": True, "message": "Kapsül silindi"})
    except Exception as e:
        print(f"Error deleting draft: {e}")
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

# Legacy endpoint - redirect to new flow
@app.post("/api/capsules/create")
async def api_create_capsule(
    request: Request,
    lat: float = Form(...),
    lng: float = Form(...),
    title: str = Form(...),
    unlock_at: str = Form(...),
    location_name: str = Form(...)
):
    """Legacy endpoint - now creates draft and redirects to dashboard"""
    return await api_create_draft_capsule(request, lat, lng, title, unlock_at, location_name)

@app.get("/api/capsules/public")
def api_get_public_capsules():
    try:
        con = db()
        cur = con.cursor()
        
        # Check which columns exist
        cols = {r["name"] for r in cur.execute("PRAGMA table_info(capsules)").fetchall()}
        has_status = "status" in cols
        has_capsule_number = "capsule_number" in cols
        
        # Build query based on available columns
        if has_status:
            # New schema - only show paid capsules
            capsules = cur.execute("""
                SELECT id, lat, lng, capsule_title, unlock_at, location_name 
                FROM capsules 
                WHERE is_public=1 AND status='paid' AND lat IS NOT NULL AND lng IS NOT NULL
            """).fetchall()
        else:
            # Old schema - show all public capsules
            capsules = cur.execute("""
                SELECT id, lat, lng, capsule_title, unlock_at, location_name 
                FROM capsules 
                WHERE is_public=1 AND lat IS NOT NULL AND lng IS NOT NULL
            """).fetchall()
        
        con.close()
        
        result = []
        for cap in capsules:
            unlock_dt = parse_iso(cap["unlock_at"])
            is_open_flag = is_open(cap["unlock_at"])
            
            # Handle None title
            cap_title = cap["capsule_title"] or "İsimsiz Kapsül"
            title_masked = cap_title[:20] + "..." if len(cap_title) > 20 else cap_title
            
            result.append({
                "id": cap["id"],
                "lat": cap["lat"],
                "lng": cap["lng"],
                "title": title_masked,
                "city": cap["location_name"] or "Bilinmeyen",
                "unlock_at": unlock_dt.strftime("%d %B %Y") if unlock_dt else "Bilinmiyor",
                "status": "open" if is_open_flag else "locked"
            })
        
        return JSONResponse({"capsules": result})
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse({"capsules": []})

@app.get("/success")
def success_page(request: Request, token: str = "", pin: str = ""):
    qr_code = ""
    
    # Generate QR code from token
    if token:
        try:
            claim_url = f"{str(request.base_url).rstrip('/')}/claim?token={token}"
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(claim_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            qr_code = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        except Exception as e:
            print(f"QR generation error: {e}")
    
    return templates.TemplateResponse("success.html", {
        "request": request,
        "token": token,
        "pin": pin,
        "qr_code": qr_code
    })

# Actions (keep existing add-note, upload-photo, etc)
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
        return HTMLResponse("Storage hatası: R2 upload başarısız.", status_code=502)
    
    cur.execute(
        """INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at)
           VALUES(?,?,?,?,?,?,?)""",
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
        return HTMLResponse("Storage hatası: R2 upload başarısız.", status_code=502)
    
    cur.execute(
        """INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at)
           VALUES(?,?,?,?,?,?,?)""",
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
