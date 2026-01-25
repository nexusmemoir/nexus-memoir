# -*- coding: utf-8 -*-
"""AkademikSoru FAZ 3.1 - Claude API + Gelişmiş Araştırma"""

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

async def call_gpt(messages: list, max_tokens: int = 4096, model: str = "gpt-4o") -> str:
    """Fallback: OpenAI GPT"""
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
    """Gelişmiş sorgu üretimi - Claude ile çok daha iyi"""
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
- Akademik terminoloji kullan (effects, impact, meta-analysis, systematic review, clinical trial, randomized controlled trial, longitudinal study, vb)
- Her sorgu NET ve ARAMAYI DARALTACAK şekilde olmalı
- Çok genel ("health") veya çok dar olma
- Bilimsel veri tabanlarında gerçekten kullanılan terimleri kullan

ÖRNEK:
Soru: "Kahve içmek kalbe zararlı mı?"
Sorgular:
1. "coffee consumption cardiovascular health" (Geniş)
2. "coffee intake heart disease risk" (Spesifik)
3. "coffee cardiovascular effects meta-analysis" (Metodolojik)
4. "caffeine cardiac health outcomes" (Alternatif terim)
5. "dietary caffeine cardiovascular disease" (İlgili alan)

ŞİMDİ YUKARIDAKI SORU İÇİN 5 sorgu üret.

JSON formatında yanıt ver:
{{
    "queries": ["sorgu1", "sorgu2", "sorgu3", "sorgu4", "sorgu5"],
    "main_keywords": ["keyword1", "keyword2", "keyword3"],
    "research_field": "Ana araştırma alanı",
    "reasoning": "Neden bu sorguları seçtin - kısaca"
}}'''
    
    result = await call_gpt([{"role": "user", "content": prompt}], 800, model="gpt-4o")
    try:
        # JSON çıkar
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m: 
            data = json.loads(m.group())
            queries = data.get("queries", [])[:5]
            # Boş veya çok kısa sorguları filtrele
            queries = [q.strip() for q in queries if len(q.strip()) > 5]
            
            if len(queries) >= 3:
                print(f"[SORGU ÜRETİMİ] {len(queries)} akıllı sorgu oluşturuldu")
                print(f"[SORGU] {queries}")
                return queries
    except Exception as e:
        print(f"Sorgu üretim hatası: {e}")
    
    # Fallback: Manuel akıllı sorgular
    q_lower = question.lower()
    fallback_queries = []
    
    # Ana kelimeler
    if "kahve" in q_lower: 
        fallback_queries = ["coffee consumption health effects", "caffeine cardiovascular impact", "coffee intake disease risk"]
    elif "uyku" in q_lower:
        fallback_queries = ["sleep duration health outcomes", "sleep deprivation effects", "optimal sleep recommendations"]
    elif "meditasyon" in q_lower or "mindfulness" in q_lower:
        fallback_queries = ["meditation stress reduction", "mindfulness mental health", "meditation brain effects"]
    elif "vitamin" in q_lower:
        fallback_queries = ["vitamin supplementation health", "micronutrient deficiency effects", "vitamin intake recommendations"]
    else:
        # Genel fallback
        fallback_queries = [question, f"{question} research study", f"{question} health effects"]
    
    print(f"[SORGU ÜRETİMİ] Fallback kullanıldı: {fallback_queries}")
    return fallback_queries[:5]

async def check_paper_relevance(question: str, paper: dict) -> dict:
    """Claude ile alakalılık kontrolü - çok daha doğru"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or ""
    
    # Abstract yoksa veya çok kısa ise düşük skor
    if not abstract or len(abstract) < 50:
        return {"score": 25, "reason": "Özet eksik veya çok kısa"}
    
    # GPT-4o ile anlamsal relevance check
    prompt = f'''SORU: "{question}"

MAKALE:
Başlık: {title}
Özet: {abstract[:600]}

GÖREV: Bu makale yukarıdaki soruyu yanıtlamak için NE KADAR ALAKALI?

