# -*- coding: utf-8 -*-
# ClaimCheck - İddia Kaynak Sorgulama Tool
# GPT-4o mini + GDELT + Semantic Scholar

import os
import re
import json
import hashlib
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import traceback
from collections import defaultdict
import asyncio
import httpx

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# ========================
# CONFIG
# ========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "claimcheck-secret-key-change-me")

# Rate limiting
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 5  # requests per window

# Cache
CACHE_TTL = 24 * 60 * 60  # 24 hours
claim_cache = {}  # In production, use Redis

# Rate limit storage
rate_limits = defaultdict(list)

# ========================
# APP SETUP
# ========================

app = FastAPI(title="ClaimCheck", description="İddia Kaynak Sorgulama")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# ========================
# HELPERS
# ========================

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def check_rate_limit(ip: str) -> bool:
    """Returns True if rate limited"""
    now = time.time()
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limits[ip]) >= RATE_LIMIT_MAX:
        return True
    rate_limits[ip].append(now)
    return False

def get_cache_key(claim: str, lang: str) -> str:
    return hashlib.sha256(f"{claim.lower().strip()}:{lang}".encode()).hexdigest()[:16]

def get_cached_result(cache_key: str) -> Optional[dict]:
    if cache_key in claim_cache:
        entry = claim_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
    return None

def set_cache(cache_key: str, data: dict):
    claim_cache[cache_key] = {
        "timestamp": time.time(),
        "data": data
    }

# ========================
# GPT-4o mini
# ========================

async def call_gpt(prompt: str, system_message: str = None) -> str:
    """Call GPT-4o mini API"""
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2000
            }
        )
        
        if response.status_code != 200:
            print(f"GPT Error: {response.status_code} - {response.text}")
            raise Exception(f"GPT API error: {response.status_code}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def extract_claim_and_queries(claim_text: str, lang: str) -> dict:
    """Use GPT to normalize claim and generate MULTIPLE smart search queries"""
    
    system_message = """Sen bir haber araştırma uzmanısın. Kullanıcının verdiği iddiayı analiz et ve HABER SİTELERİNDE aranabilecek sorgular üret.

ÖNEMLİ KURALLAR:
1. Sosyal medya dili ile haber dili FARKLIDIR
   - Kullanıcı: "kazandı" → Haber: "karar çıktı", "sonuçlandı", "mahkeme kararı"
   - Kullanıcı: "patladı" → Haber: "gündem oldu", "viral oldu", "tartışma yarattı"
   
2. Türkçe ekleri düşün - farklı varyasyonlar üret:
   - İmamoğlu, Imamoglu, Ekrem İmamoğlu
   - davası, davayı, dava
   
3. Hem GENEL hem SPESİFİK sorgular üret

4. Güncel olaylar için tarih/ay ekle (örn: "Ocak 2026")

ASLA doğru/yanlış hükmü verme. Sadece arama sorguları üret.
Yanıtını SADECE JSON formatında ver, başka hiçbir şey yazma."""

    prompt = f"""Kullanıcı iddiası: "{claim_text}"

Aşağıdaki JSON formatında yanıt ver. EN AZ 8 Türkçe ve 4 İngilizce sorgu üret:

{{
    "normalized_claim": "İddiayı haber dilinde tek cümle olarak yaz",
    "main_topic": "Ana konu (1-2 kelime)",
    "queries_tr": [
        "Haber sitelerinde aranacak Türkçe sorgu 1 (resmi dil)",
        "Farklı kelimelerle Türkçe sorgu 2",
        "Kişi/kurum adı + olay şeklinde sorgu 3",
        "Tarihli sorgu (örn: Ocak 2026 + konu)",
        "Daha genel sorgu 5",
        "Çok spesifik sorgu 6",
        "Alternatif yazım sorgusu 7",
        "Son dakika / gündem tarzı sorgu 8"
    ],
    "queries_en": [
        "English news query 1",
        "English query with name variations 2", 
        "Broader English query 3",
        "Specific English query 4"
    ],
    "keywords": ["anahtar1", "anahtar2", "anahtar3"],
    "entities": ["kişi adları", "kurum adları", "yer adları"],
    "time_context": "yaklaşık tarih veya dönem (biliniyorsa)"
}}

ÖRNEK - Kullanıcı "İmamoğlu davayı kazandı" derse:
- queries_tr: ["Ekrem İmamoğlu mahkeme kararı", "İmamoğlu davası sonuçlandı", "İBB Başkanı dava karar", "İmamoğlu hakkında mahkeme", "Ekrem İmamoğlu beraat", "İmamoğlu yargılama sonucu", "İstanbul Büyükşehir Belediye Başkanı dava", "İmamoğlu son dakika mahkeme"]
- queries_en: ["Ekrem Imamoglu court verdict", "Istanbul mayor trial decision", "Imamoglu case ruling", "Ekrem Imamoglu acquitted"]"""

    try:
        result = await call_gpt(prompt, system_message)
        # Clean markdown formatting if present
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        
        parsed = json.loads(result)
        
        # Ensure we have enough queries
        if len(parsed.get("queries_tr", [])) < 4:
            parsed["queries_tr"] = parsed.get("queries_tr", []) + [claim_text]
        if len(parsed.get("queries_en", [])) < 2:
            parsed["queries_en"] = parsed.get("queries_en", []) + [claim_text]
            
        return parsed
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}, raw: {result[:500]}")
        return {
            "normalized_claim": claim_text,
            "main_topic": "",
            "queries_tr": [claim_text],
            "queries_en": [],
            "keywords": [],
            "entities": [],
            "time_context": ""
        }

