# CLAUDE.md — Dikiş Atölyesi Performans Takip Sistemi

## Proje Özeti
Dikiş atölyesinde her makinenin başındaki dikişçinin kaç adet dikim döngüsü (cycle)
yaptığını otomatik sayan AI tabanlı video analiz sistemi.
Tüm yönetim web arayüzünden yapılır (video yükleme, eğitim, canlı sayım, dashboard).

## Teknoloji Yığını (Net Liste)

| Bileşen | Teknoloji | Versiyon | Neden Bu? |
|---------|-----------|----------|-----------|
| El Takibi | MediaPipe Hands | >=0.10.9 | Hafif, CPU'da çalışır, 21 landmark |
| Sinyal Yumuşatma | SciPy Savitzky-Golay | >=1.11 | Gürültü temizleme, sinyal koruma |
| Frekans Filtre | SciPy Butterworth Bandpass | >=1.11 | Düşük/yüksek frekans gürültü kesme |
| Döngü Tespit | SciPy find_peaks | >=1.11 | Peak detection + prominence filtre |
| Şablon Eşleme | NumPy corrcoef | >=1.24 | Normalized cross-correlation |
| Video I/O | OpenCV | >=4.9 | Kamera, RTSP, video dosya okuma |
| Web Arayüzü | FastAPI + Vanilla JS | >=0.109 | REST API + gömülü HTML dashboard |
| Veritabanı | SQLite (stdlib) | - | Sıfır kurulum, tek dosya DB |
| Konfigürasyon | PyYAML | >=6.0 | YAML bazlı ayar yönetimi |
| Veri Modeli | Pydantic | >=2.5 | API request/response doğrulama |
| Görselleştirme | Matplotlib | >=3.8 | Eğitim sonuç grafikleri |
| Hedef Donanım | NVIDIA Jetson Orin | JetPack 6+ | Edge AI, çoklu kamera |
| Üretim Framework | DeepStream SDK | 7.0 | TensorRT + GStreamer pipeline |

## Kullanılan Yöntemler (Algoritmik)

### 1. El Takibi (Hand Tracking)
- **MediaPipe Hands**: Her frame'de 21 el landmark noktası çıkarır
- Birincil sinyal: WRIST (bilek) Y pozisyonu -> dikişçinin yukarı-aşağı hareketi
- İkincil sinyaller: el açıklık skoru, hareket hızı (velocity)
- Baskın el seçimi: bounding box alanı en büyük olan el

### 2. Sinyal İşleme (Signal Processing)
- **Combined Signal**: 0.5*Y_pozisyon + 0.3*velocity + 0.2*el_açıklık
- **Savitzky-Golay Filtre**: Pencere=15, polinom=3 -> gürültüyü yumuşat
- **Butterworth Bandpass**: 0.1-3.0 Hz -> çok yavaş drift ve titreşimi kes
- **Min-Max Normalizasyon**: 0-1 arasına normalize et

### 3. Döngü Tespit (Cycle Detection)
- **Peak Detection**: scipy.signal.find_peaks ile tepe noktalarını bul
  - min_distance: minimum döngü süresi x FPS
  - prominence: peak belirginliği eşiği
  - height: minimum peak yüksekliği
- **Template Matching**: Referans profilden öğrenilen şablonla korelasyon
  - Normalized cross-correlation (np.corrcoef)
  - Eşik: 0.6 (kalibre edilebilir)
- **Adaptif Kalibrasyon**: İlk 5 döngüden sonra eşikleri otomatik ayarla

### 4. Referans Eğitim (Reference Training)
- Grid search ile optimal peak parametrelerini bul
- Tüm döngüleri kes -> aynı uzunluğa resample et -> ortalama template oluştur
- Outlier döngüleri filtrele (korelasyon < 0.3)
- İstatistikleri hesapla ve JSON profiline kaydet

## Komutlar

### Bağımlılık Kurulumu
```bash
pip install -r requirements.txt
```

### Web Arayüzünü Başlat (TÜM İŞLEMLER BURADAN YAPILIR)
```bash
python scripts/run_dashboard.py
# -> http://localhost:8080           Ana dashboard
# -> http://localhost:8080/ui/train  Eğitim sayfası (video yükle, döngü sayısı gir)
# -> http://localhost:8080/ui/live   Canlı sayım başlat/durdur
# -> http://localhost:8080/ui/profiles Profil yönetimi
# -> http://localhost:8080/docs      API dokümantasyonu (Swagger)
```

### Terminal'den Kullanım (Alternatif)
```bash
python scripts/train_reference.py --video <VIDEO> --cycles <SAYI> --product-name <AD>
python scripts/run_live_counter.py --product <AD> --camera 0
python scripts/run_video_analysis.py --video <VIDEO> --product <AD>
```

### Testler
```bash
python tests/test_signal_processor.py
pytest tests/ -v
```

## Web Arayüzü Sayfaları