SKORLAMA KRİTERLERİ:
- 0-20: Tamamen alakasız, soruyla hiç ilgisi yok
- 21-40: Uzaktan ilgili, soruyu dolaylı yoldan ilgilendirebilir
- 41-60: Kısmen alakalı, sorunun bazı yönlerini ele alıyor
- 61-80: Alakalı, soruyu doğrudan veya yakından ele alıyor
- 81-100: Çok alakalı, tam olarak bu soruyu araştırıyor

ÖNEMLİ: Çok katı ol. Sadece gerçekten alakalı makalelere yüksek skor ver.

JSON formatında SADECE şu çıktıyı ver:
{{"score": 0-100, "reason": "Kısa açıklama (max 20 kelime)"}}'''
    
    result = await call_gpt([{"role": "user", "content": prompt}], 200, model="gpt-4o")
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m:
            data = json.loads(m.group())
            score = int(data.get("score", 50))
            reason = data.get("reason", "")
            return {"score": score, "reason": reason}
    except:
        pass
    
    # Basit fallback
    q_words = set(question.lower().split())
    title_words = set(title.lower().split())
    abstract_words = set(abstract.lower().split())
    
    title_match = len(q_words & title_words) / max(len(q_words), 1)
    abstract_match = len(q_words & abstract_words) / max(len(q_words), 1)
    
    simple_score = int((title_match * 60 + abstract_match * 40) * 100)
    return {"score": simple_score, "reason": "Keyword eşleşmesi"}

async def search_semantic_scholar(query: str, limit: int = 20) -> list:
    """Semantic Scholar arama - limit artırıldı"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.get(
                f"{SEMANTIC_SCHOLAR_API}/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "fields": "title,abstract,year,citationCount,authors,url,venue,openAccessPdf,publicationTypes"
                }
            )
            if r.status_code == 200:
                return r.json().get("data", [])
        except Exception as e:
            print(f"Semantic Scholar Error: {e}")
    return []

async def search_papers(question: str) -> list:
    """Gelişmiş makale arama - DAHA FAZLA MAKALE"""
    # 1. Akıllı sorgular üret (5 sorgu)
    queries = await generate_search_queries(question)
    print(f"\n[ARAŞTIRMA] 🔍 {len(queries)} akıllı sorgu üretildi")
    
    # 2. Her sorgudan 20'şer makale al (toplam ~100 makale potansiyel)
    all_papers, seen_ids = [], set()
    results = await asyncio.gather(*[search_semantic_scholar(q, 20) for q in queries])
    
    for papers in results:
        for p in papers:
            paper_id = p.get("paperId", "")
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                all_papers.append(p)
    
    print(f"[ARAŞTIRMA] 📚 Toplam {len(all_papers)} benzersiz makale bulundu")
    
    if len(all_papers) == 0:
        return []
    
    # 3. İlk 50 makaleyi relevance kontrolünden geçir (daha fazla kontrol)
    papers_to_check = all_papers[:50]
    print(f"[ARAŞTIRMA] 🎯 {len(papers_to_check)} makale alakalılık kontrolünden geçiriliyor...")
    
    # Batch olarak kontrol et (performans için 10'ar 10'ar)
    relevance_scores = []
    for i in range(0, len(papers_to_check), 10):
        batch = papers_to_check[i:i+10]
        batch_checks = await asyncio.gather(*[check_paper_relevance(question, p) for p in batch])
        relevance_scores.extend(batch_checks)
    
    # Skorları ekle
    for i, check in enumerate(relevance_scores):
        papers_to_check[i]["relevance_score"] = check.get("score", 50)
        papers_to_check[i]["relevance_reason"] = check.get("reason", "")
    
    # 4. Alakalı makaleleri filtrele (skor >= 35, daha az strict)
    filtered_papers = [p for p in papers_to_check if p.get("relevance_score", 0) >= 35]
    print(f"[ARAŞTIRMA] ✅ {len(filtered_papers)} alakalı makale bulundu (skor >= 35)")
    
    if len(filtered_papers) == 0:
        # Hiç alakalı makale yoksa threshold'u düşür
        print(f"[ARAŞTIRMA] ⚠️ Threshold düşürülüyor...")
        filtered_papers = [p for p in papers_to_check if p.get("relevance_score", 0) >= 25]
        print(f"[ARAŞTIRMA] 📌 {len(filtered_papers)} makale bulundu (skor >= 25)")
    
    # 5. Akıllı sıralama: Relevance + Citation + Recency
    for p in filtered_papers:
        rel_score = p.get("relevance_score", 0)
        citations = p.get("citationCount", 0)
        year = p.get("year", 2000)
        
        # Recency bonus (son 5 yıl)
        current_year = 2025
        recency_bonus = max(0, 10 - (current_year - year)) if year >= 2020 else 0
        
        # Kombine skor: %60 relevance, %30 citations, %10 recency
        normalized_citations = min(citations / 50, 30)  # Max 30 puan
        combined_score = (rel_score * 0.6) + normalized_citations + recency_bonus
        
        p["combined_score"] = combined_score
    
    filtered_papers.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
    
    # En iyi 25 makaleyi döndür (önceden 15'ti)
    return filtered_papers[:25]

async def synthesize_results(question: str, papers: list, level: str = "medium") -> dict:
    """GPT-4o ile sentez - Maliyet optimize edildi"""
    levels = {
        "simple": "10 yaşındaki bir çocuğa anlatır gibi, ÇOK BASİT dil kullan. Teknik terim kullanma.", 
        "medium": "Lise mezunu bir yetişkine anlatır gibi, ANLAŞILIR dil kullan. Gerekirse basit terimlerle açıkla.", 
        "academic": "Üniversite öğrencisine anlatır gibi, DETAYLI ve teknik terimlerle açıkla."
    }
    
    # En alakalı 12 makaleyi kullan (önceden 8'di)
    relevant_papers = sorted(
        papers, 
        key=lambda x: x.get("relevance_score", x.get("citationCount", 0) / 10),
        reverse=True
    )[:12]
    
    papers_text = "\n\n".join([
        f"""MAKALE {i}:
Başlık: {p.get('title', '?')}
Yıl: {p.get('year', '?')} | Atıf Sayısı: {p.get('citationCount', 0)} | Alakalılık Skoru: {p.get('relevance_score', 'N/A')}
Özet: {(p.get('abstract') or 'Özet yok')[:500]}"""
        for i, p in enumerate(relevant_papers, 1)
    ])
    
    prompt = f'''ARAŞTIRILAN TÜRKÇE SORU: "{question}"

