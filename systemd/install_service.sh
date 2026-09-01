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

echo "Limpiando instalación previa (si existe)..."
if [ -f "/etc/systemd/system/$SERVICE_NAME" ]; then
    systemctl stop "$SERVICE_NAME" || true
    systemctl disable "$SERVICE_NAME" || true
    rm -f "/etc/systemd/system/$SERVICE_NAME"
fi

echo "Configurando servicio Tri-Core para usuario $CURRENT_USER en $SCRIPT_DIR..."

# Identificar backend
BACKEND="cpu"
if [ "$ARCH" = "aarch64" ]; then
    BACKEND="rknn"
fi

PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$(command -v python3 || echo /usr/bin/python3)"
fi

echo " Instalando servicios FLUXA Corredor Tri-Core..."

for CORE in 0 1 2; do
  PORT=$((5000 + CORE))
  NODE_ID="CRUCE_0$((CORE + 1))"
  SVC_NAME="fluxa-node${CORE}.service"
  SVC_DEST="/etc/systemd/system/${SVC_NAME}"
  
  cat << EOF > "$SVC_DEST"
[Unit]
Description=FLUXA - Nodo ${NODE_ID} (Core ${CORE})
After=network.target mariadb.service mysql.service
Wants=mariadb.service mysql.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=-${SCRIPT_DIR}/.env
ExecStart=${PYTHON_EXEC} ${SCRIPT_DIR}/main.py --topology 4_way --backend ${BACKEND} --headless --port ${PORT} --npu-core ${CORE}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=OPENCV_LOG_LEVEL=ERROR
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

  chmod 644 "$SVC_DEST"
  echo " Servicio ${SVC_NAME} creado."
done

echo " Recargando daemon de systemd..."
systemctl daemon-reload

for CORE in 0 1 2; do
  SVC_NAME="fluxa-node${CORE}.service"
  systemctl enable "$SVC_NAME"
  systemctl restart "$SVC_NAME"
done

echo "=========================================================================="
echo "Servicios FLUXA Tri-Core instalados y habilitados exitosamente en background."
echo "Los 3 cruces inician automáticamente al arrancar la Orange Pi (o servidor)."
echo " - Cruce 01 (Puerto 5000): sudo systemctl status fluxa-node0"
echo " - Cruce 02 (Puerto 5001): sudo systemctl status fluxa-node1"
echo " - Cruce 03 (Puerto 5002): sudo systemctl status fluxa-node2"
echo "Para detener el corredor entero: sudo systemctl stop fluxa-node{0..2}"
echo "=========================================================================="
