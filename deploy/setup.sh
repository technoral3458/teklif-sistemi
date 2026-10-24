#!/bin/bash
# B2B Teklif Sistemi - Sunucu Kurulum Scripti
# Ubuntu 22.04 / Hetzner
# Kullanım: bash setup.sh

set -e

APP_DIR="/opt/teklif-sistemi"
REPO_URL="https://github.com/technoral3458/teklif-sistemi.git"
BRANCH="claude/new-server-setup-71krv9"
SERVICE_NAME="ersanb2b"

echo "=== B2B Teklif Sistemi Kurulum ==="

# 1. System packages
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git

# 2. Clone / update repo
if [ -d "$APP_DIR/.git" ]; then
  echo "Repo güncelleniyor..."
  cd "$APP_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
else
  echo "Repo klonlanıyor..."
  rm -rf "$APP_DIR"
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

# 3. Virtual environment
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip -q
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

# 4. Directories
mkdir -p "$APP_DIR/data"
mkdir -p "$APP_DIR/static/img/uploads"

# 5. Service file
cp "$APP_DIR/deploy/ersanb2b.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "=== Kurulum tamamlandı! ==="
echo "Servis durumu: systemctl status $SERVICE_NAME"
echo "Uygulama adresi: http://$(hostname -I | awk '{print $1}'):8501"
echo ""
echo "NOT: /etc/systemd/system/${SERVICE_NAME}.service dosyasındaki"
echo "SECRET_KEY, ADMIN_EMAIL ve ADMIN_PASS değerlerini değiştirin!"
