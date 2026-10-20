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

if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && [ "$EUID" -ne 0 ]; then
  echo "Por favor ejecuta este script con privilegios root (sudo bash systemd/install_service.sh)"
  exit 1
fi

MIGRATE=0
for arg in "$@"; do
    if [ "$arg" = "--migrate" ]; then
        MIGRATE=1
    fi
done

SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
TARGET_DEST="${SYSTEMD_DIR}/fluxa.target"
MONOLITHIC_SVC="${SYSTEMD_DIR}/$SERVICE_NAME"
SHOULD_ENABLE=1

MONOLITHIC_DETECTED=0
if [ -f "$MONOLITHIC_SVC" ]; then
    MONOLITHIC_DETECTED=1
elif [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null || systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        MONOLITHIC_DETECTED=1
    fi
fi

if [ "$MONOLITHIC_DETECTED" -eq 1 ]; then
    if [ "$MIGRATE" -eq 1 ]; then
        if [ -f "$MONOLITHIC_SVC" ]; then
            BAK_MONO="${MONOLITHIC_SVC}.bak.$(date +%Y%m%d_%H%M%S)"
            echo "📦 Migración solicitada (--migrate): Respaldando ${MONOLITHIC_SVC} en ${BAK_MONO}..."
            cp -a "$MONOLITHIC_SVC" "$BAK_MONO"
        fi
        if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
            systemctl stop "$SERVICE_NAME" 2>/dev/null || true
            systemctl disable "$SERVICE_NAME" 2>/dev/null || true
            systemctl daemon-reload
        fi
        if [ -f "$MONOLITHIC_SVC" ]; then
            rm -f "$MONOLITHIC_SVC"
        fi
        echo " Servicio monolítico previo respaldado y desactivado. Procediendo con instalación Tri-Core."
    else
        echo "⚠️  Aviso: Se detectó un servicio monolítico fluxa.service preexistente (activo, habilitado o en ${MONOLITHIC_SVC})."
        echo "   Para evitar colisiones de puertos (5000) o conflictos de hardware entre cruces,"
        echo "   NO se instalarán, habilitarán ni arrancarán los servicios fluxa-node{0,1,2} ni fluxa.target."
        echo "   Para migrar automáticamente a Tri-Core respaldando la unit previa y activando los nodos, ejecute:"
        echo "     sudo bash systemd/install_service.sh --migrate"
        echo "   O alternativamente desde el instalador principal:"
        echo "     sudo bash install.sh --migrate"
        exit 0
    fi
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
Type=notify
NotifyAccess=all
WatchdogSec=15
TimeoutStartSec=60
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=-${SCRIPT_DIR}/.env
ExecStart=${PYTHON_EXEC} ${SCRIPT_DIR}/main.py --topology 4_way --backend ${BACKEND} --headless --port ${PORT} --npu-core ${CORE}
Restart=always
RestartSec=3
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

if [ "$SHOULD_ENABLE" -eq 1 ]; then
    if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
        echo " Recargando daemon de systemd..."
        systemctl daemon-reload

        systemctl enable fluxa.target
        for CORE in 0 1 2; do
          SVC_NAME="fluxa-node${CORE}.service"
          systemctl enable "$SVC_NAME"
          systemctl restart "$SVC_NAME"
        done
    fi
else
    echo "⚠️  Atención: No se habilitaron ni iniciaron los servicios Tri-Core porque existe $MONOLITHIC_SVC."
    echo "   Para proceder con la migración, ejecute: sudo bash systemd/install_service.sh --migrate"
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
