# -*- coding: utf-8 -*-
"""Database module for AkademikSoru"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "akademiksoru.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        display_name TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        token TEXT UNIQUE NOT NULL, ip_address TEXT, user_agent TEXT,
        created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS saved_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        question TEXT NOT NULL, category TEXT, result_data TEXT, created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        question TEXT NOT NULL, ip_address TEXT, created_at TEXT NOT NULL)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        question_hash TEXT NOT NULL, vote_type TEXT NOT NULL,
        ip_address TEXT, created_at TEXT NOT NULL)""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS topic_follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        category TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id), UNIQUE(user_id, category))""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS newsletter_subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        user_id INTEGER, frequency TEXT DEFAULT 'weekly', created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    
    cur.execute("""CREATE TABLE IF NOT EXISTS popular_questions_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
        question_hash TEXT UNIQUE NOT NULL, category TEXT, preview TEXT,
        evidence_level TEXT, search_count INTEGER DEFAULT 1,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hash_obj.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hash_hex = stored.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hash_obj.hex() == hash_hex
    except:
        return False

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def create_user(email: str, username: str, password: str, display_name: str = "") -> Optional[int]:
    conn = get_db()
    cur = conn.cursor()
    try:
        now = now_iso()
        cur.execute("INSERT INTO users (email, username, password_hash, display_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (email.lower(), username.lower(), hash_password(password), display_name or username, now, now))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> Optional[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ? OR username = ?", (email.lower(), email.lower()))
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None

def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def create_session(user_id: int, ip: str = "", user_agent: str = "") -> str:
    token = secrets.token_urlsafe(32)
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=30)
    cur.execute("INSERT INTO sessions (user_id, token, ip_address, user_agent, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, token, ip, user_agent, now.isoformat(), expires.isoformat()))
    conn.commit()
    conn.close()
    return token

def get_session(token: str) -> Optional[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sessions WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    if row:
        expires = datetime.fromisoformat(row["expires_at"].replace('Z', '+00:00'))
        if datetime.now(timezone.utc) < expires:
            return dict(row)
    return None

def delete_session(token: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

def save_question(user_id: int, question: str, category: str = "", result_data: str = "") -> Optional[int]:
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO saved_questions (user_id, question, category, result_data, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, question, category, result_data, now_iso()))
        conn.commit()
        return cur.lastrowid
    except:
        return None
    finally:
        conn.close()

def get_saved_questions(user_id: int) -> list:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM saved_questions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_saved_question(save_id: int, user_id: int) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM saved_questions WHERE id = ? AND user_id = ?", (save_id, user_id))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted

def log_search(user_id: Optional[int], question: str, ip: str = ""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO search_history (user_id, question, ip_address, created_at) VALUES (?, ?, ?, ?)",
        (user_id, question, ip, now_iso()))
    conn.commit()
    conn.close()

def get_search_history(user_id: int, limit: int = 20) -> list:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def vote_question(user_id: Optional[int], question_hash: str, vote_type: Optional[str], ip: str = ""):
    conn = get_db()
    cur = conn.cursor()
    if user_id:
        cur.execute("DELETE FROM votes WHERE user_id = ? AND question_hash = ?", (user_id, question_hash))
    else:
        cur.execute("DELETE FROM votes WHERE ip_address = ? AND question_hash = ? AND user_id IS NULL", (ip, question_hash))
    if vote_type:
        cur.execute("INSERT INTO votes (user_id, question_hash, vote_type, ip_address, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, question_hash, vote_type, ip, now_iso()))
    conn.commit()
    conn.close()

def get_vote_counts(question_hash: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT vote_type, COUNT(*) as c FROM votes WHERE question_hash = ? GROUP BY vote_type", (question_hash,))
    rows = cur.fetchall()
    conn.close()
    counts = {"upvotes": 0, "downvotes": 0}
    for r in rows:
        if r["vote_type"] == "up":
            counts["upvotes"] = r["c"]
        elif r["vote_type"] == "down":
            counts["downvotes"] = r["c"]
    return counts

def get_user_vote(user_id: Optional[int], question_hash: str, ip: str = "") -> Optional[str]:
    conn = get_db()
    cur = conn.cursor()
    if user_id:
        cur.execute("SELECT vote_type FROM votes WHERE user_id = ? AND question_hash = ?", (user_id, question_hash))
    else:
        cur.execute("SELECT vote_type FROM votes WHERE ip_address = ? AND question_hash = ? AND user_id IS NULL", (ip, question_hash))
    row = cur.fetchone()
    conn.close()
    return row["vote_type"] if row else None

def follow_topic(user_id: int, category: str):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO topic_follows (user_id, category, created_at) VALUES (?, ?, ?)", (user_id, category, now_iso()))
        conn.commit()
    finally:
        conn.close()

def unfollow_topic(user_id: int, category: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM topic_follows WHERE user_id = ? AND category = ?", (user_id, category))
    conn.commit()
    conn.close()

def get_followed_topics(user_id: int) -> list:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT category FROM topic_follows WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [r["category"] for r in rows]

def is_following_topic(user_id: int, category: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM topic_follows WHERE user_id = ? AND category = ?", (user_id, category))
    row = cur.fetchone()
    conn.close()
    return row is not None

def subscribe_newsletter(email: str, user_id: Optional[int] = None, frequency: str = "weekly"):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR REPLACE INTO newsletter_subscribers (email, user_id, frequency, created_at) VALUES (?, ?, ?, ?)",
            (email.lower(), user_id, frequency, now_iso()))
        conn.commit()
    finally:
        conn.close()

def update_popular_cache(question: str, category: str, preview: str, evidence_level: str):
    question_hash = hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]
    conn = get_db()
    cur = conn.cursor()
    now = now_iso()
    cur.execute("SELECT id, search_count FROM popular_questions_cache WHERE question_hash = ?", (question_hash,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE popular_questions_cache SET search_count = search_count + 1, updated_at = ? WHERE id = ?", (now, row["id"]))
    else:
        cur.execute("INSERT INTO popular_questions_cache (question, question_hash, category, preview, evidence_level, search_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
            (question, question_hash, category, preview, evidence_level, now, now))
    conn.commit()
    conn.close()

def get_trending_questions(limit: int = 6) -> list:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM popular_questions_cache ORDER BY search_count DESC, updated_at DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_stats(user_id: int) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM saved_questions WHERE user_id = ?", (user_id,))
    saved = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM search_history WHERE user_id = ?", (user_id,))
    searches = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM topic_follows WHERE user_id = ?", (user_id,))
    follows = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) as c FROM votes WHERE user_id = ?", (user_id,))
    votes = cur.fetchone()["c"]
    conn.close()
    return {"saved_count": saved, "search_count": searches, "follow_count": follows, "vote_count": votes}
