"""
Veri Kayıt Modülü (Data Logger)
================================
Üretim sayım verilerini SQLite veritabanına kaydeder.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class DataLogger:
    """
    SQLite tabanlı üretim veri kaydedici.

    Kullanım:
        logger = DataLogger("data/logs/production.db")
        session_id = logger.start_session("gomlek", machine_id="M01")
        logger.log_cycle(session_id, cycle_number=1, timestamp=12.5, confidence=0.95)
        logger.end_session(session_id, total_cycles=150)
    """

    def __init__(self, db_path: str = "data/logs/production.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Veritabanı tablolarını oluştur."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                machine_id TEXT DEFAULT 'M01',
                operator_name TEXT DEFAULT '',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_cycles INTEGER DEFAULT 0,
                avg_cycle_duration REAL DEFAULT 0,
                cycles_per_minute REAL DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                cycle_number INTEGER NOT NULL,
                timestamp_sec REAL NOT NULL,
                confidence REAL DEFAULT 1.0,
                duration_sec REAL DEFAULT 0,
                detection_method TEXT DEFAULT 'peak',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                hour_start TEXT NOT NULL,
                cycle_count INTEGER DEFAULT 0,
                avg_speed REAL DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        conn.commit()
        conn.close()

    def start_session(
        self,
        product_name: str,
        machine_id: str = "M01",
        operator_name: str = "",
    ) -> int:
        """Yeni üretim oturumu başlat. Session ID döndürür."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (product_name, machine_id, operator_name, started_at) "
            "VALUES (?, ?, ?, ?)",
            (product_name, machine_id, operator_name, datetime.now().isoformat()),
        )
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"[DataLogger] Oturum başlatıldı: #{session_id} | "
              f"{product_name} | {machine_id}")
        return session_id

    def log_cycle(
        self,
        session_id: int,
        cycle_number: int,
        timestamp_sec: float,
        confidence: float = 1.0,
        duration_sec: float = 0.0,
        detection_method: str = "peak",
    ):
        """Tek bir döngü olayını kaydet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cycles (session_id, cycle_number, timestamp_sec, "
            "confidence, duration_sec, detection_method) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, cycle_number, timestamp_sec, confidence,
             duration_sec, detection_method),
        )
        conn.commit()
        conn.close()

    def end_session(
        self,
        session_id: int,
        total_cycles: int,
        avg_duration: float = 0.0,
        cpm: float = 0.0,
    ):
        """Oturumu kapat."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET ended_at=?, total_cycles=?, avg_cycle_duration=?, "
            "cycles_per_minute=?, status='completed' WHERE id=?",
            (datetime.now().isoformat(), total_cycles, avg_duration, cpm, session_id),
        )
        conn.commit()
        conn.close()
        print(f"[DataLogger] Oturum kapatıldı: #{session_id} | "
              f"Toplam: {total_cycles} adet")

    def get_session_summary(self, session_id: int) -> Optional[Dict]:
        """Oturum özetini getir."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id=?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_daily_report(self, date: Optional[str] = None) -> List[Dict]:
        """Günlük üretim raporu."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE started_at LIKE ?",
            (f"{date}%",),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
