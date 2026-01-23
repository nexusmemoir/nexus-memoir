# NexusMemoir - Dijital Zaman Kapsülü

## Düzeltilen Bug'lar

### 1. ✅ Landing Page Butonları Çalışmıyor
**Sebep:** `#neuralBg` canvas elementi tüm sayfayı kaplıyordu ve `pointer-events` engelliyordu.
**Çözüm:** Tüm CSS dosyalarında `#neuralBg` elementine `pointer-events: none` eklendi.

### 2. ✅ Harita Hover Bug'ı (Nokta Sol Üste Kaçıyor)
**Sebep:** Marker elementine doğrudan `transform: scale()` uygulanınca Mapbox marker pozisyonu kayıyordu.
**Çözüm:** `map-landing.js` yeniden yazıldı - scale transform'u container yerine inner element'e uygulanıyor.

### 3. ✅ Tarih + Saat Seçimi
**Çözüm:** `create-capsule.html`'de `type="date"` → `type="datetime-local"` değiştirildi.

### 4. ✅ Gömme Animasyonu
**Çözüm:** `create-sync.js`'de ödeme başarılı olduktan sonra gömme animasyonu gösteriliyor.

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
│   │   ├── create-sync.js      # ✅ Gömme animasyonu eklendi
│   │   ├── countdown.js
│   │   ├── globe-hero.js
│   │   └── create-wizard.js
│   └── images/
│       ├── nexusmemoir-logo.png
│       ├── product.png
│       ├── locked.png
│       └── unlocked.png
└── templates/
    ├── map-landing.html   # Ana sayfa (harita)
    ├── landing.html       # Alternatif landing
    ├── globe-landing.html # 3D globe landing
    ├── create-capsule.html # ✅ datetime-local eklendi
    ├── dashboard.html
    ├── claim.html
    ├── success.html
    └── admin-dashboard.html
```

## Kurulum

```bash
cd nexusmemoir
pip install -r requirements.txt --break-system-packages
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Mevcut Akış

1. **Yer Seç** → Haritada double-click (desktop) veya 3-tap (mobile)
2. **Kaz (Dig)** → Otomatik kazma animasyonu
3. **Detaylar** → Başlık ve açılış tarihi+saati gir
4. **Önizleme** → Kapsülün nasıl görüneceğini gör
5. **Ödeme** → Ödemeyi tamamla
6. **Gömme Animasyonu** → Kapsül gömülüyor animasyonu
7. **Başarı** → QR kod ve PIN gösterilir

## Veritabanı Şeması

```sql
capsules:
- id, token_hash, pin_hash, unlock_at
- lat, lng, location_name, capsule_title
- is_public (0=gizli, 1=haritada görünür)
- status (draft, locked, paid)
- created_at

notes:
- id, capsule_id, text, created_at

media:
- id, capsule_id, kind (photo/video)
- r2_key, original_name, content_type
- size_bytes, created_at
```

## API Endpoints

- `GET /` - Ana sayfa (map-landing)
- `GET /create` - Kapsül oluşturma sayfası
- `POST /api/capsules/create` - Yeni kapsül oluştur
- `GET /api/capsules/public` - Haritada görünen kapsüller
- `POST /claim` - Token+PIN ile kapsüle eriş
- `GET /dashboard` - Kapsül dashboard'u
- `POST /add-note` - Metin ekle
- `POST /upload/photo` - Foto yükle (R2)
- `POST /upload/video` - Video yükle (R2)

## Notlar

- Token'lar SHA256 ile hash'lenerek saklanıyor ✅
- R2 upload çalışıyor ✅
- Şu anda ödeme simüle ediliyor (gerçek ödeme entegrasyonu gerekli)
