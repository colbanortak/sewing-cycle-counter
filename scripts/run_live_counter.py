#!/usr/bin/env python3
"""
Canlı Döngü Sayım Scripti
===========================
Kamera veya RTSP akışından gerçek zamanlı dikim döngüsü sayar.

Kullanım:
    # USB kamera ile (profil ile)
    python scripts/run_live_counter.py --product gomlek --camera 0

    # IP kamera ile
    python scripts/run_live_counter.py --product gomlek \
        --camera "rtsp://192.168.1.100:554/stream"

    # Profil olmadan (sadece peak detection)
    python scripts/run_live_counter.py --camera 0 --no-profile

    # Makine ve operatör bilgisi ile (loglama için)
    python scripts/run_live_counter.py --product gomlek --camera 0 \
        --machine M03 --operator "Ahmet"
"""

import sys
import argparse
import yaml
import cv2
import time
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.hand_tracker import HandTracker
from src.core.signal_processor import SignalProcessor
from src.core.cycle_detector import CycleDetector
from src.models.cycle_profile import CycleProfile
from src.utils.video_utils import VideoSource
from src.utils.visualization import Visualizer
from src.utils.data_logger import DataLogger


def main():
    parser = argparse.ArgumentParser(description="Canlı döngü sayımı")
    parser.add_argument("--product", "-p", default=None,
                        help="Ürün adı (profil yüklemek için)")
    parser.add_argument("--camera", "-c", default="0",
                        help="Kamera kaynağı (0=USB, veya RTSP URL)")
    parser.add_argument("--config", default="configs/default_config.yaml",
                        help="Konfigürasyon dosyası")
    parser.add_argument("--profile-path", default=None,
                        help="Özel profil dosya yolu")
    parser.add_argument("--no-profile", action="store_true",
                        help="Profil kullanmadan çalıştır")
    parser.add_argument("--machine", default="M01",
                        help="Makine ID (loglama için)")
    parser.add_argument("--operator", default="",
                        help="Operatör adı")
    parser.add_argument("--no-display", action="store_true",
                        help="Görsel pencere gösterme")
    parser.add_argument("--record", action="store_true",
                        help="Çıktı videosunu kaydet")

    args = parser.parse_args()

    # Config yükle
    config_path = Path(PROJECT_ROOT / args.config)
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)

    # Profil yükle
    profile = None
    if not args.no_profile and args.product:
        profile_path = args.profile_path or \
            f"data/trained_models/{args.product}_profile.json"

        if Path(profile_path).exists():
            profile = CycleProfile.load(profile_path)
        else:
            print(f"UYARI: Profil bulunamadı ({profile_path}). "
                  f"Profil olmadan devam ediliyor.")
            print(f"Önce eğitim yapın: python scripts/train_reference.py "
                  f"--video <video> --product-name {args.product}")

    # Kamera kaynağı
    cam_source = int(args.camera) if args.camera.isdigit() else args.camera
    resolution = tuple(config.get("camera", {}).get("resolution", [1280, 720]))

    # Bileşenleri başlat
    video_src = VideoSource(cam_source, resolution=resolution)
    tracker = HandTracker(config)
    processor = SignalProcessor(config, fps=video_src.fps)
    detector = CycleDetector(config, profile=profile)
    detector.set_fps(video_src.fps)
    visualizer = Visualizer(config)
    logger = DataLogger(config.get("database", {}).get("path", "data/logs/production.db"))

    product_name = args.product or "unknown"
    session_id = logger.start_session(product_name, args.machine, args.operator)

    print(f"\n{'='*50}")
    print(f"CANLI SAYIM BAŞLADI")
    print(f"{'='*50}")
    print(f"Ürün: {product_name}")
    print(f"Makine: {args.machine}")
    print(f"Profil: {'Yüklü' if profile else 'Yok'}")
    print(f"Çıkmak için 'q' veya ESC tuşuna basın")
    print(f"{'='*50}\n")

    # Video kaydedici (opsiyonel)
    writer = None
    if args.record:
        from src.utils.video_utils import VideoWriter
        out_path = f"data/logs/{product_name}_{args.machine}_{int(time.time())}.mp4"
        writer = VideoWriter(out_path, video_src.fps, (video_src.width, video_src.height))

    # Ana döngü
    try:
        last_cycle_count = 0
        for frame, frame_idx, timestamp in video_src.frames():
            # 1. El takibi
            hand_data = tracker.process_frame(frame, frame_idx, timestamp)

            # 2. Sinyal işleme
            processor.add_sample(hand_data)
            signal = processor.get_signal()

            # 3. Döngü tespit
            new_cycles = detector.update(signal, timestamp)

            # 4. Yeni döngü algılandıysa logla
            if new_cycles > 0:
                state = detector.get_state()
                for event in state.events[last_cycle_count:]:
                    logger.log_cycle(
                        session_id=session_id,
                        cycle_number=event.cycle_number,
                        timestamp_sec=event.timestamp_sec,
                        confidence=event.confidence,
                        duration_sec=event.duration_sec,
                        detection_method=event.detection_method,
                    )
                    print(f"  ✓ Döngü #{event.cycle_number} | "
                          f"t={event.timestamp_sec:.1f}s | "
                          f"güven={event.confidence:.2f} | "
                          f"süre={event.duration_sec:.1f}s")
                last_cycle_count = state.total_cycles

            # 5. Görselleştirme
            if not args.no_display:
                state = detector.get_state()

                # El landmark'larını çiz
                display_frame = tracker.draw_landmarks(frame, hand_data)

                # Overlay
                display_frame = visualizer.draw_overlay(
                    display_frame, state, signal, fps=video_src.fps
                )

                if not Visualizer.show_frame("Dikiş Sayacı", display_frame):
                    break

            # 6. Video kayıt
            if writer:
                writer.write(display_frame if not args.no_display else frame)

    except KeyboardInterrupt:
        print("\n\nDurduruldu.")

    finally:
        # Temizlik
        state = detector.get_state()
        logger.end_session(
            session_id=session_id,
            total_cycles=state.total_cycles,
            avg_duration=state.avg_cycle_duration,
            cpm=state.cycles_per_minute,
        )

        video_src.release()
        tracker.release()
        if writer:
            writer.release()
        if not args.no_display:
            cv2.destroyAllWindows()

        print(f"\n{'='*50}")
        print(f"OTURUM SONUÇLARI")
        print(f"{'='*50}")
        print(f"Toplam döngü: {state.total_cycles}")
        print(f"Dakika başı: {state.cycles_per_minute:.1f}")
        print(f"Ort. döngü süresi: {state.avg_cycle_duration:.1f}s")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()
