"""
Referans Video Eğitim Modülü (Reference Trainer)
=================================================
5 dakikalık referans videoyu analiz ederek döngü profilini öğrenir.

Akış:
1. Videoyu aç ve tüm frame'leri işle (el takibi)
2. El hareket sinyalini çıkar ve işle
3. Otomatik peak detection ile döngü sınırlarını bul
4. Her döngüyü ayrı ayrı kes
5. Ortalama döngü şablonu (template) oluştur
6. İstatistikleri hesapla ve profili kaydet

Bu profil daha sonra canlı sayımda kullanılır.
"""

import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Tuple

from src.core.hand_tracker import HandTracker
from src.core.signal_processor import SignalProcessor
from src.models.cycle_profile import CycleProfile


class ReferenceTrainer:
    """
    Referans video ile döngü profili eğitimi.

    Kullanım:
        trainer = ReferenceTrainer(config)
        profile = trainer.train(
            video_path="gomlek_reference.mp4",
            expected_cycles=50,
            product_name="gomlek"
        )
        profile.save()
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Tam konfigürasyon sözlüğü
        """
        self.config = config
        self.train_cfg = config.get("training", {})

    def train(
        self,
        video_path: str,
        expected_cycles: int = 50,
        product_name: str = "unnamed",
        show_progress: bool = True,
    ) -> CycleProfile:
        """
        Referans videoyu analiz ederek döngü profili oluştur.

        Args:
            video_path: Referans video dosya yolu
            expected_cycles: Videodaki beklenen döngü sayısı
            product_name: Ürün adı (gömlek, tişört vb.)
            show_progress: İlerleme çubuğu göster

        Returns:
            Eğitilmiş CycleProfile nesnesi
        """
        video_path = str(video_path)
        print(f"\n{'='*60}")
        print(f"REFERANS VİDEO EĞİTİMİ BAŞLIYOR")
        print(f"{'='*60}")
        print(f"Video: {video_path}")
        print(f"Ürün: {product_name}")
        print(f"Beklenen döngü: {expected_cycles}")
        print(f"{'='*60}\n")

        # ---- ADIM 1: Video bilgilerini al ----
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Video açılamadı: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps

        print(f"[Adım 1/5] Video bilgileri:")
        print(f"  FPS: {fps}")
        print(f"  Toplam frame: {total_frames}")
        print(f"  Süre: {duration_sec:.1f}s ({duration_sec/60:.1f} dk)\n")

        # ---- ADIM 2: Tüm frame'leri işle (el takibi) ----
        print(f"[Adım 2/5] El takibi yapılıyor...")
        tracker = HandTracker(self.config)
        processor = SignalProcessor(self.config, fps=fps)

        iterator = range(total_frames)
        if show_progress:
            iterator = tqdm(iterator, desc="Frame işleniyor", unit="frame")

        detected_count = 0
        for frame_idx in iterator:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_idx / fps
            hand_data = tracker.process_frame(frame, frame_idx, timestamp)
            processor.add_sample(hand_data)

            if hand_data.detected:
                detected_count += 1

        cap.release()
        tracker.release()

        detection_rate = detected_count / total_frames * 100
        print(f"  El algılama oranı: {detection_rate:.1f}%")
        print(f"  İşlenen frame: {total_frames}\n")

        if detection_rate < 30:
            print("UYARI: El algılama oranı çok düşük! Kamera açısını kontrol edin.")

        # ---- ADIM 3: Sinyal işle ve peak'leri bul ----
        print(f"[Adım 3/5] Sinyal analizi ve peak detection...")
        signal = processor.get_signal()

        if len(signal) == 0:
            raise ValueError("Sinyal oluşturulamadı. Video veya el takibi sorunu.")

        # İlk denemede peak detection yap
        peaks, props = self._find_optimal_peaks(
            signal, fps, expected_cycles
        )

        found_cycles = len(peaks)
        print(f"  Bulunan döngü: {found_cycles} (beklenen: {expected_cycles})")
        print(f"  Fark: {abs(found_cycles - expected_cycles)}\n")

        # ---- ADIM 4: Döngüleri kes ve şablon oluştur ----
        print(f"[Adım 4/5] Döngü şablonu oluşturuluyor...")
        cycle_segments = self._extract_cycle_segments(signal, peaks)

        min_cycles = self.train_cfg.get("min_cycles_for_profile", 30)
        if len(cycle_segments) < min_cycles:
            print(f"UYARI: Bulunan döngü ({len(cycle_segments)}) minimum "
                  f"({min_cycles}) altında. Eşikler gevşetiliyor...")
            peaks, props = self._find_optimal_peaks(
                signal, fps, expected_cycles, relaxed=True
            )
            cycle_segments = self._extract_cycle_segments(signal, peaks)
            print(f"  Yeni döngü sayısı: {len(cycle_segments)}")

        template, all_cycles_resampled = self._build_template(cycle_segments)
        print(f"  Template uzunluğu: {len(template)} sample\n")

        # ---- ADIM 5: Profil oluştur ve istatistikleri hesapla ----
        print(f"[Adım 5/5] Profil oluşturuluyor...")
        profile = self._build_profile(
            product_name=product_name,
            video_path=video_path,
            template=template,
            all_cycles=all_cycles_resampled,
            peaks=peaks,
            signal=signal,
            fps=fps,
        )

        print(f"\n{profile.summary()}")
        return profile

    def _find_optimal_peaks(
        self,
        signal: np.ndarray,
        fps: float,
        expected_cycles: int,
        relaxed: bool = False,
    ) -> Tuple[np.ndarray, dict]:
        """
        Beklenen döngü sayısına en yakın sonucu veren peak parametrelerini bul.
        Grid search ile farklı prominence ve height değerlerini dener.
        """
        best_peaks = np.array([])
        best_props = {}
        best_diff = float("inf")

        # Parametre aralıkları
        if relaxed:
            prominences = np.arange(0.03, 0.3, 0.02)
            heights = np.arange(0.1, 0.6, 0.05)
        else:
            prominences = np.arange(0.05, 0.4, 0.02)
            heights = np.arange(0.15, 0.7, 0.05)

        for prom in prominences:
            for h in heights:
                peaks, props = SignalProcessor.find_peaks_in_signal(
                    signal, fps=fps,
                    min_cycle_sec=0.8,
                    max_cycle_sec=20.0,
                    prominence=prom,
                    height=h,
                )
                diff = abs(len(peaks) - expected_cycles)
                if diff < best_diff:
                    best_diff = diff
                    best_peaks = peaks
                    best_props = props
                    best_prominence = prom
                    best_height = h

                    if diff == 0:
                        break
            if best_diff == 0:
                break

        print(f"  Optimal parametreler: prominence={best_prominence:.3f}, "
              f"height={best_height:.3f}")
        return best_peaks, best_props

    def _extract_cycle_segments(
        self,
        signal: np.ndarray,
        peaks: np.ndarray,
    ) -> list:
        """Peak noktaları arasındaki sinyal segmentlerini çıkar."""
        segments = []

        for i in range(len(peaks) - 1):
            start = peaks[i]
            end = peaks[i + 1]
            segment = signal[start:end]
            if len(segment) > 5:
                segments.append(segment)

        return segments

    def _build_template(
        self,
        segments: list,
        target_length: Optional[int] = None,
    ) -> Tuple[np.ndarray, list]:
        """
        Tüm döngü segmentlerinden ortalama şablon oluştur.

        Tüm segmentler aynı uzunluğa resample edilir, sonra ortalaması alınır.

        Returns:
            (template, all_resampled_cycles)
        """
        if not segments:
            return np.array([]), []

        # Hedef uzunluk: medyan segment uzunluğu
        lengths = [len(s) for s in segments]
        if target_length is None:
            target_length = int(np.median(lengths))

        # Tüm segmentleri aynı uzunluğa resample et
        resampled = []
        for seg in segments:
            new_seg = np.interp(
                np.linspace(0, 1, target_length),
                np.linspace(0, 1, len(seg)),
                seg,
            )
            # Normalize (0-1)
            mn, mx = new_seg.min(), new_seg.max()
            if mx - mn > 1e-8:
                new_seg = (new_seg - mn) / (mx - mn)
            resampled.append(new_seg)

        # Aykırı döngüleri filtrele (optional)
        resampled_arr = np.array(resampled)
        mean_profile = np.mean(resampled_arr, axis=0)

        # Her döngünün template'e benzerliğini kontrol et
        filtered = []
        for seg in resampled:
            corr = np.corrcoef(mean_profile, seg)[0, 1]
            if corr > 0.3:  # Çok düşük korelasyonlu outlier'ları at
                filtered.append(seg)

        if len(filtered) < len(resampled) * 0.5:
            # Çok fazla atıldıysa filtresiz kullan
            filtered = resampled

        # Final template
        template = np.mean(np.array(filtered), axis=0)

        print(f"  Kullanılan döngü: {len(filtered)}/{len(segments)}")
        return template, [seg.tolist() for seg in filtered]

    def _build_profile(
        self,
        product_name: str,
        video_path: str,
        template: np.ndarray,
        all_cycles: list,
        peaks: np.ndarray,
        signal: np.ndarray,
        fps: float,
    ) -> CycleProfile:
        """Tüm verileri CycleProfile nesnesine topla."""

        # Döngü süreleri
        cycle_durations = []
        for i in range(len(peaks) - 1):
            dur = (peaks[i + 1] - peaks[i]) / fps
            cycle_durations.append(dur)

        durations = np.array(cycle_durations) if cycle_durations else np.array([3.0])

        # Peak istatistikleri
        peak_heights = signal[peaks] if len(peaks) > 0 else np.array([0.5])

        # Kalibre edilmiş min distance
        avg_dur = float(np.mean(durations))
        std_dur = float(np.std(durations))
        cal_min_distance = int(max(avg_dur - 2 * std_dur, 0.5) * fps)

        profile = CycleProfile(
            product_name=product_name,
            reference_video_path=video_path,
            template_signal=template.tolist(),
            template_length_frames=len(template),
            template_duration_sec=float(np.median(durations)),
            total_cycles_in_reference=len(peaks),
            avg_cycle_duration_sec=avg_dur,
            std_cycle_duration_sec=std_dur,
            min_cycle_duration_sec=float(np.min(durations)),
            max_cycle_duration_sec=float(np.max(durations)),
            avg_peak_prominence=0.15,  # Güncellenecek
            avg_peak_height=float(np.mean(peak_heights)),
            signal_fps=fps,
            calibrated_peak_prominence=max(0.05, float(np.std(signal) * 0.5)),
            calibrated_peak_height=max(0.1, float(np.mean(peak_heights) * 0.6)),
            calibrated_min_distance_frames=cal_min_distance,
            calibrated_similarity_threshold=0.6,
            all_cycle_signals=all_cycles,
        )

        return profile


def train_from_video(
    video_path: str,
    product_name: str,
    expected_cycles: int = 50,
    config: Optional[dict] = None,
    save_path: Optional[str] = None,
) -> CycleProfile:
    """
    Kolaylık fonksiyonu: Referans video ile eğitim yap ve profili kaydet.

    Args:
        video_path: Referans video yolu
        product_name: Ürün adı
        expected_cycles: Beklenen döngü sayısı
        config: Konfigürasyon (None ise varsayılan)
        save_path: Profil kayıt yolu (None ise otomatik)

    Returns:
        Eğitilmiş profil
    """
    if config is None:
        import yaml
        config_path = Path(__file__).parent.parent.parent / "configs" / "default_config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
        else:
            config = {}

    trainer = ReferenceTrainer(config)
    profile = trainer.train(
        video_path=video_path,
        expected_cycles=expected_cycles,
        product_name=product_name,
    )

    saved_path = profile.save(save_path)
    print(f"\nProfil kaydedildi: {saved_path}")
    return profile
