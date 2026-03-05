#!/usr/bin/env python3
"""
Referans Video Eğitim Scripti
==============================
Yeni bir ürün tipi için referans videodan döngü profili eğitir.

Kullanım:
    python scripts/train_reference.py \
        --video data/reference_videos/gomlek_50cycles.mp4 \
        --cycles 50 \
        --product-name gomlek

    # Özel config ile
    python scripts/train_reference.py \
        --video data/reference_videos/tisort_ref.mp4 \
        --cycles 50 \
        --product-name tisort \
        --config configs/custom_config.yaml

    # Eğitim sonucunu görselleştir
    python scripts/train_reference.py \
        --video data/reference_videos/gomlek_50cycles.mp4 \
        --cycles 50 \
        --product-name gomlek \
        --visualize
"""

import sys
import argparse
import yaml
import numpy as np
import matplotlib
from pathlib import Path

# Proje kök dizinini path'e ekle
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.reference_trainer import ReferenceTrainer
from src.core.hand_tracker import HandTracker
from src.core.signal_processor import SignalProcessor


def load_config(config_path: str) -> dict:
    """YAML konfigürasyon dosyasını yükle."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def visualize_training_result(
    video_path: str,
    profile,
    config: dict,
):
    """
    Eğitim sonucunu görselleştir:
    - Ham ve işlenmiş sinyal grafikleri
    - Tespit edilen peak noktaları
    - Döngü şablonu
    """
    matplotlib.use("Agg")  # Başsız (headless) ortam için
    import matplotlib.pyplot as plt

    print("\n[Görselleştirme] Sinyal analiz grafikleri oluşturuluyor...")

    # Videoyu tekrar işle (sinyal çıkarmak için)
    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    tracker = HandTracker(config)
    processor = SignalProcessor(config, fps=fps)

    for frame_idx in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        timestamp = frame_idx / fps
        hand_data = tracker.process_frame(frame, frame_idx, timestamp)
        processor.add_sample(hand_data)

    cap.release()
    tracker.release()

    # Sinyalleri al
    raw_signal = processor.get_raw_signal()
    processed_signal = processor.get_signal()
    timestamps = processor.get_timestamps()

    # Peak detection
    peaks, _ = SignalProcessor.find_peaks_in_signal(
        processed_signal,
        fps=fps,
        prominence=profile.calibrated_peak_prominence,
        height=profile.calibrated_peak_height,
    )

    # Grafik oluştur
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))

    # 1. Ham sinyal
    ax1 = axes[0]
    if len(timestamps) == len(raw_signal):
        ax1.plot(timestamps, raw_signal, "b-", alpha=0.5, linewidth=0.5)
    ax1.set_title("Ham El Pozisyon Sinyali (Wrist Y)", fontsize=14)
    ax1.set_ylabel("Y Pozisyon (normalize)")
    ax1.grid(True, alpha=0.3)

    # 2. İşlenmiş sinyal + peak'ler
    ax2 = axes[1]
    t = np.linspace(0, len(processed_signal) / fps, len(processed_signal))
    ax2.plot(t, processed_signal, "b-", linewidth=1, label="İşlenmiş Sinyal")
    if len(peaks) > 0:
        peak_times = peaks / fps
        ax2.plot(peak_times, processed_signal[peaks], "rv",
                 markersize=10, label=f"Döngü ({len(peaks)} adet)")
    ax2.set_title(f"İşlenmiş Sinyal + Tespit Edilen Döngüler ({len(peaks)} adet)",
                  fontsize=14)
    ax2.set_ylabel("Sinyal Değeri")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Döngü şablonu
    ax3 = axes[2]
    template = profile.get_template_array()
    if len(template) > 0:
        t_template = np.linspace(0, profile.template_duration_sec, len(template))
        ax3.plot(t_template, template, "r-", linewidth=2, label="Ortalama Şablon")
        # Birkaç örnek döngü de çiz
        for i, cycle in enumerate(profile.all_cycle_signals[:5]):
            cycle_arr = np.array(cycle)
            t_c = np.linspace(0, profile.template_duration_sec, len(cycle_arr))
            ax3.plot(t_c, cycle_arr, "--", alpha=0.3, linewidth=1)
        ax3.set_title("Öğrenilen Döngü Şablonu (Template)", fontsize=14)
        ax3.set_xlabel("Zaman (saniye)")
        ax3.set_ylabel("Sinyal Değeri")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

    plt.tight_layout()

    # Kaydet
    output_path = Path(f"data/trained_models/{profile.product_name}_analysis.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Grafik kaydedildi: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Referans video ile döngü profili eğitimi"
    )
    parser.add_argument(
        "--video", "-v", required=True,
        help="Referans video dosya yolu"
    )
    parser.add_argument(
        "--cycles", "-c", type=int, default=50,
        help="Videodaki beklenen döngü sayısı (varsayılan: 50)"
    )
    parser.add_argument(
        "--product-name", "-p", required=True,
        help="Ürün adı (örn: gomlek, tisort)"
    )
    parser.add_argument(
        "--config", default="configs/default_config.yaml",
        help="Konfigürasyon dosyası yolu"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Profil kayıt yolu (varsayılan: data/trained_models/<product>_profile.json)"
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="Eğitim sonucunu görselleştir"
    )

    args = parser.parse_args()

    # Config yükle
    config_path = Path(PROJECT_ROOT / args.config)
    if config_path.exists():
        config = load_config(str(config_path))
    else:
        print(f"UYARI: Config bulunamadı ({config_path}), varsayılan değerler kullanılacak.")
        config = {}

    # Video kontrolü
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"HATA: Video bulunamadı: {video_path}")
        sys.exit(1)

    # Eğitim
    trainer = ReferenceTrainer(config)
    profile = trainer.train(
        video_path=str(video_path),
        expected_cycles=args.cycles,
        product_name=args.product_name,
    )

    # Profili kaydet
    save_path = args.output or f"data/trained_models/{args.product_name}_profile.json"
    profile.save(save_path)

    # Görselleştirme
    if args.visualize:
        visualize_training_result(str(video_path), profile, config)

    print("\n✓ Eğitim tamamlandı!")
    print(f"  Profil: {save_path}")
    print(f"  Döngü sayısı: {profile.total_cycles_in_reference}")
    print(f"  Ort. süre: {profile.avg_cycle_duration_sec:.2f}s")
    print(f"\nSonraki adım:")
    print(f"  python scripts/run_live_counter.py --product {args.product_name} --camera 0")


if __name__ == "__main__":
    main()
