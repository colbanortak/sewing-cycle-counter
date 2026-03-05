"""
Signal Processor ve Cycle Detector Testleri
=============================================
Sentetik sinyal ile döngü tespit doğruluğunu test eder.
Kamera/video olmadan çalışır.

Kullanım:
    pytest tests/ -v
    python tests/test_signal_processor.py
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.signal_processor import SignalProcessor
from src.core.cycle_detector import CycleDetector


def generate_synthetic_signal(
    num_cycles: int = 20,
    cycle_duration_sec: float = 3.0,
    fps: float = 30.0,
    noise_level: float = 0.05,
) -> np.ndarray:
    """
    Sentetik periyodik sinyal üret (dikim döngüsü simülasyonu).
    Her döngü: yukarı hareket (kumaş al) → aşağı hareket (makineye koy) → dikiş
    """
    samples_per_cycle = int(cycle_duration_sec * fps)
    total_samples = num_cycles * samples_per_cycle

    t = np.linspace(0, num_cycles * 2 * np.pi, total_samples)

    # Temel periyodik sinyal (yarım sinüs benzeri)
    signal = 0.5 + 0.4 * np.sin(t)

    # Rastgele gürültü ekle
    noise = np.random.normal(0, noise_level, len(signal))
    signal += noise

    # 0-1 arasına normalize
    signal = (signal - signal.min()) / (signal.max() - signal.min())

    return signal


def test_peak_detection_accuracy():
    """Peak detection'ın beklenen döngü sayısına yakın sonuç vermesini test et."""
    expected_cycles = 20
    fps = 30.0
    cycle_duration = 3.0

    signal = generate_synthetic_signal(
        num_cycles=expected_cycles,
        cycle_duration_sec=cycle_duration,
        fps=fps,
        noise_level=0.03,
    )

    peaks, _ = SignalProcessor.find_peaks_in_signal(
        signal,
        fps=fps,
        min_cycle_sec=cycle_duration * 0.5,
        max_cycle_sec=cycle_duration * 2.0,
        prominence=0.1,
        height=0.3,
    )

    found = len(peaks)
    tolerance = 3  # ±3 döngü tolerans

    print(f"\n[TEST] Peak Detection Doğruluğu")
    print(f"  Beklenen: {expected_cycles}, Bulunan: {found}")
    print(f"  Tolerans: ±{tolerance}")

    assert abs(found - expected_cycles) <= tolerance, \
        f"Peak sayısı beklentiden çok uzak: {found} vs {expected_cycles}"
    print(f"  ✓ GEÇTI\n")


def test_cycle_detector_counting():
    """CycleDetector'ın süreç boyunca doğru saymasını test et."""
    fps = 30.0
    cycle_duration = 3.0
    num_cycles = 15

    config = {
        "detection": {
            "min_cycle_duration_sec": cycle_duration * 0.5,
            "max_cycle_duration_sec": cycle_duration * 2.0,
            "peak_prominence": 0.1,
            "peak_height": 0.3,
            "use_template_matching": False,
            "adaptive_threshold": False,
        }
    }

    detector = CycleDetector(config, profile=None)
    detector.set_fps(fps)

    signal = generate_synthetic_signal(
        num_cycles=num_cycles,
        cycle_duration_sec=cycle_duration,
        fps=fps,
        noise_level=0.03,
    )

    # Sinyali kademeli olarak besle (canlı simülasyonu)
    chunk_size = int(fps * 1)  # Her saniye bir güncelleme
    for i in range(0, len(signal), chunk_size):
        partial_signal = signal[: i + chunk_size]
        current_time = (i + chunk_size) / fps
        detector.update(partial_signal, current_time)

    state = detector.get_state()
    tolerance = 4

    print(f"[TEST] Cycle Detector Sayım")
    print(f"  Beklenen: ~{num_cycles}, Bulunan: {state.total_cycles}")
    print(f"  Tolerans: ±{tolerance}")

    assert abs(state.total_cycles - num_cycles) <= tolerance, \
        f"Sayım beklentiden çok uzak: {state.total_cycles} vs {num_cycles}"
    print(f"  ✓ GEÇTI\n")


def test_signal_processor_pipeline():
    """SignalProcessor tam pipeline testleri."""
    fps = 30.0
    config = {
        "signal": {
            "signal_type": "y_position",
            "smoothing_window": 11,
            "smoothing_method": "savgol",
            "savgol_polyorder": 3,
            "bandpass_enabled": True,
            "bandpass_low_hz": 0.1,
            "bandpass_high_hz": 5.0,
            "normalize": True,
        }
    }

    processor = SignalProcessor(config, fps=fps)

    # Sentetik veri besle
    raw = generate_synthetic_signal(num_cycles=10, fps=fps)
    processed = processor.process_full_signal(raw)

    print(f"[TEST] Signal Processor Pipeline")
    print(f"  Giriş uzunluğu: {len(raw)}")
    print(f"  Çıkış uzunluğu: {len(processed)}")
    print(f"  Çıkış min/max: {processed.min():.3f} / {processed.max():.3f}")

    assert len(processed) == len(raw), "Çıkış uzunluğu eşleşmiyor"
    assert processed.min() >= -0.01, "Normalizasyon hatası (min)"
    assert processed.max() <= 1.01, "Normalizasyon hatası (max)"
    print(f"  ✓ GEÇTI\n")


if __name__ == "__main__":
    test_signal_processor_pipeline()
    test_peak_detection_accuracy()
    test_cycle_detector_counting()
    print("═" * 50)
    print("TÜM TESTLER BAŞARILI ✓")
    print("═" * 50)
