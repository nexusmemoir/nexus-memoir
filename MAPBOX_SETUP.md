# 🗺️ MAPBOX SETUP - ÖNEMLİ!

## 🔑 Mapbox Token Alma (ÜCRETSİZ):

### 1️⃣ Hesap Oluştur:
```
https://account.mapbox.com/auth/signup/
```
- Email ile kayıt ol
- ÜCRETSİZ! 50,000 request/ay

### 2️⃣ Token Al:
```
https://account.mapbox.com/access-tokens/
```
- "Create a token" tıkla
- Token'ı kopyala (pk.eyJ... ile başlar)

### 3️⃣ Token'ı Ekle:
`static/js/map-landing.js` dosyasını aç:

**Satır 5'i değiştir:**
```javascript
// ESKİ:
mapboxgl.accessToken = 'pk.eyJ1IjoiZXhhbXBsZXVzZXIiLCJhIjoiY2tjdjN5NDk3MDd2ZTJ5bzh5a2ZkYmZjYSJ9...';

// YENİ (kendi token'ın):
mapboxgl.accessToken = 'BURAYA_KENDİ_TOKENINI_YAPIŞTIR';
```

### 4️⃣ Test Et:
```
http://localhost:8000/
```
Harita görünmeli!

---

## 🎨 ÖZELLEŞTİRME:

### Harita Stili Değiştir:
`map-landing.js` içinde `style` objesini değiştir.

**Mevcut:** CartoDB Light (pastel)
**Alternatifler:**
- Mapbox Streets: `mapbox://styles/mapbox/streets-v11`
- Mapbox Outdoors: `mapbox://styles/mapbox/outdoors-v11`
- Custom: Kendi stilini oluştur

### Baloncuk Renklerini Değiştir:
`map-landing.js` - Satır 26:
```javascript
const zoneColors = {
    premium: '#ff6b9d',   // Pembe
    popular: '#ffa94d',   // Turuncu
    standard: '#ffd93d',  // Sarı
    basic: '#95e1d3'      // Mint
};
```

---

## 🚀 PRODUCTION NOTLARI:

1. **Token Güvenliği:**
   - Token'ı `.env` dosyasına koy
   - Backend'den inject et
   - Asla GitHub'a commit etme!

2. **Rate Limits:**
   - 50,000 request/ay ücretsiz
   - Aşarsan ücretli plana geç
   - CDN kullan (cache)

3. **Performance:**
   - Lazy load markers
   - Cluster çok kapsül varsa
   - Optimize tile requests

---

## ❓ SORUN GİDERME:

**Harita görünmüyor:**
- Token doğru mu kontrol et
- Console'da hata var mı bak (F12)
- İnternet bağlantısı var mı?

**Token hatası:**
- Yeni token oluştur
- Public token kullanıyorsan limiti aşmış olabilirsin

**Baloncuklar görünmüyor:**
- `sampleCapsules` array'ine bak
- Koordinatlar doğru mu?

---

## 💡 NEXT STEPS:

1. ✅ Token ekle
2. ✅ Test et
3. ✅ Deploy et
4. 🔜 API'den gerçek kapsülleri çek
5. 🔜 Real-time updates ekle (WebSocket)

**HAZIR!** 🎉
