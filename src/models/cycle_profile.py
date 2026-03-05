"""
Döngü Profili Veri Modeli
========================
Referans videodan öğrenilen döngü şablonunu (template) ve istatistikleri saklar.
Her ürün tipi (gömlek, tişört vb.) için ayrı bir profil oluşturulur.
"""

import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class CycleProfile:
    """Bir ürün tipi için öğrenilmiş döngü profili."""

    # Ürün bilgileri
    product_name: str                           # Ürün adı (örn: "gomlek", "tisort")
    created_at: str = ""                        # Oluşturulma tarihi
    reference_video_path: str = ""              # Kaynak referans video yolu

    # Döngü şablonu (template)
    template_signal: list = field(default_factory=list)   # Ortalama döngü sinyali (normalize)
    template_length_frames: int = 0             # Şablon uzunluğu (frame)
    template_duration_sec: float = 0.0          # Şablon süresi (saniye)

    # İstatistikler
    total_cycles_in_reference: int = 0          # Referans videodaki toplam döngü sayısı
    avg_cycle_duration_sec: float = 0.0         # Ortalama döngü süresi
    std_cycle_duration_sec: float = 0.0         # Döngü süresi standart sapması
    min_cycle_duration_sec: float = 0.0         # Minimum döngü süresi
    max_cycle_duration_sec: float = 0.0         # Maksimum döngü süresi

    # Sinyal parametreleri
    avg_peak_prominence: float = 0.0            # Ortalama peak belirginliği
    avg_peak_height: float = 0.0                # Ortalama peak yüksekliği
    signal_fps: float = 30.0                    # Sinyalin FPS'i

    # Eşik değerleri (bu ürün tipi için kalibre edilmiş)
    calibrated_peak_prominence: float = 0.15
    calibrated_peak_height: float = 0.3
    calibrated_min_distance_frames: int = 30
    calibrated_similarity_threshold: float = 0.6

    # Tüm döngü sinyalleri (augmentation ve analiz için)
    all_cycle_signals: list = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def save(self, path: Optional[str] = None) -> str:
        """Profili JSON dosyasına kaydet."""
        if path is None:
            path = f"data/trained_models/{self.product_name}_profile.json"

        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(self)
        # numpy array'leri listeye çevir
        data["template_signal"] = [float(x) for x in self.template_signal]
        data["all_cycle_signals"] = [
            [float(x) for x in cycle] for cycle in self.all_cycle_signals
        ]

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[CycleProfile] Profil kaydedildi: {save_path}")
        return str(save_path)

    @classmethod
    def load(cls, path: str) -> "CycleProfile":
        """JSON dosyasından profil yükle."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = cls(**data)
        print(f"[CycleProfile] Profil yüklendi: {path}")
        print(f"  Ürün: {profile.product_name}")
        print(f"  Döngü sayısı: {profile.total_cycles_in_reference}")
        print(f"  Ort. döngü süresi: {profile.avg_cycle_duration_sec:.2f}s")
        return profile

    def get_template_array(self) -> np.ndarray:
        """Template sinyalini numpy array olarak döndür."""
        return np.array(self.template_signal, dtype=np.float64)

    def get_expected_cycle_frames(self) -> int:
        """Beklenen döngü uzunluğu (frame)."""
        return int(self.avg_cycle_duration_sec * self.signal_fps)

    def summary(self) -> str:
        """Profil özeti."""
        return (
            f"=== Döngü Profili: {self.product_name} ===\n"
            f"Oluşturulma: {self.created_at}\n"
            f"Referans video: {self.reference_video_path}\n"
            f"Toplam referans döngü: {self.total_cycles_in_reference}\n"
            f"Ort. döngü süresi: {self.avg_cycle_duration_sec:.2f}s "
            f"(±{self.std_cycle_duration_sec:.2f}s)\n"
            f"Min/Max süre: {self.min_cycle_duration_sec:.2f}s / "
            f"{self.max_cycle_duration_sec:.2f}s\n"
            f"Template uzunluğu: {self.template_length_frames} frame\n"
            f"Kalibre edilmiş prominence: {self.calibrated_peak_prominence:.3f}\n"
            f"Kalibre edilmiş height: {self.calibrated_peak_height:.3f}\n"
        )
