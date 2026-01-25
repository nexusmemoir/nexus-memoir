# -*- coding: utf-8 -*-
# AkademikSoru v3.0 - FAZ 2
# Kullanıcı sistemi, soru kaydetme, oylama, newsletter

import os
import re
import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
import traceback
from collections import defaultdict
import asyncio
import httpx

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import (
    init_database, hash_question,
    create_user, get_user_by_id, authenticate_user,
    create_session, get_session, delete_session,
    save_question, get_saved_questions, delete_saved_question, is_question_saved,
    log_search, get_search_history,
    vote_question, get_vote_counts, get_user_vote,
    follow_topic, unfollow_topic, get_followed_topics, is_following,
    subscribe_newsletter, unsubscribe_newsletter,
    get_trending, get_user_stats
)

# ========================
# CONFIG
# ========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-123")

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10
CACHE_TTL = 48 * 60 * 60

question_cache = {}
rate_limits = defaultdict(list)

# Statik popüler sorular (fallback)
POPULAR_QUESTIONS = [
    {"id": "kahve", "question": "Kahve içmek sağlığa zararlı mı?", "category": "Beslenme", "icon": "☕", "preview": "Günde 3-4 fincan kahvenin olumlu etkileri var.", "evidence_level": "strong"},
    {"id": "isitma", "question": "Yemekleri tekrar ısıtmak zararlı mı?", "category": "Beslenme", "icon": "🍲", "preview": "Çoğu yemek için güvenli.", "evidence_level": "moderate"},
    {"id": "uyku", "question": "Gece geç uyumak kilo aldırır mı?", "category": "Sağlık", "icon": "😴", "preview": "Gece geç yemek yeme alışkanlığı etkili.", "evidence_level": "moderate"},
    {"id": "cvitamin", "question": "C vitamini soğuk algınlığına iyi gelir mi?", "category": "Sağlık", "icon": "🍊", "preview": "Önleyici etkisi sınırlı.", "evidence_level": "moderate"},
    {"id": "plastik", "question": "Plastik şişeler kanser yapar mı?", "category": "Sağlık", "icon": "🧴", "preview": "Normal kullanımda güvenli.", "evidence_level": "moderate"},
    {"id": "fasting", "question": "Aralıklı oruç işe yarıyor mu?", "category": "Beslenme", "icon": "⏰", "preview": "Umut verici bulgular var.", "evidence_level": "moderate"},
    {"id": "mavi", "question": "Mavi ışık uyku kalitesini etkiler mi?", "category": "Sağlık", "icon": "📱", "preview": "Melatonin üretimini baskılayabilir.", "evidence_level": "strong"},
    {"id": "seker", "question": "Şeker bağımlılık yapar mı?", "category": "Beslenme", "icon": "🍬", "preview": "Ödül mekanizmalarını tetikler.", "evidence_level": "moderate"}
]

CATEGORIES = [
    {"name": "Beslenme", "icon": "🥗", "color": "#10b981"},
    {"name": "Sağlık", "icon": "❤️", "color": "#ef4444"},
    {"name": "Uyku", "icon": "😴", "color": "#8b5cf6"},
    {"name": "Psikoloji", "icon": "🧠", "color": "#f59e0b"},
    {"name": "Egzersiz", "icon": "💪", "color": "#06b6d4"},
    {"name": "Teknoloji", "icon": "📱", "color": "#6366f1"}
]

# ========================
# APP SETUP
# ========================

app = FastAPI(title="AkademikSoru", version="3.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.on_event("startup")
def startup():
    init_database()
    print("[APP] AkademikSoru v3.0 - FAZ 2")

# ========================
# HELPERS
# ========================

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def get_current_user(request: Request):
    token = request.cookies.get("auth_token")
    if not token:
        return None
    session = get_session(token)
    if not session:
        return None
    return {
        "id": session["user_id"],
        "email": session["email"],
        "username": session["username"],
        "display_name": session["display_name"]
    }

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limits[ip]) >= RATE_LIMIT_MAX:
        return True
    rate_limits[ip].append(now)
    return False

def get_cache_key(q: str) -> str:
    return hashlib.sha256(q.lower().strip().encode()).hexdigest()[:16]

def get_cached(key: str):
    if key in question_cache:
        entry = question_cache[key]
        if time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]
    return None

def set_cache(key: str, data: dict):
    question_cache[key] = {"ts": time.time(), "data": data}

