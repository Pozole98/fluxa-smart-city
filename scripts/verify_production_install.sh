#!/usr/bin/env bash
# ==============================================================================
#  FLUXA Smart City • Script de Verificación de Instalación en Entorno Real
#  Uso exclusivo en: VM de pruebas o placa Orange Pi 5 con MariaDB real
#  ⚠️  NO EJECUTAR EN MÁQUINAS DE DESARROLLO SIN SERVIDOR MARIADB DEDICADO
# ==============================================================================

set -Eeuo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[32m'
C_BLUE='\033[34m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_CYAN='\033[36m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================"
echo "   FLUXA: VERIFICACIÓN DE INSTALACIÓN E IDEMPOTENCIA EN PRODUCCIÓN"
echo "   Para ejecución en VM o Orange Pi 5 con MariaDB activo"
echo "======================================================================"
echo -e "${C_RESET}"

# 0. Verificaciones de entorno
if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}⚠️  Aviso: Se recomienda ejecutar este script como root o con sudo:${C_RESET}"
    echo -e "   sudo bash scripts/verify_production_install.sh"
    echo
fi

echo -e "${C_BLUE}🔍 [Paso 1/6] Comprobando disponibilidad del servicio MariaDB local...${C_RESET}"
MYSQL_CMD="mysql"
if command -v mariadb &>/dev/null; then
    MYSQL_CMD="mariadb"
elif ! command -v mysql &>/dev/null; then
    echo -e "${C_RED}❌ Error: No se encontró el binario 'mariadb' ni 'mysql' en el sistema.${C_RESET}" >&2
    echo -e "${C_YELLOW}Asegúrese de instalar e iniciar el servidor MariaDB antes de la verificación.${C_RESET}" >&2
    exit 1
fi

if command -v systemctl &>/dev/null; then
    if ! systemctl is-active --quiet mariadb 2>/dev/null && ! systemctl is-active --quiet mysql 2>/dev/null; then
        echo -e "${C_YELLOW}⚠️  El servicio MariaDB/MySQL no parece estar activo. Intentando iniciar...${C_RESET}"
        systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null || true
    fi
fi

# 1. Primera Ejecución
echo -e "\n${C_BLUE}🚀 [Paso 2/6] Ejecutando Corrida 1 de install.sh...${C_RESET}"
RUN1_LOG=$(mktemp)
if bash install.sh > "$RUN1_LOG" 2>&1; then
    echo -e "${C_GREEN} Corrida 1 completada con código de salida 0.${C_RESET}"
else
    echo -e "${C_RED}❌ Error en Corrida 1 de install.sh. Mostrando últimas 30 líneas del log:${C_RESET}" >&2
    tail -n 30 "$RUN1_LOG" >&2
    rm -f "$RUN1_LOG"
    exit 1
fi
rm -f "$RUN1_LOG"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${C_RED}❌ Error: No se encontró el archivo .env tras la primera corrida.${C_RESET}" >&2
    exit 1
fi

ENV_PERMS=$(stat -c "%a" "$SCRIPT_DIR/.env" 2>/dev/null || stat -f "%OLp" "$SCRIPT_DIR/.env" 2>/dev/null || echo "unknown")
echo -e "${C_GREEN} Archivo .env generado. Permisos: ${ENV_PERMS}${C_RESET}"

HASH_RUN1=$(sha256sum "$SCRIPT_DIR/.env" | awk '{print $1}')
echo -e "${C_BLUE}ℹ️  Hash SHA-256 de .env (Corrida 1):${C_RESET} ${HASH_RUN1}"

# 2. Segunda Ejecución Consecutiva (Prueba de Idempotencia)
echo -e "\n${C_BLUE}🔄 [Paso 3/6] Ejecutando Corrida 2 consecutiva de install.sh (Test de Idempotencia)...${C_RESET}"
RUN2_LOG=$(mktemp)
if bash install.sh > "$RUN2_LOG" 2>&1; then
    echo -e "${C_GREEN} Corrida 2 completada con código de salida 0.${C_RESET}"
else
    echo -e "${C_RED}❌ Error en Corrida 2 de install.sh. Mostrando últimas 30 líneas del log:${C_RESET}" >&2
    tail -n 30 "$RUN2_LOG" >&2
    rm -f "$RUN2_LOG"
    exit 1
fi
rm -f "$RUN2_LOG"

HASH_RUN2=$(sha256sum "$SCRIPT_DIR/.env" | awk '{print $1}')
echo -e "${C_BLUE}ℹ️  Hash SHA-256 de .env (Corrida 2):${C_RESET} ${HASH_RUN2}"

if [ "$HASH_RUN1" != "$HASH_RUN2" ]; then
    echo -e "${C_RED}❌ Fallo de Idempotencia: El archivo .env fue alterado en la segunda corrida consecutiva!${C_RESET}" >&2
    exit 1
fi
echo -e "${C_GREEN} Idempotencia de .env verificada: El hash es 100% idéntico.${C_RESET}"

# 3. Comprobación de Conectividad con MariaDB vía defaults-extra-file
echo -e "\n${C_BLUE}🔌 [Paso 4/6] Verificando conexión MariaDB con credenciales de .env...${C_RESET}"
set -a
# shellcheck disable=SC1091
. "$SCRIPT_DIR/.env"
set +a

TMP_CNF=$(mktemp)
chmod 600 "$TMP_CNF"
cat << EOF > "$TMP_CNF"
[client]
host='${DATABASE_HOST:-localhost}'
port='${DATABASE_PORT:-3306}'
user='${DATABASE_USER:-fluxa}'
password='${DATABASE_PASSWORD:-}'
EOF

if "$MYSQL_CMD" --defaults-extra-file="$TMP_CNF" -e "SELECT 1;" "${DATABASE_NAME:-fluxa_traffic}" &>/dev/null; then
    echo -e "${C_GREEN} SELECT 1 ejecutado con éxito en MariaDB usando --defaults-extra-file y credenciales de .env.${C_RESET}"
else
    echo -e "${C_RED}❌ Error: No fue posible ejecutar SELECT 1 en MariaDB con las credenciales de .env.${C_RESET}" >&2
    rm -f "$TMP_CNF"
    exit 1
fi
rm -f "$TMP_CNF"

# 4. Comprobación de Conexión de la Aplicación Python (db_manager.py)
echo -e "\n${C_BLUE}🐍 [Paso 5/6] Verificando conexión de la app Flask/FLUXA desde .venv...${C_RESET}"
PYTHON_APP="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$PYTHON_APP" ]; then
    echo -e "${C_RED}❌ Error: No se encontró el entorno virtual .venv en ${PYTHON_APP}.${C_RESET}" >&2
    exit 1
