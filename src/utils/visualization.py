"""
Görselleştirme Modülü
=====================
Video üzerine overlay çizimi ve sinyal grafikleri.
"""

import cv2
import numpy as np
from typing import Optional
from src.core.cycle_detector import CounterState


class Visualizer:
    """Canlı video önizleme ve overlay çizici."""

    def __init__(self, config: dict):
        vis_cfg = config.get("visualization", {})
        self.show_landmarks = vis_cfg.get("show_landmarks", True)
        self.overlay_count = vis_cfg.get("overlay_count", True)
        self.show_signal = vis_cfg.get("show_signal_plot", True)
        self.signal_window_sec = vis_cfg.get("plot_window_sec", 30)

    def draw_overlay(
        self,
        frame: np.ndarray,
        state: CounterState,
        signal: Optional[np.ndarray] = None,
        peaks: Optional[np.ndarray] = None,
        fps: float = 30.0,
    ) -> np.ndarray:
        """
        Frame üzerine sayaç bilgisi ve mini sinyal grafiği çiz.

        Args:
            frame: BGR frame
            state: Güncel sayaç durumu
            signal: İşlenmiş sinyal (mini grafik için)
            peaks: Tespit edilen peak indeksleri
            fps: Video FPS

        Returns:
            Overlay çizilmiş frame
        """
        output = frame.copy()
        h, w = output.shape[:2]

        # --- Üst bilgi paneli ---
        # Yarı saydam siyah arka plan
        overlay_panel = output.copy()
        cv2.rectangle(overlay_panel, (0, 0), (w, 90), (0, 0, 0), -1)
        cv2.addWeighted(overlay_panel, 0.6, output, 0.4, 0, output)

        # Sayaç (büyük)
        count_text = f"{state.total_cycles}"
        cv2.putText(output, count_text, (20, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 0), 4)

        # Birim
        cv2.putText(output, "adet", (20 + len(count_text) * 45, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        # Dakika başı hız
        cpm_text = f"{state.cycles_per_minute:.1f} adet/dk"
        cv2.putText(output, cpm_text, (w - 250, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Ortalama süre
        if state.avg_cycle_duration > 0:
            dur_text = f"Ort: {state.avg_cycle_duration:.1f}s/adet"
            cv2.putText(output, dur_text, (w - 250, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # Aktiflik durumu
        status_color = (0, 255, 0) if state.is_active else (0, 0, 255)
        status_text = "AKTIF" if state.is_active else "BEKLEMEDE"
        cv2.circle(output, (w - 280, 50), 8, status_color, -1)
        cv2.putText(output, status_text, (w - 265, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)

        # --- Mini sinyal grafiği (alt kısım) ---
        if self.show_signal and signal is not None and len(signal) > 30:
            output = self._draw_signal_plot(output, signal, peaks, fps)

        return output

    def _draw_signal_plot(
        self,
        frame: np.ndarray,
        signal: np.ndarray,
        peaks: Optional[np.ndarray],
        fps: float,
    ) -> np.ndarray:
        """Frame altına mini sinyal grafiği çiz."""
        h, w = frame.shape[:2]

        # Grafik alanı
        plot_h = 100
        plot_y = h - plot_h - 10
        plot_x = 10
        plot_w = w - 20

        # Yarı saydam arka plan
        overlay = frame.copy()
        cv2.rectangle(overlay, (plot_x, plot_y), (plot_x + plot_w, plot_y + plot_h),
                       (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        # Son N saniye sinyali göster
        window_frames = int(self.signal_window_sec * fps)
        sig = signal[-window_frames:] if len(signal) > window_frames else signal

        if len(sig) < 2:
            return frame

        # Sinyali pixel koordinatlarına dönüştür
        x_coords = np.linspace(plot_x, plot_x + plot_w, len(sig)).astype(int)
        y_min, y_max = sig.min(), sig.max()
        if y_max - y_min < 1e-8:
            y_max = y_min + 1
        y_coords = (
            plot_y + plot_h - ((sig - y_min) / (y_max - y_min) * (plot_h - 10) + 5)
        ).astype(int)

        # Sinyal çizgisi
        points = np.column_stack([x_coords, y_coords]).reshape(-1, 1, 2)
        cv2.polylines(frame, [points], False, (0, 200, 255), 2)

        # Peak noktaları
        if peaks is not None:
            offset = max(0, len(signal) - window_frames)
            for p in peaks:
                local_p = p - offset
                if 0 <= local_p < len(sig):
                    px = x_coords[local_p]
                    py = y_coords[local_p]
                    cv2.circle(frame, (px, py), 5, (0, 255, 0), -1)

        return frame

    @staticmethod
    def show_frame(window_name: str, frame: np.ndarray) -> bool:
        """
        Frame'i göster. ESC veya 'q' tuşuna basılırsa False döndür.
        """
        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        return key != 27 and key != ord("q")