def calculate_evidence_strength(papers: List[Dict]) -> str:
    if not papers:
        return "insufficient"
    total = len(papers)
    recent = len([p for p in papers if p.get('year', 0) >= 2020])
    cited = len([p for p in papers if p.get('citations', 0) >= 50])
    score = 0
    if total >= 15: score += 2
    elif total >= 8: score += 1
    if recent >= 8: score += 2
    elif recent >= 4: score += 1
    if cited >= 5: score += 2
    elif cited >= 2: score += 1
    if score >= 5: return "strong"
    elif score >= 3: return "moderate"
    return "limited"

def get_related_questions(q: str) -> List[Dict]:
    import random
    filtered = [x for x in POPULAR_QUESTIONS if x['question'].lower() != q.lower()]
    return random.sample(filtered, min(4, len(filtered)))

# ========================
# GPT-4o mini
# ========================

async def call_gpt(prompt: str, system: str = None) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("No API key")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.3, "max_tokens": 2500}
        )
        if r.status_code != 200:
            raise Exception(f"GPT error: {r.status_code}")
        return r.json()["choices"][0]["message"]["content"]

async def analyze_question(question: str) -> dict:
    system = "Sen bir bilimsel araştırma asistanısın. Yanıtını SADECE JSON formatında ver."
    prompt = f"""Soru: "{question}"

JSON formatında yanıt ver:
{{
    "normalized_question": "Soruyu net şekilde yaz",
    "category": "Beslenme/Sağlık/Uyku/Psikoloji/Egzersiz/Teknoloji",
    "scientific_terms": ["terim1", "terim2"],
    "queries_tr": ["sorgu1", "sorgu2", "sorgu3"],
    "queries_en": ["query1", "query2", "query3", "query4", "query5"],
    "research_areas": ["alan1", "alan2"],
    "related_topics": ["konu1", "konu2"]
}}"""
    try:
        result = await call_gpt(prompt, system)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        return json.loads(result)
    except:
        return {"normalized_question": question, "category": "Sağlık", "queries_tr": [question], "queries_en": [question], "scientific_terms": [], "research_areas": [], "related_topics": []}

# ========================
# SEMANTIC SCHOLAR
# ========================

async def search_scholar(query: str, limit: int = 15) -> List[Dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": limit, "fields": "title,authors,year,venue,url,abstract,citationCount,isOpenAccess"}
            )
            if r.status_code == 200:
                for paper in r.json().get("data", []):
                    authors = paper.get("authors", [])
                    author_str = ", ".join([a.get("name", "") for a in authors[:3]])
                    if len(authors) > 3: author_str += " et al."
                    results.append({
                        "title": paper.get("title", ""),
                        "authors": author_str,
                        "year": paper.get("year"),
                        "venue": paper.get("venue", ""),
                        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "abstract": (paper.get("abstract") or "")[:400],
                        "citations": paper.get("citationCount", 0),
                        "open_access": paper.get("isOpenAccess", False)
                    })
    except Exception as e:
        print(f"Scholar error: {e}")
    return results

async def search_multiple(queries_tr: List[str], queries_en: List[str]) -> List[Dict]:
    all_results = []
    seen = set()
    all_queries = queries_en[:5] + queries_tr[:3]
    tasks = [search_scholar(q, 12) for q in all_queries]
    try:
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        for results in results_list:
            if isinstance(results, Exception): continue
            for p in results:
                title_lower = p.get("title", "").lower()
                if title_lower and title_lower not in seen:
                    seen.add(title_lower)
                    all_results.append(p)
    except: pass
    all_results.sort(key=lambda x: x.get('citations', 0), reverse=True)
    return all_results[:30]

# ========================
# SYNTHESIS
# ========================

async def synthesize(question: str, papers: List[Dict], analysis: dict, level: str = "medium") -> dict:
    if not papers:
        return {"summary": "Bu konuda yeterli kaynak bulunamadı.", "consensus": None, "key_findings": [], "conflicting_views": [], "research_gaps": [], "quality_note": "", "disclaimer": "Bu bilimsel literatür özetidir."}
    
    levels = {
        "simple": "Çok basit dilde yaz. Teknik terim kullanma.",
        "medium": "Orta seviyede, anlaşılır ama bilgilendirici yaz.",
        "academic": "Akademik ve detaylı yaz. Teknik terimler kullan."
    }
    
    system = f"""Sen bilimsel araştırma özetleyicisisin.
ASLA kesin hüküm verme. "Araştırmalar gösteriyor ki..." formatında yaz.
SEVİYE: {levels.get(level, levels['medium'])}
Yanıtını SADECE JSON formatında ver."""

    papers_text = ""
    for i, p in enumerate(papers[:15]):
        papers_text += f"[{i+1}] {p['title']} ({p['year']}) - Atıf: {p['citations']}\n"

    prompt = f"""Soru: "{question}"
Makaleler:
{papers_text}

JSON:
{{
    "summary": "2-3 paragraf özet",
    "consensus": "konsensüs varsa yaz, yoksa null",
    "key_findings": ["bulgu [kaynak]", "bulgu [kaynak]"],
    "conflicting_views": ["çelişki [kaynak]"],
    "research_gaps": ["eksik alan"],
    "quality_note": "güvenilirlik notu",
    "disclaimer": "uyarı metni"
}}"""
    try:
        result = await call_gpt(prompt, system)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        return json.loads(result)
    except:
        return {"summary": f"{len(papers)} makale bulundu.", "consensus": None, "key_findings": [], "conflicting_views": [], "research_gaps": [], "quality_note": "", "disclaimer": "Bu bilimsel literatür özetidir."}