### /ui/train (Eğitim Sayfası)
Kullanıcı şunları girer:
- Ürün Adı: gomlek, tisort, pantolon vb.
- Döngü Sayısı: Referans videodaki dikim sayısı (varsayılan 50, 10-500 arası)
- Video Dosyası: MP4/AVI/MOV referans video
- Model Karmaşıklığı: 0=hafif, 1=orta, 2=ağır
- Sinyal Türü: combined, y_position, velocity
Backend: Video yüklenir -> ReferenceTrainer çalışır -> Profil JSON kaydedilir

### /ui/live (Canlı Sayım)
Kullanıcı şunları girer:
- Profil: Daha önce eğitilmiş ürün profili (dropdown)
- Kamera: 0=USB, rtsp://... IP kamera
- Makine ID: M01, M02 vb.
- Operatör Adı: İsteğe bağlı
Backend: Arka planda run_live_counter.py subprocess başlar

### /ui/profiles (Profil Yönetimi)
Tüm eğitilmiş profillerin kartları, silme butonu

### / (Dashboard - Tam Yönetim Paneli)
5 sekmeli web arayüzü:
- **Genel Bakış**: Bugün toplam üretim, aktif makine, eğitilmiş ürün kartları + son oturumlar tablosu
- **Ürün Eğitimi**: Video yükle, döngü sayısı gir (kullanıcı belirler, 50 sabit değil), eğitimi başlat
- **Makineler**: Makine ekle, kamera kaynağı (USB/RTSP) ve operatör ata
- **Canlı Sayım**: Makine+ürün dropdown'dan seç, sayımı başlat/durdur
- **Raporlar**: Tarih seç → günlük üretim raporu (makine ve ürün bazlı)

## Proje Yapısı
```
sewing-cycle-counter/
├── CLAUDE.md                          <- Claude Code bu dosyayı okur
├── README.md                          <- Genel dokümantasyon
├── requirements.txt                   <- pip bağımlılıkları
├── setup.py
├── configs/
│   └── default_config.yaml            <- Tüm sistem ayarları
├── src/
│   ├── core/
│   │   ├── hand_tracker.py            <- MediaPipe el takibi
│   │   ├── signal_processor.py        <- Sinyal filtreleme
│   │   ├── cycle_detector.py          <- Döngü tespit motoru
│   │   └── reference_trainer.py       <- Referans video eğitim
│   ├── utils/
│   │   ├── video_utils.py             <- Kamera/video I/O
│   │   ├── visualization.py           <- Video overlay
│   │   └── data_logger.py             <- SQLite loglama
│   ├── api/
│   │   └── server.py                  <- FastAPI + Web UI (TEK DOSYA)
│   └── models/
│       └── cycle_profile.py           <- Döngü profili veri modeli
├── scripts/
│   ├── train_reference.py             <- CLI eğitim
│   ├── run_live_counter.py            <- CLI canlı sayım
│   ├── run_video_analysis.py          <- CLI video analizi
│   └── run_dashboard.py               <- Web sunucusu başlatma
├── tests/
│   └── test_signal_processor.py
├── data/
│   ├── reference_videos/
│   ├── trained_models/
│   └── logs/
└── docs/
    ├── DEPLOYMENT_JETSON.md
    └── DEEPSTREAM_MIGRATION.md
```

## Kodlama Kuralları
- Python 3.10+ gerekli
- Type hint kullan
- Her modülün başında Türkçe docstring olmalı
- NumPy array işlemleri for döngüsüne tercih edilmeli
- Config değerleri hardcode DEĞİL, YAML veya kullanıcı input'undan okunmalı
- Yeni özellikler tests/ altına test ile eklenmeli
- Web UI: Vanilla JS, gömülü HTML (tek dosya server.py)

## Veri Akışı
```
Kullanıcı Web UI'dan video yükler + döngü sayısı girer
  -> /api/train endpoint (FastAPI)
    -> Video diske kaydedilir (data/reference_videos/)
    -> ReferenceTrainer.train() çağrılır
      -> HandTracker: her frame -> MediaPipe -> el landmark
      -> SignalProcessor: landmark -> sinyal -> filtre -> normalize
      -> Peak Detection: grid search -> optimal parametreler -> döngü tespiti
      -> Template Builder: döngüler kes -> resample -> ortalama şablon
    -> CycleProfile JSON kaydedilir (data/trained_models/)

Kullanıcı Web UI'dan canlı sayım başlatır
  -> /api/live/start endpoint
    -> run_live_counter.py subprocess başlar
      -> Kamera -> frame loop -> HandTracker -> SignalProcessor -> CycleDetector
      -> Her yeni döngü -> SQLite'a yazılır
    -> UI her 2 saniyede poll eder -> canlı sayım gösterilir
```

## Yol Haritası
1. [x] PoC: Tek kamera + MediaPipe + Peak Detection + Web UI
2. [ ] TCN/LSTM model entegrasyonu (derin öğrenme döngü tespiti)
3. [ ] DeepStream pipeline (çoklu kamera, TensorRT)
4. [ ] Mobil dashboard
5. [ ] OEE (Overall Equipment Effectiveness) hesaplaması
