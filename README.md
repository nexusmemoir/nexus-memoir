# NexusMemoir 🌍

Dijital zaman kapsülü uygulaması. Anılarını dünyaya göm, gelecekte açılsın!

## Özellikler ✨

- 🗺️ **İnteraktif Harita**: 3D dünya haritasında özel lokasyon seçimi
- 🔒 **Zamana Kilitli**: Belirlediğin tarihe kadar kimse açamaz
- 📸 **Çoklu Format**: 5 metin, 10 fotoğraf, 1 video
- 🌐 **Herkese Açık**: Kapsülün haritada görünür, içerik sadece senin
- 📱 **QR Kod**: Mobil erişim için QR kod desteği
- ☁️ **Cloudflare R2**: Güvenli ve ölçeklenebilir medya depolama

## Teknolojiler 🛠️

- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **Storage**: Cloudflare R2 (S3 compatible)
- **Frontend**: Vanilla JS, Mapbox GL
- **Hosting**: Render.com ready

## Kurulum 🚀

### 1. Gereksinimler

- Python 3.10+
- Cloudflare R2 hesabı
- (Opsiyonel) Mapbox hesabı (ücretsiz)

### 2. Projeyi Klonla

```bash
git clone <your-repo-url>
cd nexusmemoir
```

### 3. Sanal Ortam Oluştur

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 4. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 5. Environment Variables

`.env.example` dosyasını `.env` olarak kopyala ve doldur:

```bash
cp .env.example .env
```

Gerekli değerler:
- `SECRET_KEY`: Rastgele uzun bir string
- `ADMIN_PASSWORD`: Admin erişimi için şifre
- `R2_ENDPOINT`: Cloudflare R2 endpoint URL'i
- `R2_ACCESS_KEY_ID`: R2 access key
- `R2_SECRET_ACCESS_KEY`: R2 secret key
- `R2_BUCKET`: R2 bucket adı

### 6. Mapbox Token (Opsiyonel)

`static/js/create-sync.js` ve `static/js/map-landing.js` dosyalarındaki Mapbox token'ını kendi token'ınla değiştir:

```javascript
mapboxgl.accessToken = 'YOUR_MAPBOX_TOKEN_HERE';
```

Ücretsiz token için: https://www.mapbox.com/

### 7. Uygulamayı Çalıştır

```bash
uvicorn app:app --reload --port 8000
```

Tarayıcıda aç: http://localhost:8000

## Render'a Deploy 🌐

### 1. Render Hesabı Oluştur

https://render.com adresinden ücretsiz hesap aç

### 2. Yeni Web Service Oluştur

1. Dashboard → New → Web Service
2. GitHub repo'nuzu bağlayın
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables Ekle

Render Dashboard → Environment sekmesinden ekle:
- `SECRET_KEY`
- `ADMIN_PASSWORD`
- `R2_ENDPOINT`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`

### 4. Persistent Disk Ekle

Dashboard → Disks → Add Disk:
- Name: `nexusmemoir-data`
- Mount Path: `/var/data`
- Size: 1GB (ücretsiz)

Environment Variables'a ekle:
```
DB_PATH=/var/data/db.sqlite3
```

### 5. Deploy Et

"Create Web Service" butonuna tıkla ve bekle!

## Cloudflare R2 Kurulumu ☁️

### 1. R2 Aktif Et

Cloudflare Dashboard → R2 → Enable R2

### 2. Bucket Oluştur

Create Bucket → `nexusmemoir-media`

### 3. API Token Oluştur

R2 → Manage R2 API Tokens → Create API Token
- Permissions: Object Read & Write
- Token Name: nexusmemoir-api

Token bilgilerini `.env` dosyasına ekle.

## Kullanım 📖

### Kapsül Oluşturma

1. Ana sayfada → "Kapsülünü Oluştur"
2. Haritada bir lokasyon seç (çift tıklama veya 3 tıklama mobilde)
3. Başlık ve açılış tarihi belirle
4. Ödemeyi tamamla (mock payment)
5. QR kod ve PIN'i kaydet

### Kapsüle Erişim

1. QR kodu okut veya `/claim?token=XXX` linkine git
2. PIN gir
3. Dashboard'da içerik ekle veya görüntüle

### İçerik Ekleme

Dashboard'da:
- 📝 Metin notu ekle (max 5)
- 📸 Fotoğraf yükle (max 10, 10MB/foto)
- 🎥 Video yükle (max 1, 80MB)

### Kapsül Açılışı

Belirlenen tarihte otomatik olarak açılır. Countdown timer ile geri sayım.

## Proje Yapısı 📁

```
nexusmemoir/
├── app.py                 # FastAPI backend
├── requirements.txt       # Python bağımlılıkları
├── render.yaml           # Render deploy config
├── .env.example          # Environment variables template
├── static/
│   ├── css/             # Stil dosyaları
│   ├── js/              # JavaScript dosyaları
│   └── images/          # Görseller
└── templates/           # HTML şablonları
    ├── map-landing.html     # Ana sayfa (harita)
    ├── globe-landing.html   # Alternatif landing (globe)
    ├── landing.html         # Standart landing
    ├── create-capsule.html  # Kapsül oluşturma wizard
    ├── claim.html           # Kapsül claim sayfası
    ├── dashboard.html       # Kapsül dashboard
    └── success.html         # Başarı sayfası
