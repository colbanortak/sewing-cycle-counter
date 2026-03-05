"""
Web Yonetim Paneli (Management Dashboard)
==========================================
Dikis atolyesi yonetim arayuzu.

Baslatma:
    python scripts/run_dashboard.py
    -> http://localhost:8080
"""

import os
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

try:
    from src.api.dashboard_html import DASHBOARD_HTML
except ImportError:
    from dashboard_html import DASHBOARD_HTML

app = FastAPI(title="Dikis Atolyesi Yonetim Paneli", version="0.2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "reference_videos"
MODELS_DIR = DATA_DIR / "trained_models"
LOGS_DIR = DATA_DIR / "logs"
DB_PATH = LOGS_DIR / "production.db"

for d in [UPLOAD_DIR, MODELS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

training_jobs = {}
live_sessions = {}


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL, machine_id TEXT DEFAULT 'M01',
        operator_name TEXT DEFAULT '', started_at TEXT NOT NULL,
        ended_at TEXT, total_cycles INTEGER DEFAULT 0,
        avg_cycle_duration REAL DEFAULT 0, cycles_per_minute REAL DEFAULT 0,
        status TEXT DEFAULT 'active')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL, cycle_number INTEGER NOT NULL,
        timestamp_sec REAL NOT NULL, confidence REAL DEFAULT 1.0,
        duration_sec REAL DEFAULT 0, detection_method TEXT DEFAULT 'peak',
        FOREIGN KEY (session_id) REFERENCES sessions(id))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, reference_video TEXT,
        profile_path TEXT, cycle_count INTEGER DEFAULT 50,
        video_duration_sec REAL DEFAULT 300, status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL, trained_at TEXT,
        avg_cycle_duration REAL DEFAULT 0, notes TEXT DEFAULT '')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY, name TEXT NOT NULL,
        camera_source TEXT DEFAULT '0', operator TEXT DEFAULT '',
        current_product TEXT DEFAULT '', is_active INTEGER DEFAULT 0,
        total_today INTEGER DEFAULT 0)""")
    conn.commit()
    conn.close()

init_db()


# ============================================================
# URUN YONETIMI
# ============================================================

@app.post("/api/products/create")
async def create_product(
    background_tasks: BackgroundTasks,
    product_name: str = Form(...),
    cycle_count: int = Form(50),
    video_duration_min: float = Form(5.0),
    notes: str = Form(""),
    video: UploadFile = File(...),
):
    safe_name = product_name.lower().replace(" ", "_")
    ext = Path(video.filename).suffix or ".mp4"
    video_filename = f"{safe_name}_ref_{int(datetime.now().timestamp())}{ext}"
    video_path = UPLOAD_DIR / video_filename

    with open(video_path, "wb") as f:
        content = await video.read()
        f.write(content)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO products (name, reference_video, cycle_count, "
            "video_duration_sec, status, created_at, notes) VALUES (?,?,?,?,?,?,?)",
            (safe_name, str(video_path), cycle_count,
             video_duration_min * 60, "uploading", datetime.now().isoformat(), notes),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(400, f"'{safe_name}' zaten var.")
    conn.close()

    background_tasks.add_task(run_training, safe_name, str(video_path), cycle_count)
    return {"status": "ok", "message": f"'{safe_name}' olusturuldu. Egitim basliyor.",
            "product_name": safe_name, "cycle_count": cycle_count}


def run_training(product_name, video_path, cycle_count):
    training_jobs[product_name] = {"status": "running", "started_at": datetime.now().isoformat()}

    conn = get_db()
    conn.execute("UPDATE products SET status='training' WHERE name=?", (product_name,))
    conn.commit(); conn.close()

    try:
        profile_path = str(MODELS_DIR / f"{product_name}_profile.json")
        cmd = ["python", str(BASE_DIR / "scripts" / "train_reference.py"),
               "--video", video_path, "--cycles", str(cycle_count),
               "--product-name", product_name, "--output", profile_path, "--visualize"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode == 0:
            avg_dur = 0.0
            if Path(profile_path).exists():
                with open(profile_path) as f:
                    avg_dur = json.load(f).get("avg_cycle_duration_sec", 0.0)

            conn = get_db()
            conn.execute("UPDATE products SET status='ready', profile_path=?, trained_at=?, avg_cycle_duration=? WHERE name=?",
                         (profile_path, datetime.now().isoformat(), avg_dur, product_name))
            conn.commit(); conn.close()
            training_jobs[product_name] = {"status": "completed", "completed_at": datetime.now().isoformat()}
        else:
            conn = get_db()
            conn.execute("UPDATE products SET status='failed' WHERE name=?", (product_name,))
            conn.commit(); conn.close()
            training_jobs[product_name] = {"status": "failed", "error": result.stderr[-500:]}
    except Exception as e:
        conn = get_db()
        conn.execute("UPDATE products SET status='failed' WHERE name=?", (product_name,))
        conn.commit(); conn.close()
        training_jobs[product_name] = {"status": "failed", "error": str(e)}


@app.get("/api/products")
async def list_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()
    conn.close()
    products = [dict(r) for r in rows]
    for p in products:
        if p["name"] in training_jobs:
            p["training_status"] = training_jobs[p["name"]]
    return products


@app.get("/api/products/{name}")
async def get_product(name: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE name=?", (name,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404, "Urun bulunamadi")
    return dict(row)


@app.delete("/api/products/{name}")
async def delete_product(name: str):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE name=?", (name,))
    conn.commit(); conn.close()
    p = MODELS_DIR / f"{name}_profile.json"
    if p.exists(): p.unlink()
    return {"status": "deleted"}


# ============================================================
# MAKINE YONETIMI
# ============================================================

@app.post("/api/machines")
async def add_machine(machine_id: str = Form(...), name: str = Form(...),
                      camera_source: str = Form("0"), operator: str = Form("")):
    conn = get_db()
    try:
        conn.execute("INSERT INTO machines (id, name, camera_source, operator) VALUES (?,?,?,?)",
                     (machine_id, name, camera_source, operator))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close(); raise HTTPException(400, f"'{machine_id}' zaten var.")
    conn.close()
    return {"status": "ok", "machine_id": machine_id}


@app.get("/api/machines")
async def list_machines():
    conn = get_db()
    rows = conn.execute("SELECT * FROM machines").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# CANLI SAYIM
# ============================================================

@app.post("/api/live/start")
async def start_live(background_tasks: BackgroundTasks,
                     machine_id: str = Form(...), product_name: str = Form(...),
                     operator: str = Form("")):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE name=? AND status='ready'", (product_name,)).fetchone()
    if not product: conn.close(); raise HTTPException(400, f"'{product_name}' hazir degil.")
    machine = conn.execute("SELECT * FROM machines WHERE id=?", (machine_id,)).fetchone()
    camera = machine["camera_source"] if machine else "0"
    conn.execute("UPDATE machines SET is_active=1, current_product=?, operator=? WHERE id=?",
                 (product_name, operator, machine_id))
    conn.commit(); conn.close()

    background_tasks.add_task(run_live_counter, machine_id, product_name, camera, operator)
    live_sessions[machine_id] = {"status": "running", "product": product_name}
    return {"status": "ok", "message": f"{machine_id} baslatildi."}


def run_live_counter(machine_id, product_name, camera, operator):
    cmd = ["python", str(BASE_DIR / "scripts" / "run_live_counter.py"),
           "--product", product_name, "--camera", camera,
           "--machine", machine_id, "--operator", operator, "--no-display"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=28800)
    except: pass
    live_sessions[machine_id] = {"status": "stopped"}
    conn = get_db()
    conn.execute("UPDATE machines SET is_active=0 WHERE id=?", (machine_id,))
    conn.commit(); conn.close()


@app.post("/api/live/stop/{machine_id}")
async def stop_live(machine_id: str):
    live_sessions[machine_id] = {"status": "stopping"}
    conn = get_db()
    conn.execute("UPDATE machines SET is_active=0 WHERE id=?", (machine_id,))
    conn.commit(); conn.close()
    return {"status": "ok"}


@app.get("/api/live/status")
async def get_live_status():
    conn = get_db()
    machines = conn.execute("SELECT * FROM machines").fetchall()
    result = []
    for m in machines:
        data = dict(m)
        if m["id"] in live_sessions: data["live_status"] = live_sessions[m["id"]]
        last = conn.execute("SELECT * FROM sessions WHERE machine_id=? ORDER BY id DESC LIMIT 1", (m["id"],)).fetchone()
        if last: data["last_session"] = dict(last)
        result.append(data)
    conn.close()
    return result


# ============================================================
# RAPORLAR
# ============================================================

@app.get("/api/reports/daily")
async def daily_report(date: Optional[str] = None):
    if date is None: date = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    sessions = conn.execute("SELECT * FROM sessions WHERE started_at LIKE ?", (f"{date}%",)).fetchall()
    conn.close()
    total = sum(s["total_cycles"] for s in sessions)
    by_machine = {}; by_product = {}
    for s in sessions:
        by_machine[s["machine_id"]] = by_machine.get(s["machine_id"], 0) + s["total_cycles"]
        by_product[s["product_name"]] = by_product.get(s["product_name"], 0) + s["total_cycles"]
    return {"date": date, "total_cycles": total, "session_count": len(sessions),
            "by_machine": by_machine, "by_product": by_product, "sessions": [dict(s) for s in sessions]}


@app.get("/api/sessions")
async def get_sessions(limit: int = 50, machine_id: Optional[str] = None):
    conn = get_db()
    if machine_id:
        rows = conn.execute("SELECT * FROM sessions WHERE machine_id=? ORDER BY id DESC LIMIT ?", (machine_id, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
# ANA SAYFA
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML



