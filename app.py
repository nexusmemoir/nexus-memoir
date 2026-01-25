# -*- coding: utf-8 -*-
"""AkademikSoru FAZ 3.1 - GPT-5-mini + Gelişmiş Araştırma - DÜZELTİLMİŞ"""

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

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"

rate_limit_store = {}

app = FastAPI(title="AkademikSoru", version="3.1")
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

async def call_gpt(messages: str, max_tokens: int = 4096, model: str = "gpt-4.1-mini") -> str:
    """OpenAI API - Chat Completions (daha güvenilir)"""
    if not OPENAI_API_KEY:
        return ""

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            # Chat Completions API kullan (daha stabil)
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": messages}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }

            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )

            if r.status_code != 200:
                print(f"[GPT] ❌ API Error {r.status_code}: {r.text}")
                return ""

            data = r.json()
            
            # Chat Completions yanıt yapısı
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    if isinstance(content, str) and content.strip():
                        # Finish reason kontrolü
                        finish_reason = choice.get("finish_reason")
                        if finish_reason == "length":
                            print(f"[GPT] ⚠️ Yanıt max_tokens limitine ulaştı, kısmi sonuç")
                        return content.strip()
            
            print(f"[GPT] ⚠️ Beklenmeyen yanıt yapısı")
            print(f"[GPT] Keys: {list(data.keys())[:10]}")
            return ""

        except Exception as e:
            print(f"[GPT] ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            return ""


async def generate_search_queries(question: str) -> list:
    """Gelişmiş sorgu üretimi - GPT-5-mini ile"""
    prompt = f'''Türkçe Soru: "{question}"

SEN BİR AKADEMİK ARAŞTIRMA UZMANISIM. Bu soruyu ANLAMSAL olarak analiz et ve Semantic Scholar'da bu soruyu yanıtlayacak makaleleri bulmak için AKILLI İngilizce sorgular oluştur.

STRATEJİ:
1. **Geniş Kavramsal Sorgu**: Sorunun ana bilimsel kavramlarını içeren genel sorgu (3-5 kelime)
2. **Spesifik Araştırma Sorgusu**: Tam olarak bu sorunun araştırıldığı çalışmaları bul (4-7 kelime) 
3. **Metodolojik Sorgu**: Meta-analysis, systematic review, clinical trial gibi terimlerle (5-8 kelime)
4. **Alternatif Terimler**: Aynı konunun farklı bilimsel terimleriyle (3-6 kelime)
5. **İlgili Alan Sorgusu**: Bu sorunun bağlı olduğu geniş araştırma alanı (3-5 kelime)

KURALLAR:
- Kelime kelime çeviri YAPMA, ANLAMI çevir
- Akademik terminoloji kullan
- Her sorgu NET ve ARAMAYI DARALTACAK şekilde olmalı

ÖRNEK:
Soru: "Kahve içmek kalbe zararlı mı?"
Çıktı:
```json
{{
    "queries": [
        "coffee consumption cardiovascular health",
        "coffee intake heart disease risk",
        "coffee cardiovascular effects meta-analysis",
        "caffeine cardiac health outcomes",
        "dietary caffeine cardiovascular disease"
    ]
}}
```

ŞİMDİ YUKARIDAKİ SORU İÇİN SADECE JSON çıktısı ver (başka hiçbir şey yazma):'''
    
    result = await call_gpt(prompt, 1000)  # 800 -> 1000 token
    
    if not result:
        print("[SORGU] ❌ GPT yanıt vermedi, fallback kullanılıyor")
        return generate_fallback_queries(question)
    
    try:
        # JSON çıkar (markdown backtick'leri temizle)
        clean = result.replace("```json", "").replace("```", "").strip()
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m: 
            data = json.loads(m.group())
            queries = data.get("queries", [])[:5]
            queries = [q.strip() for q in queries if len(q.strip()) > 5]
            
            if len(queries) >= 3:
                print(f"[SORGU] ✅ {len(queries)} sorgu üretildi: {queries}")
                return queries
    except Exception as e:
        print(f"[SORGU] ⚠️ Parse hatası: {e}")
    
    print("[SORGU] ⚠️ Fallback kullanılıyor")
    return generate_fallback_queries(question)

def generate_fallback_queries(question: str) -> list:
    """Manuel akıllı sorgular - GPT başarısız olursa"""
    q_lower = question.lower()
    
    if "kahve" in q_lower: 
        return ["coffee consumption health effects", "caffeine cardiovascular impact", "coffee intake disease risk", "coffee health meta-analysis", "caffeine health outcomes"]
    elif "uyku" in q_lower:
        return ["sleep duration health outcomes", "sleep deprivation effects", "optimal sleep recommendations", "sleep health meta-analysis", "sleep quality health"]
    elif "meditasyon" in q_lower or "mindfulness" in q_lower:
        return ["meditation stress reduction", "mindfulness mental health", "meditation brain effects", "mindfulness intervention", "meditation health benefits"]
    elif "vitamin" in q_lower:
        return ["vitamin supplementation health", "micronutrient deficiency effects", "vitamin intake recommendations", "vitamin supplementation meta-analysis", "vitamin health outcomes"]
    elif "spor" in q_lower or "egzersiz" in q_lower:
        return ["exercise health benefits", "physical activity health outcomes", "exercise disease prevention", "physical activity recommendations", "exercise health meta-analysis"]
    else:
        base = question.replace("?", "").replace("mı", "").replace("mi", "").strip()
        return [f"{base} health effects", f"{base} research study", f"{base} meta-analysis", f"{base} systematic review", f"{base} health outcomes"]

async def check_paper_relevance(question: str, paper: dict) -> dict:
    """GPT-5-mini ile alakalılık kontrolü"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or ""
    
    if not abstract or len(abstract) < 50:
        return {"score": 20, "reason": "Özet eksik"}
    
    prompt = f'''SORU: "{question}"

MAKALE:
Başlık: {title}
Özet: {abstract[:800]}

GÖREV: Bu makale soruyu yanıtlamak için NE KADAR ALAKALI?

SKORLAMA:
- 0-20: Tamamen alakasız
- 21-40: Uzaktan ilgili
- 41-60: Kısmen alakalı
- 61-80: Alakalı
- 81-100: Çok alakalı

SADECE JSON çıktısı ver (başka hiçbir şey yazma):
```json
{{"score": 0-100, "reason": "Kısa açıklama"}}
```'''
    
    result = await call_gpt(prompt, 500)  # 300 -> 500 token
    
    if not result:
        return simple_relevance_check(question, title, abstract)
    
    try:
        clean = result.replace("```json", "").replace("```", "").strip()
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m:
            data = json.loads(m.group())
            score = int(data.get("score", 50))
            reason = data.get("reason", "")
            print(f"[RELEVANCE] Skor: {score} - {title[:40]}")
            return {"score": score, "reason": reason}
    except Exception as e:
        print(f"[RELEVANCE] Parse hatası: {e}")
    
    return simple_relevance_check(question, title, abstract)

def simple_relevance_check(question: str, title: str, abstract: str) -> dict:
    """Basit keyword tabanlı check - fallback"""
    q_words = set(question.lower().split())
    title_words = set(title.lower().split())
    abstract_words = set(abstract.lower().split())
    
    title_match = len(q_words & title_words) / max(len(q_words), 1)
    abstract_match = len(q_words & abstract_words) / max(len(q_words), 1)
    
    score = int((title_match * 60 + abstract_match * 40) * 100)
    return {"score": score, "reason": "Keyword match (fallback)"}

async def search_semantic_scholar(query: str, limit: int = 20) -> list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(3):
            try:
                r = await client.get(
                    f"{SEMANTIC_SCHOLAR_API}/paper/search",
                    params={
                        "query": query,
                        "limit": limit,
                        "fields": "paperId,title,abstract,year,citationCount,authors,url,venue,openAccessPdf,publicationTypes"
                    }
                )
                if r.status_code == 200:
                    return r.json().get("data", [])
                if r.status_code == 429:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
            except Exception as e:
                print(f"Semantic Scholar Error: {e}")
                return []
    return []


async def search_papers(question: str) -> list:
    """Gelişmiş makale arama"""
    print(f"\n{'='*80}")
    print(f"[ARAŞTIRMA] Soru: {question}")
    print(f"{'='*80}\n")
    
    # 1. Sorgular üret
    queries = await generate_search_queries(question)
    
    # 2. Makaleleri topla
    all_papers, seen_ids = [], set()
    results = await asyncio.gather(*[search_semantic_scholar(q, 25) for q in queries])
    
    for papers in results:
        for p in papers:
            paper_id = p.get("paperId", "")
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                all_papers.append(p)
    
    print(f"\n[ARAŞTIRMA] 📚 Toplam {len(all_papers)} makale bulundu")
    
    if len(all_papers) == 0:
        print("[ARAŞTIRMA] ❌ HİÇ MAKALE YOK!")
        return []
    
    # 3. Relevance check (ilk 30 makale)
    papers_to_check = all_papers[:30]
    print(f"\n[ARAŞTIRMA] 🎯 {len(papers_to_check)} makale kontrol ediliyor...\n")
    
    relevance_scores = []
    for i in range(0, len(papers_to_check), 10):
        batch = papers_to_check[i:i+10]
        print(f"[ARAŞTIRMA] Batch {i//10 + 1} işleniyor...")
        batch_checks = await asyncio.gather(*[check_paper_relevance(question, p) for p in batch])
        relevance_scores.extend(batch_checks)
    
    for i, check in enumerate(relevance_scores):
        papers_to_check[i]["relevance_score"] = check.get("score", 50)
        papers_to_check[i]["relevance_reason"] = check.get("reason", "")
    
    # 4. Filtrele (skor >= 35)
    filtered_papers = [p for p in papers_to_check if p.get("relevance_score", 0) >= 35]
    print(f"\n[ARAŞTIRMA] ✅ {len(filtered_papers)} alakalı makale (skor >= 35)")
    
    if len(filtered_papers) == 0:
        print(f"[ARAŞTIRMA] ⚠️ Threshold düşürülüyor...")
        filtered_papers = [p for p in papers_to_check if p.get("relevance_score", 0) >= 25]
        print(f"[ARAŞTIRMA] 📌 {len(filtered_papers)} makale (skor >= 25)")
    
    if len(filtered_papers) == 0:
        print("[ARAŞTIRMA] ❌ ALAKALI MAKALE YOK!")
        return []
    
    # 5. Sıralama
    for p in filtered_papers:
        rel_score = p.get("relevance_score", 0)
        citations = p.get("citationCount", 0)
        year = p.get("year", 2000)
        
        current_year = datetime.now().year
        recency_bonus = max(0, 10 - (current_year - year)) if year >= 2020 else 0
        normalized_citations = min(citations / 50, 30)
        combined_score = (rel_score * 0.6) + normalized_citations + recency_bonus
        
        p["combined_score"] = combined_score
    
    filtered_papers.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
    
    final = filtered_papers[:20]
    print(f"\n[ARAŞTIRMA] 🎖️ En iyi {len(final)} makale seçildi\n")
    
    return final

async def synthesize_results(question: str, papers: list, level: str = "medium") -> dict:
    """GPT-5-mini ile sentez"""
    levels = {
        "simple": "10 yaşındaki bir çocuğa anlatır gibi, ÇOK BASİT dil kullan.", 
        "medium": "Lise mezunu bir yetişkine anlatır gibi, ANLAŞILİR dil kullan.", 
        "academic": "Üniversite öğrencisine anlatır gibi, DETAYLI ve teknik terimlerle açıkla."
    }
    
    if not papers:
        return {
            "summary": "Bu konu hakkında yeterli akademik kaynak bulunamadı.",
            "evidence_strength": "insufficient",
            "evidence_description": "Alakalı makale yok.",
            "key_points": [],
            "limitations": "Yeterli veri yok",
            "related_questions": []
        }
    
    relevant_papers = sorted(papers, key=lambda x: x.get("combined_score", 0), reverse=True)[:12]
    
    print(f"\n[SENTEZ] 📝 {len(relevant_papers)} makale ile sentez yapılıyor...")
    
    papers_text = "\n\n".join([
        f"""MAKALE {i}:
Başlık: {p.get('title', '?')}
Yıl: {p.get('year', '?')} | Atıf: {p.get('citationCount', 0)} | Skor: {p.get('relevance_score', 'N/A')}
Özet: {(p.get('abstract') or 'Özet yok')[:600]}"""
        for i, p in enumerate(relevant_papers, 1)
    ])
    
    prompt = f'''SORU: "{question}"

MAKALELER:
{papers_text}

GÖREV: Bu makaleleri analiz edip soruyu TÜRKÇE yanıtla.

KURALLAR:
1. Makaleler İngilizce ama TAMAMEN TÜRKÇE yaz
2. SADECE alakalı makaleleri kullan
3. Çelişkiler varsa göster
4. Madde işareti KULLANMA - düz paragraf yaz
5. Türkçe karakterler düzgün (ç, ğ, ı, ö, ş, ü)

AÇIKLAMA: {levels.get(level, levels["medium"])}

KANIT GÜCÜ:
- strong: 5+ kaliteli çalışma, tutarlı
- moderate: 3-5 çalışma, çoğunlukla tutarlı
- limited: 1-2 çalışma veya çelişkili
- insufficient: Yetersiz veri

SADECE JSON çıktısı ver:
```json
{{
    "summary": "3-4 paragraf TÜRKÇE özet. Düz paragraf, madde yok.",
    "evidence_strength": "strong/moderate/limited/insufficient",
    "evidence_description": "Kanıt gücü açıklaması",
    "key_points": ["Nokta 1", "Nokta 2", "Nokta 3"],
    "limitations": "Sınırlılıklar - neyi bilmiyoruz?",
    "related_questions": ["Soru 1", "Soru 2", "Soru 3"]
}}
```'''
    
    result = await call_gpt(prompt, 3000)
    
    if not result:
        print("[SENTEZ] ❌ GPT yanıt vermedi!")
        return {
            "summary": "Sentez yapılamadı.",
            "evidence_strength": "insufficient",
            "evidence_description": "GPT hatası.",
            "key_points": [],
            "limitations": "Teknik hata",
            "related_questions": []
        }
    
    try:
        clean = result.replace("```json", "").replace("```", "").strip()
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m: 
            data = json.loads(m.group())
            
            summary = data.get("summary", "")
            if not summary or len(summary) < 100:
                print("[SENTEZ] ⚠️ Özet çok kısa")
                data["summary"] = "Bulunan makaleler soruyu doğrudan yanıtlamıyor."
                data["evidence_strength"] = "insufficient"
            else:
                print(f"[SENTEZ] ✅ Başarılı! ({len(summary)} karakter)")
            
            return data
    except Exception as e:
        print(f"[SENTEZ] ❌ Parse hatası: {e}")
        print(f"[SENTEZ] Raw: {result[:300]}")
    
    return {
        "summary": "Sentez yapılamadı.", 
        "evidence_strength": "insufficient", 
        "evidence_description": "Parse hatası.", 
        "key_points": [], 
        "limitations": "Teknik hata", 
        "related_questions": []
    }

async def analyze_paper_deeply(paper: dict, question: str) -> dict:
    """Derin makale analizi"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or ""
    
    if not abstract:
        return {
            "relevance_score": 0,
            "main_finding": "Özet yok.",
            "key_insights": [],
            "methodology_note": "",
            "practical_takeaway": ""
        }
    
    prompt = f'''SORU: "{question}"

MAKALE:
Başlık: {title}
Özet: {abstract}

GÖREV:
1. EN ÖNEMLİ bulguları çıkar
2. TÜRKÇE çevir ve açıkla
3. Orijinal İngilizce cümleyi göster
4. Günlük hayatta ne demek?

SADECE JSON çıktısı ver:
```json
{{
    "relevance_score": 0-100,
    "main_finding": "ANA bulgu (TÜRKÇE)",
    "key_insights": [
        {{
            "turkish": "TÜRKÇE açıklama",
            "original": "Orijinal İngilizce",
            "explanation": "Günlük hayatta ne demek?"
        }}
    ],
    "methodology_note": "Araştırma yöntemi",
    "practical_takeaway": "PRATİK öneri"
}}
```'''
    
    result = await call_gpt(prompt, 1500)
    
    if not result:
        return {"relevance_score": 50, "main_finding": "Analiz yapılamadı.", "key_insights": [], "methodology_note": "", "practical_takeaway": ""}
    
    try:
        clean = result.replace("```json", "").replace("```", "").strip()
        m = re.search(r'\{.*\}', clean, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"Derin analiz hatası: {e}")
    
    return {"relevance_score": 50, "main_finding": "Parse hatası.", "key_insights": [], "methodology_note": "", "practical_takeaway": ""}

# PAGES
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    trending = get_trending_questions(6)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "categories": CATEGORIES,
        "popular_questions": trending or POPULAR_QUESTIONS
    })

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    return templates.TemplateResponse("result.html", {
        "request": request,
        "user": get_current_user(request)
    })

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {
        "request": request,
        "user": get_current_user(request)
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/profile", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "saved_questions": get_saved_questions(user["id"]),
        "followed_topics": get_followed_topics(user["id"]),
        "search_history": get_search_history(user["id"], 20),
        "stats": get_user_stats(user["id"]),
        "categories": CATEGORIES
    })

