#!/usr/bin/env bash
# ==============================================================================
# FLUXA - Script de Instalación de Servicio Systemd Universal
# Compatible con: Armbian (Orange Pi 5), openSUSE, Fedora, Ubuntu, Debian
# ==============================================================================
set -e

SERVICE_NAME="fluxa.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DEST="/etc/systemd/system/$SERVICE_NAME"
CURRENT_USER="${SUDO_USER:-$USER}"
ARCH=$(uname -m)

if [ "$EUID" -ne 0 ]; then
  echo "Por favor ejecuta este script con privilegios root (sudo bash systemd/install_service.sh)"
  exit 1
fi

echo " Configurando servicio $SERVICE_NAME para usuario $CURRENT_USER en $SCRIPT_DIR..."

BACKEND="cpu"
if [ "$ARCH" = "aarch64" ]; then
    BACKEND="rknn"
fi

PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$(command -v python3 || echo /usr/bin/python3)"
fi

cat << EOF > "$SERVICE_DEST"
[Unit]
Description=FLUXA - Control Semaforico Inteligente y Telemetria Edge
After=network.target mariadb.service mysql.service
Wants=mariadb.service mysql.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=-${SCRIPT_DIR}/.env
ExecStart=${PYTHON_EXEC} ${SCRIPT_DIR}/main.py --topology 4_way --backend ${BACKEND} --headless --port 5000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=OPENCV_LOG_LEVEL=ERROR
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_DEST"

echo " Recargando daemon de systemd..."
systemctl daemon-reload

echo "Habilitando servicio para auto-arranque..."
systemctl enable "$SERVICE_NAME"

echo " Iniciando servicio FLUXA..."
systemctl restart "$SERVICE_NAME"

echo "Servicio FLUXA instalado y corriendo exitosamente (Backend: $BACKEND)."
echo "Para verificar el estado ejecuta: sudo systemctl status $SERVICE_NAME"
echo "Para ver logs en tiempo real ejecuta: sudo journalctl -u $SERVICE_NAME -f"
