#!/usr/bin/env python3
"""
Kayıtlı Video Analiz Scripti
==============================
Daha önce kaydedilmiş bir videoyu analiz ederek döngü sayar.

Kullanım:
    python scripts/run_video_analysis.py \
        --video test_video.mp4 \
        --product gomlek \
        --output results.json
"""

import sys
import json
import argparse
import yaml
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.hand_tracker import HandTracker
from src.core.signal_processor import SignalProcessor
from src.core.cycle_detector import CycleDetector
from src.models.cycle_profile import CycleProfile
from src.utils.video_utils import VideoSource


def main():
    parser = argparse.ArgumentParser(description="Kayıtlı video analizi")
    parser.add_argument("--video", "-v", required=True, help="Video dosya yolu")
    parser.add_argument("--product", "-p", default=None, help="Ürün adı (profil için)")
    parser.add_argument("--profile-path", default=None, help="Özel profil yolu")
    parser.add_argument("--config", default="configs/default_config.yaml")
    parser.add_argument("--output", "-o", default=None, help="Sonuç JSON dosyası")
    parser.add_argument("--save-signal", action="store_true",
                        help="İşlenmiş sinyali de kaydet")

    args = parser.parse_args()

    # Config
    config_path = Path(PROJECT_ROOT / args.config)
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)

    # Profil
    profile = None
    if args.product:
        ppath = args.profile_path or f"data/trained_models/{args.product}_profile.json"
        if Path(ppath).exists():
            profile = CycleProfile.load(ppath)

    # Video aç
    video_src = VideoSource(args.video)
    tracker = HandTracker(config)
    processor = SignalProcessor(config, fps=video_src.fps)
    detector = CycleDetector(config, profile=profile)
    detector.set_fps(video_src.fps)

    print(f"\nVideo analiz ediliyor: {args.video}")
    print(f"Profil: {'Yüklü - ' + profile.product_name if profile else 'Yok'}\n")

    # Tüm frame'leri işle
    for frame, frame_idx, timestamp in tqdm(
        video_src.frames(),
        total=video_src.total_frames,
        desc="Analiz",
        unit="frame",
    ):
        hand_data = tracker.process_frame(frame, frame_idx, timestamp)
        processor.add_sample(hand_data)
        signal = processor.get_signal()
        detector.update(signal, timestamp)

    video_src.release()
    tracker.release()

    # Sonuçlar
    state = detector.get_state()
    duration = video_src.total_frames / video_src.fps

    results = {
        "video": args.video,
        "product": args.product or "unknown",
        "duration_sec": round(duration, 1),
        "total_cycles": state.total_cycles,
        "cycles_per_minute": round(state.cycles_per_minute, 2),
        "avg_cycle_duration_sec": round(state.avg_cycle_duration, 2),
        "events": [
            {
                "cycle": e.cycle_number,
                "time_sec": round(e.timestamp_sec, 2),
                "confidence": round(e.confidence, 3),
                "duration_sec": round(e.duration_sec, 2),
                "method": e.detection_method,
            }
            for e in state.events
        ],
    }

    if args.save_signal:
        signal = processor.get_signal()
        results["signal"] = [round(float(x), 6) for x in signal]

    # Sonuçları yazdır
    print(f"\n{'='*50}")
    print(f"ANALİZ SONUÇLARI")
    print(f"{'='*50}")
    print(f"Video süresi: {duration:.1f}s ({duration/60:.1f} dk)")
    print(f"Toplam döngü: {state.total_cycles}")
    print(f"Dakika başı hız: {state.cycles_per_minute:.1f}")
    print(f"Ort. döngü süresi: {state.avg_cycle_duration:.1f}s")
    print(f"{'='*50}")

    # JSON kaydet
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSonuçlar kaydedildi: {output_path}")
    else:
        default_out = f"data/logs/{Path(args.video).stem}_results.json"
        Path(default_out).parent.mkdir(parents=True, exist_ok=True)
        with open(default_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSonuçlar kaydedildi: {default_out}")


if __name__ == "__main__":
    main()
