#!/usr/bin/env bash
set -euo pipefail

APP_NAME="medauth-backend"
INSTALL_DIR="/opt/medauth-sentinel"
REPO_DIR="${INSTALL_DIR}/repo"
APP_SUBDIR="${APP_SUBDIR:-medauth-sentinel}"
APP_DIR="${REPO_DIR}/${APP_SUBDIR}"
REPO_URL="${REPO_URL:-https://github.com/KeshavKhippal/Veersa-Victors.git}"
BRANCH="${BRANCH:-main}"
SERVICE_USER="${SERVICE_USER:-medauth}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo."
  exit 1
fi

if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "GROQ_API_KEY is required."
  exit 1
fi

echo "[1/8] Installing system packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  nginx \
  python3 \
  python3-pip \
  python3-venv \
  ufw

echo "[2/8] Creating service user"
if ! id "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

echo "[3/8] Fetching application"
if [[ -d "${REPO_DIR}/.git" ]]; then
  git -C "${REPO_DIR}" fetch origin "${BRANCH}"
  git -C "${REPO_DIR}" reset --hard "origin/${BRANCH}"
else
  rm -rf "${REPO_DIR}"
  mkdir -p "${INSTALL_DIR}"
  git clone --branch "${BRANCH}" "${REPO_URL}" "${REPO_DIR}"
fi
if [[ ! -f "${APP_DIR}/requirements.txt" ]]; then
  echo "Could not find application at ${APP_DIR}. Set APP_SUBDIR if the repo layout changes."
  exit 1
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"

echo "[4/8] Creating Python virtual environment"
sudo -u "${SERVICE_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${SERVICE_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u "${SERVICE_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[5/8] Writing environment file"
install -d -m 0750 -o "${SERVICE_USER}" -g "${SERVICE_USER}" "${APP_DIR}/.deploy"
cat > "${APP_DIR}/.deploy/backend.env" <<ENV
APP_ENV=production
APP_NAME=MedAuth Sentinel
PORT=${BACKEND_PORT}
GROQ_API_KEY=${GROQ_API_KEY}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
ENV
chmod 0640 "${APP_DIR}/.deploy/backend.env"
chown "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}/.deploy/backend.env"

echo "[6/8] Installing systemd service"
cat > "/etc/systemd/system/${APP_NAME}.service" <<SERVICE
[Unit]
Description=MedAuth Sentinel FastAPI backend
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.deploy/backend.env
ExecStart=${APP_DIR}/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port ${BACKEND_PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "${APP_NAME}"
systemctl restart "${APP_NAME}"

echo "[7/8] Configuring nginx"
cat > "/etc/nginx/sites-available/${APP_NAME}" <<NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"
nginx -t
systemctl reload nginx

echo "[8/8] Configuring firewall"
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

cat > "${APP_DIR}/deploy/oracle/redeploy-backend.sh" <<'REDEPLOY'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/medauth-sentinel/repo"
APP_DIR="${REPO_DIR}/medauth-sentinel"
APP_NAME="medauth-backend"
BRANCH="${BRANCH:-main}"
SERVICE_USER="${SERVICE_USER:-medauth}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo."
  exit 1
fi

git -C "${REPO_DIR}" fetch origin "${BRANCH}"
git -C "${REPO_DIR}" reset --hard "origin/${BRANCH}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${REPO_DIR}"
sudo -u "${SERVICE_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
systemctl restart "${APP_NAME}"
systemctl status "${APP_NAME}" --no-pager
REDEPLOY

chmod +x "${APP_DIR}/deploy/oracle/redeploy-backend.sh"
chown "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}/deploy/oracle/redeploy-backend.sh"

echo
echo "Backend deployed."
echo "Health check: http://$(curl -fsS ifconfig.me || hostname -I | awk '{print $1}')/api/health"
systemctl status "${APP_NAME}" --no-pager
