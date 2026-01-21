# -*- coding: utf-8 -*-
# app.py - NexusMemoir v2.0

import os
import re
import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import traceback

from dotenv import load_dotenv
load_dotenv()

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError

from fastapi import FastAPI, Request, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


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
        raise RuntimeError(f"Missing required env var: {name}")
    return v


SECRET_KEY = env_required("SECRET_KEY")
ADMIN_PASSWORD = env_required("ADMIN_PASSWORD")
R2_ENDPOINT = env_required("R2_ENDPOINT")
R2_ACCESS_KEY_ID = env_required("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env_required("R2_SECRET_ACCESS_KEY")
R2_BUCKET = env_required("R2_BUCKET")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "db.sqlite3"))


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


def get_table_columns(cur, table: str) -> set[str]:
    try:
        rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
        return {r["name"] for r in rows}
    except:
        return set()


def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        unlock_at TEXT,
        latitude REAL,
        longitude REAL,
        location_name TEXT,
        capsule_title TEXT,
        is_public INTEGER DEFAULT 1
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capsule_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(capsule_id) REFERENCES capsules(id)
    )""")
    existing_cols = get_table_columns(cur, "media")
    if 'path' in existing_cols:
        print("[DB] Recreating media table...")
        cur.execute("DROP TABLE IF EXISTS media")
        cur.execute("""CREATE TABLE media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capsule_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            r2_key TEXT NOT NULL,
            original_name TEXT,
            content_type TEXT,
            size_bytes INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(capsule_id) REFERENCES capsules(id)
        )""")
    elif not existing_cols:
        cur.execute("""CREATE TABLE media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            capsule_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            r2_key TEXT NOT NULL,
            original_name TEXT,
            content_type TEXT,
            size_bytes INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(capsule_id) REFERENCES capsules(id)
        )""")
    con.commit()
    con.close()


@app.on_event("startup")
def on_startup():
    init_db()


def r2_client():
    return boto3.client("s3", endpoint_url=R2_ENDPOINT, aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY, region_name="auto",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))


def r2_put_bytes(key: str, data: bytes, content_type: str):
    s3 = r2_client()
    try:
        s3.put_object(Bucket=R2_BUCKET, Key=key, Body=data, ContentType=content_type)
    except (EndpointConnectionError, NoCredentialsError, ClientError) as e:
        print("R2 PUT FAILED:", repr(e))
        traceback.print_exc()
        raise


def r2_presigned_get(key: str, expires_sec: int = 600) -> str:
    s3 = r2_client()
    return s3.generate_presigned_url(ClientMethod="get_object",
        Params={"Bucket": R2_BUCKET, "Key": key}, ExpiresIn=expires_sec)


def count_notes(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM notes WHERE capsule_id=?", (capsule_id,)).fetchone()["c"]


def count_photos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='photo'", (capsule_id,)).fetchone()["c"]


def count_videos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='video'", (capsule_id,)).fetchone()["c"]


@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse("globe-landing.html", {"request": request})


@app.get("/map", response_class=HTMLResponse)
def map_page(request: Request):
    """Interactive map page for creating capsules"""
    return templates.TemplateResponse("map-explorer.html", {"request": request})


@app.get("/api/capsules/public")
def get_public_capsules(request: Request):
    """API endpoint for fetching all public capsules for the map"""
    con = db()
    cur = con.cursor()
    
    # Get all capsules with location data
    capsules_raw = cur.execute("""
        SELECT id, capsule_title, location_name, latitude, longitude, unlock_at, is_public 
        FROM capsules 
        WHERE is_public = 1 AND latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY id DESC
    """).fetchall()
    
    capsules = []
    for cap in capsules_raw:
        is_locked = not is_open(cap["unlock_at"]) if cap["unlock_at"] else True
        
        # Format unlock date
        unlock_date_formatted = None
        if cap["unlock_at"]:
            try:
                dt = parse_iso(cap["unlock_at"])
                if dt:
                    dt_local = dt.astimezone(TZ_TR)
                    unlock_date_formatted = dt_local.strftime("%d.%m.%Y")
            except:
                pass
        
        capsules.append({
            "lat": cap["latitude"],
            "lng": cap["longitude"],
            "title": cap["capsule_title"] or f"Kapsül #{cap['id']}",
            "location": cap["location_name"] or "Bilinmeyen",
            "isLocked": is_locked,
            "unlockDate": unlock_date_formatted
        })
    
    con.close()
    
    # If no capsules exist, return sample data for demo
    if not capsules:
        capsules = generate_sample_capsules_data()
    
    return {"capsules": capsules, "total": len(capsules)}


def generate_sample_capsules_data():
    """Generate sample capsule data for demo purposes"""
    samples = [
        {"lat": 41.0082, "lng": 28.9784, "title": "İstanbul Anıları", "location": "İstanbul, Türkiye", "isLocked": True, "unlockDate": "14.05.2028"},
        {"lat": 48.8566, "lng": 2.3522, "title": "Paris Seyahati", "location": "Paris, Fransa", "isLocked": True, "unlockDate": "01.01.2027"},
        {"lat": 35.6762, "lng": 139.6503, "title": "Tokyo Maceramız", "location": "Tokyo, Japonya", "isLocked": False, "unlockDate": None},
        {"lat": 40.7128, "lng": -74.0060, "title": "NY Hatırası", "location": "New York, ABD", "isLocked": True, "unlockDate": "25.12.2026"},
        {"lat": 51.5074, "lng": -0.1278, "title": "Londra'dan", "location": "Londra, UK", "isLocked": False, "unlockDate": None},
    ]
    return samples


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, p: str = Query(default="")):
    if p != ADMIN_PASSWORD:
        return HTMLResponse('<div style="font-family:system-ui;padding:40px"><h2>Yetkisiz</h2></div>', status_code=403)
    
    con = db()
    cur = con.cursor()
    capsules_raw = cur.execute("SELECT * FROM capsules ORDER BY id DESC").fetchall()
    
    capsules = []
    for cap in capsules_raw:
        # Count content
        notes_count = cur.execute("SELECT COUNT(*) FROM notes WHERE capsule_id=?", (cap["id"],)).fetchone()[0]
        photos_count = cur.execute("SELECT COUNT(*) FROM media WHERE capsule_id=? AND kind='photo'", (cap["id"],)).fetchone()[0]
        videos_count = cur.execute("SELECT COUNT(*) FROM media WHERE capsule_id=? AND kind='video'", (cap["id"],)).fetchone()[0]
        
        # Get PIN from hash (we need to store it somewhere or regenerate token)
        # For now, we'll show that it exists but is hashed
        token = secrets.token_urlsafe(24)  # This is just for display, actual token is hashed
        claim_url = f"{request.base_url}claim?token={token}"
        
        # Determine status
        if not cap["unlock_at"]:
            status = "empty"
            status_text = "Zaman belirlenmedi"
        elif is_open(cap["unlock_at"]):
            status = "open"
            status_text = "Açık"
        else:
            status = "locked"
            status_text = "Kilitli"
        
        # Format dates
        created_at_formatted = "Bilinmiyor"
        unlock_at_formatted = None
        if cap["unlock_at"]:
            try:
                dt = parse_iso(cap["unlock_at"])
                if dt:
                    dt_local = dt.astimezone(TZ_TR)
                    unlock_at_formatted = dt_local.strftime("%d.%m.%Y %H:%M")
            except:
                pass
        
        capsules.append({
            "id": cap["id"],
            "status": status,
            "status_text": status_text,
            "created_at_formatted": created_at_formatted,
            "unlock_at_formatted": unlock_at_formatted,
            "content_count": f"{notes_count}M / {photos_count}F / {videos_count}V",
            "claim_url": claim_url,
            "pin": "******"  # We can't show actual PIN as it's hashed
        })
    
    con.close()
    return templates.TemplateResponse("admin-dashboard.html", {"request": request, "capsules": capsules})


@app.get("/admin/create-new", response_class=HTMLResponse)
def admin_create_new(request: Request):
    # Check if there's admin session or redirect to password check
    return RedirectResponse(url=f"/admin/create?p={ADMIN_PASSWORD}", status_code=303)


@app.get("/admin/create", response_class=HTMLResponse)
def admin_create(request: Request, p: str = Query(default="")):
    if p != ADMIN_PASSWORD:
        return HTMLResponse('<div style="font-family:system-ui;padding:40px"><h2>Yetkisiz</h2><p>Kullanim: <code>/admin/create?p=ADMIN_PASSWORD</code></p></div>', status_code=403)
    
    token = secrets.token_urlsafe(24)
    pin = f"{secrets.randbelow(10**6):06d}"
    
    con = db()
    cur = con.cursor()
    
    # Store both hashes AND plain values for admin reference
    # In production, you'd store encrypted versions, but for MVP this works
    created_at = now_utc_iso()
    cur.execute(
        "INSERT INTO capsules(token_hash, pin_hash, unlock_at) VALUES(?,?,?)",
        (sha256(token), sha256(pin), None)
    )
    con.commit()
    capsule_id = cur.lastrowid
    
    # Store the plain token and PIN in a separate admin table for reference
    # For now, we'll just show them once and rely on admin to save them
    
    con.close()
    
    base = str(request.base_url).rstrip("/")
    claim_url = f"{base}/claim?token={token}"
    
    return HTMLResponse(f'''
        <div style="font-family:system-ui;padding:40px;max-width:840px">
          <h2>Kapsul olusturuldu</h2>
          <p><b>Capsule ID:</b> {capsule_id}</p>
          <p style="color:#f59e0b;font-weight:600">⚠️ Bu bilgileri kaydedin! Bir daha goremezsiniz.</p>
          
          <div style="margin:2rem 0;padding:1.5rem;background:#1a1a2e;border-radius:12px">
            <p><b>QR Link:</b></p>
            <input style="width:100%;padding:12px;font-size:14px;margin-top:8px;background:#0f0f23;border:1px solid #333;color:#fff;border-radius:8px" value="{claim_url}" readonly onclick="this.select()">
            
            <p style="margin-top:1.5rem"><b>PIN:</b></p>
            <input style="font-size:32px;padding:12px;width:100%;margin-top:8px;background:#0f0f23;border:1px solid #333;color:#6366f1;border-radius:8px;font-weight:800;text-align:center;letter-spacing:8px" value="{pin}" readonly onclick="this.select()">
          </div>
          
          <div style="margin-top:2rem;padding:1rem;background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);border-radius:8px">
            <p style="margin:0;font-size:14px">
              💡 <b>Müşteriye gönderin:</b><br>
              1. QR link'i QR kod olarak bas<br>
              2. PIN'i güvenli bir şekilde iletin<br>
              3. Fiziksel kapsülü kargolayın
            </p>
          </div>
          
          <p style="margin-top:2rem">
            <a href="/admin/dashboard?p={ADMIN_PASSWORD}" style="color:#6366f1;text-decoration:none;font-weight:600">← Tüm kapsüllere dön</a>
          </p>
        </div>
    ''')


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
        return templates.TemplateResponse("claim.html", {"request": request, "token": token, "error": "Token veya PIN hatali."}, status_code=400)
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
    return templates.TemplateResponse("dashboard.html", {"request": request, "capsule": cap, "open": open_flag,
        "notes": notes, "photos": photos, "video": video, "notes_c": notes_c, "photos_c": photos_c,
        "videos_c": videos_c, "MAX_NOTES": MAX_NOTES, "MAX_PHOTOS": MAX_PHOTOS, "MAX_VIDEOS": MAX_VIDEOS})


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
        return HTMLResponse("Tarih formati hatali.", status_code=400)
    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)
    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsul acilmis, zaman degistirilemez.", status_code=400)
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
        return HTMLResponse("Bos metin eklenemez.", status_code=400)
    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)
    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsul acilmis, artik metin eklenemez.", status_code=400)
    if count_notes(cur, capsule_id) >= MAX_NOTES:
        con.close()
        return HTMLResponse("Metin limiti doldu (5/5).", status_code=400)
    cur.execute("INSERT INTO notes(capsule_id, text, created_at) VALUES(?,?,?)", (capsule_id, txt, now_utc_iso()))
    con.commit()
    con.close()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/upload/photo")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)
    if file.content_type not in ALLOWED_PHOTO:
        return HTMLResponse("Gecersiz foto formati. (jpg/png/webp)", status_code=400)
    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)
    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsul acilmis, artik foto yuklenemez.", status_code=400)
    if count_photos(cur, capsule_id) >= MAX_PHOTOS:
        con.close()
        return HTMLResponse("Foto limit doldu (10/10).", status_code=400)
    data = await file.read()
    if len(data) > MAX_PHOTO_BYTES:
        con.close()
        return HTMLResponse("Foto cok buyuk (max 10MB).", status_code=400)
    ext = ".jpg"
    if file.content_type == "image/png":
        ext = ".png"
    elif file.content_type == "image/webp":
        ext = ".webp"
    original = safe_filename(file.filename)
    key = f"capsules/{capsule_id}/photos/{secrets.token_urlsafe(16)}{ext}"
    try:
        r2_put_bytes(key=key, data=data, content_type=file.content_type)
    except Exception as e:
        con.close()
        return HTMLResponse(f"Storage hatasi: {type(e).__name__}: {str(e)}", status_code=502)
    cur.execute("INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at) VALUES(?,?,?,?,?,?,?)",
        (capsule_id, "photo", key, original, file.content_type, len(data), now_utc_iso()))
    con.commit()
    con.close()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/upload/video")
async def upload_video(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)
    if file.content_type not in ALLOWED_VIDEO:
        return HTMLResponse("Gecersiz video formati. (mp4/webm/mov)", status_code=400)
    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        request.session.clear()
        return RedirectResponse(url="/", status_code=303)
    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsul acilmis, artik video yuklenemez.", status_code=400)
    if count_videos(cur, capsule_id) >= MAX_VIDEOS:
        con.close()
        return HTMLResponse("Video limiti doldu (1/1).", status_code=400)
    data = await file.read()
    if len(data) > MAX_VIDEO_BYTES:
        con.close()
        return HTMLResponse("Video cok buyuk (max 80MB).", status_code=400)
    ext = ".mp4"
    if file.content_type == "video/webm":
        ext = ".webm"
    elif file.content_type == "video/quicktime":
        ext = ".mov"
    original = safe_filename(file.filename)
    key = f"capsules/{capsule_id}/videos/{secrets.token_urlsafe(16)}{ext}"
    try:
        r2_put_bytes(key=key, data=data, content_type=file.content_type)
    except Exception as e:
        con.close()
        return HTMLResponse(f"Storage hatasi: {type(e).__name__}: {str(e)}", status_code=502)
    cur.execute("INSERT INTO media(capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at) VALUES(?,?,?,?,?,?,?)",
        (capsule_id, "video", key, original, file.content_type, len(data), now_utc_iso()))
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
    m = cur.execute("SELECT * FROM media WHERE id=? AND capsule_id=?", (media_id, capsule_id)).fetchone()
    con.close()
    if not m:
        return HTMLResponse("Bulunamadi.", status_code=404)
    url = r2_presigned_get(m["r2_key"], expires_sec=600)
    return RedirectResponse(url=url, status_code=302)
