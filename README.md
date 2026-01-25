# 🔬 AkademikSoru - Bilimsel Araştırma Platformu

**FAZ 3: Gelişmiş Anlamsal Araştırma ve Derin Makale Analizi**

Günlük sorularınıza akademik makalelerden kanıta dayalı yanıtlar bulan, yapay zeka destekli araştırma platformu.

## ✨ Özellikler

### 🎯 Akıllı Araştırma Sistemi (YENİ!)
- **Anlamsal Sorgu Üretimi**: Kelime bazlı değil, anlam bazlı sorgu üretimi
- **Relevance Checker**: Her makaleye 0-100 arası alakalılık skoru
- **Akıllı Filtreleme**: Alakasız makaleler otomatik elenir
- **Stratejik Sıralama**: %50 Alakalılık + %50 Atıf sayısı

### 🔍 Derin Makale Analizi (FAZ 3)
- **Türkçe Çeviri**: İngilizce makalelerden Türkçe çeviri ve açıklama
- **Önemli Bulgular**: Her makaleden EN ÖNEMLİ 3 bulgu çıkarımı
- **Orijinal Metinler**: Her bulgunun orijinal İngilizce cümlesi
- **Pratik Sonuçlar**: "Peki ne yapmalıyız?" sorusuna yanıt
- **İlgililik Metriği**: Makalenin soruyla alakalılık yüzdesi

### 🧠 Yapay Zeka Destekli Analiz
- GPT-4 ile makale analizi ve sentez
- 3 seviye açıklama: Basit, Orta, Akademik
- Türkçe özet ve anahtar noktalar
- Kanıt gücü değerlendirmesi (Güçlü/Orta/Sınırlı/Yetersiz)

### 👤 Kullanıcı Özellikleri
- Kullanıcı hesapları ve oturum yönetimi
- Soruları kaydetme ve geçmiş
- Konu takibi ve newsletter
- Soru oylama sistemi
- Arama geçmişi

### 📊 Veri & Kaynaklar
- Semantic Scholar API entegrasyonu
- 200M+ akademik makale erişimi
- Atıf sayısı ve yayın yılı filtreleme
- Açık erişimli PDF bağlantıları

## 🚀 Kurulum

### Gereksinimler
- Python 3.8+
- OpenAI API key

### 1. Projeyi İndirin
```bash
git clone <repo-url>
cd akademiksoru
```

### 2. Sanal Ortam Oluşturun
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Ortam Değişkenlerini Ayarlayın
```bash
cp .env.example .env
# .env dosyasını düzenleyip OpenAI API key'inizi ekleyin
```

### 5. Uygulamayı Başlatın
```bash
python app.py
```

Tarayıcınızda `http://localhost:8000` adresine gidin.

## 📁 Proje Yapısı

```
akademiksoru/
├── app.py                  # Ana FastAPI uygulaması
├── database.py             # SQLite veritabanı işlemleri
├── requirements.txt        # Python bağımlılıkları
├── templates/              # Jinja2 HTML şablonları
│   ├── index.html
│   ├── result.html
│   ├── profile.html
│   ├── about.html
│   └── ...
└── static/
    └── css/
        └── style.css       # Premium modern UI
```

## 🎨 Kullanım

### 1. Soru Sorun
Ana sayfada sorunuzu yazın ve açıklama seviyesini seçin:
- 🎈 **Basit**: 10 yaşındaki birine anlatır gibi
- 📖 **Orta**: Lise mezunu birine anlatır gibi
- 🎓 **Akademik**: Üniversite öğrencisine anlatır gibi

### 2. Sonuçları İnceleyin
- Türkçe özet ve anahtar noktalar
- Kanıt gücü göstergesi
- Kaynak makaleler listesi
- İlgili sorular önerileri

### 3. Derin Analiz (YENİ!)
Her makale için **"🔬 Derinlemesine Analiz Et"** butonuna tıklayın:
- Ana bulgu özeti
- Türkçe çevrilmiş önemli noktalar
- Orijinal İngilizce metinler
- Pratik öneriler
- İlgililik metriği

### 4. Kaydedin ve Takip Edin
- Soruları kaydedin
- Konuları takip edin
- Newsletter'a abone olun

## 🔧 Teknik Detaylar

### Araştırma Algoritması