@app.get("/category/{name}", response_class=HTMLResponse)
async def category_page(request: Request, name: str):
    user = get_current_user(request)
    cat = next((c for c in CATEGORIES if c["name"] == name), None)
    if not cat:
        return RedirectResponse(url="/", status_code=303)
    is_following = is_following_topic(user["id"], name) if user else False
    questions = [q for q in POPULAR_QUESTIONS if q["category"] == name]
    return templates.TemplateResponse("category.html", {
        "request": request,
        "user": user,
        "category": cat,
        "questions": questions,
        "is_following": is_following
    })

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("auth_token")
    if token:
        delete_session(token)
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("auth_token")
    return response

# AUTH API
@app.post("/api/register")
async def api_register(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form("")
):
    if len(password) < 6:
        return JSONResponse({"error": "Şifre en az 6 karakter olmalı"}, status_code=400)
    
    user_id = create_user(email, username, password, display_name or username)
    if not user_id:
        return JSONResponse({"error": "Bu email veya kullanıcı adı kullanılıyor"}, status_code=400)
    
    token = create_session(
        user_id,
        request.client.host if request.client else "",
        request.headers.get("user-agent", "")
    )
    
    response = JSONResponse({"success": True, "redirect": "/profile"})
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=30*24*60*60
    )
    return response

