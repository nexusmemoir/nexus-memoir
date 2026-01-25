# -*- coding: utf-8 -*-
# AkademikSoru - Bilimsel Literatür Araştırma Platformu v2.0
# FAZ 1: Popüler sorular, kanıt gücü, anlatım seviyesi, SEO

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

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ========================
# CONFIG
# ========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "academic-secret-key-change-me")

# Rate limiting
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10

# Cache
CACHE_TTL = 48 * 60 * 60
question_cache = {}
rate_limits = defaultdict(list)

# FAZ 1: Popüler sorular (statik - ileride dinamik olacak)
POPULAR_QUESTIONS = [
    {
        "id": "kahve-saglık",
        "question": "Kahve içmek sağlığa zararlı mı?",
        "category": "Beslenme",
        "icon": "☕",
        "preview": "Günde 3-4 fincan kahvenin genel sağlık üzerinde olumlu etkileri olduğunu gösteren çok sayıda çalışma var.",
        "evidence_level": "strong"
    },
    {
        "id": "yemek-isitma",
        "question": "Yemekleri tekrar ısıtmak zararlı mı?",
        "category": "Beslenme",
        "icon": "🍲",
        "preview": "Çoğu yemek için güvenli, ancak bazı besinlerde (ıspanak, mantar) nitrat oluşumu riski var.",
        "evidence_level": "moderate"
    },
    {
        "id": "gece-uyku",
        "question": "Gece geç uyumak kilo aldırır mı?",
        "category": "Sağlık",
        "icon": "😴",
        "preview": "Doğrudan uyku saati değil, ama gece geç yemek yeme alışkanlığı kilo alımını artırabilir.",
        "evidence_level": "moderate"
    },
    {
        "id": "c-vitamini",
        "question": "C vitamini soğuk algınlığına iyi gelir mi?",
        "category": "Sağlık",
        "icon": "🍊",
        "preview": "Önleyici etkisi sınırlı, ama hastalık süresini hafifçe kısaltabilir.",
        "evidence_level": "moderate"
    },
    {
        "id": "plastik-sise",
        "question": "Plastik şişeler kanser yapar mı?",
        "category": "Sağlık",
        "icon": "🧴",
        "preview": "Normal kullanımda BPA-free şişeler güvenli görünüyor, ama yüksek ısıda kimyasal sızıntısı riski var.",
        "evidence_level": "moderate"
    },
    {
        "id": "intermittent-fasting",
        "question": "Aralıklı oruç (intermittent fasting) işe yarıyor mu?",
        "category": "Beslenme",
        "icon": "⏰",
        "preview": "Kilo verme ve metabolik sağlık için umut verici bulgular var, ama uzun vadeli etkileri araştırılıyor.",
        "evidence_level": "moderate"
    },
    {
        "id": "mavi-isik",
        "question": "Mavi ışık uyku kalitesini etkiler mi?",
        "category": "Sağlık",
        "icon": "📱",
        "preview": "Gece mavi ışık maruziyeti melatonin üretimini baskılayarak uyku kalitesini olumsuz etkileyebilir.",
        "evidence_level": "strong"
    },
    {
        "id": "seker-bagimliligi",
        "question": "Şeker bağımlılık yapar mı?",
        "category": "Beslenme",
        "icon": "🍬",
        "preview": "Beyin üzerinde ödül mekanizmalarını tetikler, ama klasik anlamda 'bağımlılık' tartışmalı.",
        "evidence_level": "moderate"
    }
]

# Kategoriler
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

app = FastAPI(title="AkademikSoru", description="Bilimsel Literatür Araştırma Platformu")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ========================
# HELPERS
# ========================

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limits[ip]) >= RATE_LIMIT_MAX:
        return True
    rate_limits[ip].append(now)
    return False

def get_cache_key(question: str) -> str:
    return hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]

def get_cached_result(cache_key: str) -> Optional[dict]:
    if cache_key in question_cache:
        entry = question_cache[cache_key]
        if time.time() - entry["timestamp"] < CACHE_TTL:
            return entry["data"]
    return None

def set_cache(cache_key: str, data: dict):
    question_cache[cache_key] = {
        "timestamp": time.time(),
        "data": data
    }

def calculate_evidence_strength(papers: List[Dict]) -> str:
    """Kanıt gücünü hesapla"""
    if not papers:
        return "insufficient"
    
    total_papers = len(papers)
    recent_papers = len([p for p in papers if p.get('year', 0) >= 2020])
    highly_cited = len([p for p in papers if p.get('citations', 0) >= 50])
    
    # Basit skorlama
    score = 0
    if total_papers >= 15:
        score += 2
    elif total_papers >= 8:
        score += 1
    
    if recent_papers >= 8:
        score += 2
    elif recent_papers >= 4:
        score += 1
    
    if highly_cited >= 5:
        score += 2
    elif highly_cited >= 2:
        score += 1
    
    if score >= 5:
        return "strong"
    elif score >= 3:
        return "moderate"
    else:
        return "limited"

