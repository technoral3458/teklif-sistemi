#!/bin/bash
# ============================================================
# B2B Teklif Sistemi — Hetzner Ubuntu Kurulum Scripti
# Sunucu: ubuntu-4gb-fsn1-1 (167.233.104.21)
# Servis: ersanb2b
# ============================================================

set -e

APP_DIR="/opt/ersanb2b"
APP_USER="ersanb2b"
SERVICE="ersanb2b"
REPO_URL="https://github.com/technoral3458/teklif-sistemi.git"
PORT=8501

echo "=== [1/8] Sistem güncelleniyor ==="
apt-get update -y
apt-get upgrade -y
apt-get install -y python3 python3-pip python3-venv git curl ufw nginx certbot python3-certbot-nginx

echo "=== [2/8] Kullanıcı oluşturuluyor ==="
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
fi

echo "=== [3/8] Uygulama dizini hazırlanıyor ==="
mkdir -p "$APP_DIR"
chown "$APP_USER":"$APP_USER" "$APP_DIR"

echo "=== [4/8] Kod kopyalanıyor ==="
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR" && sudo -u "$APP_USER" git pull origin main
else
    sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
fi

echo "=== [5/8] Python sanal ortam ve paketler ==="
cd "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv venv
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r requirements.txt

echo "=== [6/8] Dizinler ve izinler ==="
sudo -u "$APP_USER" mkdir -p "$APP_DIR/data" "$APP_DIR/images"
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

echo "=== [7/8] systemd servisi kuruluyor ==="
cp "$APP_DIR/deploy/ersanb2b.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"

echo "=== [8/8] Firewall ayarları ==="
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw allow "$PORT"
ufw --force enable

echo ""
echo "============================================"
echo "✅ Kurulum tamamlandı!"
echo "Uygulama: http://167.233.104.21:$PORT"
echo "Servis durumu: systemctl status $SERVICE"
echo "Loglar: journalctl -u $SERVICE -f"
echo "============================================"