```

## API Endpoints 🔌

### Public Endpoints
- `GET /` - Ana sayfa (map landing)
- `GET /globe` - Globe landing
- `GET /landing` - Standard landing
- `GET /create` - Kapsül oluşturma sayfası
- `GET /claim` - Kapsül claim sayfası
- `GET /api/capsules/public` - Public kapsüller listesi

### Auth Required
- `GET /dashboard` - Kapsül dashboard
- `POST /set-unlock` - Unlock zamanı ayarla
- `POST /add-note` - Metin notu ekle
- `POST /upload/photo` - Fotoğraf yükle
- `POST /upload/video` - Video yükle
- `GET /m/{media_id}` - Medya erişimi (presigned URL)

### API Endpoints
- `POST /api/capsules/create` - Yeni kapsül oluştur
- `POST /claim` - Kapsül claim et

## Güvenlik 🔐

- Session-based authentication
- SHA-256 token ve PIN hashing
- R2 presigned URLs (600 saniye geçerli)
- File type validation
- File size limits
- CORS koruması

## Limitler ⚠️

- Metin: 5 nota
- Fotoğraf: 10 adet, 10MB/foto
- Video: 1 adet, 80MB
- Session timeout: Tarayıcı kapatılana kadar

## Geliştirme 🔧

### Yeni Feature Eklemek

1. `app.py` - Backend endpoint ekle
2. `templates/` - HTML template oluştur/güncelle
3. `static/js/` - Frontend logic ekle
4. Test et
5. Deploy et

### Veritabanı Şeması

```sql
-- Kapsüller
CREATE TABLE capsules (
    id INTEGER PRIMARY KEY,
    token_hash TEXT UNIQUE,
    pin_hash TEXT,
    unlock_at TEXT,
    title TEXT,
    lat REAL,
    lng REAL,
    location_name TEXT,
    created_at TEXT
);

-- Notlar
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    capsule_id INTEGER,
    text TEXT,
    created_at TEXT
);

-- Medya
CREATE TABLE media (
    id INTEGER PRIMARY KEY,
    capsule_id INTEGER,
    kind TEXT,  -- 'photo' | 'video'
    r2_key TEXT,
    original_name TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    created_at TEXT
);
```

## Sorun Giderme 🔍

### R2 Upload Başarısız
- R2 credentials doğru mu?
- Bucket adı doğru mu?
- Endpoint URL doğru mu?

### Harita Yüklenmiyor
- Mapbox token geçerli mi?
- Internet bağlantısı var mı?

### Kapsül Açılmıyor
- Tarih format kontrolü (ISO 8601)
- Timezone ayarları (Europe/Istanbul)
- Unlock tarihi geçmiş mi?

## Lisans 📄

MIT License - İstediğin gibi kullan!

## Katkıda Bulunma 🤝

Pull request'ler hoş geldiniz! Büyük değişiklikler için önce issue açın.

## İletişim 📧

Sorular için: [email]

---

**NexusMemoir** - Anılarını dünyaya göm 🌍💫
