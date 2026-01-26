# 🔧 Render.com Deploy - Hata Çözüldü!

## ❌ Önceki Hata

```
error: failed to create directory `/usr/local/cargo/registry/cache`
Read-only file system (os error 30)
pydantic-core derleme hatası
```

## ✅ Çözüm

**requirements.txt güncellendi:**
- ✅ Pre-built wheel'leri kullanan versiyonlar
- ✅ Rust derleme gerektirmez
- ✅ Python 3.11 uyumlu
- ✅ Range specifications (esnek)

## 🚀 Deploy Adımları

### 1. Repository Hazırlama

```bash
# Zip'i aç
unzip whatif-tr-python.zip
cd whatif-tr-python

# Git init
git init
git add .
git commit -m "Python FastAPI backend ready"

# GitHub'a push
git remote add origin https://github.com/your-username/whatif-tr.git
git branch -M main
git push -u origin main
```

### 2. Render Dashboard

**https://dashboard.render.com → New → Web Service**

#### Repository
- Connect your GitHub repo
- Branch: `main`

#### Settings
```
Name: whatif-tr-backend
Region: Frankfurt (Europe) veya Oregon (USA)
Branch: main
Root Directory: (boş bırak)

Runtime: Python 3
Python Version: 3.11.11 (otomatik algılanacak runtime.txt'den)

Build Command:
pip install --upgrade pip && pip install -r requirements.txt

Start Command:
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1

Instance Type: Free
```

#### Environment Variables

**Add Environment Variable** butonuna tıkla:

```
OPENAI_API_KEY = sk-proj-your-actual-key-here
PORT = 10000
CORS_ORIGIN = *
DEBUG = false
PYTHON_VERSION = 3.11.11
```

### 3. Deploy!

**Create Web Service** → Deploy başlayacak

#### Beklenen Log Çıktısı:

```
==> Downloading cache...
==> Installing Python version 3.11.11...
==> Using Python version 3.11.11
==> Running build command 'pip install --upgrade pip && pip install -r requirements.txt'
Collecting fastapi>=0.115.0
  Using cached fastapi-0.115.6-py3-none-any.whl
Collecting uvicorn[standard]>=0.30.0
  Using cached uvicorn-0.34.0-py3-none-any.whl
...
Successfully installed fastapi uvicorn pydantic openai ...
==> Build succeeded 😀
==> Starting service with 'uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1'
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
==> Your service is live 🎉
```

## ✅ Test Et

### Health Check
```bash
curl https://whatif-tr-backend.onrender.com/health
```

**Beklenen:**
```json
{
  "status": "ok",
  "timestamp": "2025-01-27T..."
}
```

### API Docs
```
https://whatif-tr-backend.onrender.com/docs
```

### İlk Simülasyon
```bash
curl -X POST https://whatif-tr-backend.onrender.com/api/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": "2020-01-01",
    "amount": 10000,
    "asset": "USD",
    "includeLLM": false
  }'
```

## 🐛 Sorun Giderme

### Hata 1: "Build failed - pydantic-core"
**Çözüm:** ✅ Zaten çözüldü! Yeni requirements.txt pre-built wheel kullanıyor.

### Hata 2: "Application failed to start"
**Sebep:** Start command yanlış  
**Çözüm:** 
```
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
```

### Hata 3: "ModuleNotFoundError"
**Sebep:** Build command eksik  
**Çözüm:**
```
pip install --upgrade pip && pip install -r requirements.txt
```

### Hata 4: "Port already in use"
**Sebep:** PORT env variable yok  
**Çözüm:** Environment Variables'a `PORT=10000` ekle

### Hata 5: "OpenAI API error"
**Sebep:** API key yanlış veya eksik  
**Çözüm:** OPENAI_API_KEY'i kontrol et, `sk-proj-` ile başlamalı

### Hata 6: "Service unavailable after deploy"
**Sebep:** Free tier sleep mode (15 dakika inaktiflik sonrası)  
**Çözüm:** Normal, ilk istek 30sn sürebilir

## 📊 Render Free Tier Limitleri

- ✅ 750 saat/ay (bir service için yeterli)
- ✅ Otomatik SSL (HTTPS)
- ✅ Custom domain desteği
- ⚠️ 15 dakika inaktiflik sonrası sleep
- ⚠️ İlk istek ~30sn gecikme (cold start)
- ⚠️ 512 MB RAM
- ⚠️ 0.1 CPU

## 🔄 Otomatik Deploy

### GitHub Push ile Otomatik Deploy

Render servisi oluşturduktan sonra, her GitHub push otomatik deploy tetikler.

```bash
# Kod değişikliği yap
git add .
git commit -m "Update API"
git push

# Render otomatik deploy eder
```

### Manuel Deploy

Dashboard → Your Service → Manual Deploy → Deploy latest commit

## 🌐 Frontend Bağlantısı

Backend deploy olduktan sonra frontend'i bağla:

### Netlify'da

**Environment Variables:**
```
VITE_API_URL=https://whatif-tr-backend.onrender.com
```

### Vercel'de

```
VITE_API_URL=https://whatif-tr-backend.onrender.com
```

## 📝 Dosya Yapısı Özeti

```
whatif-tr-python/
├── main.py                # ⭐ FastAPI app
├── requirements.txt       # ⭐ GÜNCELLENDI (pre-built wheels)
├── runtime.txt           # ⭐ YENİ (Python 3.11.11)
├── render.yaml           # ⭐ GÜNCELLENDI (tam config)
├── .env.example
├── services/
│   ├── data_service.py
│   ├── calculation_service.py
│   └── llm_service.py
├── data/manual/          # JSON files
└── frontend/             # React app
```

## 🎉 Başarı!

Backend URL'iniz:
```
https://whatif-tr-backend.onrender.com
```

API Docs:
```
https://whatif-tr-backend.onrender.com/docs
```

Health:
```
https://whatif-tr-backend.onrender.com/health
```

---

## 💡 İpuçları

1. **İlk deploy 5-10 dakika sürebilir** - sabırlı olun
2. **Logs'u takip edin** - Dashboard → Logs
3. **Free tier sleep mode** - Production için $7/ay Starter plan alın
4. **Custom domain** - Render'da ücretsiz SSL ile ekleyebilirsiniz
5. **Monitoring** - Render otomatik health check yapar

## 🆘 Hala Sorun mu Var?

1. **Logs'u kontrol et:** Dashboard → Your Service → Logs
2. **Build logs:** Deploy logs'da tüm detaylar var
3. **Runtime logs:** Service başladıktan sonraki hatalar
4. **Environment variables:** Doğru girilmiş mi?
5. **Render Status:** https://status.render.com

---

**Render Deploy artık sorunsuz çalışacak! 🚀**

Güncellenen dosyalar:
- ✅ requirements.txt (pre-built wheels)
- ✅ runtime.txt (Python 3.11.11)
- ✅ render.yaml (tam config)
