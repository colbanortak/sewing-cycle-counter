# Dikiş Atölyesi Performans Takip Sistemi - PoC
## Sewing Workshop Cycle Counter (AI-Powered)

### 🎯 Proje Amacı
Dikiş atölyesinde her makinenin başındaki dikişçinin **kaç adet dikim işlemi (cycle)** yaptığını
otomatik olarak sayan, yapay zeka tabanlı bir video analiz sistemi.

### 📐 Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SEWING CYCLE COUNTER                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────┐ │
│  │  Camera   │───▶│  Hand/Pose   │───▶│ Signal        │───▶│Count │ │
│  │  Input    │    │  Tracker     │    │ Processor     │    │Engine│ │
│  │  (OpenCV) │    │  (MediaPipe) │    │ (SciPy)       │    │      │ │
│  └──────────┘    └──────────────┘    └───────────────┘    └──┬───┘ │
│                                                              │     │
│  ┌──────────────────────────────────────────────────────────┐│     │
│  │                    Reference Trainer                      ││     │
│  │  5-min video → 50 cycles → cycle profile extraction      ││     │
│  └──────────────────────────────────────────────────────────┘│     │
│                                                              │     │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────┐│     │
│  │  Dashboard   │◀───│  API Server   │◀───│  Data Logger   │◀┘     │
│  │  (Web UI)    │    │  (FastAPI)    │    │  (SQLite)      │       │
│  └──────────────┘    └───────────────┘    └────────────────┘       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 🔄 Sistem Akışı

#### AŞAMA 1: Referans Video ile Eğitim
1. Yeni ürün geldiğinde (gömlek, tişört vb.) 5 dakikalık referans video çekilir
2. Videoda dikişçi düzenli tempoda 50 adet dikim döngüsü yapar
3. Sistem bu videoyu analiz eder:
   - MediaPipe ile her frame'de el/bilek pozisyonları çıkarılır
   - El hareketleri zaman serisi sinyaline dönüştürülür
   - Otomatik peak detection ile döngü sınırları bulunur
   - Ortalama döngü profili (template) ve istatistikler kaydedilir

#### AŞAMA 2: Canlı Sayım
1. Kamera açılır, canlı video akışı başlar
2. Her frame'de el pozisyonları takip edilir
3. Oluşan sinyal, referans döngü profili ile karşılaştırılır
4. Template matching + peak detection ile yeni döngüler tespit edilir
5. Sayaç artırılır, zamanlama kaydedilir

### 📁 Proje Yapısı

```
sewing-cycle-counter/
├── README.md                          # Bu dosya
├── requirements.txt                   # Python bağımlılıkları
├── setup.py                           # Kurulum dosyası
├── configs/
│   └── default_config.yaml            # Varsayılan konfigürasyon
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── hand_tracker.py            # MediaPipe el takibi
│   │   ├── signal_processor.py        # Sinyal işleme ve peak detection
│   │   ├── cycle_detector.py          # Döngü tespit motoru
│   │   └── reference_trainer.py       # Referans video ile eğitim
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── video_utils.py             # Video okuma/yazma yardımcıları
│   │   ├── visualization.py           # Görselleştirme araçları
│   │   └── data_logger.py             # Veritabanı kayıt
│   ├── api/
│   │   ├── __init__.py
│   │   └── server.py                  # FastAPI REST API
│   └── models/
│       ├── __init__.py
│       └── cycle_profile.py           # Döngü profili veri modeli
├── scripts/
│   ├── train_reference.py             # Referans video eğitim scripti
│   ├── run_live_counter.py            # Canlı sayım scripti
│   ├── run_video_analysis.py          # Kayıtlı video analiz scripti
│   └── run_dashboard.py               # Dashboard başlatma
├── tests/
│   ├── test_hand_tracker.py
│   ├── test_signal_processor.py
│   └── test_cycle_detector.py
├── data/
│   ├── reference_videos/              # Referans videolar buraya
│   ├── trained_models/                # Eğitilmiş döngü profilleri
│   └── logs/                          # Sayım logları
└── docs/
    ├── DEPLOYMENT_JETSON.md           # Jetson Orin kurulum rehberi
    └── DEEPSTREAM_MIGRATION.md        # DeepStream'e geçiş planı
```

### 🚀 Hızlı Başlangıç

```bash
# 1. Bağımlılıkları kur
pip install -r requirements.txt

# 2. Referans video ile eğitim yap
python scripts/train_reference.py --video data/reference_videos/gomlek_50cycles.mp4 --cycles 50 --product-name "gomlek"

# 3a. Canlı kamera ile sayım başlat
python scripts/run_live_counter.py --product "gomlek" --camera 0

# 3b. Veya kayıtlı video üzerinde analiz yap
python scripts/run_video_analysis.py --video test_video.mp4 --product "gomlek"

# 4. Dashboard'u başlat (opsiyonel)
python scripts/run_dashboard.py
```

### ⚙️ Konfigürasyon

`configs/default_config.yaml` dosyasını düzenleyerek ayarları değiştirebilirsiniz.
Önemli parametreler:
- `camera.resolution`: Kamera çözünürlüğü (varsayılan 1280x720)
- `tracker.model_complexity`: MediaPipe model karmaşıklığı (0-2)
- `signal.smoothing_window`: Sinyal yumuşatma penceresi
- `detection.min_cycle_duration`: Minimum döngü süresi (saniye)
- `detection.similarity_threshold`: Döngü benzerlik eşiği

### 🎯 Hedef Platform
- **PoC**: Herhangi bir Linux/Windows PC (Python 3.10+)
- **Üretim**: NVIDIA Jetson Orin Nano/NX + DeepStream 7.0
- **Kamera**: USB webcam (PoC), IP kamera (üretim)

### 📊 Beklenen Performans
- PoC doğruluğu: %80-90
- İşleme hızı: 15-30 FPS (tek kamera, PC)
- Jetson Orin hedef: 30 FPS x 8 kamera eş zamanlı