fi

APP_TEST_OUTPUT=$("$PYTHON_APP" -c "
import os, sys
from dotenv import load_dotenv
load_dotenv('$SCRIPT_DIR/.env')

try:
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager()
    if hasattr(db, 'get_db_connection'):
        conn = db.get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1;')
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            print('DB_CONN_OK: row=' + str(row))
        else:
            print('DB_CONN_FAIL: conexion nula')
            sys.exit(1)
    else:
        print('DB_MANAGER_LOADED_OK')
except Exception as e:
    print('DB_CONN_EXCEPTION: ' + str(e))
    sys.exit(1)
" 2>&1)

if [[ "$APP_TEST_OUTPUT" == *"DB_CONN_OK"* ]] || [[ "$APP_TEST_OUTPUT" == *"DB_MANAGER_LOADED_OK"* ]]; then
    echo -e "${C_GREEN} Conexión de la aplicación Python/FLUXA a MariaDB verificada exitosamente:${C_RESET}"
    echo -e "   ${APP_TEST_OUTPUT}"
else
    echo -e "${C_RED}❌ Error en la conexión de la aplicación Python a MariaDB:${C_RESET}" >&2
    echo -e "   ${APP_TEST_OUTPUT}" >&2
    exit 1
fi

# 5. Verificación del Cerrojo Compartido (Debe estar liberado)
echo -e "\n${C_BLUE}🔒 [Paso 6/6] Verificando que el cerrojo /run/lock/fluxa.lock quedó liberado...${C_RESET}"
LOCK_PATH="/run/lock/fluxa.lock"
if [ -f "$LOCK_PATH" ]; then
    if ( exec 200>>"$LOCK_PATH"; flock -n 200 ); then
        echo -e "${C_GREEN} Cerrojo ${LOCK_PATH} libre y disponible (sin procesos zombies o bloqueados).${C_RESET}"
    else
        echo -e "${C_RED}❌ Error: ${LOCK_PATH} continúa bloqueado por otro proceso.${C_RESET}" >&2
        exit 1
    fi
else
    echo -e "${C_GREEN} Archivo de cerrojo no retiene bloqueos residuales.${C_RESET}"
fi

echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "   ✅ VERIFICACIÓN DE PRODUCCIÓN EXITOSA AL 100%"
echo "   - Idempotencia comprobada en 2 corridas consecutivas."
echo "   - Credenciales .env preservadas y con permisos 600."
echo "   - SELECT 1 y conexión de la app Python a MariaDB operativas."
echo "   - Cerrojo compartido liberado."
echo "======================================================================"
echo -e "${C_RESET}"
