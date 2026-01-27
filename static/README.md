# NexusMemoir - Dijital Zaman Kapsülü

## Yeni Akış (Güncellendi)

```
1. /create → Yer seç (harita) + Tarih/Saat + Başlık
2. "Yer Kaz" butonu → Kazma animasyonu → 6 haneli kapsül kodu üretilir
3. /dashboard → İçerik yükle (metin/foto/video)
4. "Ödemeyi Tamamla ve Kilitle" butonu
5. /success → QR kod + PIN gösterilir
6. Kapsül haritada görünür (sadece paid olanlar)
```

## Düzeltilen Bug'lar

| Bug | Sebep | Çözüm |
|-----|-------|-------|
| Landing page butonları tıklanmıyor | `#neuralBg` canvas pointer event'leri engelliyor | Tüm CSS'lerde `pointer-events: none` eklendi |
| Harita hover bug'ı (nokta sol üste kaçıyor) | Container'a `scale()` transform uygulanınca Mapbox pozisyonu kayıyor | Transform inner element'e taşındı |
| Sadece tarih seçimi | `type="date"` kullanılıyordu | `type="datetime-local"` yapıldı |
| Kapsül ID karışıklığı | Sıralı ID (1, 2, 3...) | 6 haneli random kod (örn: 847291) |

## Proje Yapısı

```
nexusmemoir/
├── app.py                 # FastAPI backend
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── static/
│   ├── css/
│   │   ├── app.css
│   │   ├── landing.css
│   │   ├── map-landing.css
│   │   ├── globe-landing.css
│   │   └── create-sync.css
│   ├── js/
│   │   ├── neural-bg.js
│   │   ├── map-landing.js      # ✅ Hover bug düzeltildi
│   │   ├── countdown.js
│   │   └── ...
│   └── images/
└── templates/
    ├── map-landing.html   # Ana sayfa (harita)
    ├── create-capsule.html # ✅ Yeni akış (yer seç → kaz → dashboard)
    ├── dashboard.html      # ✅ İçerik yükle + ödeme butonu
    ├── success.html        # ✅ QR kod + PIN
    ├── claim.html
    └── ...
```

## Kurulum

```bash
cd nexusmemoir
pip install -r requirements.txt --break-system-packages
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Yeni Akış Endpoint'leri
- `POST /api/capsules/create-draft` - Draft kapsül oluştur (yer seç → kaz)
- `POST /api/capsules/pay-and-lock` - Ödemeyi tamamla ve kilitle
- `POST /api/capsules/delete-draft` - Ödenmemiş draft'ı sil

### Diğer Endpoint'ler
- `GET /` - Ana sayfa (map-landing)
- `GET /create` - Kapsül oluşturma sayfası
- `GET /api/capsules/public` - Haritada görünen kapsüller (sadece paid)
- `POST /claim` - Token+PIN ile kapsüle eriş
- `GET /dashboard` - Kapsül dashboard'u
- `GET /success` - Başarı sayfası (QR kod oluşturur)
- `POST /add-note` - Metin ekle
- `POST /upload/photo` - Foto yükle (R2)
- `POST /upload/video` - Video yükle (R2)

## Veritabanı Şeması

```sql
capsules:
- id (INTEGER PRIMARY KEY)
- capsule_number (TEXT UNIQUE) -- 6 haneli random kod
- token_hash (TEXT UNIQUE)
- pin_hash (TEXT)
- unlock_at (TEXT)
- lat, lng (REAL)
- location_name, capsule_title (TEXT)
- is_public (INTEGER) -- 0=gizli, 1=haritada (sadece paid=1)
- status (TEXT) -- draft, paid
- created_at (TEXT)

notes: id, capsule_id, text, created_at
media: id, capsule_id, kind, r2_key, original_name, content_type, size_bytes, created_at
```

## Kapsül Durumları (status)

| Status | Açıklama | Haritada |
|--------|----------|----------|
| `draft` | Ödeme bekleniyor, içerik yüklenebilir | ❌ |
| `paid` | Ödeme tamamlandı, kilitli | ✅ |

## Notlar

- Token'lar SHA256 ile hash'lenerek saklanıyor
- R2 upload çalışıyor
- Ödeme şu an simüle ediliyor (gerçek entegrasyon için Stripe/Iyzico eklenebilir)
- Ödeme başarısız olursa `/api/capsules/delete-draft` ile kayıtlar silinebilir
