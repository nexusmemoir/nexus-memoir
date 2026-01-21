# 🚀 DEPLOYMENT CHECKLIST

## ✅ Adım Adım Deploy Rehberi

### 1️⃣ Dosyaları Projeye Kopyala

```bash
# Tüm yeni dosyaları git'e ekle:
git add app.py
git add templates/
git add static/
git add README.md

# Commit
git commit -m "feat: Add modern neural-themed UI with countdown timer

- New landing page with animated neural network background
- Redesigned dashboard with glassmorphism UI
- Live countdown timer for locked capsules
- Modern claim page
- Responsive mobile design
- Updated templates and static assets"

# Push
git push origin main
```

### 2️⃣ Render.com'da Kontrol Et

- [ ] Render dashboard'a git
- [ ] Yeni deploy başladığını gör
- [ ] Build logs'u izle
- [ ] "Build successful" mesajını bekle
- [ ] "Live" durumuna geçmesini bekle

### 3️⃣ Test Et

**Landing Page:**
- [ ] `https://your-app.onrender.com/` → Modern landing page açılıyor mu?
- [ ] Neural network animasyonu çalışıyor mu?
- [ ] Scroll smooth çalışıyor mu?
- [ ] CTA butonları doğru yönlendiriyor mu?

**Admin:**
- [ ] `/admin/create?p=PASSWORD` → Kapsül oluşturuluyor mu?
- [ ] QR link ve PIN görünüyor mu?

**Claim:**
- [ ] QR link'i aç
- [ ] PIN gir
- [ ] Dashboard'a yönlendiriliyor mu?

**Dashboard:**
- [ ] Zaman ayarlama çalışıyor mu?
- [ ] Metin ekleme çalışıyor mu?
- [ ] Foto yükleme çalışıyor mu?
- [ ] Video yükleme çalışıyor mu?

**Countdown:**
- [ ] Zaman ayarlandıktan sonra countdown görünüyor mu?
- [ ] Saniyeler düzgün sayıyor mu?
- [ ] Progress bar'lar doğru gösteriliyor mu?

### 4️⃣ Veritabanı Migration (Otomatik)

Uygulama ilk çalıştığında:
- [ ] Eski `media` tablosu varsa drop edilip yeniden oluşturulacak
- [ ] Logs'ta "[DB] Database initialized successfully!" görünmeli

Eğer sorun varsa:
```bash
# Render'da DB_PATH değişkenini değiştir:
DB_PATH=/var/data/db_v2.sqlite3
```

### 5️⃣ Mobil Test

- [ ] iPhone/Android'den aç
- [ ] Touch scroll çalışıyor mu?
- [ ] Butonlar responsive mi?
- [ ] Forms mobile'da kullanılabilir mi?

### 6️⃣ Production Checklist

- [ ] ADMIN_PASSWORD güçlü bir şifre mi?
- [ ] SECRET_KEY uzun ve rastgele mi?
- [ ] R2 bucket private mı?
- [ ] CORS ayarları doğru mu?
- [ ] Error handling çalışıyor mu?

---

## 🐛 Olası Sorunlar ve Çözümler

### Sorun: "Internal Server Error" - Foto yükleme
**Çözüm:**
1. Render logs'u kontrol et
2. R2 credentials doğru mu kontrol et
3. Veritabanı migration oldu mu bak
4. `/admin/create` ile yeni kapsül oluştur

### Sorun: Static files 404
**Çözüm:**
1. `static/` klasörü repo'da var mı kontrol et
2. `app.py`'de `app.mount("/static", ...)` var mı bak
3. Git'e düzgün eklendi mi kontrol et

### Sorun: Template not found
**Çözüm:**
1. `templates/` klasörü repo'da var mı
2. Dosya isimleri doğru mu: `landing.html`, `claim.html`, `dashboard.html`

### Sorun: Countdown çalışmıyor
**Çözüm:**
1. Browser console'da JS hataları var mı bak
2. `countdown.js` yükleniyor mu kontrol et
3. `data-unlock` attribute doğru mu kontrol et

---

## 🎉 Deploy Başarılı!

Artık şunları yapabilirsin:

1. **Landing page'i paylaş** - Ürünü tanıt
2. **Demo kapsüller oluştur** - Test et
3. **Countdown'ı test et** - 2-3 dakika sonrasına ayarla
4. **Mobil'den dene** - QR okut
5. **Domain ekle** - (İsteğe bağlı) Cloudflare Pages ile

---

## 📊 Sonraki Adımlar

### Domain Almak İstersen:

1. Domain satın al (ör: nexusmemoir.com)
2. Cloudflare'e ekle
3. Render'da custom domain ayarla
4. SSL otomatik gelir

### Analytics Eklemek İstersen:

```html
<!-- landing.html <head> içine -->
<script async src="https://www.googletagmanager.com/gtag/js?id=YOUR-ID"></script>
```

### SEO İyileştirmesi:

```html
<meta name="description" content="Zamanı kilitle. Zihnini sakla. Neural-inspired dijital zaman kapsülleri.">
<meta name="keywords" content="time capsule, dijital kapsül, anı saklama">
<meta property="og:title" content="NexusMemoir">
<meta property="og:description" content="Zamanı kilitle. Zihnini sakla.">
```

---

**Tebrikler! 🎉 Uygulamam artık production'da!**
