# -*- coding: utf-8 -*-
# database.py - FAZ 2: SQLite Veritabanı
# Kullanıcılar, kayıtlı sorular, oylar, takipler, newsletter

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "akademiksoru.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def dict_from_row(row):
    if row is None:
        return None
    return dict(row)

# ========================
# SCHEMA
# ========================

def init_database():
    with get_db() as conn:
        cur = conn.cursor()
        
        # Kullanıcılar
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
        """)
        
        # Oturumlar
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        
        # Kaydedilen sorular
        cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            category TEXT,
            result_data TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, question_hash)
        )
        """)
        
        # Arama geçmişi
        cur.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_text TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            ip_address TEXT,
            created_at TEXT NOT NULL,
            result_count INTEGER DEFAULT 0
        )
        """)
        
        # Oylar
        cur.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_hash TEXT NOT NULL,
            vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
            ip_address TEXT,
            created_at TEXT NOT NULL
        )
        """)
        
        # Konu takipleri
        cur.execute("""
        CREATE TABLE IF NOT EXISTS topic_follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, category)
        )
        """)
        
        # Newsletter
        cur.execute("""
        CREATE TABLE IF NOT EXISTS newsletter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            frequency TEXT DEFAULT 'weekly',
            subscribed_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        
        # Popüler sorular cache
        cur.execute("""
        CREATE TABLE IF NOT EXISTS popular_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_hash TEXT UNIQUE NOT NULL,
            question_text TEXT NOT NULL,
            category TEXT,
            search_count INTEGER DEFAULT 0,
            upvotes INTEGER DEFAULT 0,
            downvotes INTEGER DEFAULT 0,
            last_searched TEXT,
            updated_at TEXT NOT NULL
        )
        """)
        
        # İndeksler
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_saved_user ON saved_questions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_votes_hash ON votes(question_hash)")
        
        conn.commit()
        print("[DB] Initialized")

# ========================
# PASSWORD
# ========================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{h.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(':')
        new_h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_h.hex() == h
    except:
        return False

def hash_question(q: str) -> str:
    return hashlib.sha256(q.lower().strip().encode()).hexdigest()[:16]

# ========================
# USERS
# ========================

def create_user(email: str, username: str, password: str, display_name: str = None) -> Optional[int]:
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
            INSERT INTO users (email, username, password_hash, display_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (
                email.lower().strip(),
                username.lower().strip(),
                hash_password(password),
                display_name or username,
                datetime.now(timezone.utc).isoformat()
            ))
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_user_by_email(email: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email.lower().strip(),))
        return dict_from_row(cur.fetchone())

def get_user_by_username(username: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ? AND is_active = 1", (username.lower().strip(),))
        return dict_from_row(cur.fetchone())

def get_user_by_id(user_id: int):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,))
        return dict_from_row(cur.fetchone())

def authenticate_user(email_or_username: str, password: str):
    user = get_user_by_email(email_or_username) or get_user_by_username(email_or_username)
    if user and verify_password(password, user['password_hash']):
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET last_login = ? WHERE id = ?", 
                       (datetime.now(timezone.utc).isoformat(), user['id']))
            conn.commit()
        return user
    return None

# ========================
# SESSIONS
# ========================

def create_session(user_id: int, ip: str = None, days: int = 30) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=days)
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO sessions (user_id, token, created_at, expires_at, ip_address)
        VALUES (?, ?, ?, ?, ?)
        """, (user_id, token, datetime.now(timezone.utc).isoformat(), expires.isoformat(), ip))
        conn.commit()
    return token

