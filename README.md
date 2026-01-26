# 🐍 WhatIf TR - Python Backend

## 📦 Teknoloji Stack

- **Framework:** FastAPI
- **Server:** Uvicorn
- **LLM:** OpenAI GPT-4
- **Python:** 3.9+

## 🚀 Hızlı Başlangıç

### 1. Sanal Ortam Oluştur
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 2. Bağımlılıkları Yükle
```bash
pip install -r requirements.txt
```

### 3. Environment Variables Ayarla
```bash
cp .env.example .env
# .env dosyasını düzenle ve OPENAI_API_KEY ekle
```

### 4. Çalıştır
```bash
uvicorn main:app --reload --port 8000
```

### 5. Test Et
```bash
curl http://localhost:8000/health
```

API Docs: http://localhost:8000/docs

## 📁 Proje Yapısı

```
whatif-tr-python/
├── main.py                 # FastAPI uygulaması
├── requirements.txt        # Python bağımlılıkları
├── .env.example           # Environment variables şablonu
├── services/              # İş mantığı
│   ├── data_service.py    # Veri yükleme
│   ├── calculation_service.py  # Hesaplamalar
│   └── llm_service.py     # OpenAI entegrasyonu
└── data/                  # Manuel veri
    └── manual/*.json      # Fiyat verileri
```

## 🌐 API Endpoints

### Health Check
```bash
GET /health
```

### Simülasyon Çalıştır
```bash
POST /api/simulation/run
Content-Type: application/json

{
  "startDate": "2020-01-01",
  "amount": 10000,
  "asset": "USD",
  "endDate": "2025-01-27",
  "includeLLM": true
}
```

### Varlık Listesi
```bash
GET /api/data/assets
```

### Örnek Senaryolar
```bash
GET /api/simulation/examples
```

### Zaman Serisi
```bash
POST /api/simulation/time-series

{
  "startDate": "2020-01-01",
  "endDate": "2025-01-27",
  "asset": "USD",
  "amount": 10000
}
```

## 🚀 Render.com'a Deploy

### Yöntem 1: Web UI

1. **Render Dashboard** → New Web Service
2. **Repository** bağla
3. **Ayarlar:**
   - Name: `whatif-tr-backend`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free

4. **Environment Variables:**
   ```
   OPENAI_API_KEY=sk-your-key
   PORT=10000
   CORS_ORIGIN=https://your-frontend-url.com
   DEBUG=false
   ```

5. **Deploy!**

### Yöntem 2: render.yaml (Otomatik)

```yaml
# render.yaml zaten proje içinde mevcut
services:
  - type: web
    name: whatif-tr-backend
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

GitHub'a push → Render'da "New Blueprint Instance"

## 📊 Veri Yönetimi

### Desteklenen Varlıklar
- USD (Dolar)
- EUR (Euro)
- GOLD (Altın)
- SILVER (Gümüş)
- BTC (Bitcoin)
- INTEREST (Faiz)
- HOUSING (Konut m²)
- CAR_NEW (Sıfır Araç)
- CAR_USED (İkinci El Araç)

### Veri Ekleme
1. `data/manual/` klasörüne JSON dosyası ekle
2. Format: `{"2020-01-01": 5.94, ...}`
3. `data_service.py`'de yeni fonksiyon ekle

## 🔧 Geliştirme

### Hot Reload
```bash
uvicorn main:app --reload
```

### Test
```bash
pip install pytest
pytest
```

### Type Checking
```bash
pip install mypy
mypy main.py
```

## 💰 Maliyet

### Render.com (Ücretsiz Plan)
- ✅ 750 saat/ay
- ✅ Otomatik SSL
- ✅ Otomatik deploy
- ⚠️ 15 dakika sonra sleep (ilk istek 30sn gecikme)

### OpenAI API
- ~$0.02/simülasyon (GPT-4)
- ~$20/ay (1000 kullanıcı)

## 🐛 Sorun Giderme

### "No module named 'fastapi'"
```bash
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Farklı port kullan
uvicorn main:app --port 8001
```

### "OpenAI API key required"
```bash
# .env dosyasını kontrol et
cat .env | grep OPENAI_API_KEY
```

### Render'da "Application failed to start"
- Logs → Check errors
- Start command doğru mu?: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables tanımlı mı?

## 📝 Notlar

- Python 3.9+ gerekli
- FastAPI otomatik docs: `/docs` veya `/redoc`
- CORS middleware aktif (tüm origin'lere izin)
- File-based cache (hızlı)
- Manuel veri: 2020-2025

## 🆘 Destek

- FastAPI Docs: https://fastapi.tiangolo.com
- Render Docs: https://render.com/docs/deploy-fastapi
- OpenAI Docs: https://platform.openai.com/docs

---

**Python Backend Hazır! 🎉**

Frontend için: `whatif-tr/frontend/` klasörünü kullanın (React)