BULUNAN AKADEMİK MAKALELER (En alakalı 12 tanesi):
{papers_text}

SENİN GÖREVİN:
Bu akademik makaleleri analiz edip soruyu TÜRKÇE olarak yanıtla.

ÖNEMLİ KURALLAR:
1. Makaleler İngilizce ama sen TAMAMEN TÜRKÇE yaz
2. SADECE gerçekten soruyla alakalı makaleleri kullan
3. Eğer makaleler soruyu yanıtlamıyorsa, açıkça belirt
4. Çelişkili bulgular varsa, bunları göster
5. Kanıt gücünü makalelerin sayısı, kalitesi ve tutarlılığına göre belirle
6. Numaralandırma, madde işareti KULLANMA - düz paragraf halinde yaz

AÇIKLAMA SEVİYESİ: {levels.get(level, levels["medium"])}

KANIT GÜCÜ BELİRLEME:
- "strong": 5+ yüksek kaliteli çalışma, tutarlı bulgular, meta-analiz var
- "moderate": 3-5 çalışma, çoğunlukla tutarlı, bazı çelişkiler olabilir
- "limited": 1-2 çalışma veya çelişkili bulgular
- "insufficient": Alakalı çalışma yok veya yetersiz veri

JSON formatında yanıt ver (Türkçe karakterler düzgün kullan):
{{
    "summary": "3-4 paragraf TÜRKÇE özet. Makalelerden çıkan sonuçları ANLAŞILIR şekilde açıkla. Madde işareti kullanma, düz paragraf yaz.",
    "evidence_strength": "strong/moderate/limited/insufficient",
    "evidence_description": "Kanıt gücü açıklaması - kaç çalışma var, ne kadar tutarlılar, hangi metodolojiler kullanılmış?",
    "key_points": ["Ana nokta 1 - paragraf gibi yaz", "Ana nokta 2 - paragraf gibi yaz", "Ana nokta 3"],
    "limitations": "Araştırmanın sınırlılıkları - neyi bilmiyoruz, hangi sorular hala açık?",
    "related_questions": ["İlgili soru 1", "İlgili soru 2", "İlgili soru 3"]
}}'''
    
    result = await call_gpt([{"role": "user", "content": prompt}], 4096, model="gpt-4o")
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m: 
            data = json.loads(m.group())
            
            # Validation
            summary = data.get("summary", "")
            if not summary or len(summary) < 100:
                data["summary"] = "Bulunan makaleler soruyu doğrudan yanıtlamıyor. Daha spesifik bir soru sormanız veya farklı anahtar kelimeler kullanmanız önerilir."
                data["evidence_strength"] = "insufficient"
            
            return data
    except Exception as e:
        print(f"Sentez hatası: {e}")
    
    return {
        "summary": "Sentez yapılamadı. Lütfen soruyu farklı şekilde formüle edin.", 
        "evidence_strength": "insufficient", 
        "evidence_description": "Alakalı kaynak bulunamadı veya sentez sırasında hata oluştu.", 
        "key_points": [], 
        "limitations": "Yeterli veri yok", 
        "related_questions": []
    }

async def analyze_paper_deeply(paper: dict, question: str) -> dict:
    """GPT-4o ile derin makale analizi - İngilizce içeriği Türkçe'ye çevir"""
    title = paper.get("title", "")
    abstract = paper.get("abstract", "") or ""
    
    if not abstract:
        return {
            "relevance_score": 0,
            "main_finding": "Bu makale için özet bulunmuyor.",
            "key_insights": [],
            "methodology_note": "",
            "practical_takeaway": ""
        }
    
    prompt = f'''ARAŞTIRILAN SORU: "{question}"

