# -*- coding: utf-8 -*-
"""AkademikSoru FAZ 3 - Gelişmiş Bilimsel Araştırma Platformu"""

import os, re, json, hashlib, secrets, asyncio
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import (
    init_database, create_user, authenticate_user, get_user_by_id,
    create_session, get_session, delete_session,
    save_question, get_saved_questions, delete_saved_question,
    vote_question, get_vote_counts, get_user_vote,
    follow_topic, unfollow_topic, get_followed_topics, is_following_topic,
    subscribe_newsletter, log_search, update_popular_cache,
    get_trending_questions, get_user_stats, get_search_history
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

rate_limit_store = {}

app = FastAPI(title="AkademikSoru", version="3.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.on_event("startup")
async def startup():
    init_database()

CATEGORIES = [
    {"name": "Sağlık", "icon": "🏥"},
    {"name": "Beslenme", "icon": "🥗"},
    {"name": "Psikoloji", "icon": "🧠"},
    {"name": "Spor", "icon": "🏃"},
    {"name": "Teknoloji", "icon": "💻"},
    {"name": "Çevre", "icon": "🌍"},
    {"name": "Eğitim", "icon": "📚"},
    {"name": "Uyku", "icon": "😴"},
]

POPULAR_QUESTIONS = [
    {"question": "Kahve içmek sağlığa zararlı mı?", "icon": "☕", "category": "Beslenme", "preview": "Kahve tüketiminin kalp sağlığı ve bilişsel fonksiyonlar üzerindeki etkileri...", "evidence_level": "strong"},
    {"question": "Günde kaç saat uyumalıyız?", "icon": "😴", "category": "Uyku", "preview": "Yaşa göre ideal uyku süresi ve sağlık etkileri...", "evidence_level": "strong"},
    {"question": "Meditasyon gerçekten işe yarıyor mu?", "icon": "🧘", "category": "Psikoloji", "preview": "Mindfulness ve meditasyonun stres üzerindeki etkileri...", "evidence_level": "strong"},
    {"question": "Yapay tatlandırıcılar zararlı mı?", "icon": "🍬", "category": "Beslenme", "preview": "Aspartam ve diğer tatlandırıcıların güvenliği...", "evidence_level": "moderate"},
]

def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("auth_token")
    if not token: return None
    session = get_session(token)
    if not session: return None
    return get_user_by_id(session["user_id"])

def hash_question(question: str) -> str:
    return hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]

def check_rate_limit(ip: str) -> bool:
    now = datetime.now().timestamp()
    if ip in rate_limit_store:
        requests, window_start = rate_limit_store[ip]
        if now - window_start > 60:
            rate_limit_store[ip] = (1, now)
            return True
        elif requests >= 15:
            return False
        rate_limit_store[ip] = (requests + 1, window_start)
        return True
    rate_limit_store[ip] = (1, now)
    return True

def detect_category(q: str) -> str:
    q = q.lower()
    if any(w in q for w in ["kahve", "yemek", "beslenme", "diyet", "vitamin", "protein"]): return "Beslenme"
    if any(w in q for w in ["uyku", "uyumak"]): return "Uyku"
    if any(w in q for w in ["depresyon", "anksiyete", "stres", "psikoloji", "meditasyon"]): return "Psikoloji"
    if any(w in q for w in ["spor", "egzersiz", "koşu"]): return "Spor"
    if any(w in q for w in ["yapay zeka", "teknoloji", "bilgisayar"]): return "Teknoloji"
    if any(w in q for w in ["iklim", "çevre"]): return "Çevre"
    if any(w in q for w in ["eğitim", "öğrenme"]): return "Eğitim"
    return "Sağlık"

async def call_gpt(messages: list, max_tokens: int = 2000) -> str:
    if not OPENAI_API_KEY: return ""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4o-mini", "messages": messages, "max_tokens": max_tokens, "temperature": 0.3})
            return r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            print(f"GPT Error: {e}")
            return ""

async def generate_search_queries(question: str) -> list:
    prompt = f'Soru: "{question}"\nBu soru için akademik arama yapılacak 3 İngilizce sorgu oluştur.\nJSON: {{"queries": ["q1", "q2", "q3"]}}'
    result = await call_gpt([{"role": "user", "content": prompt}], 200)
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m: return json.loads(m.group()).get("queries", [question])[:3]
    except: pass
    return [question]

async def synthesize_results(question: str, papers: list, level: str = "medium") -> dict:
    levels = {"simple": "Çok basit, teknik terim kullanma.", "medium": "Orta seviye, genel kültür düzeyinde.", "academic": "Akademik, detaylı teknik terimlerle."}
    papers_text = "\n".join([f"{i}. {p.get('title','?')} (Yıl:{p.get('year','?')}, Atıf:{p.get('citationCount',0)})\n   {(p.get('abstract') or '')[:400]}" for i,p in enumerate(papers[:8],1)])
    prompt = f'''Soru: "{question}"
Makaleler:{papers_text}

GÖREV: {levels.get(level, levels["medium"])}
JSON formatında yanıt ver:
{{"summary": "3-5 paragraf Türkçe özet", "evidence_strength": "strong/moderate/limited/insufficient", "evidence_description": "Kanıt gücü açıklaması", "key_points": ["Nokta 1", "Nokta 2"], "limitations": "Sınırlılıklar", "related_questions": ["Soru 1", "Soru 2"]}}'''
    result = await call_gpt([{"role": "user", "content": prompt}], 2000)
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m: return json.loads(m.group())
    except: pass
    return {"summary": result or "Yeterli bilgi bulunamadı.", "evidence_strength": "insufficient", "evidence_description": "Kaynak bulunamadı.", "key_points": [], "limitations": "", "related_questions": []}

async def analyze_paper_deeply(paper: dict, question: str) -> dict:
    """FAZ 3: Makaleyi derinlemesine analiz et - İngilizce içeriği Türkçe'ye çevir"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or ""
    
    prompt = f'''Araştırılan Soru: "{question}"

Makale: {title}
Özet (İngilizce): {abstract}

GÖREV:
1. Bu makaleden soruyla ilgili EN ÖNEMLİ 3 bulguyu çıkar
2. Her bulguyu TÜRKÇE'ye çevir ve açıkla
3. Orijinal İngilizce cümleyi de ekle
4. Her bulgunun günlük hayatta ne anlama geldiğini yaz

JSON formatı:
{{
    "relevance_score": 0-100,
    "main_finding": "Makalenin ana bulgusu (Türkçe, 1-2 cümle)",
    "key_insights": [
        {{
            "turkish": "Türkçe çeviri ve açıklama",
            "original": "Original English sentence from abstract",
            "explanation": "Bu günlük hayatta ne anlama geliyor? Basit açıklama"
        }}
    ],
    "methodology_note": "Araştırma yöntemi (örn: 1000 kişilik çalışma, meta-analiz)",
    "practical_takeaway": "Peki ne yapmalıyız? (1 cümle pratik öneri)"
}}'''
    
    result = await call_gpt([{"role": "user", "content": prompt}], 1500)
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m: return json.loads(m.group())
    except: pass
    return {"relevance_score": 50, "main_finding": "Analiz yapılamadı.", "key_insights": [], "methodology_note": "", "practical_takeaway": ""}

async def search_semantic_scholar(query: str, limit: int = 10) -> list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(f"{SEMANTIC_SCHOLAR_API}/paper/search", params={"query": query, "limit": limit, "fields": "title,abstract,year,citationCount,authors,url,venue,openAccessPdf"})
            if r.status_code == 200: return r.json().get("data", [])
        except: pass
    return []

async def search_papers(question: str) -> list:
    queries = await generate_search_queries(question)
    all_papers, seen = [], set()
    results = await asyncio.gather(*[search_semantic_scholar(q, 8) for q in queries])
    for papers in results:
        for p in papers:
            t = p.get("title", "").lower()
            if t and t not in seen:
                seen.add(t)
                all_papers.append(p)
    all_papers.sort(key=lambda x: x.get("citationCount", 0), reverse=True)
    return all_papers[:15]

# PAGES
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    trending = get_trending_questions(6)
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "categories": CATEGORIES, "popular_questions": trending or POPULAR_QUESTIONS})

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    return templates.TemplateResponse("result.html", {"request": request, "user": get_current_user(request)})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request, "user": get_current_user(request)})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request): return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if get_current_user(request): return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user: return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "saved_questions": get_saved_questions(user["id"]), "followed_topics": get_followed_topics(user["id"]), "search_history": get_search_history(user["id"], 20), "stats": get_user_stats(user["id"]), "categories": CATEGORIES})

@app.get("/category/{name}", response_class=HTMLResponse)
async def category_page(request: Request, name: str):
    user = get_current_user(request)
    cat = next((c for c in CATEGORIES if c["name"] == name), None)
    if not cat: return RedirectResponse(url="/", status_code=303)
    is_following = is_following_topic(user["id"], name) if user else False
    questions = [q for q in POPULAR_QUESTIONS if q["category"] == name]
    return templates.TemplateResponse("category.html", {"request": request, "user": user, "category": cat, "questions": questions, "is_following": is_following})

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("auth_token")
    if token: delete_session(token)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("auth_token")
    return response

# AUTH API
@app.post("/api/register")
async def api_register(request: Request, email: str = Form(...), username: str = Form(...), password: str = Form(...), display_name: str = Form("")):
    if len(password) < 6: return JSONResponse({"error": "Şifre en az 6 karakter olmalı"}, status_code=400)
    user_id = create_user(email, username, password, display_name or username)
    if not user_id: return JSONResponse({"error": "Bu email veya kullanıcı adı kullanılıyor"}, status_code=400)
    token = create_session(user_id, request.client.host if request.client else "", request.headers.get("user-agent", ""))
    response = JSONResponse({"success": True, "redirect": "/profile"})
    response.set_cookie(key="auth_token", value=token, httponly=True, samesite="lax", max_age=30*24*60*60)
    return response

@app.post("/api/login")
async def api_login(request: Request, email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user: return JSONResponse({"error": "Email veya şifre hatalı"}, status_code=401)
    token = create_session(user["id"], request.client.host if request.client else "", request.headers.get("user-agent", ""))
    response = JSONResponse({"success": True, "redirect": "/profile"})
    response.set_cookie(key="auth_token", value=token, httponly=True, samesite="lax", max_age=30*24*60*60)
    return response

# RESEARCH API
@app.post("/api/research")
async def api_research(request: Request, question: str = Form(...), level: str = Form("medium")):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip): return JSONResponse({"error": "Çok fazla istek. Lütfen bekleyin."}, status_code=429)
    question = question.strip()
    if len(question) < 10: return JSONResponse({"error": "Soru en az 10 karakter olmalı"}, status_code=400)
    user = get_current_user(request)
    log_search(user["id"] if user else None, question, ip)
    category = detect_category(question)
    papers = await search_papers(question)
    if not papers:
        return JSONResponse({"question": question, "category": category, "summary": "Bu konu hakkında yeterli akademik kaynak bulunamadı.", "evidence_strength": "insufficient", "evidence_description": "Yeterli kaynak bulunamadı.", "papers": [], "key_points": [], "related_questions": [], "paper_count": 0, "question_hash": hash_question(question)})
    synthesis = await synthesize_results(question, papers, level)
    formatted_papers = []
    for p in papers[:10]:
        authors = p.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in authors[:3]])
        if len(authors) > 3: author_names += " et al."
        formatted_papers.append({"id": p.get("paperId", ""), "title": p.get("title", ""), "abstract": p.get("abstract", ""), "year": p.get("year"), "citations": p.get("citationCount", 0), "authors": author_names, "venue": p.get("venue", ""), "url": p.get("url", ""), "pdf_url": p.get("openAccessPdf", {}).get("url") if p.get("openAccessPdf") else None})
    update_popular_cache(question, category, synthesis.get("summary", "")[:200], synthesis.get("evidence_strength", "moderate"))
    return JSONResponse({"question": question, "category": category, "summary": synthesis.get("summary", ""), "evidence_strength": synthesis.get("evidence_strength", "moderate"), "evidence_description": synthesis.get("evidence_description", ""), "papers": formatted_papers, "key_points": synthesis.get("key_points", []), "limitations": synthesis.get("limitations", ""), "related_questions": synthesis.get("related_questions", []), "paper_count": len(papers), "level": level, "question_hash": hash_question(question)})

@app.post("/api/paper/analyze")
async def api_analyze_paper(request: Request, paper_id: str = Form(...), paper_title: str = Form(...), paper_abstract: str = Form(""), question: str = Form(...)):
    """FAZ 3: Derin makale analizi - İngilizce içeriği Türkçe'ye çevirir"""
    paper = {"paperId": paper_id, "title": paper_title, "abstract": paper_abstract}
    analysis = await analyze_paper_deeply(paper, question)
    return JSONResponse({"success": True, "paper_id": paper_id, "analysis": analysis})

# SAVE/VOTE/FOLLOW API
@app.post("/api/questions/save")
async def api_save_question(request: Request, question: str = Form(...), category: str = Form(""), result_data: str = Form("")):
    user = get_current_user(request)
    if not user: return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    save_id = save_question(user["id"], question, category, result_data)
    return JSONResponse({"success": True, "id": save_id}) if save_id else JSONResponse({"error": "Kaydetme başarısız"}, status_code=400)

@app.delete("/api/questions/save/{save_id}")
async def api_delete_saved(request: Request, save_id: int):
    user = get_current_user(request)
    if not user: return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    return JSONResponse({"success": True}) if delete_saved_question(save_id, user["id"]) else JSONResponse({"error": "Silme başarısız"}, status_code=400)

@app.post("/api/vote")
async def api_vote(request: Request, question_hash: str = Form(...), vote_type: str = Form(...)):
    user = get_current_user(request)
    ip = request.client.host if request.client else ""
    vote_question(user["id"] if user else None, question_hash, vote_type if vote_type != "none" else None, ip)
    counts = get_vote_counts(question_hash)
    return JSONResponse({"success": True, "upvotes": counts["upvotes"], "downvotes": counts["downvotes"], "user_vote": get_user_vote(user["id"] if user else None, question_hash, ip)})

@app.get("/api/vote/{question_hash}")
async def api_get_vote(request: Request, question_hash: str):
    user = get_current_user(request)
    ip = request.client.host if request.client else ""
    counts = get_vote_counts(question_hash)
    return JSONResponse({"upvotes": counts["upvotes"], "downvotes": counts["downvotes"], "user_vote": get_user_vote(user["id"] if user else None, question_hash, ip)})

@app.post("/api/topics/follow")
async def api_follow_topic(request: Request, category: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    follow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": True})

@app.post("/api/topics/unfollow")
async def api_unfollow_topic(request: Request, category: str = Form(...)):
    user = get_current_user(request)
    if not user: return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    unfollow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": False})

@app.post("/api/newsletter/subscribe")
async def api_subscribe_newsletter(request: Request, email: str = Form(""), frequency: str = Form("weekly")):
    user = get_current_user(request)
    if not email and user: email = user.get("email", "")
    if not email: return JSONResponse({"error": "Email gerekli"}, status_code=400)
    subscribe_newsletter(email, user["id"] if user else None, frequency)
    return JSONResponse({"success": True, "message": "Abonelik başarılı!"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
