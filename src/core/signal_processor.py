"""
Sinyal İşleme Modülü (Signal Processor)
========================================
Ham el takip verilerini (x, y, z pozisyonları) temiz, filtrelenmiş sinyallere
dönüştürür. Bu sinyaller döngü tespiti için kullanılır.

İşlem Zinciri:
  Ham Landmark → Ham Sinyal → Yumuşatma → Bandpass Filtre → Normalizasyon → Temiz Sinyal
"""

import numpy as np
from scipy import signal as scipy_signal
from scipy.signal import savgol_filter, find_peaks, butter, filtfilt
from scipy.ndimage import gaussian_filter1d
from typing import Tuple, Optional
from collections import deque


class SignalProcessor:
    """
    El hareket verilerini işlenmiş sinyallere dönüştürür.

    Kullanım:
        processor = SignalProcessor(config, fps=30)
        processor.add_sample(hand_data)  # Her frame'de çağır
        clean_signal = processor.get_signal()
    """

    def __init__(self, config: dict, fps: float = 30.0):
        """
        Args:
            config: Konfigürasyon sözlüğü (signal bölümü)
            fps: Video FPS değeri
        """
        sig_cfg = config.get("signal", {})

        self.fps = fps
        self.signal_type = sig_cfg.get("signal_type", "combined")

        # Yumuşatma
        self.smoothing_window = sig_cfg.get("smoothing_window", 15)
        self.smoothing_method = sig_cfg.get("smoothing_method", "savgol")
        self.savgol_polyorder = sig_cfg.get("savgol_polyorder", 3)

        # Bandpass filtre
        self.bandpass_enabled = sig_cfg.get("bandpass_enabled", True)
        self.bandpass_low = sig_cfg.get("bandpass_low_hz", 0.1)
        self.bandpass_high = sig_cfg.get("bandpass_high_hz", 3.0)

        # Normalizasyon
        self.normalize = sig_cfg.get("normalize", True)

        # Veri tamponları - canlı işleme için
        self._buffer_size = int(fps * 300)  # Max 5 dakika tampon
        self._raw_y = deque(maxlen=self._buffer_size)
        self._raw_x = deque(maxlen=self._buffer_size)
        self._raw_velocity = deque(maxlen=self._buffer_size)
        self._raw_openness = deque(maxlen=self._buffer_size)
        self._timestamps = deque(maxlen=self._buffer_size)
        self._detected_flags = deque(maxlen=self._buffer_size)

        # Butterworth filtre katsayıları (önceden hesapla)
        self._butter_b = None
        self._butter_a = None
        if self.bandpass_enabled:
            self._init_bandpass_filter()

        print(f"[SignalProcessor] Başlatıldı | type={self.signal_type} | "
              f"smoothing={self.smoothing_method}({self.smoothing_window})")

    def _init_bandpass_filter(self):
        """Butterworth bandpass filtre katsayılarını hesapla."""
        nyquist = self.fps / 2.0
        low = max(self.bandpass_low / nyquist, 0.001)
        high = min(self.bandpass_high / nyquist, 0.999)

        if low < high:
            self._butter_b, self._butter_a = butter(
                N=4, Wn=[low, high], btype="bandpass"
            )
        else:
            print("[SignalProcessor] UYARI: Bandpass frekansları geçersiz, devre dışı.")
            self.bandpass_enabled = False

    def add_sample(self, hand_data) -> None:
        """
        Yeni bir frame'in el verisini tampona ekle.

        Args:
            hand_data: HandData nesnesi
        """
        self._timestamps.append(hand_data.timestamp_sec)
        self._detected_flags.append(hand_data.detected)

        if hand_data.detected:
            self._raw_y.append(hand_data.wrist_y)
            self._raw_x.append(hand_data.wrist_x)
            self._raw_velocity.append(hand_data.hand_velocity)
            self._raw_openness.append(hand_data.hand_openness)
        else:
            # El algılanmadıysa son değeri tekrarla (interpolasyon)
            self._raw_y.append(self._raw_y[-1] if self._raw_y else 0.5)
            self._raw_x.append(self._raw_x[-1] if self._raw_x else 0.5)
            self._raw_velocity.append(0.0)
            self._raw_openness.append(
                self._raw_openness[-1] if self._raw_openness else 0.0
            )

    def get_signal(self, signal_type: Optional[str] = None) -> np.ndarray:
        """
        İşlenmiş sinyal dizisini döndür.

        Args:
            signal_type: Sinyal türü (None ise config'deki varsayılan)

        Returns:
            İşlenmiş sinyal (1D numpy array)
        """
        stype = signal_type or self.signal_type

        if len(self._raw_y) < self.smoothing_window + 5:
            return np.array([])

        # 1. Ham sinyal seç
        if stype == "y_position":
            raw = np.array(self._raw_y)
        elif stype == "velocity":
            raw = np.array(self._raw_velocity)
        elif stype == "acceleration":
            vel = np.array(self._raw_velocity)
            raw = np.gradient(vel)
        elif stype == "openness":
            raw = np.array(self._raw_openness)
        elif stype == "combined":
            raw = self._compute_combined_signal()
        else:
            raw = np.array(self._raw_y)

        # 2. NaN ve Inf kontrolü
        raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)

        # 3. Yumuşatma
        smoothed = self._apply_smoothing(raw)

        # 4. Bandpass filtre
        if self.bandpass_enabled and len(smoothed) > 30:
            filtered = self._apply_bandpass(smoothed)
        else:
            filtered = smoothed

        # 5. Normalizasyon
        if self.normalize:
            filtered = self._apply_normalization(filtered)

        return filtered

    def get_raw_signal(self) -> np.ndarray:
        """Ham (işlenmemiş) Y pozisyon sinyalini döndür."""
        return np.array(self._raw_y)

    def get_timestamps(self) -> np.ndarray:
        """Zaman damgalarını döndür."""
        return np.array(self._timestamps)

    def get_sample_count(self) -> int:
        """Tampondaki toplam örnek sayısı."""
        return len(self._raw_y)

    def reset(self):
        """Tamponları temizle."""
        self._raw_y.clear()
        self._raw_x.clear()
        self._raw_velocity.clear()
        self._raw_openness.clear()
        self._timestamps.clear()
        self._detected_flags.clear()

    def process_full_signal(self, y_positions: np.ndarray) -> np.ndarray:
        """
        Toplu (batch) sinyal işleme - referans video analizi için.
        Canlı tampon kullanmadan doğrudan array işler.

        Args:
            y_positions: Ham Y pozisyon dizisi

        Returns:
            İşlenmiş sinyal
        """
        raw = np.nan_to_num(y_positions, nan=0.0)
        smoothed = self._apply_smoothing(raw)

        if self.bandpass_enabled and len(smoothed) > 30:
            filtered = self._apply_bandpass(smoothed)
        else:
            filtered = smoothed

        if self.normalize:
            filtered = self._apply_normalization(filtered)

        return filtered

    def _compute_combined_signal(self) -> np.ndarray:
        """
        Birleşik sinyal: Y pozisyonu + velocity + el açıklık.
        Her bileşen normalize edilip ağırlıklı toplanır.
        """
        y = np.array(self._raw_y)
        vel = np.array(self._raw_velocity)
        openness = np.array(self._raw_openness)

        # Her bileşeni 0-1 arası normalize et
        def norm(arr):
            mn, mx = arr.min(), arr.max()
            if mx - mn < 1e-8:
                return np.zeros_like(arr)
            return (arr - mn) / (mx - mn)

        y_n = norm(y)
        vel_n = norm(vel)
        open_n = norm(openness)

        # Ağırlıklı birleşim
        # Y pozisyonu en baskın, velocity döngü geçişlerini vurgular
        combined = 0.5 * y_n + 0.3 * vel_n + 0.2 * open_n
        return combined

    def _apply_smoothing(self, data: np.ndarray) -> np.ndarray:
        """Sinyal yumuşatma uygula."""
        if len(data) < self.smoothing_window:
            return data

        window = self.smoothing_window
        if window % 2 == 0:
            window += 1  # Savgol tek sayı istiyor

        if self.smoothing_method == "savgol":
            polyorder = min(self.savgol_polyorder, window - 1)
            return savgol_filter(data, window, polyorder)

        elif self.smoothing_method == "gaussian":
            sigma = window / 4.0
            return gaussian_filter1d(data, sigma)

        elif self.smoothing_method == "moving_avg":
            kernel = np.ones(window) / window
            return np.convolve(data, kernel, mode="same")

        return data

    def _apply_bandpass(self, data: np.ndarray) -> np.ndarray:
        """Butterworth bandpass filtre uygula."""
        if self._butter_b is None or len(data) < 30:
            return data
        try:
            # padlen kontrolü
            padlen = 3 * max(len(self._butter_a), len(self._butter_b))
            if len(data) <= padlen:
                return data
            return filtfilt(self._butter_b, self._butter_a, data)
        except Exception:
            return data

    def _apply_normalization(self, data: np.ndarray) -> np.ndarray:
        """Sinyali 0-1 arasına normalize et."""
        mn, mx = data.min(), data.max()
        if mx - mn < 1e-8:
            return np.zeros_like(data)
        return (data - mn) / (mx - mn)

    @staticmethod
    def find_peaks_in_signal(
        data: np.ndarray,
        fps: float,
        min_cycle_sec: float = 1.5,
        max_cycle_sec: float = 15.0,
        prominence: float = 0.15,
        height: float = 0.3,
    ) -> Tuple[np.ndarray, dict]:
        """
        Sinyaldeki peak noktalarını bul.

        Args:
            data: İşlenmiş sinyal
            fps: Video FPS
            min_cycle_sec: Minimum döngü süresi
            max_cycle_sec: Maksimum döngü süresi
            prominence: Peak belirginliği eşiği
            height: Minimum peak yüksekliği

        Returns:
            (peak_indices, peak_properties)
        """
        min_distance = int(min_cycle_sec * fps)
        max_distance = int(max_cycle_sec * fps)

        peaks, properties = find_peaks(
            data,
            distance=min_distance,
            prominence=prominence,
            height=height,
        )

        # Çok uzak peak'leri filtrele (aralarında max_cycle_sec'den fazla boşluk)
        if len(peaks) > 1:
            valid = [peaks[0]]
            for i in range(1, len(peaks)):
                gap = peaks[i] - peaks[i - 1]
                if gap <= max_distance:
                    valid.append(peaks[i])
                # Çok uzak olanları da ekle ama uyarı logla
                else:
                    valid.append(peaks[i])
            peaks = np.array(valid)

        return peaks, properties
