#!/bin/bash
# =============================================================
# Otomatik Guncelleme Scripti
# GitHub'dan yeni commit varsa pull yapar ve servisi yeniden baslatir.
# systemd timer ile her 5 dakikada bir calisir.
# =============================================================

PROJECT_DIR="/home/colban/sewing-cycle-counter"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="sewing-dashboard"
LOG_FILE="$PROJECT_DIR/data/logs/autoupdate.log"

cd "$PROJECT_DIR" || exit 1

# Mevcut commit
LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null)

# Remote'u fetch et
git fetch origin main --quiet 2>/dev/null

# Remote commit
REMOTE_HASH=$(git rev-parse origin/main 2>/dev/null)

if [ "$LOCAL_HASH" = "$REMOTE_HASH" ]; then
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Guncelleme bulundu: $LOCAL_HASH -> $REMOTE_HASH" >> "$LOG_FILE"

# Pull
git pull origin main --quiet 2>> "$LOG_FILE"

# Bagimliliklari guncelle
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt --quiet 2>> "$LOG_FILE"

# Dashboard servisini yeniden baslat
sudo systemctl restart "$SERVICE_NAME"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Guncelleme tamamlandi. Servis yeniden baslatildi." >> "$LOG_FILE"