@app.post("/api/login")
async def api_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    user = authenticate_user(email, password)
    if not user:
        return JSONResponse({"error": "Email veya şifre hatalı"}, status_code=401)
    
    token = create_session(
        user["id"],
        request.client.host if request.client else "",
        request.headers.get("user-agent", "")
    )
    
    response = JSONResponse({"success": True, "redirect": "/profile"})
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=30*24*60*60
    )
    return response

@app.get("/api/health/openai")
async def api_health_openai():
    """OpenAI bağlantısı test endpoint'i"""
    if not OPENAI_API_KEY:
        return JSONResponse({"ok": False, "error": "OPENAI_API_KEY boş"}, status_code=500)

    test_prompt = "Sadece şu kelimeyi döndür: OK"

    try:
        out = await call_gpt(test_prompt, max_tokens=20)
        out_clean = (out or "").strip()

        return JSONResponse({
            "ok": out_clean.upper().startswith("OK"),
            "model": "gpt-5-mini",
            "output": out_clean[:200]
        })
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# RESEARCH API
@app.post("/api/research")
async def api_research(
    request: Request,
    question: str = Form(...),
    level: str = Form("medium")
):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        return JSONResponse({"error": "Çok fazla istek. Lütfen bekleyin."}, status_code=429)
    
    question = question.strip()
    if len(question) < 10:
        return JSONResponse({"error": "Soru en az 10 karakter olmalı"}, status_code=400)
    
    user = get_current_user(request)
    log_search(user["id"] if user else None, question, ip)
    
    category = detect_category(question)
    papers = await search_papers(question)
    
    if not papers:
        return JSONResponse({
            "question": question,
            "category": category,
            "summary": "Bu konu hakkında yeterli akademik kaynak bulunamadı. Lütfen sorunuzu farklı şekilde formüle edin veya daha genel bir soru sorun.",
            "evidence_strength": "insufficient",
            "evidence_description": "Alakalı makale bulunamadı.",
            "papers": [],
            "key_points": [],
            "related_questions": [],
            "paper_count": 0,
            "question_hash": hash_question(question)
        })
    
    synthesis = await synthesize_results(question, papers, level)
    
    # Format papers
    formatted_papers = []
    for p in papers[:20]:
        authors = p.get("authors", [])
        author_names = ", ".join([a.get("name", "") for a in authors[:3]])
        if len(authors) > 3:
            author_names += " et al."
        
        formatted_papers.append({
            "id": p.get("paperId", ""),
            "title": p.get("title", ""),
            "abstract": p.get("abstract", ""),
            "year": p.get("year"),
            "citations": p.get("citationCount", 0),
            "authors": author_names,
            "venue": p.get("venue", ""),
            "url": p.get("url", ""),
            "pdf_url": p.get("openAccessPdf", {}).get("url") if p.get("openAccessPdf") else None,
            "relevance_score": p.get("relevance_score", 0)
        })
    
    update_popular_cache(
        question,
        category,
        synthesis.get("summary", "")[:200],
        synthesis.get("evidence_strength", "moderate")
    )
    
    return JSONResponse({
        "question": question,
        "category": category,
        "summary": synthesis.get("summary", ""),
        "evidence_strength": synthesis.get("evidence_strength", "moderate"),
        "evidence_description": synthesis.get("evidence_description", ""),
        "papers": formatted_papers,
        "key_points": synthesis.get("key_points", []),
        "limitations": synthesis.get("limitations", ""),
        "related_questions": synthesis.get("related_questions", []),
        "paper_count": len(papers),
        "level": level,
        "question_hash": hash_question(question)
    })