def get_related_questions(current_question: str) -> List[Dict]:
    """İlgili soruları öner"""
    # Şimdilik popüler sorulardan rastgele seç, gelecekte semantic similarity kullanılacak
    import random
    filtered = [q for q in POPULAR_QUESTIONS if q['question'].lower() != current_question.lower()]
    return random.sample(filtered, min(4, len(filtered)))

# ========================
# GPT-4o mini
# ========================

async def call_gpt(prompt: str, system_message: str = None) -> str:
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
                "max_tokens": 2500
            }
        )
        
        if response.status_code != 200:
            print(f"GPT Error: {response.status_code} - {response.text}")
            raise Exception(f"GPT API error: {response.status_code}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"]

async def analyze_question_and_generate_queries(question: str) -> dict:
    """Soruyu analiz et ve akademik arama sorguları üret"""
    
    system_message = """Sen bir akademik araştırma asistanısın. Kullanıcının sorduğu soruyu bilimsel literatürde aramak için en uygun sorguları üretiyorsun.

ÖNEMLİ KURALLAR:
1. Hem Türkçe hem İngilizce sorgular üret
2. Medikal/bilimsel terimler kullan (halk dili → bilimsel terim)
3. Hem geniş hem dar sorgular üret
4. Farklı yaklaşımlar dene (hastalık adı, semptom, tedavi, vb.)

ASLA doğru/yanlış hükmü verme. Sadece arama sorguları üret.
Yanıtını SADECE JSON formatında ver."""

    prompt = f"""Kullanıcı sorusu: "{question}"

Aşağıdaki JSON formatında yanıt ver:

{{
    "normalized_question": "Soruyu akademik dilde yeniden ifade et",
    "scientific_terms": ["bilimsel terim 1", "terim 2", "terim 3"],
    "queries_tr": [
        "Türkçe akademik sorgu 1",
        "Türkçe sorgu 2 (farklı açıdan)",
        "Türkçe sorgu 3 (daha genel)",
        "Türkçe sorgu 4 (daha spesifik)"
    ],
    "queries_en": [
        "English academic query 1",
        "English query 2 (different angle)",
        "English query 3 (broader)",
        "English query 4 (more specific)",
        "English query 5 (alternative terms)",
        "English query 6 (research focus)"
    ],
    "research_areas": ["araştırma alanı 1", "alan 2"],
    "related_topics": ["ilgili konu 1", "konu 2"]
}}"""

    try:
        result = await call_gpt(prompt, system_message)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        
        parsed = json.loads(result)
        
        if len(parsed.get("queries_tr", [])) < 3:
            parsed["queries_tr"] = parsed.get("queries_tr", []) + [question]
        if len(parsed.get("queries_en", [])) < 4:
            parsed["queries_en"] = parsed.get("queries_en", []) + [question]
            
        return parsed
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {
            "normalized_question": question,
            "scientific_terms": [],
            "queries_tr": [question],
            "queries_en": [question],
            "research_areas": [],
            "related_topics": []
        }

# ========================
# SEMANTIC SCHOLAR API
# ========================

async def search_semantic_scholar(query: str, limit: int = 15) -> List[Dict]:
    """Semantic Scholar'da arama yap"""
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "fields": "title,authors,year,venue,url,abstract,citationCount,publicationDate,fieldsOfStudy,isOpenAccess,openAccessPdf"
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
                    
                    pdf_url = None
                    if paper.get("isOpenAccess") and paper.get("openAccessPdf"):
                        pdf_url = paper["openAccessPdf"].get("url")
                    
                    results.append({
                        "paper_id": paper.get("paperId", ""),
                        "title": paper.get("title", ""),
                        "authors": author_names,
                        "year": paper.get("year"),
                        "venue": paper.get("venue", ""),
                        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                        "abstract": (paper.get("abstract") or "")[:400],
                        "citations": paper.get("citationCount", 0),
                        "publication_date": paper.get("publicationDate", ""),
                        "fields": paper.get("fieldsOfStudy", []),
                        "open_access": paper.get("isOpenAccess", False),
                        "pdf_url": pdf_url
                    })
    except Exception as e:
        print(f"Semantic Scholar error for '{query}': {e}")
    
    return results

