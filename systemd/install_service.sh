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

if [ "${DRY_RUN:-0}" != "1" ] && [ "$EUID" -ne 0 ]; then
  echo "Por favor ejecuta este script con privilegios root (sudo bash systemd/install_service.sh)"
  exit 1
fi

SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
TARGET_DEST="${SYSTEMD_DIR}/fluxa.target"

if [ -f "${SYSTEMD_DIR}/$SERVICE_NAME" ]; then
    echo "⚠️  Aviso: Se detectó un servicio monolítico previo en ${SYSTEMD_DIR}/$SERVICE_NAME."
    echo "   No se modificará ni eliminará automáticamente. Si desea utilizar la arquitectura Tri-Core,"
    echo "   se recomienda detener y deshabilitar el servicio anterior: sudo systemctl disable --now $SERVICE_NAME"
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

# Crear o verificar fluxa.target
TMP_TARGET=$(mktemp)
cat << 'EOF' > "$TMP_TARGET"
[Unit]
Description=FLUXA - Cluster de Control Semaforico Inteligente Tri-Core
Wants=fluxa-node0.service fluxa-node1.service fluxa-node2.service

[Install]
WantedBy=multi-user.target
EOF

if [ -f "$TARGET_DEST" ]; then
    if ! cmp -s "$TMP_TARGET" "$TARGET_DEST"; then
        BAK_TARGET="${TARGET_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
        echo "⚠️  Aviso: $TARGET_DEST ya existe y difiere. Conservando local. Respaldo: $BAK_TARGET"
        cp -a "$TARGET_DEST" "$BAK_TARGET"
    fi
    rm -f "$TMP_TARGET"
else
    mv "$TMP_TARGET" "$TARGET_DEST"
    chmod 644 "$TARGET_DEST"
    echo " Target central fluxa.target creado."
fi

for CORE in 0 1 2; do
  PORT=$((5000 + CORE))
  NODE_ID="CRUCE_0$((CORE + 1))"
  SVC_NAME="fluxa-node${CORE}.service"
  SVC_DEST="${SYSTEMD_DIR}/${SVC_NAME}"
  
  TMP_SVC=$(mktemp)
  cat << EOF > "$TMP_SVC"
[Unit]
Description=FLUXA - Nodo ${NODE_ID} (Core ${CORE})
PartOf=fluxa.target
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
TimeoutStopSec=15
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1
Environment=OPENCV_LOG_LEVEL=ERROR
LimitNOFILE=65536

[Install]
WantedBy=fluxa.target multi-user.target
EOF

  if [ -f "$SVC_DEST" ]; then
      if ! cmp -s "$TMP_SVC" "$SVC_DEST"; then
          BAK_SVC="${SVC_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
          echo "⚠️  Aviso: $SVC_DEST ya existe y difiere de la plantilla."
          echo "   No se sobreescribe para preservar ajustes locales. Respaldo registrado en: $BAK_SVC"
          cp -a "$SVC_DEST" "$BAK_SVC"
          rm -f "$TMP_SVC"
      else
          echo "ℹ️  Servicio ${SVC_NAME} ya instalado e idéntico."
          rm -f "$TMP_SVC"
      fi
  else
      mv "$TMP_SVC" "$SVC_DEST"
      chmod 644 "$SVC_DEST"
      echo " Servicio ${SVC_NAME} creado."
  fi
done

if [ "${DRY_RUN:-0}" != "1" ] && command -v systemctl &>/dev/null; then
    echo " Recargando daemon de systemd..."
    systemctl daemon-reload

    systemctl enable fluxa.target
    for CORE in 0 1 2; do
      SVC_NAME="fluxa-node${CORE}.service"
      systemctl enable "$SVC_NAME"
      systemctl restart "$SVC_NAME"
    done
fi

echo "=========================================================================="
echo "Servicios FLUXA Tri-Core instalados y habilitados exitosamente en background."
echo "Control centralizado via target:"
echo " - Iniciar todo el cluster:   sudo systemctl start fluxa.target"
echo " - Detener todo el cluster:   sudo systemctl stop fluxa.target"
echo " - Reiniciar todo el cluster: sudo systemctl restart fluxa.target"
echo "Control individual de cruces:"
echo " - Cruce 01 (Puerto 5000): sudo systemctl status fluxa-node0"
echo " - Cruce 02 (Puerto 5001): sudo systemctl status fluxa-node1"
echo " - Cruce 03 (Puerto 5002): sudo systemctl status fluxa-node2"
echo "=========================================================================="
