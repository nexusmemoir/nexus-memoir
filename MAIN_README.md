# 🚀 WhatIf TR - Full Stack Python + React

## 📦 Proje İçeriği

Bu paket **Python (FastAPI) Backend** + **React Frontend** içerir.

```
whatif-tr-python/
├── main.py                    # Python FastAPI backend
├── requirements.txt           # Python bağımlılıkları
├── services/                  # Backend servisleri
├── data/manual/              # Veri dosyaları
├── frontend/                 # React frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── README.md                 # Ana dokümantasyon
└── .env.example              # Environment variables
```

## 🎯 Hızlı Başlangıç

### Backend (Python FastAPI)

```bash
# 1. Sanal ortam
python -m venv venv
source venv/bin/activate

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env
# .env dosyasına OPENAI_API_KEY ekle

# 4. Çalıştır
uvicorn main:app --reload --port 8000
```

Backend: http://localhost:8000  
API Docs: http://localhost:8000/docs

### Frontend (React)

```bash
# Yeni terminal
cd frontend

# Bağımlılıkları yükle
npm install

# Çalıştır
npm run dev
```

Frontend: http://localhost:5173

## 🌐 Render.com'a Deploy

### Backend Deploy (Python)

1. **Render Dashboard** → New Web Service
2. Repository bağla
3. **Settings:**
   ```
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. **Environment Variables:**
   ```
   OPENAI_API_KEY=sk-your-key
   PORT=10000
   CORS_ORIGIN=*
   ```

### Frontend Deploy (Netlify)

```bash
cd frontend
npm run build

# Netlify'a manuel deploy veya GitHub bağlantısı
```

## ✨ Özellikler

### Backend (Python/FastAPI)
- ✅ RESTful API
- ✅ OpenAI GPT-4 entegrasyonu
- ✅ 9 varlık simülasyonu
- ✅ Enflasyon hesaplama
- ✅ Otomatik API dokumentasyonu
- ✅ CORS desteği

### Frontend (React/Vite)
- ✅ Modern UI (Tailwind CSS)
- ✅ Responsive design
- ✅ Grafik desteği (Recharts)
- ✅ Form validasyonu
- ✅ Sosyal paylaşım

## 📊 Varlıklar

- 💵 Dolar (USD)
- 💶 Euro (EUR)
- 🪙 Altın (GOLD)
- ⚪ Gümüş (SILVER)
- ₿ Bitcoin (BTC)
- 🏦 Faiz (INTEREST)
- 🏠 Konut m² (HOUSING)
- 🚗 Sıfır Araç (CAR_NEW)
- 🚙 İkinci El Araç (CAR_USED)

## 💰 Maliyet Analizi

**Hosting:**
- Backend (Render): $0/ay (Free tier)
- Frontend (Netlify): $0/ay (Free tier)

**API:**
- OpenAI GPT-4: ~$20/ay (1000 kullanıcı)

**Toplam: ~$20/ay**

**Gelir Potansiyeli:**
- Google AdSense: $200-500/ay

## 🔧 Geliştirme

### Backend Test
```bash
curl http://localhost:8000/health
```

### Frontend Test
Tarayıcıda: http://localhost:5173

### API Test (Postman/cURL)
```bash
curl -X POST http://localhost:8000/api/simulation/run \
  -H "Content-Type: application/json" \
  -d '{
    "startDate": "2020-01-01",
    "amount": 10000,
    "asset": "USD",
    "includeLLM": true
  }'
```

## 📝 Önemli Dosyalar

- **`main.py`** - Backend entry point
- **`requirements.txt`** - Python dependencies
- **`services/`** - Business logic
- **`data/manual/`** - Price data (2020-2025)
- **`frontend/src/App.jsx`** - Frontend entry
- **`.env.example`** - Environment variables template

## 🐛 Sorun Giderme

### Backend Hatası
```bash
# Logs kontrol
uvicorn main:app --log-level debug

# Port değiştir
uvicorn main:app --port 8001
```

### Frontend Hatası
```bash
# Cache temizle
rm -rf node_modules package-lock.json
npm install

# Backend URL'i kontrol et
# vite.config.js içinde proxy ayarları
```

### CORS Hatası
`.env` dosyasında:
```
CORS_ORIGIN=http://localhost:5173
```

## 📚 Dokümantasyon

- **Backend:** http://localhost:8000/docs (otomatik)
- **README.md** - Bu dosya
- **Frontend README** - `frontend/README.md`

## 🆘 Destek

- FastAPI: https://fastapi.tiangolo.com
- React: https://react.dev
- Render: https://render.com/docs
- Netlify: https://docs.netlify.com

---

## 🎉 Başarılar!

Türkiye'de finansal bilinçlendirme için güzel bir araç oluşturdunuz.

**Deploy sonrası:**
- Backend: https://whatif-tr-backend.onrender.com
- Frontend: https://whatif-tr.netlify.app

**İlk test simülasyonu:**
"2020 başında 10,000 TL Dolar alsaydım bugün ne olurdu?"

Cevap: ~52,800 TL! 🚀
