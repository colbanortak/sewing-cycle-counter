# PoC'den DeepStream'e Geçiş Planı

## Mevcut PoC Mimarisi
```
OpenCV VideoCapture → MediaPipe Hands → SciPy Signal → Peak Detection → SQLite
```

## Hedef DeepStream Mimarisi
```
GStreamer Source → Streammux → nvinfer (TensorRT) → nvtracker → Custom Probe → API
```

## Geçiş Adımları

### Adım 1: Model Dönüşümü
- MediaPipe Hand Landmark modelini ONNX formatına çıkar
- ONNX → TensorRT engine dönüşümü (FP16 precision)
- Custom parser yazarak landmark çıktılarını DeepStream metadata'sına ekle

### Adım 2: GStreamer Pipeline
- Her kamera için `uridecodebin` veya `nvarguscamerasrc` kaynak
- `nvstreammux` ile batch oluşturma
- `nvinfer` ile TensorRT inference
- Custom `GstPadProbeCallback` ile sinyal işleme ve döngü sayma

### Adım 3: Sinyal İşleme Entegrasyonu
- `signal_processor.py` ve `cycle_detector.py` aynen kalır
- DeepStream probe callback içinden çağrılır
- Her kamera için ayrı processor/detector instance'ı

### Adım 4: Çıktı ve Raporlama
- `nvmsgconv` + `nvmsgbroker` ile MQTT/Kafka'ya veri gönderimi
- Veya mevcut FastAPI + SQLite yapısına doğrudan yazma

## Dikkat Edilecekler
- MediaPipe doğrudan Jetson'da çalışır (CPU modunda)
- DeepStream'e geçiş zorunlu değil, yalnızca 4+ kamera performansı gerektiğinde
- İlk Jetson deployment'ı PoC kodunu direkt kullanabilir
