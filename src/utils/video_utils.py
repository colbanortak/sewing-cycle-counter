"""
Video Yardımcı Modülü
=====================
Kamera ve video dosyası okuma/yazma işlemleri.
"""

import cv2
import time
import numpy as np
from typing import Optional, Generator, Tuple


class VideoSource:
    """
    Kamera veya video dosyasından frame okuma.

    Kullanım:
        # Kamera
        source = VideoSource(0, resolution=(1280, 720))

        # Video dosyası
        source = VideoSource("video.mp4")

        for frame, frame_idx, timestamp in source.frames():
            process(frame)

        source.release()
    """

    def __init__(
        self,
        source=0,
        resolution: Optional[Tuple[int, int]] = None,
        target_fps: Optional[float] = None,
    ):
        self.source = source
        self.cap = cv2.VideoCapture(source)

        if not self.cap.isOpened():
            raise RuntimeError(f"Video kaynağı açılamadı: {source}")

        # Çözünürlük ayarla
        if resolution and isinstance(source, int):
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.target_fps = target_fps or self.fps
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.is_camera = isinstance(source, int)
        self._frame_idx = 0

        print(f"[VideoSource] Açıldı: {source}")
        print(f"  Çözünürlük: {self.width}x{self.height} @ {self.fps:.1f} FPS")
        if not self.is_camera:
            duration = self.total_frames / self.fps
            print(f"  Süre: {duration:.1f}s | Frame: {self.total_frames}")

    def frames(self) -> Generator[Tuple[np.ndarray, int, float], None, None]:
        """
        Frame generator. Her iterasyonda (frame, frame_idx, timestamp) döndürür.
        """
        self._frame_idx = 0
        start_time = time.time()

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            if self.is_camera:
                timestamp = time.time() - start_time
            else:
                timestamp = self._frame_idx / self.fps

            yield frame, self._frame_idx, timestamp
            self._frame_idx += 1

    def read_frame(self) -> Optional[Tuple[np.ndarray, int, float]]:
        """Tek bir frame oku. None döndürürse video bitti."""
        ret, frame = self.cap.read()
        if not ret:
            return None

        timestamp = self._frame_idx / self.fps
        result = (frame, self._frame_idx, timestamp)
        self._frame_idx += 1
        return result

    def release(self):
        """Kaynağı serbest bırak."""
        if self.cap.isOpened():
            self.cap.release()
        print("[VideoSource] Kapatıldı.")


class VideoWriter:
    """Çıktı video kaydedici."""

    def __init__(self, path: str, fps: float, resolution: Tuple[int, int]):
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self.writer = cv2.VideoWriter(path, fourcc, fps, resolution)
        self.path = path
        print(f"[VideoWriter] Kayıt başladı: {path}")

    def write(self, frame: np.ndarray):
        self.writer.write(frame)

    def release(self):
        self.writer.release()
        print(f"[VideoWriter] Kayıt tamamlandı: {self.path}")
