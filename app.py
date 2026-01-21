# -*- coding: utf-8 -*-
# app.py — NexusMemoir (clean + production-ish MVP)
# - Session-based ownership (token URL'de kalmaz)
# - Cloudflare R2 (S3 compatible) media storage (private bucket + presigned URL)
# - SQLite DB (Render'da kalıcılık için persistent disk önerilir)
# - Limits: 5 notes, 10 photos, 1 video
#
# ENV (Render -> Environment):
#   SECRET_KEY               (zorunlu, uzun rastgele)
#   ADMIN_PASSWORD           (zorunlu, /admin/create?p=... için)
#   R2_ENDPOINT              (zorunlu)  https://<ACCOUNT_ID>.r2.cloudflarestorage.com
#   R2_ACCESS_KEY_ID         (zorunlu)
#   R2_SECRET_ACCESS_KEY     (zorunlu)
#   R2_BUCKET                (zorunlu)  nexusmemoir-media
#   DB_PATH                  (opsiyonel) /var/data/db.sqlite3 (persistent disk önerilir)

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
ALLOWED_VIDEO = {"video/mp4", "video/webm", "video/quicktime"}  # mov=quicktime

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


# -------------------------
# DB helpers
# -------------------------
def db():
    # check_same_thread=False: FastAPI async ortamda daha stabil olabilir
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


def _table_exists(cur, name: str) -> bool:
    return cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def _table_columns(cur, table: str) -> set[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return {r["name"] for r in rows}


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS capsules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_hash TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        unlock_at TEXT
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

    # Yeni şema (r2_key var)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS media (
         # ---- SAFE migration (never crash app on old DBs) ----
    def ensure_column(table: str, col: str, ddl: str):
        try:
            cols = {r["name"] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
            if col in cols:
                return
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        except sqlite3.OperationalError as e:
            # "duplicate column name" gibi durumlarda crash etme
            print(f"[MIGRATION] skip {table}.{col}: {e}")

    # media tablosu eskiyse kolonları ekle
    if cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='media'").fetchone():
        ensure_column("media", "capsule_id", "capsule_id INTEGER")
        ensure_column("media", "kind", "kind TEXT")
        ensure_column("media", "r2_key", "r2_key TEXT")
        ensure_column("media", "original_name", "original_name TEXT")
        ensure_column("media", "content_type", "content_type TEXT")
        ensure_column("media", "size_bytes", "size_bytes INTEGER")
        ensure_column("media", "created_at", "created_at TEXT")


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
            s3={"addressing_style": "path"},  # R2 için daha stabil
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
# Counting
# -------------------------
def count_notes(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM notes WHERE capsule_id=?", (capsule_id,)).fetchone()["c"]


def count_photos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='photo'", (capsule_id,)).fetchone()["c"]


def count_videos(cur, capsule_id: int) -> int:
    return cur.execute("SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='video'", (capsule_id,)).fetchone()["c"]


# -------------------------
# Pages
# -------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/admin/create", response_class=HTMLResponse)
def admin_create(request: Request, p: str = Query(default="")):
    if p != ADMIN_PASSWORD:
        return HTMLResponse(
            """
            <div style="font-family:system-ui;padding:40px">
              <h2>Yetkisiz</h2>
              <p>Kullanım: <code>/admin/create?p=ADMIN_PASSWORD</code></p>
            </div>
            """,
            status_code=403,
        )

    token = secrets.token_urlsafe(24)
    pin = f"{secrets.randbelow(10**6):06d}"

    con = db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO capsules(token_hash, pin_hash, unlock_at) VALUES(?,?,?)",
        (sha256(token), sha256(pin), None),
    )
    con.commit()
    capsule_id = cur.lastrowid
    con.close()

    base = str(request.base_url).rstrip("/")
    claim_url = f"{base}/claim?token={token}"

    return HTMLResponse(
        f"""
        <div style="font-family:system-ui;padding:40px;max-width:840px">
          <h2>Kapsül oluşturuldu </h2>
          <p><b>Capsule ID:</b> {capsule_id}</p>

          <p><b>QR Link:</b></p>
          <input style="width:100%;padding:12px;font-size:14px" value="{claim_url}" readonly>

          <p style="margin-top:14px"><b>PIN:</b></p>
          <input style="font-size:22px;padding:12px;width:220px" value="{pin}" readonly>

          <p style="margin-top:18px"><a href="/">Ana sayfa</a></p>
          <p><a href="{claim_url}">Claim sayfasına git</a></p>
        </div>
        """
    )


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
# Actions (session-based)
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
            "Storage hatası: R2 upload başarısız. Konsolda/Render Logs'ta 'R2 PUT FAILED' satırına bak.",
            status_code=502,
        )

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
        return HTMLResponse(
            "Storage hatası: R2 upload başarısız. Konsolda/Render Logs'ta 'R2 PUT FAILED' satırına bak.",
            status_code=502,
        )

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
