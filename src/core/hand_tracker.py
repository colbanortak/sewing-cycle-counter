"""
El Takip Modülü (Hand Tracker)
==============================
MediaPipe Hands kullanarak video frame'lerinden el landmark pozisyonlarını çıkarır.
Her frame için el bilek (wrist), parmak ucu vb. noktaların x, y, z koordinatlarını döndürür.

Bu modül ham video frame'ini alır ve yapılandırılmış landmark verisine dönüştürür.
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional


# MediaPipe el landmark indeksleri (referans)
LANDMARK_NAMES = {
    0: "WRIST",
    4: "THUMB_TIP",
    5: "INDEX_MCP",
    8: "INDEX_TIP",
    9: "MIDDLE_MCP",
    12: "MIDDLE_TIP",
    13: "RING_MCP",
    16: "RING_TIP",
    17: "PINKY_MCP",
    20: "PINKY_TIP",
}


@dataclass
class HandData:
    """Tek bir frame'deki el verileri."""

    frame_idx: int
    timestamp_sec: float
    detected: bool                          # El algılandı mı

    # Ana landmark pozisyonları (normalize 0-1)
    landmarks: Optional[np.ndarray] = None  # Shape: (num_landmarks, 3) -> x, y, z

    # Pixel pozisyonları (çizim için)
    landmarks_px: Optional[np.ndarray] = None  # Shape: (num_landmarks, 2) -> x, y

    # Tek landmark değerleri (hızlı erişim)
    wrist_y: float = 0.0                    # Bilek Y pozisyonu (normalize)
    wrist_x: float = 0.0                    # Bilek X pozisyonu (normalize)
    index_tip_y: float = 0.0                # İşaret parmağı ucu Y
    middle_tip_y: float = 0.0               # Orta parmak ucu Y

    # Hesaplanan metrikler
    hand_openness: float = 0.0              # El açıklık skoru
    hand_velocity: float = 0.0              # El hareket hızı