async def generate_summary_and_timeline(claim: str, news_results: list, scholar_results: list) -> dict:
    """Use GPT to generate summary and timeline from results"""
    
    if not news_results and not scholar_results:
        return {
            "summary": "Bu iddia ifadesiyle eşleşen belirgin kaynak bulunamadı.",
            "timeline": [],
            "notes": ["Farklı anahtar kelimelerle tekrar aramayı deneyebilirsiniz."]
        }
    
    system_message = """Sen nötr bir araştırma asistanısın. 
ASLA "doğrudur" veya "yanlıştır" gibi hükümler verme.
Sadece "bu kaynaklarda şu bilgiler geçiyor" şeklinde nötr bir dil kullan.
Yanıtını SADECE JSON formatında ver."""

    # Prepare results summary for GPT
    sources_text = "HABER KAYNAKLARI:\n"
    for i, news in enumerate(news_results[:10]):
        sources_text += f"[{i}] {news.get('title', 'Başlıksız')} - {news.get('source', 'Bilinmeyen')} ({news.get('date', 'Tarih yok')})\n"
    
    if scholar_results:
        sources_text += "\nAKADEMİK KAYNAKLAR:\n"
        for i, paper in enumerate(scholar_results[:5]):
            idx = len(news_results) + i
            sources_text += f"[{idx}] {paper.get('title', 'Başlıksız')} ({paper.get('year', 'Yıl yok')})\n"

    prompt = f"""İddia: "{claim}"

Bulunan kaynaklar:
{sources_text}

Aşağıdaki JSON formatında yanıt ver:
{{
    "summary": "2-3 cümlelik nötr özet. 'Bu iddia şu kaynaklarda şu şekilde geçiyor...' formatında.",
    "timeline": [
        {{"date": "YYYY-MM veya YYYY", "event": "Ne oldu kısa açıklama", "refs": [kaynak_indexleri]}}
    ],
    "notes": ["Varsa belirsizlikler veya eksik bilgiler"]
}}

Timeline'da en eski 3 ve en yeni 2 önemli olay olsun (toplam max 5).
Kesin tarih yoksa yaklaşık yıl kullan."""

    try:
        result = await call_gpt(prompt, system_message)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        return json.loads(result)
    except Exception as e:
        print(f"Summary generation error: {e}")
        return {
            "summary": f"{len(news_results)} haber ve {len(scholar_results)} akademik kaynak bulundu.",
            "timeline": [],
            "notes": ["Otomatik özet oluşturulamadı."]
        }