#### 1. Akıllı Sorgu Üretimi
```python
# Eski: Basit kelime çevirisi
queries = ["vitamin D deficiency depression"]

# Yeni: Stratejik ve anlamsal
queries = [
    "vitamin D deficiency depression relationship",  # Ana kavram
    "cholecalciferol mental health meta-analysis",   # Spesifik terim
    "vitamin D supplementation mood disorders trial" # Araştırma alanı
]
```

#### 2. Relevance Scoring
Her makale için:
- GPT-4 ile anlamsal analiz (0-100 skor)
- Abstract ve başlık kontrolü
- Skor < 40 ise elenir
- Sonuçlar alakalılık + atıf ile sıralanır

#### 3. Sentez ve Analiz
- Sadece alakalı makaleler kullanılır
- Çoklu kaynak birleştirme
- Çelişkili bulgular belirlenir
- Kanıt gücü hesaplanır

### API Uç Noktaları

```
GET  /                          # Ana sayfa
GET  /result?q=...&level=...    # Sonuç sayfası
POST /api/research              # Araştırma yap
POST /api/paper/analyze         # Makale analizi (YENİ!)
POST /api/questions/save        # Soru kaydet
POST /api/vote                  # Oy ver
GET  /profile                   # Profil sayfası
```

## 🎯 Örnek Kullanım Senaryoları

### Senaryo 1: Basit Soru
**Soru**: "Kahve içmek zararlı mı?"

**Sistem**:
1. Akıllı sorgular: "coffee consumption health effects", "caffeine cardiovascular meta-analysis"
2. 15-20 makale bulur
3. Relevance check: 8 alakalı makale seçilir
4. Sentez: "Günde 3-4 fincan kahve genellikle zararsız..."

### Senaryo 2: Derin Analiz
**Makale**: "Coffee consumption and health: umbrella review"

**Derin Analiz Sonucu**:
- 🎯 Ana Bulgu: "Orta kahve tüketimi (3-5 fincan) kardiyovasküler hastalık riskini %15 azaltıyor"
- 💡 Önemli Nokta 1: "Hamile kadınlar günde 200mg'ı geçmemeli"
- 💡 Önemli Nokta 2: "Filtresiz kahve kolesterol artırabilir"
- ✅ Pratik: "Günde 3-4 fincan filtre kahve ideal"
- 📊 İlgililik: %92

## ⚠️ Önemli Notlar

1. **Tıbbi Tavsiye Değildir**: Bu platform sadece bilgilendirme amaçlıdır
2. **Uzman Danışın**: Sağlık kararları için mutlaka doktor danışın
3. **Kaynak Kontrol**: AI her zaman %100 doğru olmayabilir
4. **Rate Limit**: Dakikada 15 istek limiti var

## 🛠️ Geliştirme

### Test Etme
```bash
# Zorlu testler
python test_research.py

# Örnek sorular:
# - "Omega-3 çocuklarda DEHB'ye iyi gelir mi?"
# - "İntermittent fasting metabolik sendrom üzerine etkisi?"
```

### Debug
```bash
# Console'da göreceksiniz:
# [ARAŞTIRMA] Üretilen sorgular: [...]
# [ARAŞTIRMA] Toplam X makale bulundu
# [ARAŞTIRMA] Alakalı Y makale bulundu (skor >= 40)
```

## 📝 Değişiklik Geçmişi

### FAZ 3 (v3.0) - Anlamsal Araştırma
- ✅ Akıllı sorgu üretimi
- ✅ Relevance checker sistemi
- ✅ Alakalılık skorlaması
- ✅ Stratejik makale sıralaması
- ✅ Derin makale analizi
- ✅ Türkçe çeviri ve açıklama
- ✅ Orijinal metin gösterimi

### FAZ 2 (v2.0) - Kullanıcı Sistemi
- Hesap ve oturum yönetimi
- Soru kaydetme
- Konu takibi
- Oylama sistemi

### FAZ 1 (v1.0) - MVP
- Temel araştırma
- GPT entegrasyonu
- Semantic Scholar API

## 📄 Lisans

MIT License

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır!

## 📞 İletişim

Sorularınız için issue açabilirsiniz.

---

**© 2025 AkademikSoru** - Bilimsel Araştırma Platformu
