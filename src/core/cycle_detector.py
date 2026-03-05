"""
Döngü Tespit Motoru (Cycle Detector)
=====================================
Referans profilden öğrenilen döngü şablonunu kullanarak canlı sinyalde
yeni döngüleri tespit eder ve sayar.

İki yöntem kullanır:
1. Peak Detection: Sinyaldeki tepe noktalarını bularak döngü sayar
2. Template Matching: Referans şablonla korelasyon hesaplayarak doğrular

İkisi birlikte kullanıldığında güvenilirlik artar.
"""

import numpy as np
from scipy.signal import correlate
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from src.models.cycle_profile import CycleProfile
from src.core.signal_processor import SignalProcessor


@dataclass
class CycleEvent:
    """Tespit edilen tek bir döngü olayı."""
    cycle_number: int
    timestamp_sec: float
    peak_frame_idx: int
    confidence: float           # 0-1 arası güven skoru
    duration_sec: float         # Bu döngünün süresi
    detection_method: str       # "peak" | "template" | "both"


@dataclass
class CounterState:
    """Sayaç durumu."""
    total_cycles: int = 0
    cycles_per_minute: float = 0.0
    last_cycle_time: float = 0.0
    avg_cycle_duration: float = 0.0
    session_start: str = ""
    events: List[CycleEvent] = field(default_factory=list)
    is_active: bool = False     # Dikişçi aktif mi (son 30 sn içinde döngü var mı)