async def filter_relevant_results(claim: str, results: list, result_type: str = "news") -> list:
    """Use GPT to filter out irrelevant results"""
    
    if not results:
        return []
    
    # Prepare results for GPT
    results_text = ""
    for i, r in enumerate(results[:20]):
        title = r.get('title', '')[:100]
        results_text += f"{i}. {title}\n"
    
    system_message = """Sen bir haber alakalılık filtresi olarak çalışıyorsun.
Verilen iddia ile GERÇEKTEN alakalı olan haberlerin index numaralarını döndür.
Sadece DOĞRUDAN alakalı olanları seç. Genel benzerlik yetmez.
Yanıtını SADECE JSON formatında ver."""

    prompt = f"""İddia: "{claim}"

Haber başlıkları:
{results_text}

Bu başlıklardan hangileri iddia ile DOĞRUDAN alakalı?

Alakalı olanların index numaralarını JSON array olarak döndür:
{{"relevant_indices": [0, 2, 5]}}

KURALLAR:
- Sadece iddia ile DOĞRUDAN ilgili olanları seç
- Genel konu benzerliği yetmez (örn: "penguen" iddiası için "penguen belgeseli" alakasız)
- Kişi/kurum adı eşleşmeli
- Olay türü eşleşmeli
- Hiçbiri alakalı değilse boş array döndür: {{"relevant_indices": []}}"""

    try:
        result = await call_gpt(prompt, system_message)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        
        parsed = json.loads(result)
        relevant_indices = parsed.get("relevant_indices", [])
        
        # Filter results
        filtered = []
        for idx in relevant_indices:
            if 0 <= idx < len(results):
                filtered.append(results[idx])
        
        return filtered if filtered else results[:5]  # Fallback to top 5 if all filtered
        
    except Exception as e:
        print(f"Filter error: {e}")
        return results[:10]  # Fallback

# ========================
# GDELT API (Free News)
# ========================

async def search_gdelt(query: str, lang: str = "tr", max_results: int = 10) -> list:
    """Search GDELT for news articles"""
    results = []
    
    try:
        # GDELT DOC 2.0 API
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": str(max_results),
            "format": "json",
            "sort": "datedesc"  # En yeni haberler önce
        }
        
        # Dil filtresi
        if lang == "tr":
            params["sourcelang"] = "turkish"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                for article in articles:
                    results.append({
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("domain", article.get("source", "")),
                        "date": article.get("seendate", "")[:10] if article.get("seendate") else "",
                        "snippet": article.get("title", "")[:200],
                        "image": article.get("socialimage", ""),
                        "language": article.get("language", "")
                    })
    except Exception as e:
        print(f"GDELT error for '{query}': {e}")
    
    return results


async def search_gdelt_context(query: str) -> list:
    """Search GDELT without language filter for broader results"""
    results = []
    
    try:
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": "10",
            "format": "json",
            "sort": "datedesc"
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])
                
                for article in articles:
                    results.append({
                        "title": article.get("title", ""),
                        "url": article.get("url", ""),
                        "source": article.get("domain", ""),
                        "date": article.get("seendate", "")[:10] if article.get("seendate") else "",
                        "snippet": article.get("title", "")[:200],
                        "image": article.get("socialimage", ""),
                        "language": article.get("language", "")
                    })
    except Exception as e:
        print(f"GDELT context error: {e}")
    
    return results


async def search_news_multiple(queries_tr: list, queries_en: list) -> list:
    """Search multiple queries in parallel and deduplicate"""
    all_results = []
    seen_urls = set()
    
    # Create tasks for parallel execution
    tasks = []
    
    # Turkish queries - with Turkish filter
    for query in queries_tr[:6]:
        tasks.append(search_gdelt(query, "tr", 8))
    
    # English queries - no language filter for international news
    for query in queries_en[:4]:
        tasks.append(search_gdelt_context(query))
    
    # Execute all searches in parallel
    try:
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for results in results_list:
            if isinstance(results, Exception):
                print(f"Search task error: {results}")
                continue
            
            for r in results:
                url = r.get("url", "")
                # Deduplicate by URL
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
    except Exception as e:
        print(f"Parallel search error: {e}")
    
    # Sort by date (newest first)
    all_results.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return all_results[:30]  # Max 30 results before filtering

# ========================
# Semantic Scholar API (Free Academic)
# ========================

async def search_semantic_scholar(query: str) -> list:
    """Search Semantic Scholar for academic papers"""
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": 10,
                    "fields": "title,authors,year,venue,url,abstract,citationCount"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])
                
                for paper in papers:
                    authors = paper.get("authors", [])
                    author_names = ", ".join([a.get("name", "") for a in authors[:3]])
                    if len(authors) > 3:
                        author_names += " et al."
                    
                    results.append({
                        "title": paper.get("title", ""),
                        "authors": author_names,
                        "year": paper.get("year"),
                        "venue": paper.get("venue", ""),
                        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "abstract": (paper.get("abstract") or "")[:300],
                        "citations": paper.get("citationCount", 0)
                    })
    except Exception as e:
        print(f"Semantic Scholar error: {e}")
    
    return results

