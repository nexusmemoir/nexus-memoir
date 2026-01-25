#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AkademikSoru Test Script
Hızlı test için örnek sorgular
"""

import asyncio
import os
from app import search_papers, synthesize_results, generate_search_queries

async def test_research(question: str):
    """Bir soruyu test et"""
    print(f"\n{'='*80}")
    print(f"🔍 SORU: {question}")
    print(f"{'='*80}\n")
    
    # 1. Sorgu üretimi
    print("📝 Akıllı sorgular üretiliyor...")
    queries = await generate_search_queries(question)
    print(f"   Üretilen sorgular: {queries}")
    
    # 2. Makale arama
    print("\n📚 Makaleler aranıyor...")
    papers = await search_papers(question)
    print(f"   Bulunan makale sayısı: {len(papers)}")
    
    if papers:
        print("\n🎯 En alakalı 3 makale:")
        for i, p in enumerate(papers[:3], 1):
            rel_score = p.get('relevance_score', 'N/A')
            citations = p.get('citationCount', 0)
            print(f"   {i}. {p.get('title', 'Başlıksız')}")
            print(f"      İlgililik: {rel_score} | Atıf: {citations}")
    
    # 3. Sentez
    print("\n🤖 GPT ile sentez yapılıyor...")
    synthesis = await synthesize_results(question, papers, level="medium")
    
    print("\n📊 SONUÇLAR:")
    print(f"   Kanıt Gücü: {synthesis.get('evidence_strength', 'N/A')}")
    print(f"\n   Özet:\n   {synthesis.get('summary', 'Yok')[:300]}...")
    
    if synthesis.get('key_points'):
        print(f"\n   Anahtar Noktalar:")
        for i, point in enumerate(synthesis.get('key_points', []), 1):
            print(f"   {i}. {point}")
    
    print(f"\n{'='*80}\n")

async def main():
    """Ana test fonksiyonu"""
    
    # API key kontrolü
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ HATA: OPENAI_API_KEY bulunamadı!")
        print("   .env dosyasını oluşturun ve API key'inizi ekleyin")
        return
    
    print("\n" + "="*80)
    print("🔬 AkademikSoru - Test Modu")
    print("="*80)
    
    # Test soruları
    test_questions = [
        "Kahve içmek sağlığa zararlı mı?",
        "Omega-3 çocuklarda DEHB'ye iyi gelir mi?",
        "Meditasyon gerçekten işe yarıyor mu?",
    ]
    
    print("\n📋 Test edilecek sorular:")
    for i, q in enumerate(test_questions, 1):
        print(f"   {i}. {q}")
    
    # İlk soruyu test et
    await test_research(test_questions[0])
    
    print("\n✅ Test tamamlandı!")
    print("💡 İpucu: Diğer soruları test etmek için kodu düzenleyin")

if __name__ == "__main__":
    asyncio.run(main())