class CycleDetector:
    """
    Canlı döngü tespit ve sayım motoru.

    Kullanım:
        detector = CycleDetector(config, profile)
        # Her frame'de:
        detector.update(processed_signal, current_time)
        state = detector.get_state()
        print(f"Toplam: {state.total_cycles}")
    """

    def __init__(self, config: dict, profile: Optional[CycleProfile] = None):
        """
        Args:
            config: Konfigürasyon (detection bölümü)
            profile: Öğrenilmiş döngü profili (None ise sadece peak detection)
        """
        det_cfg = config.get("detection", {})
        self.profile = profile

        # Peak detection parametreleri
        self.min_cycle_sec = det_cfg.get("min_cycle_duration_sec", 1.5)
        self.max_cycle_sec = det_cfg.get("max_cycle_duration_sec", 15.0)
        self.peak_prominence = det_cfg.get("peak_prominence", 0.15)
        self.peak_height = det_cfg.get("peak_height", 0.3)

        # Template matching
        self.use_template = det_cfg.get("use_template_matching", True)
        self.similarity_threshold = det_cfg.get("similarity_threshold", 0.6)
        self.match_method = det_cfg.get("template_match_method", "correlation")

        # Adaptif eşik
        self.adaptive = det_cfg.get("adaptive_threshold", True)
        self.warmup_cycles = det_cfg.get("warmup_cycles", 5)

        # Profil varsa kalibre edilmiş değerleri kullan
        if profile:
            self.peak_prominence = profile.calibrated_peak_prominence
            self.peak_height = profile.calibrated_peak_height
            self.min_cycle_sec = max(
                profile.min_cycle_duration_sec * 0.7, 0.5
            )
            self.max_cycle_sec = profile.max_cycle_duration_sec * 1.5
            self._template = profile.get_template_array()
            self._expected_cycle_frames = profile.get_expected_cycle_frames()
        else:
            self._template = None
            self._expected_cycle_frames = 90  # 3 saniye varsayılan

        # İç durum
        self._state = CounterState(session_start=datetime.now().isoformat())
        self._last_check_idx = 0                # Son kontrol edilen sinyal indeksi
        self._recent_peak_frames: List[int] = []  # Son bulunan peak frame'leri
        self._cycle_durations: List[float] = []   # Adaptif kalibrasyon için
        self._fps = 30.0

        print(f"[CycleDetector] Başlatıldı | profile={'var' if profile else 'yok'} | "
              f"prominence={self.peak_prominence:.3f} | height={self.peak_height:.3f}")

    def set_fps(self, fps: float):
        """FPS değerini güncelle."""
        self._fps = fps

    def update(self, signal: np.ndarray, current_time_sec: float) -> int:
        """
        Sinyali kontrol et ve yeni döngü varsa sayacı güncelle.

        Bu metot her frame'de çağrılabilir. İç mantık gereksiz yeniden hesaplamayı önler.

        Args:
            signal: Güncel işlenmiş sinyal (tüm tampon)
            current_time_sec: Güncel zaman (saniye)

        Returns:
            Bu güncellemede tespit edilen yeni döngü sayısı
        """
        if len(signal) < int(self.min_cycle_sec * self._fps) + 10:
            return 0

        # Minimum kontrol aralığı: yarım döngü süresi
        min_check_gap = max(int(self._expected_cycle_frames * 0.5), 10)
        if len(signal) - self._last_check_idx < min_check_gap:
            return 0

        # Peak detection uygula
        peaks, props = SignalProcessor.find_peaks_in_signal(
            signal,
            fps=self._fps,
            min_cycle_sec=self.min_cycle_sec,
            max_cycle_sec=self.max_cycle_sec,
            prominence=self.peak_prominence,
            height=self.peak_height,
        )

        # Yeni peak'leri filtrele (daha önce tespit edilmemiş olanlar)
        new_count = 0
        for peak_idx in peaks:
            if peak_idx <= self._last_check_idx:
                continue

            # Daha önce bu bölgede peak bulunmuş mu?
            if self._is_duplicate_peak(peak_idx):
                continue

            # Template matching ile doğrula (profil varsa)
            confidence = 1.0
            method = "peak"

            if self.use_template and self._template is not None:
                match_score = self._template_match_at(signal, peak_idx)
                confidence = match_score

                if match_score >= self.similarity_threshold:
                    method = "both"
                elif match_score < self.similarity_threshold * 0.5:
                    # Çok düşük benzerlik → atla
                    continue
                else:
                    method = "peak"
                    confidence = 0.5 + match_score * 0.5

            # Yeni döngü onayla
            self._state.total_cycles += 1
            new_count += 1

            # Döngü süresi hesapla
            duration = 0.0
            if self._recent_peak_frames:
                duration = (peak_idx - self._recent_peak_frames[-1]) / self._fps

            self._recent_peak_frames.append(peak_idx)
            if duration > 0:
                self._cycle_durations.append(duration)

            # Olay kaydet
            event = CycleEvent(
                cycle_number=self._state.total_cycles,
                timestamp_sec=current_time_sec,
                peak_frame_idx=int(peak_idx),
                confidence=confidence,
                duration_sec=duration,
                detection_method=method,
            )
            self._state.events.append(event)

        # Durum güncelle
        self._last_check_idx = len(signal) - int(self.min_cycle_sec * self._fps)

        if self._state.events:
            self._state.last_cycle_time = self._state.events[-1].timestamp_sec
            self._state.is_active = (
                current_time_sec - self._state.last_cycle_time < 30.0
            )

        # Dakika başı döngü hesapla
        if current_time_sec > 0:
            self._state.cycles_per_minute = (
                self._state.total_cycles / current_time_sec * 60.0
            )

        # Ortalama döngü süresi
        if self._cycle_durations:
            self._state.avg_cycle_duration = float(np.mean(self._cycle_durations))

        # Adaptif kalibrasyon
        if self.adaptive and len(self._cycle_durations) >= self.warmup_cycles:
            self._adapt_thresholds()

        return new_count

    def get_state(self) -> CounterState:
        """Güncel sayaç durumunu döndür."""
        return self._state

    def reset(self):
        """Sayacı sıfırla."""
        self._state = CounterState(session_start=datetime.now().isoformat())
        self._last_check_idx = 0
        self._recent_peak_frames.clear()
        self._cycle_durations.clear()

    def _is_duplicate_peak(self, peak_idx: int) -> bool:
        """Bu peak daha önce tespit edilmiş bir peak'e çok yakın mı?"""
        min_gap = int(self.min_cycle_sec * self._fps * 0.8)
        for prev_peak in self._recent_peak_frames[-10:]:
            if abs(peak_idx - prev_peak) < min_gap:
                return True
        return False

    def _template_match_at(self, signal: np.ndarray, peak_idx: int) -> float:
        """
        Sinyalin peak_idx etrafındaki bölgesini template ile karşılaştır.

        Returns:
            Benzerlik skoru (0-1)
        """
        if self._template is None:
            return 1.0

        template_len = len(self._template)
        half_len = template_len // 2

        # Peak etrafındaki pencereyi al
        start = max(0, peak_idx - half_len)
        end = min(len(signal), peak_idx + half_len)
        segment = signal[start:end]

        if len(segment) < template_len // 2:
            return 0.0

        # Segment'i template uzunluğuna yeniden örnekle
        if len(segment) != template_len:
            segment = np.interp(
                np.linspace(0, 1, template_len),
                np.linspace(0, 1, len(segment)),
                segment,
            )

        if self.match_method == "correlation":
            # Normalized cross-correlation
            corr = np.corrcoef(self._template, segment)[0, 1]
            return max(0.0, float(corr))
        else:
            # Basit Euclidean distance bazlı skor
            dist = np.linalg.norm(self._template - segment)
            max_dist = np.sqrt(template_len)  # Teorik max
            return max(0.0, 1.0 - dist / max_dist)

    def _adapt_thresholds(self):
        """
        İlk N döngüden sonra eşik değerlerini otomatik ayarla.
        Sadece bir kez çalışır (warmup sonrası).
        """
        if not hasattr(self, "_adapted"):
            durations = np.array(self._cycle_durations[-self.warmup_cycles:])
            mean_dur = np.mean(durations)
            std_dur = np.std(durations)

            # Minimum döngü süresini ayarla
            new_min = max(mean_dur - 2 * std_dur, 0.5)
            new_max = mean_dur + 3 * std_dur

            self.min_cycle_sec = float(new_min)
            self.max_cycle_sec = float(new_max)
            self._expected_cycle_frames = int(mean_dur * self._fps)

            self._adapted = True
            print(f"[CycleDetector] Adaptif kalibrasyon: "
                  f"min={self.min_cycle_sec:.1f}s, max={self.max_cycle_sec:.1f}s, "
                  f"beklenen={mean_dur:.1f}s")
