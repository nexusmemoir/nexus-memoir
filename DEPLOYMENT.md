# NexusMemoir - Hızlı Başlangıç Rehberi 🚀

## Yerel Geliştirme (5 Dakika)

### 1. Kurulum
```bash
# Sanal ortam oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya: venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Environment Variables
`.env` dosyası mevcut! Şunları güncelle:
- `R2_ENDPOINT` - Cloudflare R2 endpoint
- `R2_ACCESS_KEY_ID` - R2 access key
- `R2_SECRET_ACCESS_KEY` - R2 secret key
- `R2_BUCKET` - Bucket adın (örn: nexusmemoir-media)

### 3. Çalıştır
```bash
uvicorn app:app --reload --port 8000
```

Tarayıcıda aç: http://localhost:8000

---

## Render Deploy (10 Dakika)

### Gereksinimler
✅ GitHub hesabı
✅ Cloudflare R2 hesabı (ücretsiz)
✅ Render hesabı (ücretsiz)

### Adım 1: GitHub'a Yükle
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

### Adım 2: Cloudflare R2 Kur

1. https://dash.cloudflare.com → R2
2. "Enable R2" (ücretsiz)
3. Create Bucket → `nexusmemoir-media`
4. Manage R2 API Tokens → Create API Token
   - Name: nexusmemoir-api
   - Permissions: Object Read & Write
5. Token bilgilerini kaydet (bir daha görmeyeceksin!)

### Adım 3: Render'da Deploy

1. https://render.com → Sign Up (GitHub ile)
2. Dashboard → New → Web Service
3. Connect GitHub repo'nu
4. Settings:
   - **Name**: nexusmemoir
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`

5. **Environment Variables ekle**:
   ```
   SECRET_KEY = <rastgele-uzun-string>
   ADMIN_PASSWORD = <admin-şifren>
   R2_ENDPOINT = https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID = <r2-access-key>
   R2_SECRET_ACCESS_KEY = <r2-secret-key>
   R2_BUCKET = nexusmemoir-media
   DB_PATH = /var/data/db.sqlite3
   ```

6. **Disk ekle** (Database için):
   - Dashboard → Disks → Add Disk
   - Name: nexusmemoir-data
   - Mount Path: /var/data
   - Size: 1GB (ücretsiz)

7. "Create Web Service" → Bekle (2-3 dakika)

### Adım 4: Test Et!

Deploy tamamlandıktan sonra:
```
https://your-app-name.onrender.com
```

---

## Mapbox Token (Opsiyonel - Daha İyi Haritalar)

Şu an harita çalışıyor ama Mapbox token eklemek daha iyi görünüm sağlar:

1. https://www.mapbox.com → Sign Up (ücretsiz)
2. Access Tokens → Create Token
3. Token'ı kopyala

4. Bu dosyalarda güncelFle:
   - `static/js/create-sync.js` (satır 7)
   - `static/js/map-landing.js` (satır 1)
   
   ```javascript
   mapboxgl.accessToken = 'pk.YOUR_TOKEN_HERE';
   ```

5. Git push yap → Render otomatik deploy eder

---

## Sorun Giderme

### "R2 PUT FAILED" Hatası
✓ R2 credentials doğru mu kontrol et
✓ Bucket adı tam olarak eşleşiyor mu?
✓ API token'ın "Object Read & Write" yetkisi var mı?

### Harita Yüklenmiyor
✓ Mapbox token geçerli mi?
✓ Browser console'da hata var mı? (F12)

### Database Hatası (Render'da)
✓ Disk mount edildi mi? (/var/data)
✓ DB_PATH environment variable doğru mu?

---

## Test Senaryosu

1. **Ana Sayfa** → Haritada kapsüller görünüyor mu?
2. **Kapsül Oluştur** → Haritada lokasyon seç
3. **Bilgileri Doldur** → Başlık + tarih
4. **Success Page** → QR kod + PIN göründü mü?
5. **Claim** → QR ile veya /claim?token=XXX
6. **Dashboard** → İçerik ekle (metin, foto, video)
7. **Tarih Geç** → Countdown çalışıyor mu?
8. **Açılış** → İçerikler görünür mü?

---

## İpuçları

💡 **Geliştirme**: `.env` dosyasını kullan
💡 **Production**: Render environment variables kullan
💡 **Test**: Unlock zamanını 2 dakika sonraya ayarla
💡 **Debug**: Render Logs sekmesinden log'ları takip et
💡 **Backup**: SQLite veritabanını düzenli yedekle

---

## Destek Gerekirse

- README.md dosyasına bak
- Render logs kontrol et
- GitHub issues aç
- Cloudflare R2 docs: https://developers.cloudflare.com/r2/

**Başarılar! 🚀**
