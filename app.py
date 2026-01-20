from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
ADMIN_PASSWORD = "zihin-anahtar-2026"

APP_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(APP_DIR, "db.sqlite3")
UPLOAD_DIR = os.path.join(APP_DIR, "uploads")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ✅ Session (prod'da secret key'i değiştir!)
app.add_middleware(SessionMiddleware, secret_key="CHANGE_ME_TO_A_LONG_RANDOM_SECRET_1234567890")

# Limitler
MAX_NOTES = 5
MAX_PHOTOS = 10
MAX_VIDEOS = 1

# Dosya boyutu limitleri (byte)
MAX_PHOTO_BYTES = 10 * 1024 * 1024   # 10MB
MAX_VIDEO_BYTES = 80 * 1024 * 1024   # 80MB


# -------------------------
# Helpers
# -------------------------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def parse_unlock(unlock_at):
    if not unlock_at:
        return None
    return datetime.fromisoformat(unlock_at)

def is_open(unlock_at):
    dt = parse_unlock(unlock_at)
    return dt is not None and datetime.now(timezone.utc) >= dt

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS media (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capsule_id INTEGER NOT NULL,
        kind TEXT NOT NULL,       -- 'photo' | 'video'
        path TEXT NOT NULL,
        original_name TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(capsule_id) REFERENCES capsules(id)
    )
    """)

    con.commit()
    con.close()

def count_notes(cur, capsule_id: int) -> int:
    return cur.execute(
        "SELECT COUNT(*) AS c FROM notes WHERE capsule_id=?",
        (capsule_id,)
    ).fetchone()["c"]

def count_photos(cur, capsule_id: int) -> int:
    return cur.execute(
        "SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='photo'",
        (capsule_id,)
    ).fetchone()["c"]

def count_videos(cur, capsule_id: int) -> int:
    return cur.execute(
        "SELECT COUNT(*) AS c FROM media WHERE capsule_id=? AND kind='video'",
        (capsule_id,)
    ).fetchone()["c"]

def require_capsule_id(request: Request):
    capsule_id = request.session.get("capsule_id")
    return capsule_id

def safe_filename(name: str) -> str:
    return (name or "file").replace("/", "_").replace("\\", "_")


@app.on_event("startup")
def on_startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    init_db()


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

from fastapi import Query

@app.get("/admin/create", response_class=HTMLResponse)
def admin_create(request: Request, p: str = Query(default="")):
    # Admin şifresi kontrolü
    if p != ADMIN_PASSWORD:
        return HTMLResponse("""
        <div style="font-family:sans-serif;padding:40px">
            <h2>🚫 Yetkisiz Erişim</h2>
            <p>Bu alan sadece admin içindir.</p>
            <p>Kullanım: <code>/admin/create?p=ADMIN_SIFRESI</code></p>
        </div>
        """, status_code=403)

    token = secrets.token_urlsafe(24)
    pin = f"{secrets.randbelow(10**6):06d}"

    con = db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO capsules(token_hash, pin_hash, unlock_at) VALUES(?,?,?)",
        (sha256(token), sha256(pin), None)
    )
    con.commit()
    capsule_id = cur.lastrowid
    con.close()

    claim_url = f"/claim?token={token}"

    return HTMLResponse(f"""
    <div style="font-family:sans-serif;padding:40px">
        <h2>🧠 Kapsül oluşturuldu ✅</h2>
        <p><b>Capsule ID:</b> {capsule_id}</p>

        <p><b>QR Link:</b></p>
        <input style="width:100%;padding:10px" value="{claim_url}" readonly>

        <p><b>PIN:</b></p>
        <input style="font-size:22px;padding:10px" value="{pin}" readonly>

        <p style="margin-top:16px"><a href="/">Ana sayfa</a></p>
        <p><a href="{claim_url}">Claim sayfasına git</a></p>
    </div>
    """)


@app.get("/claim", response_class=HTMLResponse)
def claim_page(request: Request, token: str = ""):
    return templates.TemplateResponse("claim.html", {"request": request, "token": token, "error": ""})

@app.post("/claim")
def claim_submit(request: Request, token: str = Form(...), pin: str = Form(...)):
    con = db()
    cur = con.cursor()
    row = cur.execute(
        "SELECT * FROM capsules WHERE token_hash=?",
        (sha256(token),)
    ).fetchone()
    con.close()

    if not row or row["pin_hash"] != sha256(pin):
        return templates.TemplateResponse(
            "claim.html",
            {"request": request, "token": token, "error": "Token veya PIN hatalı."},
            status_code=400
        )

    # ✅ Oturum aç: token artık URL’de taşınmayacak
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
        (cap["id"],)
    ).fetchall()

    photos = cur.execute(
        "SELECT * FROM media WHERE capsule_id=? AND kind='photo' ORDER BY id",
        (cap["id"],)
    ).fetchall()

    video = cur.execute(
        "SELECT * FROM media WHERE capsule_id=? AND kind='video' ORDER BY id",
        (cap["id"],)
    ).fetchone()

    notes_c = count_notes(cur, cap["id"])
    photos_c = count_photos(cur, cap["id"])
    videos_c = count_videos(cur, cap["id"])

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
            "MAX_VIDEOS": MAX_VIDEOS
        }
    )


# -------------------------
# Actions (session-based)
# -------------------------
@app.post("/set-unlock")
def set_unlock(request: Request, unlock_at: str = Form(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    # Kullanıcı TR saati giriyor (UTC+3). UTC'ye çeviriyoruz.
    try:
        dt_local = datetime.fromisoformat(unlock_at)
        dt = dt_local.replace(tzinfo=timezone(timedelta(hours=3))).astimezone(timezone.utc)
    except Exception:
        return HTMLResponse("Tarih formatı hatalı.", status_code=400)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap:
        con.close()
        return RedirectResponse(url="/logout", status_code=303)

    cur.execute("UPDATE capsules SET unlock_at=? WHERE id=?", (dt.isoformat(), cap["id"]))
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/add-note")
def add_note(request: Request, text: str = Form(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()

    if not cap:
        con.close()
        return RedirectResponse(url="/logout", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık metin eklenemez.", status_code=400)

    if count_notes(cur, cap["id"]) >= MAX_NOTES:
        con.close()
        return HTMLResponse("Metin limiti doldu (5/5).", status_code=400)

    cur.execute(
        "INSERT INTO notes(capsule_id, text, created_at) VALUES(?,?,?)",
        (cap["id"], text.strip(), now_utc())
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/upload-photo")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()

    if not cap:
        con.close()
        return RedirectResponse(url="/logout", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık foto yüklenemez.", status_code=400)

    if not (file.content_type or "").startswith("image/"):
        con.close()
        return HTMLResponse("Lütfen fotoğraf dosyası yükleyin.", status_code=400)

    if count_photos(cur, cap["id"]) >= MAX_PHOTOS:
        con.close()
        return HTMLResponse("Foto limit doldu (10/10).", status_code=400)

    content = await file.read()
    if len(content) > MAX_PHOTO_BYTES:
        con.close()
        return HTMLResponse("Foto çok büyük (max 10MB).", status_code=400)

    cap_dir = os.path.join(UPLOAD_DIR, str(cap["id"]))
    os.makedirs(cap_dir, exist_ok=True)

    fname = f"photo_{secrets.token_hex(6)}_{safe_filename(file.filename)}"
    path = os.path.join(cap_dir, fname)

    with open(path, "wb") as f:
        f.write(content)

    cur.execute(
        "INSERT INTO media(capsule_id, kind, path, original_name, created_at) VALUES(?,?,?,?,?)",
        (cap["id"], "photo", path, file.filename, now_utc())
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/upload-video")
async def upload_video(request: Request, file: UploadFile = File(...)):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return RedirectResponse(url="/", status_code=303)

    con = db()
    cur = con.cursor()
    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()

    if not cap:
        con.close()
        return RedirectResponse(url="/logout", status_code=303)

    if is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kapsül açılmış, artık video yüklenemez.", status_code=400)

    if not (file.content_type or "").startswith("video/"):
        con.close()
        return HTMLResponse("Lütfen video dosyası yükleyin.", status_code=400)

    if count_videos(cur, cap["id"]) >= MAX_VIDEOS:
        con.close()
        return HTMLResponse("Video limiti doldu (1/1).", status_code=400)

    content = await file.read()
    if len(content) > MAX_VIDEO_BYTES:
        con.close()
        return HTMLResponse("Video çok büyük (max 80MB).", status_code=400)

    cap_dir = os.path.join(UPLOAD_DIR, str(cap["id"]))
    os.makedirs(cap_dir, exist_ok=True)

    fname = f"video_{secrets.token_hex(6)}_{safe_filename(file.filename)}"
    path = os.path.join(cap_dir, fname)

    with open(path, "wb") as f:
        f.write(content)

    cur.execute(
        "INSERT INTO media(capsule_id, kind, path, original_name, created_at) VALUES(?,?,?,?,?)",
        (cap["id"], "video", path, file.filename, now_utc())
    )
    con.commit()
    con.close()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/file")
def serve_file(request: Request, media_id: int):
    capsule_id = require_capsule_id(request)
    if not capsule_id:
        return HTMLResponse("Yetkisiz.", status_code=403)

    con = db()
    cur = con.cursor()

    cap = cur.execute("SELECT * FROM capsules WHERE id=?", (capsule_id,)).fetchone()
    if not cap or not is_open(cap["unlock_at"]):
        con.close()
        return HTMLResponse("Kilitli.", status_code=403)

    m = cur.execute(
        "SELECT * FROM media WHERE id=? AND capsule_id=?",
        (media_id, capsule_id)
    ).fetchone()

    con.close()

    if not m:
        return HTMLResponse("Dosya bulunamadı.", status_code=404)

    return FileResponse(m["path"])
