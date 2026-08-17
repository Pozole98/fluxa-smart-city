#!/usr/bin/env bash
# ==============================================================================
# FLUXA - Script de Instalación de Servicio Systemd para Orange Pi 5 / Linux Edge
# ==============================================================================
set -e

SERVICE_NAME="fluxa.service"
SERVICE_SRC="$(dirname "$(realpath "$0")")/$SERVICE_NAME"
SERVICE_DEST="/etc/systemd/system/$SERVICE_NAME"

echo "🚦 Instalando servicio $SERVICE_NAME en $SERVICE_DEST..."

if [ "$EUID" -ne 0 ]; then
  echo "⚠️ Por favor ejecuta este script con privilegios root (sudo ./install_service.sh)"
  exit 1
fi

cp "$SERVICE_SRC" "$SERVICE_DEST"
chmod 644 "$SERVICE_DEST"

echo "🔄 Recargando daemon de systemd..."
systemctl daemon-reload

echo "⚡ Habilitando servicio para auto-arranque al encender..."
systemctl enable "$SERVICE_NAME"

echo "🚀 Iniciando servicio FLUXA..."
systemctl restart "$SERVICE_NAME"

echo "✅ Servicio FLUXA instalado y corriendo exitosamente."
echo "Para verificar el estado ejecuta: sudo systemctl status $SERVICE_NAME"
echo "Para ver logs en tiempo real ejecuta: sudo journalctl -u $SERVICE_NAME -f"