# ========================
# MAIN PIPELINE
# ========================

async def process_question(question: str, level: str = "medium", user_id: int = None, ip: str = None) -> dict:
    print(f"[PIPELINE] {question[:40]}... (Level: {level})")
    
    analysis = await analyze_question(question)
    normalized = analysis.get("normalized_question", question)
    queries_tr = analysis.get("queries_tr", [question])
    queries_en = analysis.get("queries_en", [question])
    category = analysis.get("category", "Sağlık")
    
    papers = await search_multiple(queries_tr, queries_en)
    synthesis = await synthesize(normalized, papers, analysis, level)
    evidence = calculate_evidence_strength(papers)
    related = get_related_questions(question)
    
    # DB kayıt
    log_search(question, user_id=user_id, ip=ip, result_count=len(papers))
    
    return {
        "original_question": question,
        "normalized_question": normalized,
        "category": category,
        "scientific_terms": analysis.get("scientific_terms", []),
        "synthesis": synthesis,
        "papers": papers[:20],
        "stats": {
            "total_papers": len(papers),
            "recent_count": len([p for p in papers if p.get('year') and p['year'] >= 2020]),
            "highly_cited_count": len([p for p in papers if p.get('citations', 0) >= 50])
        },
        "evidence_strength": evidence,
        "related_questions": related,
        "explanation_level": level,
        "question_hash": hash_question(question),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ========================
# PAGE ROUTES
# ========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = await get_current_user(request)
    trending = get_trending(8)
    popular = trending if trending else POPULAR_QUESTIONS
    return templates.TemplateResponse("index.html", {
        "request": request, "user": user, "popular_questions": popular, "categories": CATEGORIES
    })

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse("result.html", {"request": request, "user": user})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    user = await get_current_user(request)
    return templates.TemplateResponse("about.html", {"request": request, "user": user})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = await get_current_user(request)
    if user: return RedirectResponse("/profile", 303)
    return templates.TemplateResponse("login.html", {"request": request, "user": None})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = await get_current_user(request)
    if user: return RedirectResponse("/profile", 303)
    return templates.TemplateResponse("register.html", {"request": request, "user": None})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = await get_current_user(request)
    if not user: return RedirectResponse("/login", 303)
    saved = get_saved_questions(user["id"], 20)
    history = get_search_history(user["id"], 20)
    followed = get_followed_topics(user["id"])
    stats = get_user_stats(user["id"])
    return templates.TemplateResponse("profile.html", {
        "request": request, "user": user, "saved_questions": saved,
        "search_history": history, "followed_topics": followed,
        "stats": stats, "categories": CATEGORIES
    })

@app.get("/category/{name}", response_class=HTMLResponse)
async def category_page(request: Request, name: str):
    user = await get_current_user(request)
    category = next((c for c in CATEGORIES if c['name'].lower() == name.lower()), None)
    if not category:
        return HTMLResponse("Kategori bulunamadı", 404)
    questions = [q for q in POPULAR_QUESTIONS if q.get('category') == category['name']]
    is_follow = is_following(user["id"], category['name']) if user else False
    return templates.TemplateResponse("category.html", {
        "request": request, "user": user, "category": category,
        "questions": questions, "is_following": is_follow
    })

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("auth_token")
    if token: delete_session(token)
    response = RedirectResponse("/", 303)
    response.delete_cookie("auth_token")
    return response

# ========================
# AUTH API
# ========================

@app.post("/api/register")
async def api_register(request: Request, email: str = Form(...), username: str = Form(...), password: str = Form(...), display_name: str = Form(None)):
    if len(username) < 3 or len(username) > 20:
        return JSONResponse({"error": "Kullanıcı adı 3-20 karakter olmalı."}, 400)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return JSONResponse({"error": "Kullanıcı adı sadece harf, rakam ve _ içerebilir."}, 400)
    if len(password) < 6:
        return JSONResponse({"error": "Şifre en az 6 karakter olmalı."}, 400)
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return JSONResponse({"error": "Geçerli email girin."}, 400)
    
    user_id = create_user(email, username, password, display_name)
    if not user_id:
        return JSONResponse({"error": "Bu email veya kullanıcı adı kullanılıyor."}, 400)
    
    token = create_session(user_id, get_client_ip(request))
    response = JSONResponse({"success": True})
    response.set_cookie("auth_token", token, max_age=30*24*60*60, httponly=True, samesite="lax")
    return response

@app.post("/api/login")
async def api_login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        return JSONResponse({"error": "Email/kullanıcı adı veya şifre hatalı."}, 401)
    
    token = create_session(user["id"], get_client_ip(request))
    response = JSONResponse({"success": True})
    response.set_cookie("auth_token", token, max_age=30*24*60*60, httponly=True, samesite="lax")
    return response

@app.post("/api/logout")
async def api_logout(request: Request):
    token = request.cookies.get("auth_token")
    if token: delete_session(token)
    response = JSONResponse({"success": True})
    response.delete_cookie("auth_token")
    return response

# ========================
# RESEARCH API
# ========================

@app.post("/api/research")
async def api_research(request: Request, question: str = Form(...), level: str = Form("medium")):
    ip = get_client_ip(request)
    if check_rate_limit(ip):
        return JSONResponse({"error": "Çok fazla istek. Bir dakika bekleyin."}, 429)
    
    question = question.strip()
    if not question or len(question) < 10 or len(question) > 500:
        return JSONResponse({"error": "Soru 10-500 karakter arası olmalı."}, 400)
    if level not in ["simple", "medium", "academic"]:
        level = "medium"
    
    user = await get_current_user(request)
    user_id = user["id"] if user else None
    
    cache_key = get_cache_key(question + level)
    cached = get_cached(cache_key)
    if cached:
        cached["from_cache"] = True
        if user: cached["is_saved"] = is_question_saved(user_id, question)
        return JSONResponse(cached)
    
    try:
        result = await process_question(question, level, user_id, ip)
        result["from_cache"] = False
        if user: result["is_saved"] = is_question_saved(user_id, question)
        set_cache(cache_key, result)
        return JSONResponse(result)
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return JSONResponse({"error": "Bir hata oluştu."}, 500)

# ========================
# SAVE/VOTE/FOLLOW APIs
# ========================

@app.post("/api/questions/save")
async def api_save(request: Request, question: str = Form(...), category: str = Form(None)):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmanız gerekiyor."}, 401)
    qid = save_question(user["id"], question, category)
    if qid:
        return JSONResponse({"success": True, "id": qid})
    return JSONResponse({"error": "Bu soru zaten kayıtlı."}, 400)

@app.delete("/api/questions/save/{qid}")
async def api_delete_saved(request: Request, qid: int):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmanız gerekiyor."}, 401)
    if delete_saved_question(user["id"], qid):
        return JSONResponse({"success": True})
    return JSONResponse({"error": "Soru bulunamadı."}, 404)

@app.post("/api/vote")
async def api_vote(request: Request, question_hash: str = Form(...), vote_type: str = Form(...)):
    user = await get_current_user(request)
    user_id = user["id"] if user else None
    ip = get_client_ip(request) if not user else None
    result = vote_question(question_hash, vote_type, user_id, ip)
    return JSONResponse(result)

@app.get("/api/vote/{qhash}")
async def api_get_vote(request: Request, qhash: str):
    user = await get_current_user(request)
    user_id = user["id"] if user else None
    ip = get_client_ip(request) if not user else None
    counts = get_vote_counts(qhash)
    user_vote = get_user_vote(qhash, user_id, ip)
    return JSONResponse({**counts, "user_vote": user_vote})

@app.post("/api/topics/follow")
async def api_follow(request: Request, category: str = Form(...)):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmanız gerekiyor."}, 401)
    follow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": True})

@app.post("/api/topics/unfollow")
async def api_unfollow(request: Request, category: str = Form(...)):
    user = await get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmanız gerekiyor."}, 401)
    unfollow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": False})

@app.post("/api/newsletter")
async def api_newsletter(request: Request, email: str = Form(...), frequency: str = Form("weekly")):
    user = await get_current_user(request)
    user_id = user["id"] if user else None
    if subscribe_newsletter(email, user_id, frequency):
        return JSONResponse({"success": True, "message": "Abone oldunuz!"})
    return JSONResponse({"error": "Bu email zaten kayıtlı."}, 400)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0-faz2", "timestamp": datetime.now(timezone.utc).isoformat()}
