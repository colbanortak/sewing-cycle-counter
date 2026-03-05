# Jetson Orin Deployment Rehberi

## Donanım Gereksinimleri

- NVIDIA Jetson Orin Nano (8GB) veya Orin NX (16GB)
- USB3.0 veya GigE kameralar (makine başına 1 adet)
- Ethernet switch (IP kamera kullanılacaksa)
- 64GB+ microSD veya NVMe SSD

## Kurulum Adımları

### 1. JetPack SDK Kurulumu
```bash
# JetPack 6.0+ kurulu olmalı (L4T R36.x)
# DeepStream 7.0 JetPack ile birlikte gelir
sudo apt update && sudo apt upgrade -y

# Python bağımlılıkları
pip3 install mediapipe opencv-python numpy scipy pyyaml fastapi uvicorn sqlalchemy
```

### 2. DeepStream Python Bindings
```bash
# DeepStream 7.0 Python bindings
pip3 install pyds-ext
# veya kaynak koddan derleme:
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps
pip3 install ./bindings/
```

### 3. TensorRT ile Model Optimizasyonu
```bash
# MediaPipe → ONNX → TensorRT dönüşümü
# Bu adım PoC'den üretime geçişte yapılacak
python3 scripts/convert_to_tensorrt.py --model hand_landmark --precision fp16
```

### 4. Çoklu Kamera Konfigürasyonu
```yaml
# configs/jetson_production.yaml
deepstream:
  enabled: true
  batch_size: 8
  cameras:
    - id: "M01"
      source: "rtsp://192.168.1.101:554/stream"
      operator: "Ahmet"
    - id: "M02"
      source: "rtsp://192.168.1.102:554/stream"
      operator: "Mehmet"
    # ... 8 kameraya kadar
```

## DeepStream Pipeline Mimarisi (Faz 2)

```
[Kamera 1] ──┐
[Kamera 2] ──┤    ┌──────────┐   ┌──────────┐   ┌──────────┐
[Kamera 3] ──┼───▶│ Streammux │──▶│ nvinfer  │──▶│ nvtracker│──▶ Cycle Counter
   ...       │    │ (batch)  │   │(TensorRT)│   │  (NvDCF) │
[Kamera 8] ──┘    └──────────┘   └──────────┘   └──────────┘
```

## Performans Beklentileri

| Cihaz | Kamera Sayısı | FPS/Kamera | Güç |
|-------|--------------|------------|-----|
| Orin Nano 8GB | 4 | 30 | 15W |
| Orin NX 16GB | 8 | 30 | 25W |
| Orin AGX 64GB | 16 | 30 | 50W |

## Geçiş Planı: PoC → Üretim

1. PoC doğrulama (PC/Laptop) ✓
2. Jetson'a port (MediaPipe + OpenCV)
3. DeepStream entegrasyonu (TensorRT inference)
4. Çoklu kamera testi
5. Tam atölye deployment
