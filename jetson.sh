#!/bin/bash
# ============================================
# COLBAN Dikis Sayim - Jetson Kontrol
# ============================================
# Kullanim:
#   ./jetson.sh start   -> Baslat
#   ./jetson.sh stop    -> Durdur
#   ./jetson.sh status  -> Durum
#   ./jetson.sh logs    -> Son loglar
#   ./jetson.sh update  -> GitHub'dan guncelle
#   ./jetson.sh ssh     -> Jetson'a baglan
# ============================================

KEY="$HOME/.ssh/jetson_key"
HOST="colban@100.94.34.114"
PASS="123456321"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no $HOST"

case "$1" in
  start)
    echo "Dashboard baslatiliyor..."
    $SSH "echo $PASS | sudo -S systemctl start sewing-dashboard.service && echo $PASS | sudo -S systemctl start sewing-autoupdate.timer"
    echo "Dashboard: http://100.94.34.114:8080"
    ;;
  stop)
    echo "Dashboard durduruluyor..."
    $SSH "echo $PASS | sudo -S systemctl stop sewing-dashboard.service && echo $PASS | sudo -S systemctl stop sewing-autoupdate.timer"
    echo "Durduruldu."
    ;;
  status)
    $SSH "echo $PASS | sudo -S systemctl status sewing-dashboard.service --no-pager 2>&1 | head -5; echo ''; echo $PASS | sudo -S systemctl status sewing-autoupdate.timer --no-pager 2>&1 | head -5"
    ;;
  logs)
    $SSH "echo $PASS | sudo -S journalctl -u sewing-dashboard.service --no-pager -n 30 2>&1"
    ;;
  update)
    echo "GitHub'dan guncelleniyor..."
    $SSH "cd /home/colban/sewing-cycle-counter && git pull origin master && echo $PASS | sudo -S systemctl restart sewing-dashboard.service"
    echo "Guncellendi ve yeniden baslatildi."
    ;;
  ssh)
    ssh -i $KEY -o StrictHostKeyChecking=no $HOST
    ;;
  *)
    echo "COLBAN Dikis Sayim - Jetson Kontrol"
    echo ""
    echo "Kullanim: ./jetson.sh <komut>"
    echo ""
    echo "  start   - Dashboard'u baslat"
    echo "  stop    - Dashboard'u durdur"
    echo "  status  - Servis durumunu goster"
    echo "  logs    - Son loglari goster"
    echo "  update  - GitHub'dan guncelle + yeniden baslat"
    echo "  ssh     - Jetson'a baglan"
    echo ""
    echo "Dashboard URL: http://100.94.34.114:8080"
    ;;
esac