@app.post("/api/paper/analyze")
async def api_analyze_paper(
    request: Request,
    paper_id: str = Form(...),
    paper_title: str = Form(...),
    paper_abstract: str = Form(""),
    question: str = Form(...)
):
    """Derin makale analizi"""
    paper = {
        "paperId": paper_id,
        "title": paper_title,
        "abstract": paper_abstract
    }
    
    analysis = await analyze_paper_deeply(paper, question)
    return JSONResponse({
        "success": True,
        "paper_id": paper_id,
        "analysis": analysis
    })

# SAVE/VOTE/FOLLOW API
@app.post("/api/questions/save")
async def api_save_question(
    request: Request,
    question: str = Form(...),
    category: str = Form(""),
    result_data: str = Form("")
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    
    save_id = save_question(user["id"], question, category, result_data)
    return JSONResponse({"success": True, "id": save_id}) if save_id else JSONResponse({"error": "Kaydetme başarısız"}, status_code=400)

@app.delete("/api/questions/save/{save_id}")
async def api_delete_saved(request: Request, save_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    
    return JSONResponse({"success": True}) if delete_saved_question(save_id, user["id"]) else JSONResponse({"error": "Silme başarısız"}, status_code=400)

@app.post("/api/vote")
async def api_vote(
    request: Request,
    question_hash: str = Form(...),
    vote_type: str = Form(...)
):
    user = get_current_user(request)
    ip = request.client.host if request.client else ""
    vote_question(
        user["id"] if user else None,
        question_hash,
        vote_type if vote_type != "none" else None,
        ip
    )
    counts = get_vote_counts(question_hash)
    return JSONResponse({
        "success": True,
        "upvotes": counts["upvotes"],
        "downvotes": counts["downvotes"],
        "user_vote": get_user_vote(user["id"] if user else None, question_hash, ip)
    })

@app.get("/api/vote/{question_hash}")
async def api_get_vote(request: Request, question_hash: str):
    user = get_current_user(request)
    ip = request.client.host if request.client else ""
    counts = get_vote_counts(question_hash)
    return JSONResponse({
        "upvotes": counts["upvotes"],
        "downvotes": counts["downvotes"],
        "user_vote": get_user_vote(user["id"] if user else None, question_hash, ip)
    })

@app.post("/api/topics/follow")
async def api_follow_topic(request: Request, category: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    follow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": True})

@app.post("/api/topics/unfollow")
async def api_unfollow_topic(request: Request, category: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Giriş yapmalısınız"}, status_code=401)
    unfollow_topic(user["id"], category)
    return JSONResponse({"success": True, "following": False})

@app.post("/api/newsletter/subscribe")
async def api_subscribe_newsletter(
    request: Request,
    email: str = Form(""),
    frequency: str = Form("weekly")
):
    user = get_current_user(request)
    if not email and user:
        email = user.get("email", "")
    if not email:
        return JSONResponse({"error": "Email gerekli"}, status_code=400)
    
    subscribe_newsletter(email, user["id"] if user else None, frequency)
    return JSONResponse({"success": True, "message": "Abonelik başarılı!"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)