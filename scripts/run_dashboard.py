#!/usr/bin/env python3
"""
Dashboard Başlatma Scripti
===========================
FastAPI sunucusunu başlatır. Tarayıcıdan http://localhost:8080 ile erişilir.

Kullanım:
    python scripts/run_dashboard.py
    python scripts/run_dashboard.py --port 9090
"""

import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Dashboard başlat")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    import uvicorn
    print(f"\n🧵 Dikiş Atölyesi Dashboard")
    print(f"   http://localhost:{args.port}")
    print(f"   API Docs: http://localhost:{args.port}/docs\n")

    uvicorn.run(
        "src.api.server:app",
        host=args.host,
        port=args.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
