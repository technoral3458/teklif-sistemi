#!/bin/bash
# ============================================================
# B2B Teklif Sistemi — Güncelleme Scripti
# Kullanım: sudo bash /opt/ersanb2b/deploy/update.sh
# ============================================================

set -e

APP_DIR="/opt/ersanb2b"
APP_USER="ersanb2b"
SERVICE="ersanb2b"

echo "=== Güncelleme başlıyor ==="

echo "[1/4] Kod güncelleniyor..."
cd "$APP_DIR"
sudo -u "$APP_USER" git pull origin main

echo "[2/4] Paketler güncelleniyor..."
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r requirements.txt --quiet

echo "[3/4] Servis yeniden başlatılıyor..."
systemctl restart "$SERVICE"

echo "[4/4] Durum kontrol ediliyor..."
sleep 2
systemctl status "$SERVICE" --no-pager

echo ""
echo "✅ Güncelleme tamamlandı!"
