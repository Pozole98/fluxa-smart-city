#!/usr/bin/env bash
# ==============================================================================
#  FLUXA Smart Mobility • Script de Desinstalación
#  Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
# ==============================================================================

set -e

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_GREEN='\033[32m'
C_CYAN='\033[36m'

echo -e "${C_YELLOW}${C_BOLD}"
echo "======================================================================"
echo "   FLUXA SMART MOBILITY • DESINSTALADOR DEL SISTEMA"
echo "   TESCo • División de Ingeniería en Sistemas Computacionales"
echo "   Desarrollador Principal: Moisés Emilio Martínez Arias"
echo "======================================================================"
echo -e "${C_RESET}"

run_sudo() {
    if [ "$EUID" -ne 0 ]; then
        sudo "$@"
    else
        "$@"
    fi
}

# 1. Detener y Deshabilitar Servicio Systemd
echo -e "${C_CYAN}➡️  [1/4] Deteniendo y eliminando servicio systemd...${C_RESET}"
if [ -f /etc/systemd/system/fluxa.service ]; then
    run_sudo systemctl stop fluxa 2>/dev/null || true
    run_sudo systemctl disable fluxa 2>/dev/null || true
    run_sudo rm -f /etc/systemd/system/fluxa.service
    run_sudo systemctl daemon-reload
    echo -e "${C_GREEN}Servicio systemd eliminado.${C_RESET}"
else
    echo -e "${C_RESET}ℹ️  Servicio systemd no encontrado.${C_RESET}"
fi

# 2. Eliminar Wrapper Global en /usr/local/bin/fluxa
echo -e "${C_CYAN}➡️  [2/4] Eliminando comando global 'fluxa'...${C_RESET}"
if [ -f /usr/local/bin/fluxa ]; then
    run_sudo rm -f /usr/local/bin/fluxa
    echo -e "${C_GREEN}Acceso directo /usr/local/bin/fluxa eliminado.${C_RESET}"
fi

# 3. Preguntar si se desea eliminar el entorno virtual .venv
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/.venv" ]; then
    echo -e "\n${C_YELLOW}¿Deseas eliminar el entorno virtual de Python (.venv)? [s/N]:${C_RESET} "
    read -r resp
    if [[ "$resp" =~ ^[sSyY]$ ]]; then
        rm -rf "$SCRIPT_DIR/.venv"
        echo -e "${C_GREEN}Directorio .venv eliminado.${C_RESET}"
    fi
fi

# 4. Preguntar si se desea purgar la base de datos MariaDB
echo -e "\n${C_YELLOW}¿Deseas eliminar la base de datos 'fluxa_traffic' de MariaDB? (Se borrará el historial) [s/N]:${C_RESET} "
read -r resp_db
if [[ "$resp_db" =~ ^[sSyY]$ ]]; then
    MYSQL_EXEC="mysql"
    if ! command -v mysql &>/dev/null && command -v mariadb &>/dev/null; then
        MYSQL_EXEC="mariadb"
    fi
    run_sudo $MYSQL_EXEC -e "DROP DATABASE IF EXISTS fluxa_traffic; DROP USER IF EXISTS 'fluxa'@'localhost'; FLUSH PRIVILEGES;" 2>/dev/null || true
    echo -e "${C_GREEN}Base de datos 'fluxa_traffic' y usuario 'fluxa' eliminados.${C_RESET}"
fi

# 5. Limpieza de credenciales locales (.env e instance/)
echo -e "\n${C_YELLOW}¿Deseas eliminar credenciales locales (.env e instance/)? [s/N]:${C_RESET} "
read -r resp_creds
if [[ "$resp_creds" =~ ^[sSyY]$ ]]; then
    rm -f "$SCRIPT_DIR/.env"
    rm -rf "$SCRIPT_DIR/instance"
    echo -e "${C_GREEN}Archivos de credenciales locales eliminados.${C_RESET}"
fi

echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "   DESINSTALACIÓN DE FLUXA FINALIZADA CORRECTAMENTE"
echo "   TESCo • División de Ingeniería en Sistemas Computacionales"
echo "======================================================================"
echo -e "${C_RESET}\n"