async def search_multiple_academic(queries_tr: List[str], queries_en: List[str]) -> List[Dict]:
    """Birden fazla sorgu ile paralel akademik arama"""
    all_results = []
    seen_ids = set()
    
    tasks = []
    
    for query in queries_tr[:2]:
        tasks.append(search_semantic_scholar(query, 8))
    
    for query in queries_en[:6]:
        tasks.append(search_semantic_scholar(query, 12))
    
    try:
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for results in results_list:
            if isinstance(results, Exception):
                print(f"Search task error: {results}")
                continue
            
            for paper in results:
                paper_id = paper.get("paper_id", "")
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    all_results.append(paper)
    except Exception as e:
        print(f"Parallel search error: {e}")
    
    all_results.sort(key=lambda x: x.get("citations", 0), reverse=True)
    
    return all_results[:25]

# ========================
# GPT ANALYSIS & SYNTHESIS
# ========================

async def synthesize_research(question: str, papers: List[Dict], analysis_data: dict, explanation_level: str = "medium") -> dict:
    """Makaleleri analiz et ve sentezle - FAZ 1: Anlatım seviyesi eklendi"""
    
    if not papers:
        return {
            "summary": "Bu soru için yeterli akademik kaynak bulunamadı. Farklı kelimelerle tekrar deneyebilirsiniz.",
            "consensus": None,
            "key_findings": [],
            "conflicting_views": [],
            "research_gaps": [],
            "quality_note": "Sonuç bulunamadı"
        }
    
    # Anlatım seviyesine göre sistem mesajı
    level_instructions = {
        "simple": "Lise öğrencisine anlatır gibi, çok basit kelimeler kullan. Teknik terim kullanma.",
        "medium": "Üniversite mezununa anlatır gibi, anlaşılır ama bilimsel terimler de kullanabilirsin.",
        "academic": "Akademisyene anlatır gibi, bilimsel terminoloji ve detaylı açıklamalar kullan."
    }
    
    system_message = f"""Sen bir bilimsel literatür analiz asistanısın.

KURALLAR:
1. Objektif ol - asla kesin hüküm verme
2. "Araştırmalar gösteriyor ki..." formatında yaz
3. Çelişkili bulguları açıkça belirt
4. Kaynak kalitesini göz önünde bulundur (citation count)
5. "Bu tıbbi/bilimsel tavsiye değildir" uyarısı ekle

ANLATIM SEVİYESİ: {level_instructions.get(explanation_level, level_instructions['medium'])}

ASLA kesin ifadeler kullanma: "zararlıdır", "yararlıdır", "kesinlikle" vb.
DAİMA nüans ekle: "bazı çalışmalarda", "sınırlı kanıt", "daha fazla araştırma gerekli"

Yanıtını SADECE JSON formatında ver."""

    papers_text = ""
    for i, paper in enumerate(papers[:15]):
        papers_text += f"""
[{i+1}] {paper['title']}
Yazarlar: {paper['authors']}
Yıl: {paper['year'] or 'N/A'}
Atıf: {paper['citations']} 
Özet: {paper['abstract'][:250]}...
---"""

    prompt = f"""Soru: "{question}"

Bilimsel Terimler: {', '.join(analysis_data.get('scientific_terms', []))}

Bulunan akademik makaleler:
{papers_text}

Aşağıdaki JSON formatında yanıt ver:

{{
    "summary": "2-3 paragraf halinde genel özet. 'Literatür taraması gösteriyor ki...' formatında.",
    "consensus": "var ise bilimsel konsensüs, yoksa null",
    "key_findings": [
        "Ana bulgu 1 [kaynak numarası]",
        "Ana bulgu 2 [kaynak numarası]",
        "Ana bulgu 3 [kaynak numarası]"
    ],
    "conflicting_views": [
        "Çelişkili görüş 1 ve açıklaması [kaynaklar]",
        "Çelişkili görüş 2 [kaynaklar]"
    ],
    "research_gaps": [
        "Eksik araştırma alanı 1",
        "Eksik alan 2"
    ],
    "quality_note": "Bulguların güvenilirliği hakkında not (atıf sayıları, yayın tarihleri, vs.)",
    "disclaimer": "Bu bilimsel literatür özetidir, tıbbi/kişisel tavsiye değildir..."
}}

ÖNEMLİ: 
- Her bulguya kaynak numarası ekle [1], [3,5] gibi
- Anlatım seviyesine uy
- Kesin hüküm verme"""

    try:
        result = await call_gpt(prompt, system_message)
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```json?\n?', '', result)
            result = re.sub(r'\n?```$', '', result)
        
        return json.loads(result)
    except Exception as e:
        print(f"Synthesis error: {e}")
        return {
            "summary": f"{len(papers)} akademik makale bulundu. Otomatik özet oluşturulamadı.",
            "consensus": None,
            "key_findings": [],
            "conflicting_views": [],
            "research_gaps": [],
            "quality_note": "Manuel inceleme önerilir",
            "disclaimer": "Bu bilimsel literatür özetidir."
        }

# ========================
# MAIN PIPELINE
# ========================