MAKALE:
Başlık: {title}
Özet (İngilizce): {abstract}

GÖREVİN:
1. Bu makaleden soruyla ilgili EN ÖNEMLİ bulguları çıkar
2. Her bulguyu TÜRKÇE'ye çevir ve basitçe açıkla
3. Orijinal İngilizce cümleyi de göster
4. Her bulgunun günlük hayatta ne anlama geldiğini yaz

KURALLAR:
- TÜRKÇE karakterleri düzgün kullan (ç, ğ, ı, ö, ş, ü)
- Orijinal metinden DOĞRUDAN alıntı yap (manipüle etme)
- 2-3 önemli bulgu yeterli, fazla detaya girme
- Pratik ve uygulanabilir öneriler sun

JSON formatında yanıt ver:
{{
    "relevance_score": 0-100,
    "main_finding": "Makalenin ANA bulgusu (TÜRKÇE, 1-2 cümle)",
    "key_insights": [
        {{
            "turkish": "TÜRKÇE çeviri ve açıklama - anlaşılır dil",
            "original": "Orijinal İngilizce cümle - birebir alıntı",
            "explanation": "Bu günlük hayatta ne demek? - basit açıklama"
        }}
    ],
    "methodology_note": "Araştırma yöntemi (örn: 1000 kişilik kohort çalışması, meta-analiz, RCT)",
    "practical_takeaway": "Peki ne yapmalıyız? (1-2 cümle PRATİK öneri)"
}}'''
    
    result = await call_gpt([{"role": "user", "content": prompt}], 2000, model="gpt-4o")
    try:
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"Derin analiz hatası: {e}")
    
    return {
        "relevance_score": 50,
        "main_finding": "Analiz yapılamadı.",
        "key_insights": [],
        "methodology_note": "",
        "practical_takeaway": ""
    }

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
    for p in papers[:20]:  # 20 makale göster (önceden 10'du)
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
    """Derin makale analizi - Claude ile"""
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
