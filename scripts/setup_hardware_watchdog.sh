#!/usr/bin/env bash
# ==============================================================================
# FLUXA Smart Mobility • Configuración del Watchdog de Hardware (RK3588 / Linux)
# Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
# ==============================================================================
# Conecta el supervisor de Systemd con el temporizador físico del chip (/dev/watchdog).
# Si el kernel o el sistema operativo sufren un cuelgue crítico (Kernel Panic o
# congelamiento térmico en gabinete), el hardware resetea la placa automáticamente
# en 20 segundos para recuperar el cruce vial sin requerir técnico en sitio.
# ==============================================================================

set -Eeuo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[32m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_CYAN='\033[36m'

echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================"
echo "   FLUXA: CONFIGURACIÓN DE WATCHDOG DE HARDWARE (NIVEL KERNEL/SOC)"
echo "   Rockchip RK3588 (Orange Pi 5) / Linux Industrial"
echo "======================================================================"
echo -e "${C_RESET}"

if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && [ "$EUID" -ne 0 ]; then
    echo -e "${C_RED}❌ Este script requiere privilegios de root.${C_RESET}" >&2
    echo -e "   Ejecute: ${C_BOLD}sudo bash scripts/setup_hardware_watchdog.sh${C_RESET}" >&2
    exit 1
fi

WATCHDOG_DEV="/dev/watchdog"
if [ ! -e "$WATCHDOG_DEV" ] && [ -e "/dev/watchdog0" ]; then
    WATCHDOG_DEV="/dev/watchdog0"
fi

if [ -e "$WATCHDOG_DEV" ]; then
    echo -e "${C_GREEN} Dispositivo de watchdog de hardware detectado en: ${WATCHDOG_DEV}${C_RESET}"
else
    echo -e "${C_YELLOW}⚠️  Aviso: No se detectó ${WATCHDOG_DEV} en este equipo.${C_RESET}"
    echo -e "${C_YELLOW}   (Común en máquinas virtuales o entornos de prueba sin chip de hardware).${C_RESET}"
fi

CONF_DIR="/etc/systemd/system.conf.d"
CONF_FILE="${CONF_DIR}/10-fluxa-hardware-watchdog.conf"

if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    mkdir -p "$CONF_DIR"
    cat << 'EOF' > "$CONF_FILE"
# ==============================================================================
# FLUXA - Supervisión de Hardware a Nivel Kernel
# ==============================================================================
[Manager]
# Alimenta /dev/watchdog periódicamente. Si el kernel colapsa, resetea a los 20s.
RuntimeWatchdogSec=20s
# Tiempo máximo para apagados limpios antes de reset por hardware.
RebootWatchdogSec=5min
EOF

    chmod 644 "$CONF_FILE"
    echo -e "${C_GREEN} Configuración de supervisión registrada en: ${CONF_FILE}${C_RESET}"

    if command -v systemctl &>/dev/null; then
        systemctl daemon-reexec || systemctl daemon-reload
        echo -e "${C_GREEN} Supervisor Systemd recargado con watchdog de hardware activo.${C_RESET}"
    fi
else
    echo -e "${C_BLUE}ℹ️  [FLUXA_TEST_MODE] Simulación de configuración completada.${C_RESET}"
fi

echo -e "\n${C_GREEN}${C_BOLD}✅ Watchdog de hardware configurado exitosamente.${C_RESET}\n"
