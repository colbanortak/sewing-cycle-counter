#!/bin/bash
# =============================================================
# Jetson Orin - Ilk Kurulum Scripti
# =============================================================
# Bu script Jetson uzerinde bir kez calistirilir.
# Projeyi kurar, servis dosyalarini olusturur ve auto-update yapar.
# =============================================================

set -e

REPO_URL="https://github.com/colbanortak/sewing-cycle-counter.git"
PROJECT_DIR="/home/colban/sewing-cycle-counter"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="sewing-dashboard"
UPDATE_SERVICE_NAME="sewing-autoupdate"

echo "============================================="
echo "  Dikis Atolyesi - Jetson Kurulum Basladi"
echo "============================================="

# 1. Sistem paketleri
echo "[1/7] Sistem paketleri yukleniyor..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-pip python3-venv git libgl1-mesa-glx libglib2.0-0 > /dev/null 2>&1
echo "  OK"

# 2. Projeyi klonla veya guncelle
echo "[2/7] Proje indiriliyor..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git pull origin main
    echo "  Guncellendi"
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    echo "  Klonlandi"
fi
cd "$PROJECT_DIR"

# 3. Virtual environment
echo "[3/7] Python sanal ortami olusturuluyor..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  OK"

# 4. Data dizinleri
echo "[4/7] Veri dizinleri olusturuluyor..."
mkdir -p data/reference_videos data/trained_models data/logs
echo "  OK"

# 5. Dashboard systemd servisi
echo "[5/7] Dashboard servisi olusturuluyor..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << SERV_EOF
[Unit]
Description=Dikis Atolyesi Dashboard
After=network.target

[Service]
Type=simple
User=colban
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_DIR/bin/python scripts/run_dashboard.py --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
Environment=PYTHONPATH=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
SERV_EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}
echo "  OK - Dashboard http://$(hostname -I | awk '{print $1}'):8080"

# 6. Auto-update timer
echo "[6/7] Otomatik guncelleme ayarlaniyor..."
sudo tee /etc/systemd/system/${UPDATE_SERVICE_NAME}.service > /dev/null << UPD_EOF
[Unit]
Description=Sewing Cycle Counter Auto Update
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=colban
WorkingDirectory=$PROJECT_DIR
ExecStart=/bin/bash $PROJECT_DIR/deploy/auto_update.sh
UPD_EOF

sudo tee /etc/systemd/system/${UPDATE_SERVICE_NAME}.timer > /dev/null << TMR_EOF
[Unit]
Description=Sewing Cycle Counter Auto Update Timer

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
TMR_EOF

sudo systemctl daemon-reload
sudo systemctl enable ${UPDATE_SERVICE_NAME}.timer
sudo systemctl start ${UPDATE_SERVICE_NAME}.timer
echo "  OK - Her 5 dakikada GitHub'dan guncelleme kontrolu"

# 7. Firewall
echo "[7/7] Port ayarlari..."
sudo ufw allow 8080/tcp 2>/dev/null || true
echo "  OK"

echo ""
echo "============================================="
echo "  KURULUM TAMAMLANDI!"
echo "============================================="
echo "  Dashboard: http://$(hostname -I | awk '{print $1}'):8080"
echo "  Servis durumu: sudo systemctl status ${SERVICE_NAME}"
echo "  Loglar: sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Auto-update: sudo systemctl status ${UPDATE_SERVICE_NAME}.timer"
echo "============================================="