async def process_research_question(question: str, explanation_level: str = "medium") -> dict:
    """Ana araştırma pipeline - FAZ 1: Anlatım seviyesi eklendi"""
    
    print(f"[PIPELINE] Processing: {question[:50]}... (Level: {explanation_level})")
    
    analysis = await analyze_question_and_generate_queries(question)
    normalized_q = analysis.get("normalized_question", question)
    queries_tr = analysis.get("queries_tr", [question])
    queries_en = analysis.get("queries_en", [question])
    
    print(f"[PIPELINE] Generated {len(queries_tr)} TR, {len(queries_en)} EN queries")
    
    papers = await search_multiple_academic(queries_tr, queries_en)
    print(f"[PIPELINE] Found {len(papers)} unique papers")
    
    synthesis = await synthesize_research(normalized_q, papers, analysis, explanation_level)
    
    recent_papers = [p for p in papers if p.get('year') and p['year'] >= 2020]
    highly_cited = [p for p in papers if p.get('citations', 0) >= 50]
    
    # FAZ 1: Kanıt gücü hesaplama
    evidence_strength = calculate_evidence_strength(papers)
    
    # FAZ 1: İlgili sorular
    related_questions = get_related_questions(question)
    
    return {
        "original_question": question,
        "normalized_question": normalized_q,
        "scientific_terms": analysis.get("scientific_terms", []),
        "research_areas": analysis.get("research_areas", []),
        "related_topics": analysis.get("related_topics", []),
        "synthesis": synthesis,
        "papers": papers[:20],
        "recent_papers": recent_papers[:10],
        "highly_cited": highly_cited[:10],
        "stats": {
            "total_papers": len(papers),
            "recent_count": len(recent_papers),
            "highly_cited_count": len(highly_cited),
            "open_access_count": sum(1 for p in papers if p.get('open_access')),
            "queries_used": len(queries_tr) + len(queries_en)
        },
        "queries_used": queries_tr[:3] + queries_en[:4],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evidence_strength": evidence_strength,
        "related_questions": related_questions,
        "explanation_level": explanation_level
    }

# ========================
# ROUTES
# ========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """FAZ 1: Zenginleştirilmiş ana sayfa"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "popular_questions": POPULAR_QUESTIONS,
        "categories": CATEGORIES
    })

@app.post("/api/research")
async def api_research(
    request: Request,
    question: str = Form(...),
    level: str = Form("medium")
):
    """Ana araştırma endpoint - FAZ 1: Anlatım seviyesi eklendi"""
    
    client_ip = get_client_ip(request)
    
    if check_rate_limit(client_ip):
        return JSONResponse({
            "error": "Çok fazla istek. Lütfen bir dakika bekleyin.",
            "retry_after": 60
        }, status_code=429)
    
    question = question.strip()
    if not question:
        return JSONResponse({"error": "Soru boş olamaz."}, status_code=400)
    
    if len(question) > 500:
        return JSONResponse({"error": "Soru 500 karakteri geçemez."}, status_code=400)
    
    if len(question) < 10:
        return JSONResponse({"error": "Soru en az 10 karakter olmalı."}, status_code=400)
    
    # Anlatım seviyesi kontrolü
    if level not in ["simple", "medium", "academic"]:
        level = "medium"
    
    cache_key = get_cache_key(question + level)
    cached = get_cached_result(cache_key)
    if cached:
        cached["from_cache"] = True
        return JSONResponse(cached)
    
    try:
        result = await process_research_question(question, level)
        result["from_cache"] = False
        
        set_cache(cache_key, result)
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"Error processing question: {e}")
        traceback.print_exc()
        return JSONResponse({
            "error": "İşlem sırasında bir hata oluştu. Lütfen tekrar deneyin."
        }, status_code=500)

@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    return templates.TemplateResponse("result.html", {"request": request})

@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/question/{question_id}", response_class=HTMLResponse)
async def question_detail(request: Request, question_id: str):
    """FAZ 1: SEO-friendly soru sayfaları"""
    # Popüler sorulardan bul
    question_data = next((q for q in POPULAR_QUESTIONS if q['id'] == question_id), None)
    
    if not question_data:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    return templates.TemplateResponse("question_detail.html", {
        "request": request,
        "question": question_data
    })

@app.get("/category/{category_name}", response_class=HTMLResponse)
async def category_page(request: Request, category_name: str):
    """FAZ 1: Kategori sayfaları"""
    category = next((c for c in CATEGORIES if c['name'].lower() == category_name.lower()), None)
    
    if not category:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    # Bu kategorideki sorular
    category_questions = [q for q in POPULAR_QUESTIONS if q['category'] == category['name']]
    
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category,
        "questions": category_questions
    })

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(), "version": "2.0-faz1"}