def get_session(token: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT s.*, u.email, u.username, u.display_name
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ? AND u.is_active = 1
        """, (token, datetime.now(timezone.utc).isoformat()))
        return dict_from_row(cur.fetchone())

def delete_session(token: str):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()

# ========================
# SAVED QUESTIONS
# ========================

def save_question(user_id: int, question: str, category: str = None, result_data: str = None):
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
            INSERT INTO saved_questions (user_id, question_text, question_hash, category, result_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, question, hash_question(question), category, result_data, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_saved_questions(user_id: int, limit: int = 50) -> List[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM saved_questions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return [dict_from_row(r) for r in cur.fetchall()]

def delete_saved_question(user_id: int, question_id: int) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM saved_questions WHERE id = ? AND user_id = ?", (question_id, user_id))
        conn.commit()
        return cur.rowcount > 0

def is_question_saved(user_id: int, question: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM saved_questions WHERE user_id = ? AND question_hash = ?", 
                   (user_id, hash_question(question)))
        return cur.fetchone() is not None

# ========================
# SEARCH HISTORY
# ========================

def log_search(question: str, user_id: int = None, ip: str = None, result_count: int = 0):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO search_history (user_id, question_text, question_hash, ip_address, created_at, result_count)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, question, hash_question(question), ip, datetime.now(timezone.utc).isoformat(), result_count))
        conn.commit()
        update_popular_cache(question, result_count)

def get_search_history(user_id: int, limit: int = 20) -> List[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        return [dict_from_row(r) for r in cur.fetchall()]

# ========================
# VOTING
# ========================

def vote_question(question_hash: str, vote_type: str, user_id: int = None, ip: str = None) -> dict:
    if vote_type not in ('up', 'down'):
        return {"success": False, "error": "Invalid vote"}
    
    with get_db() as conn:
        cur = conn.cursor()
        
        # Mevcut oy
        if user_id:
            cur.execute("SELECT id, vote_type FROM votes WHERE user_id = ? AND question_hash = ?", (user_id, question_hash))
        else:
            cur.execute("SELECT id, vote_type FROM votes WHERE ip_address = ? AND question_hash = ? AND user_id IS NULL", (ip, question_hash))
        
        existing = cur.fetchone()
        
        if existing:
            if existing['vote_type'] == vote_type:
                cur.execute("DELETE FROM votes WHERE id = ?", (existing['id'],))
                action = "removed"
            else:
                cur.execute("UPDATE votes SET vote_type = ? WHERE id = ?", (vote_type, existing['id']))
                action = "changed"
        else:
            cur.execute("""
            INSERT INTO votes (user_id, question_hash, vote_type, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (user_id, question_hash, vote_type, ip, datetime.now(timezone.utc).isoformat()))
            action = "added"
        
        conn.commit()
        
        counts = get_vote_counts(question_hash)
        update_vote_cache(question_hash, counts)
        
        return {"success": True, "action": action, **counts}

def get_vote_counts(question_hash: str) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END), 0) as upvotes,
            COALESCE(SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END), 0) as downvotes
        FROM votes WHERE question_hash = ?
        """, (question_hash,))
        row = cur.fetchone()
        return {"upvotes": row['upvotes'], "downvotes": row['downvotes']}

def get_user_vote(question_hash: str, user_id: int = None, ip: str = None) -> Optional[str]:
    with get_db() as conn:
        cur = conn.cursor()
        if user_id:
            cur.execute("SELECT vote_type FROM votes WHERE user_id = ? AND question_hash = ?", (user_id, question_hash))
        else:
            cur.execute("SELECT vote_type FROM votes WHERE ip_address = ? AND question_hash = ? AND user_id IS NULL", (ip, question_hash))
        row = cur.fetchone()
        return row['vote_type'] if row else None

# ========================
# TOPIC FOLLOWS
# ========================

def follow_topic(user_id: int, category: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
            INSERT INTO topic_follows (user_id, category, created_at) VALUES (?, ?, ?)
            """, (user_id, category, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def unfollow_topic(user_id: int, category: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM topic_follows WHERE user_id = ? AND category = ?", (user_id, category))
        conn.commit()
        return cur.rowcount > 0

def get_followed_topics(user_id: int) -> List[str]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT category FROM topic_follows WHERE user_id = ?", (user_id,))
        return [r['category'] for r in cur.fetchall()]

def is_following(user_id: int, category: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM topic_follows WHERE user_id = ? AND category = ?", (user_id, category))
        return cur.fetchone() is not None

# ========================
# NEWSLETTER
# ========================

def subscribe_newsletter(email: str, user_id: int = None, frequency: str = 'weekly') -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
            INSERT INTO newsletter (email, user_id, frequency, subscribed_at) VALUES (?, ?, ?, ?)
            """, (email.lower().strip(), user_id, frequency, datetime.now(timezone.utc).isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def unsubscribe_newsletter(email: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE newsletter SET is_active = 0 WHERE email = ?", (email.lower().strip(),))
        conn.commit()
        return cur.rowcount > 0

# ========================
# POPULAR CACHE
# ========================

def update_popular_cache(question: str, result_count: int = 0):
    q_hash = hash_question(question)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM popular_cache WHERE question_hash = ?", (q_hash,))
        if cur.fetchone():
            cur.execute("""
            UPDATE popular_cache SET search_count = search_count + 1, last_searched = ?, updated_at = ?
            WHERE question_hash = ?
            """, (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), q_hash))
        else:
            cur.execute("""
            INSERT INTO popular_cache (question_hash, question_text, search_count, last_searched, updated_at)
            VALUES (?, ?, 1, ?, ?)
            """, (q_hash, question, datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat()))
        conn.commit()

def update_vote_cache(question_hash: str, counts: dict):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        UPDATE popular_cache SET upvotes = ?, downvotes = ?, updated_at = ? WHERE question_hash = ?
        """, (counts['upvotes'], counts['downvotes'], datetime.now(timezone.utc).isoformat(), question_hash))
        conn.commit()

def get_trending(limit: int = 10) -> List[dict]:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM popular_cache 
        WHERE last_searched > datetime('now', '-7 days')
        ORDER BY search_count DESC, upvotes DESC
        LIMIT ?
        """, (limit,))
        return [dict_from_row(r) for r in cur.fetchall()]

def get_user_stats(user_id: int) -> dict:
    with get_db() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as c FROM saved_questions WHERE user_id = ?", (user_id,))
        saved = cur.fetchone()['c']
        
        cur.execute("SELECT COUNT(*) as c FROM search_history WHERE user_id = ?", (user_id,))
        searches = cur.fetchone()['c']
        
        cur.execute("SELECT COUNT(*) as c FROM topic_follows WHERE user_id = ?", (user_id,))
        following = cur.fetchone()['c']
        
        cur.execute("SELECT COUNT(*) as c FROM votes WHERE user_id = ?", (user_id,))
        votes = cur.fetchone()['c']
        
        return {"saved": saved, "searches": searches, "following": following, "votes": votes}
