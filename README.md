# 🧠 NexusMemoir - Neural-Inspired Time Capsules

**Zamanı Kilitle. Zihnini Sakla.**

Modern, sinir ağları temalı dijital zaman kapsülü uygulaması. Anılarınızı, düşüncelerinizi ve özel anlarınızı geleceğe taşıyın.

---

## ✨ Özellikler

- 🔒 **Zamana Kilitli Kapsüller** - Belirlediğiniz tarihe kadar içerik tamamen kilitli
- ⏰ **Canlı Countdown** - Şık geri sayım göstergesi
- 🧬 **Güvenli Saklama** - Cloudflare R2 ile şifrelenmiş depolama
- 📝 **Çoklu Format** - 5 metin, 10 fotoğraf, 1 video
- 🎨 **Neural Network Animasyonları** - Etkileşimli arka plan efektleri
- 📱 **QR Kod Erişim** - Her cihazdan kolay erişim
- 🔐 **PIN Korumalı** - 6 haneli güvenlik

---

## 🚀 Yeni Özellikler (v2.0)

### 1. Modern Landing Page
- Tek sayfa, gradient tasarım
- Animated neural network background
- Özellikler, nasıl çalışır, CTA sections
- Responsive mobil tasarım

### 2. Yenilenmiş Dashboard
- Modern glassmorphism UI
- Canlı countdown timer
- Progress bar'lar
- Daha iyi upload UI

### 3. Countdown Özelliği
- Gün:Saat:Dakika:Saniye formatı
- Gradient animasyonlar
- Otomatik sayfa yenileme
- TR saat dilimi desteği

---

## 📦 Dosya Yapısı

```
nexus-memoir/
├── app.py                      # Backend (FastAPI)
├── requirements.txt            # Dependencies
├── .env                        # Environment variables
├── templates/
│   ├── landing.html           # Ana sayfa
│   ├── claim.html             # QR → PIN girişi
│   └── dashboard.html         # Kapsül yönetimi + countdown
└── static/
    ├── css/
    │   ├── landing.css        # Landing page styles
    │   └── app.css            # Dashboard/claim styles
    └── js/
        ├── neural-bg.js       # Animated background
        └── countdown.js       # Timer logic
```

---

## 🛠️ Teknolojiler

- **Backend:** FastAPI (Python)
- **Database:** SQLite
- **Storage:** Cloudflare R2 (S3-compatible)
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Hosting:** Render.com
- **Animations:** Canvas API, CSS Gradients

---

## 🌐 Deploy (Render.com)

### 1. Repository Hazırlık

```bash
# Tüm dosyaları projeye kopyala
cp -r templates/ static/ app.py /path/to/your/repo/

# Git'e ekle
git add .
git commit -m "Add modern UI with neural theme and countdown"
git push
```

### 2. Render.com Ayarları

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
```
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password
R2_ENDPOINT=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET=nexusmemoir-media
DB_PATH=/var/data/db.sqlite3  (opsiyonel, persistent disk için)
```

### 3. Deploy

Render otomatik olarak deploy edecek. Logları izleyin:
- "Build successful" mesajını bekleyin
- "Live" durumuna geçmesini bekleyin

---

## 🎯 Kullanım

### Admin - Kapsül Oluşturma
```
https://your-app.onrender.com/admin/create?p=YOUR_ADMIN_PASSWORD
```

### Kullanıcı - Kapsül Açma
1. QR kodu okutun
2. PIN'i girin
3. Dashboard'da:
   - Açılma zamanını belirle
   - Metin/foto/video ekle
   - Countdown'u izle
   - Zaman geldiğinde içerikleri gör

---

## 🎨 Tasarım Konsepti

### Renk Paleti
- Primary: `#6366f1` (Indigo)
- Secondary: `#8b5cf6` (Purple)
- Accent: `#ec4899` (Pink)
- Gradient: `135deg, #6366f1 → #8b5cf6 → #ec4899`

### Tema
- **Sinir Ağları:** Animated nodes ve connections
- **Glassmorphism:** Blur effects, transparency
- **Gradient:** Mor-mavi-pembe geçişler
- **Dark Mode:** `#0f0f23` background

---

## 📱 Responsive Breakpoints

- **Desktop:** 1024px+
- **Tablet:** 768px - 1024px
- **Mobile:** < 768px

Tüm sayfalar mobil-first yaklaşımla tasarlandı.

---

## 🔮 Gelecek Özellikler (v3.0)

- [ ] Email notifications (kapsül açılmadan önce)
- [ ] Sosyal medya paylaşımı
- [ ] Tema seçenekleri (light/dark/custom)
- [ ] Çoklu dil desteği
- [ ] Admin panel (tüm kapsüller)
- [ ] Analytics dashboard
- [ ] Capsule templates
- [ ] Collaborative capsules

---

## 🐛 Sorun Giderme

### "Internal Server Error" - Foto Yükleme
**Çözüm:** R2 credentials kontrol et, veritabanı migration yapıldı mı bak

### Countdown Çalışmıyor
**Çözüm:** `countdown.js` yüklendiğinden emin ol, browser console'u kontrol et

### Static Files 404
**Çözüm:** `app.mount("/static", ...)` satırı eklenmiş mi kontrol et

### Template Bulunamıyor
**Çözüm:** `templates/` klasörü doğru konumda mı kontrol et

---

## 📝 Lisans

MIT License - Özgürce kullanabilirsiniz.

---

## 🤝 Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce issue açın.

---

## 💬 İletişim

Sorular için GitHub Issues kullanabilirsiniz.

---

**Made with 🧠 and ❤️ by NexusMemoir Team**