class HandTracker:
    """
    MediaPipe tabanlı el takip sınıfı.

    Kullanım:
        tracker = HandTracker(config)
        hand_data = tracker.process_frame(frame, frame_idx, timestamp)
        tracker.release()
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Konfigürasyon sözlüğü (tracker bölümü)
        """
        tracker_cfg = config.get("tracker", {})

        self.model_complexity = tracker_cfg.get("model_complexity", 1)
        self.min_detection_conf = tracker_cfg.get("min_detection_confidence", 0.6)
        self.min_tracking_conf = tracker_cfg.get("min_tracking_confidence", 0.5)
        self.max_hands = tracker_cfg.get("max_num_hands", 2)
        self.tracked_landmarks = tracker_cfg.get("tracked_landmarks", [0, 5, 8, 9, 12])
        self.primary_landmark = tracker_cfg.get("primary_landmark", 0)

        # MediaPipe başlat
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=self.model_complexity,
            min_detection_confidence=self.min_detection_conf,
            min_tracking_confidence=self.min_tracking_conf,
            max_num_hands=self.max_hands,
        )

        # Önceki frame verisi (velocity hesabı için)
        self._prev_wrist_y = None
        self._prev_wrist_x = None

        print(f"[HandTracker] Başlatıldı | complexity={self.model_complexity} | "
              f"max_hands={self.max_hands}")

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        timestamp_sec: float,
    ) -> HandData:
        """
        Tek bir video frame'ini işle ve el verilerini çıkar.

        Args:
            frame: BGR format OpenCV frame (H, W, 3)
            frame_idx: Frame sıra numarası
            timestamp_sec: Frame zaman damgası (saniye)

        Returns:
            HandData: Çıkarılan el verileri
        """
        h, w, _ = frame.shape

        # MediaPipe RGB bekler
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)

        # Varsayılan: el algılanmadı
        hand_data = HandData(
            frame_idx=frame_idx,
            timestamp_sec=timestamp_sec,
            detected=False,
        )

        if results.multi_hand_landmarks:
            # En büyük (en yakın) eli seç
            best_hand = self._select_dominant_hand(results.multi_hand_landmarks, w, h)

            if best_hand is not None:
                hand_data.detected = True

                # Tüm takip edilen landmark'ları çıkar
                num_landmarks = len(self.tracked_landmarks)
                landmarks = np.zeros((num_landmarks, 3), dtype=np.float64)
                landmarks_px = np.zeros((num_landmarks, 2), dtype=np.int32)

                for i, lm_idx in enumerate(self.tracked_landmarks):
                    lm = best_hand.landmark[lm_idx]
                    landmarks[i] = [lm.x, lm.y, lm.z]
                    landmarks_px[i] = [int(lm.x * w), int(lm.y * h)]

                hand_data.landmarks = landmarks
                hand_data.landmarks_px = landmarks_px

                # Birincil landmark (wrist) değerleri
                primary_idx = self.tracked_landmarks.index(self.primary_landmark) \
                    if self.primary_landmark in self.tracked_landmarks else 0
                hand_data.wrist_x = landmarks[primary_idx, 0]
                hand_data.wrist_y = landmarks[primary_idx, 1]

                # İşaret ve orta parmak uçları (varsa)
                if 8 in self.tracked_landmarks:
                    idx = self.tracked_landmarks.index(8)
                    hand_data.index_tip_y = landmarks[idx, 1]
                if 12 in self.tracked_landmarks:
                    idx = self.tracked_landmarks.index(12)
                    hand_data.middle_tip_y = landmarks[idx, 1]

                # El açıklık skoru
                hand_data.hand_openness = self._calc_hand_openness(best_hand)

                # Velocity (önceki frame'e göre)
                if self._prev_wrist_y is not None:
                    dy = hand_data.wrist_y - self._prev_wrist_y
                    dx = hand_data.wrist_x - self._prev_wrist_x
                    hand_data.hand_velocity = np.sqrt(dx**2 + dy**2)

                self._prev_wrist_y = hand_data.wrist_y
                self._prev_wrist_x = hand_data.wrist_x

        return hand_data

    def draw_landmarks(self, frame: np.ndarray, hand_data: HandData) -> np.ndarray:
        """
        Frame üzerine el landmark noktalarını çiz.

        Args:
            frame: BGR OpenCV frame
            hand_data: İşlenmiş el verisi

        Returns:
            Çizim yapılmış frame
        """
        output = frame.copy()

        if hand_data.detected and hand_data.landmarks_px is not None:
            # Landmark noktalarını çiz
            for i, (px, py) in enumerate(hand_data.landmarks_px):
                lm_idx = self.tracked_landmarks[i]
                name = LANDMARK_NAMES.get(lm_idx, str(lm_idx))

                # Birincil landmark kırmızı, diğerleri yeşil
                color = (0, 0, 255) if lm_idx == self.primary_landmark else (0, 255, 0)
                cv2.circle(output, (px, py), 6, color, -1)
                cv2.putText(output, name, (px + 8, py - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            # Bağlantı çizgileri
            if len(hand_data.landmarks_px) >= 3:
                pts = hand_data.landmarks_px
                for i in range(len(pts) - 1):
                    cv2.line(output, tuple(pts[i]), tuple(pts[i + 1]),
                             (255, 255, 0), 1)

        return output

    def _select_dominant_hand(self, multi_hand_landmarks, img_w: int, img_h: int):
        """
        Birden fazla el algılandıysa, en büyük/uygun olanı seç.
        Kriter: El bounding box alanı (en büyük = en yakın kamera).
        """
        best = None
        best_area = 0

        for hand_landmarks in multi_hand_landmarks:
            xs = [lm.x for lm in hand_landmarks.landmark]
            ys = [lm.y for lm in hand_landmarks.landmark]
            area = (max(xs) - min(xs)) * (max(ys) - min(ys))
            if area > best_area:
                best_area = area
                best = hand_landmarks

        return best

    def _calc_hand_openness(self, hand_landmarks) -> float:
        """
        El açıklık skoru hesapla.
        Parmak uçları ile bilek arasındaki ortalama mesafe.
        Kapalı el (kumaş tutma) → düşük skor
        Açık el (kumaş bırakma) → yüksek skor
        """
        wrist = hand_landmarks.landmark[0]
        tips = [
            hand_landmarks.landmark[8],   # INDEX_TIP
            hand_landmarks.landmark[12],  # MIDDLE_TIP
            hand_landmarks.landmark[16],  # RING_TIP
            hand_landmarks.landmark[20],  # PINKY_TIP
        ]

        distances = []
        for tip in tips:
            d = np.sqrt(
                (tip.x - wrist.x) ** 2
                + (tip.y - wrist.y) ** 2
                + (tip.z - wrist.z) ** 2
            )
            distances.append(d)

        return float(np.mean(distances))

    def release(self):
        """Kaynakları serbest bırak."""
        self.hands.close()
        print("[HandTracker] Kapatıldı.")