# ========================
# MAIN PIPELINE
# ========================

async def process_claim(claim_text: str, lang: str = "tr", include_scholar: bool = True) -> dict:
    """Main processing pipeline with smart filtering"""
    
    print(f"[PIPELINE] Processing: {claim_text[:50]}...")
    
    # Step 1: Extract claim and generate MULTIPLE smart queries
    extraction = await extract_claim_and_queries(claim_text, lang)
    normalized_claim = extraction.get("normalized_claim", claim_text)
    queries_tr = extraction.get("queries_tr", [claim_text])
    queries_en = extraction.get("queries_en", [])
    keywords = extraction.get("keywords", [])
    main_topic = extraction.get("main_topic", "")
    
    print(f"[PIPELINE] Generated {len(queries_tr)} TR queries, {len(queries_en)} EN queries")
    print(f"[PIPELINE] TR Queries: {queries_tr[:3]}")
    
    # Step 2: Search news with ALL queries in parallel
    raw_news_results = await search_news_multiple(queries_tr, queries_en)
    print(f"[PIPELINE] Found {len(raw_news_results)} raw news results")
    
    # Step 3: FILTER results using GPT (remove irrelevant)
    if raw_news_results:
        news_results = await filter_relevant_results(normalized_claim, raw_news_results, "news")
        print(f"[PIPELINE] After filtering: {len(news_results)} relevant news")
    else:
        news_results = []
    
    # Step 4: Search academic (Semantic Scholar)
    scholar_results = []
    if include_scholar:
        # Use English queries for better academic results, or translate main topic
        scholar_query = queries_en[0] if queries_en else main_topic if main_topic else normalized_claim
        scholar_results = await search_semantic_scholar(scholar_query)
        print(f"[PIPELINE] Found {len(scholar_results)} academic results")
    
    # Step 5: Generate summary and timeline
    summary_data = await generate_summary_and_timeline(
        normalized_claim, 
        news_results, 
        scholar_results
    )
    
    return {
        "normalized_claim": normalized_claim,
        "original_claim": claim_text,
        "main_topic": main_topic,
        "queries_used": queries_tr[:5] + queries_en[:3],  # Show subset
        "keywords": keywords,
        "news_results": news_results[:20],
        "scholar_results": scholar_results[:10],
        "summary": summary_data.get("summary", ""),
        "timeline": summary_data.get("timeline", []),
        "notes": summary_data.get("notes", []),
        "stats": {
            "total_queries": len(queries_tr) + len(queries_en),
            "raw_news_found": len(raw_news_results),
            "filtered_news": len(news_results),
            "academic_found": len(scholar_results)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ========================
# ROUTES
# ========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/claim")
async def api_check_claim(
    request: Request,
    claim_text: str = Form(...),
    lang: str = Form(default="tr"),
    include_scholar: bool = Form(default=True)
):
    """Main API endpoint for claim checking"""
    
    # Get client IP
    client_ip = get_client_ip(request)
    
    # Rate limiting
    if check_rate_limit(client_ip):
        return JSONResponse({
            "error": "Çok fazla istek. Lütfen bir dakika bekleyin.",
            "retry_after": 60
        }, status_code=429)
    
    # Validate input
    claim_text = claim_text.strip()
    if not claim_text:
        return JSONResponse({"error": "İddia metni boş olamaz."}, status_code=400)
    
    if len(claim_text) > 500:
        return JSONResponse({"error": "İddia metni 500 karakteri geçemez."}, status_code=400)
    
    if len(claim_text) < 10:
        return JSONResponse({"error": "İddia metni en az 10 karakter olmalı."}, status_code=400)
    
    # Check cache
    cache_key = get_cache_key(claim_text, lang)
    cached = get_cached_result(cache_key)
    if cached:
        cached["from_cache"] = True
        return JSONResponse(cached)
    
    try:
        # Process claim
        result = await process_claim(claim_text, lang, include_scholar)
        result["from_cache"] = False
        
        # Cache result
        set_cache(cache_key, result)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"Error processing claim: {e}")
        traceback.print_exc()
        return JSONResponse({
            "error": "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin."
        }, status_code=500)

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    """Result page (renders client-side)"""
    return templates.TemplateResponse("result.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# ========================
# HEALTH CHECK
# ========================

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
