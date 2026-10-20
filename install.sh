#!/usr/bin/env bash
# ==============================================================================
#  FLUXA Smart Mobility • Script de Instalación Automatizada e Idempotente
#  Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
#  Compatible con: Armbian 24.04 (Orange Pi 5, RK3588), openSUSE, Fedora, Ubuntu, Debian
# ==============================================================================

set -Eeuo pipefail

# Colores y Formato
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[32m'
C_BLUE='\033[34m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_CYAN='\033[36m'

echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================"
echo "   FLUXA: SISTEMA DE CONTROL SEMAFÓRICO INTELIGENTE Y TELEMETRÍA EDGE"
echo "   INSTALADOR AUTOMATIZADO DE PRODUCCIÓN (EDGE & NATIVE)"
echo "   TESCo • División de Ingeniería en Sistemas Computacionales"
echo "   Desarrollador Principal: Moisés Emilio Martínez Arias"
echo "======================================================================"
echo -e "${C_RESET}"

# Directorio de FLUXA y variables base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"
CURRENT_HOME=$(eval echo "~$CURRENT_USER")
ARCH=$(uname -m)

# ------------------------------------------------------------------------------
# 0. Definición de run_sudo y Verificación de Seguridad de FLUXA_TEST_MODE
# ------------------------------------------------------------------------------
if [ "${FLUXA_TEST_MODE:-0}" = "1" ]; then
    CANONICAL_SCRIPT_DIR=$(readlink -f "$SCRIPT_DIR" 2>/dev/null || echo "$SCRIPT_DIR")
    if [[ "$CANONICAL_SCRIPT_DIR" != /tmp/* ]] && [[ "$CANONICAL_SCRIPT_DIR" != */scratch/* ]]; then
        echo -e "${C_RED}❌ Error de seguridad: FLUXA_TEST_MODE=1 solo está permitido en directorios temporales (/tmp/ o scratch/).${C_RESET}" >&2
        echo -e "${C_RED}   Directorio actual no temporal: ${CANONICAL_SCRIPT_DIR}${C_RESET}" >&2
        exit 1
    fi
    # En modo de prueba en sandbox, run_sudo ejecuta los comandos directamente sin sudo
    # y sin silenciar errores, de modo que cualquier falla real sea visible.
    run_sudo() {
        "$@"
    }
else
    run_sudo() {
        if [ "$EUID" -ne 0 ]; then
            sudo "$@"
        else
            "$@"
        fi
    }
fi

is_interactive() {
    [ -t 0 ] && [ "${FLUXA_TEST_MODE:-0}" != "1" ]
}

# Manejo de archivos temporales y subprocesos
TMP_FILES=()
SUDO_KEEP_PID=""
cleanup() {
    if [ -n "$SUDO_KEEP_PID" ]; then
        kill "$SUDO_KEEP_PID" 2>/dev/null || true
    fi
    for f in ${TMP_FILES+"${TMP_FILES[@]}"}; do
        if [ -n "$f" ] && [ -f "$f" ]; then
            rm -f "$f" || true
        fi
    done
    return 0
}
trap cleanup EXIT

# ------------------------------------------------------------------------------
# 1. Cerrojo de Exclusión Mutua Compartido (/run/lock/fluxa.lock)
# ------------------------------------------------------------------------------
LOCK_FILE="/run/lock/fluxa.lock"
if [ "${FLUXA_TEST_MODE:-0}" = "1" ] && [ -n "${LOCK_FILE_OVERRIDE:-}" ]; then
    LOCK_FILE="$LOCK_FILE_OVERRIDE"
fi
LOCK_DIR="$(dirname "$LOCK_FILE")"
if [ ! -d "$LOCK_DIR" ]; then
    run_sudo mkdir -p "$LOCK_DIR"
fi
if [ ! -f "$LOCK_FILE" ]; then
    run_sudo touch "$LOCK_FILE"
    run_sudo chmod 666 "$LOCK_FILE"
fi

CANONICAL_LOCK_FILE=$(readlink -f "$LOCK_FILE" 2>/dev/null || echo "$LOCK_FILE")
FD200_TARGET=$(readlink -f /proc/self/fd/200 2>/dev/null || true)

LOCK_ACQUIRED=0
if [ "${FLUXA_LOCK_HELD:-0}" = "1" ] && [ -n "$FD200_TARGET" ] && [ "$FD200_TARGET" = "$CANONICAL_LOCK_FILE" ]; then
    # Verificar con flock -n 200 que el descriptor realmente sostiene el cerrojo
    if flock -n 200; then
        echo -e "${C_BLUE}ℹ️  Lock de FLUXA heredado y verificado vía fd 200 ($LOCK_FILE).${C_RESET}"
        LOCK_ACQUIRED=1
    fi
fi

if [ "$LOCK_ACQUIRED" -eq 0 ]; then
    # Abrir con >> (append) sin truncar el archivo existente
    exec 200>>"$LOCK_FILE"
    if ! flock -n 200; then
        echo -e "${C_RED}❌ Error: Ya existe un proceso de instalación o actualización de FLUXA en ejecución.${C_RESET}" >&2
        echo -e "${C_YELLOW}Archivo de bloqueo ocupado: ${LOCK_FILE}${C_RESET}" >&2
        exit 1
    fi
    export FLUXA_LOCK_HELD=1
    echo -e "${C_BLUE}ℹ️  Cerrojo de instalación adquirido exitosamente en: ${LOCK_FILE}${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 2. Elevación de Privilegios (sudo)
# ------------------------------------------------------------------------------
if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}🔑 Se requieren permisos de administrador (sudo) para paquetes de sistema y hardware.${C_RESET}"
    sudo -v
    # Mantener sudo activo en segundo plano cerrando explícitamente fd 200 para no retener el cerrojo
    ( while true; do sudo -n true; sleep 60; kill -0 "$$" 2>/dev/null || exit 0; done ) 200>&- 2>/dev/null &
    SUDO_KEEP_PID=$!
fi

echo -e "${C_BLUE}ℹ️  Usuario destino:${C_RESET} ${CURRENT_USER}"
echo -e "${C_BLUE}ℹ️  Directorio de FLUXA:${C_RESET} ${SCRIPT_DIR}"
echo -e "${C_BLUE}ℹ️  Arquitectura detectada:${C_RESET} ${ARCH}"

# Detección de distribución
DISTRO_ID="unknown"
if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
    echo -e "${C_BLUE}ℹ️  Sistema Operativo:${C_RESET} ${NAME:-Linux} (${DISTRO_ID})"
fi

# ------------------------------------------------------------------------------
# 3. Estructura de Directorios Esencial y Configuración
# ------------------------------------------------------------------------------
mkdir -p "$SCRIPT_DIR/instance" \
         "$SCRIPT_DIR/data/calibration_images" \
         "$SCRIPT_DIR/logs/violations" \
         "$SCRIPT_DIR/videos" \
         "$SCRIPT_DIR/models" \
         "$SCRIPT_DIR/logos" \
         "$SCRIPT_DIR/static/logos"

if [ ! -f "$SCRIPT_DIR/config.json" ] && [ -f "$SCRIPT_DIR/config.example.json" ]; then
    cp "$SCRIPT_DIR/config.example.json" "$SCRIPT_DIR/config.json"
    echo -e "${C_GREEN} Plantilla base config.json inicializada desde config.example.json.${C_RESET}"
elif [ -f "$SCRIPT_DIR/config.json" ]; then
    echo -e "${C_BLUE}ℹ️  Archivo config.json existente conservado intacto.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 4. Instalación de Dependencias del Sistema
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW} [1/6] Verificando dependencias del sistema operativo (Python, MariaDB, OCR, OpenCV)...${C_RESET}"

if [ "${FLUXA_TEST_MODE:-0}" = "1" ]; then
    echo -e "${C_CYAN}➡️  [FLUXA_TEST_MODE] Omitiendo gestor de paquetes de sistema.${C_RESET}"
elif command -v zypper &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via ZYPPER (openSUSE / SLES)...${C_RESET}"
    run_sudo zypper --non-interactive refresh || true
    SUSE_PKGS="mariadb mariadb-client Mesa-libGL1 libglib-2_0-0 libgthread-2_0-0 v4l-utils curl git udev openssl gcc gcc-c++ tesseract-ocr tesseract-ocr-traineddata-eng tesseract-ocr-traineddata-spa"
    PY_CANDIDATES="python3-devel python3-pip python3-tk python3-virtualenv python313-devel python312-devel python311-devel"
    PKGS_TO_INSTALL="$SUSE_PKGS"
    for candidate in $PY_CANDIDATES; do
        if zypper se -s --match-exact "$candidate" 2>/dev/null | grep -q " paquete "; then
            PKGS_TO_INSTALL="$PKGS_TO_INSTALL $candidate"
        fi
    done
    run_sudo zypper --non-interactive install -y $PKGS_TO_INSTALL
elif command -v dnf &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via DNF (Fedora / RHEL)...${C_RESET}"
    run_sudo dnf install -y python3 python3-pip python3-devel python3-tkinter mesa-libGL glib2 mariadb-server mariadb v4l-utils curl git udev openssl tesseract tesseract-langpack-eng tesseract-langpack-spa
elif command -v apt-get &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via APT (Ubuntu / Debian / Armbian)...${C_RESET}"
    run_sudo apt-get update -y
    run_sudo apt-get install -y python3 python3-pip python3-venv python3-dev python3-tk libgl1 libglib2.0-0 mariadb-server mariadb-client v4l-utils curl git udev openssl tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa
else
    echo -e "${C_YELLOW}⚠️  Gestor de paquetes no reconocido automáticamente. Verifique que Python 3, MariaDB y OpenCV estén instalados.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 5. Reglas Udev para Hardware Edge (Arduino, Cámaras, NPU RK3588)
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW} [2/6] Verificando reglas de hardware udev (Arduino, Cámaras, NPU)...${C_RESET}"

UDEV_RULES_FILE="${UDEV_RULES_FILE:-/etc/udev/rules.d/99-fluxa-hardware.rules}"
TMP_UDEV=$(mktemp)
TMP_FILES+=("$TMP_UDEV")

cat << 'EOF' > "$TMP_UDEV"
# Reglas de acceso sin root para FLUXA Smart City
# Microcontroladores Arduino y adaptadores Serial USB
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"

# Cámaras de video V4L2
KERNEL=="video*", MODE="0666", GROUP="video"

# Acelerador NPU Rockchip RK3588 (Orange Pi 5)
KERNEL=="rknpu*", MODE="0666"
EOF

if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    if [ -f "$UDEV_RULES_FILE" ]; then
        if ! cmp -s "$TMP_UDEV" "$UDEV_RULES_FILE"; then
            BAK_UDEV="${UDEV_RULES_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
            echo -e "${C_YELLOW}⚠️  Aviso: $UDEV_RULES_FILE ya existe y difiere. Guardando respaldo: $BAK_UDEV${C_RESET}"
            run_sudo cp -a "$UDEV_RULES_FILE" "$BAK_UDEV"
            run_sudo mv "$TMP_UDEV" "$UDEV_RULES_FILE"
            run_sudo chmod 644 "$UDEV_RULES_FILE"
        else
            echo -e "${C_GREEN} Reglas udev ya instaladas e idénticas.${C_RESET}"
            rm -f "$TMP_UDEV"
        fi
    else
        run_sudo mv "$TMP_UDEV" "$UDEV_RULES_FILE"
        run_sudo chmod 644 "$UDEV_RULES_FILE"
        echo -e "${C_GREEN} Reglas udev instaladas en ${UDEV_RULES_FILE}.${C_RESET}"
    fi

    if command -v udevadm &>/dev/null; then
        run_sudo udevadm control --reload-rules || true
        run_sudo udevadm trigger || true
    fi

    for grp in dialout uucp video render; do
        if grep -q "^${grp}:" /etc/group 2>/dev/null; then
            run_sudo usermod -a -G "$grp" "$CURRENT_USER" 2>/dev/null || true
        fi
    done
else
    rm -f "$TMP_UDEV"
fi

# ------------------------------------------------------------------------------
# 6. Entorno Virtual Python (.venv) Idempotente y Robusto
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW} [3/6] Configurando entorno virtual Python aislado (.venv)...${C_RESET}"

VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${C_CYAN}➡️  Creando entorno virtual en ${VENV_DIR}...${C_RESET}"
    if ! python3 -m venv "$VENV_DIR"; then
        echo -e "${C_RED}❌ Error crítico: Falló la creación del entorno virtual .venv.${C_RESET}" >&2
        echo -e "${C_YELLOW}Asegúrate de tener instalado python3-venv o python3-virtualenv en el sistema.${C_RESET}" >&2
        exit 1
    fi
    echo -e "${C_GREEN} Entorno virtual creado exitosamente.${C_RESET}"
else
    echo -e "${C_GREEN} Entorno virtual .venv existente detectado. Conservando.${C_RESET}"
fi

PIP_CMD="$VENV_DIR/bin/pip"
PYTHON_CMD="$VENV_DIR/bin/python3"

if [ ! -f "$PIP_CMD" ] || [ ! -f "$PYTHON_CMD" ]; then
    echo -e "${C_RED}❌ Error: Los binarios del entorno virtual ($PIP_CMD / $PYTHON_CMD) no son válidos.${C_RESET}" >&2
    exit 1
fi

if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    echo -e "${C_CYAN}➡️  Actualizando herramientas de empaquetado (pip, setuptools, wheel)...${C_RESET}"
    "$PIP_CMD" install --upgrade pip setuptools wheel --quiet
    echo -e "${C_CYAN}➡️  Verificando/instalando requerimientos de FLUXA desde requirements.txt...${C_RESET}"
    "$PIP_CMD" install -r "$SCRIPT_DIR/requirements.txt" --quiet
    echo -e "${C_GREEN} Dependencias de IA, visión y base de datos listas en .venv.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 7. Base de Datos MariaDB y Configuración Atómica de .env
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW} [4/6] Verificando Base de Datos MariaDB y archivo .env...${C_RESET}"

ENV_FILE="$SCRIPT_DIR/.env"
MYSQL_EXEC="mysql"
if command -v mariadb &>/dev/null; then
    MYSQL_EXEC="mariadb"
fi

# Función de validación de contraseñas: rechaza comillas simples, barras invertidas, saltos de línea y caracteres de control/NUL
validate_db_password() {
    local pass="$1"
    if [ -z "$pass" ]; then
        return 1
    fi
    if [[ "$pass" == *"'"* ]]; then
        echo -e "${C_RED}❌ La contraseña no puede contener comillas simples (').${C_RESET}" >&2
        return 1
    fi
    if [[ "$pass" == *"\\"* ]]; then
        echo -e "${C_RED}❌ La contraseña no puede contener barras invertidas (\\).${C_RESET}" >&2
        return 1
    fi
    # Rechazar caracteres de control (\x00 a \x1f y \x7f), incluyendo salto de línea y tabuladores
    if [[ "$pass" =~ [$'\r\n\t\x00-\x1F\x7F'] ]]; then
        echo -e "${C_RED}❌ La contraseña contiene caracteres de control o saltos de línea no permitidos.${C_RESET}" >&2
        return 1
    fi
    return 0
}

# Inicializar servicio MariaDB/MySQL si systemd está activo
if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
    run_sudo systemctl enable mariadb 2>/dev/null || run_sudo systemctl enable mysql 2>/dev/null || true
    run_sudo systemctl start mariadb 2>/dev/null || run_sudo systemctl start mysql 2>/dev/null || true
fi

DB_RECONFIG_NEEDED=1
DB_PASS=""
DB_HOST="localhost"
DB_USER="fluxa"
DB_NAME="fluxa_traffic"
DB_PORT="3306"

# Verificar si ya existe .env y si sus credenciales son funcionales
if [ -f "$ENV_FILE" ]; then
    # Extraer valores de forma segura sin ejecutar `source`
    EXISTING_PASS=$(grep -E '^[[:space:]]*DATABASE_PASSWORD=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | sed -e "s/^[[:space:]]*['\"]//" -e "s/['\"][[:space:]]*$//")
    EXISTING_USER=$(grep -E '^[[:space:]]*DATABASE_USER=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | sed -e "s/^[[:space:]]*['\"]//" -e "s/['\"][[:space:]]*$//")
    EXISTING_DB=$(grep -E '^[[:space:]]*DATABASE_NAME=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | sed -e "s/^[[:space:]]*['\"]//" -e "s/['\"][[:space:]]*$//")
    EXISTING_HOST=$(grep -E '^[[:space:]]*DATABASE_HOST=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | sed -e "s/^[[:space:]]*['\"]//" -e "s/['\"][[:space:]]*$//")
    EXISTING_PORT=$(grep -E '^[[:space:]]*DATABASE_PORT=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | sed -e "s/^[[:space:]]*['\"]//" -e "s/['\"][[:space:]]*$//")

    EXISTING_USER="${EXISTING_USER:-fluxa}"
    EXISTING_DB="${EXISTING_DB:-fluxa_traffic}"
    EXISTING_HOST="${EXISTING_HOST:-localhost}"
    EXISTING_PORT="${EXISTING_PORT:-3306}"

    echo -e "${C_BLUE}ℹ️  Instalación previa detectada (.env encontrado). Comprobando conectividad...${C_RESET}"

    # Sondeo mediante --defaults-extra-file temporal con permisos 600 y comillas simples
    TMP_EXTRA_CNF=$(mktemp)
    TMP_FILES+=("$TMP_EXTRA_CNF")
    chmod 600 "$TMP_EXTRA_CNF"
    cat << EOF > "$TMP_EXTRA_CNF"
[client]
host='${EXISTING_HOST}'
port='${EXISTING_PORT}'
user='${EXISTING_USER}'
password='${EXISTING_PASS}'
EOF

    CAN_CONNECT=0
    if command -v "$MYSQL_EXEC" &>/dev/null; then
        if "$MYSQL_EXEC" --defaults-extra-file="$TMP_EXTRA_CNF" -e "SELECT 1;" "$EXISTING_DB" &>/dev/null; then
            CAN_CONNECT=1
        fi
    fi
    rm -f "$TMP_EXTRA_CNF"

    if [ "$CAN_CONNECT" -eq 1 ]; then
        echo -e "${C_GREEN} Conexión a MariaDB verificada exitosamente con las credenciales existentes en .env.${C_RESET}"
        if is_interactive && [ "${FORCE_RECONFIG:-0}" != "1" ]; then
            echo -e "${C_CYAN}¿Deseas mantener la configuración y base de datos actual? [S/n]:${C_RESET} "
            read -r KEEP_ENV_CHOICE || KEEP_ENV_CHOICE="S"
            if [[ "$KEEP_ENV_CHOICE" =~ ^[Nn] ]]; then
                DB_RECONFIG_NEEDED=1
            else
                DB_RECONFIG_NEEDED=0
                echo -e "${C_GREEN} Conservando .env y credenciales existentes sin modificaciones.${C_RESET}"
            fi
        else
            DB_RECONFIG_NEEDED=0
            echo -e "${C_GREEN} Modo no-interactivo: Conservando .env existente de forma idempotente.${C_RESET}"
        fi
    else
        echo -e "${C_RED}❌ Error crítico: Se detectó un archivo .env previo en ${ENV_FILE} pero la prueba de conexión a MariaDB (SELECT 1) falló.${C_RESET}" >&2
        echo -e "${C_YELLOW}   Para evitar pérdida de consistencia o acceso a la base de datos, el instalador no regenerará .env.${C_RESET}" >&2
        echo -e "${C_YELLOW}   Verifique que el servicio MariaDB esté activo y las credenciales sean válidas.${C_RESET}" >&2
        exit 1
    fi
fi

if [ "$DB_RECONFIG_NEEDED" -eq 1 ]; then
    echo -e "${C_CYAN}➡️  Configurando usuario y base de datos en MariaDB...${C_RESET}"
    
    # Obtener o solicitar contraseña válida
    while true; do
        if [ -n "${DATABASE_PASSWORD:-}" ]; then
            CANDIDATE_PASS="$DATABASE_PASSWORD"
        elif is_interactive; then
            echo -e "${C_CYAN}Ingresa la contraseña para el usuario MariaDB 'fluxa' (o presiona ENTER para generar una aleatoria segura):${C_RESET} "
            read -s -r USER_PASS_INPUT
            echo
            if [ -n "$USER_PASS_INPUT" ]; then
                CANDIDATE_PASS="$USER_PASS_INPUT"
            else
                CANDIDATE_PASS=$(openssl rand -hex 16 2>/dev/null || date +%s%N | sha256sum | head -c 24)
                echo -e "${C_BLUE}ℹ️  Contraseña aleatoria generada de forma segura.${C_RESET}"
            fi
        else
            CANDIDATE_PASS=$(openssl rand -hex 16 2>/dev/null || date +%s%N | sha256sum | head -c 24)
            echo -e "${C_BLUE}ℹ️  Contraseña aleatoria generada automáticamente (modo no-interactivo).${C_RESET}"
        fi

        if validate_db_password "$CANDIDATE_PASS"; then
            DB_PASS="$CANDIDATE_PASS"
            break
        else
            if ! is_interactive; then
                echo -e "${C_RED}❌ Error: Contraseña inválida en modo no-interactivo.${C_RESET}" >&2
                exit 1
            fi
            echo -e "${C_YELLOW}Por favor ingresa una contraseña que cumpla con los requisitos.${C_RESET}"
            DATABASE_PASSWORD=""
        fi
    done

    # Aplicar configuración a MariaDB vía STDIN (sin -e para no exponer credenciales en la tabla de procesos)
    if command -v "$MYSQL_EXEC" &>/dev/null; then
        run_sudo "$MYSQL_EXEC" <<EOF
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
EOF
        echo -e "${C_GREEN} Base de datos '${DB_NAME}' y usuario '${DB_USER}' configurados en MariaDB.${C_RESET}"
    fi

    # Escribir .env de forma atómica con comillas simples (compatible con source y EnvironmentFile)
    TMP_ENV=$(mktemp)
    TMP_FILES+=("$TMP_ENV")
    cat << EOF > "$TMP_ENV"
DATABASE_HOST='${DB_HOST}'
DATABASE_USER='${DB_USER}'
DATABASE_PASSWORD='${DB_PASS}'
DATABASE_NAME='${DB_NAME}'
DATABASE_PORT='${DB_PORT}'
EOF
    chmod 600 "$TMP_ENV"
    mv -f "$TMP_ENV" "$ENV_FILE"
    echo -e "${C_GREEN} Archivo .env generado atómicamente con permisos 600 (valores entre comillas simples).${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 8. Credenciales de Administrador C5 (instance/admin_credentials.json)
# ------------------------------------------------------------------------------
ADMIN_CRED_FILE="$SCRIPT_DIR/instance/admin_credentials.json"
if [ ! -f "$ADMIN_CRED_FILE" ]; then
    echo -e "\n${C_BLUE}🔑 Configurando credenciales de Operador Administrador C5...${C_RESET}"
    if is_interactive; then
        "$PYTHON_CMD" "$SCRIPT_DIR/scripts/set_admin_password.py"
    else
        AUTO_ADMIN_PASS=$(openssl rand -hex 10 2>/dev/null || date +%s%N | sha256sum | head -c 20)
        PASS_BACKUP_FILE="$SCRIPT_DIR/instance/.admin_initial_pass"
        echo "$AUTO_ADMIN_PASS" > "$PASS_BACKUP_FILE"
        chmod 600 "$PASS_BACKUP_FILE"
        if [ -n "${SUDO_USER:-}" ]; then
            chown "$CURRENT_USER:" "$PASS_BACKUP_FILE" 2>/dev/null || true
        fi
        
        echo "$AUTO_ADMIN_PASS" | "$PYTHON_CMD" "$SCRIPT_DIR/scripts/set_admin_password.py" --username admin --password-stdin --force
        echo -e "${C_GREEN} Contraseña inicial de Administrador C5 generada y almacenada en:${C_RESET} ${PASS_BACKUP_FILE}"
    fi
else
    echo -e "${C_GREEN} Credenciales de Administrador C5 ya existentes. Conservadas.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 9. Aceleración NPU Rockchip RK3588 (rknn-toolkit-lite2 en aarch64)
# ------------------------------------------------------------------------------
if [ "$ARCH" = "aarch64" ]; then
    echo -e "\n${C_BLUE} Verificando soporte para NPU Rockchip RK3588 (rknn-toolkit-lite2)...${C_RESET}"
    
    if "$PYTHON_CMD" -c "from rknnlite.api import RKNNLite" 2>/dev/null; then
        echo -e "${C_GREEN} Módulo rknnlite ya instalado y operativo en .venv.${C_RESET}"
    else
        PY_VER=$("$PYTHON_CMD" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
        TARGET_WHL="$SCRIPT_DIR/wheels/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
        
        if [ -f "$TARGET_WHL" ]; then
            echo -e "${C_CYAN}➡️  Instalando paquete oficial de Rockchip local: $(basename "$TARGET_WHL")...${C_RESET}"
            "$PIP_CMD" install "$TARGET_WHL" --quiet
        else
            ALT_WHL=$(find "$SCRIPT_DIR" "$SCRIPT_DIR/.." /home /opt -name "*rknn_toolkit_lite2*cp${PY_VER}*aarch64.whl" 2>/dev/null | head -n 1 || true)
            if [ -n "$ALT_WHL" ] && [ -f "$ALT_WHL" ]; then
                echo -e "${C_CYAN}➡️  Instalando paquete alternativo encontrado: ${ALT_WHL}...${C_RESET}"
                "$PIP_CMD" install "$ALT_WHL" --quiet
            else
                echo -e "${C_YELLOW}⬇️ Descargando wheel oficial de Rockchip para Python ${PY_VER}...${C_RESET}"
                WHL_URL="https://github.com/airockchip/rknn-toolkit2/raw/master/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
                TMP_WHL=$(mktemp --suffix=.whl)
                TMP_FILES+=("$TMP_WHL")
                if curl -fsSL "$WHL_URL" -o "$TMP_WHL" 2>/dev/null; then
                    "$PIP_CMD" install "$TMP_WHL" --quiet || true
                fi
            fi
        fi

        if "$PYTHON_CMD" -c "from rknnlite.api import RKNNLite" 2>/dev/null; then
            echo -e "${C_GREEN} Soporte de NPU Rockchip RK3588 (rknnlite) verificado y activo.${C_RESET}"
        else
            echo -e "${C_YELLOW}⚠️  Aviso: rknnlite no pudo cargarse en este momento. El sistema operará con CPU de respaldo.${C_RESET}"
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 10. Acceso Directo Global CLI 'fluxa' (/usr/local/bin/fluxa)
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW} [5/6] Verificando comando global CLI 'fluxa'...${C_RESET}"

WRAPPER_PATH="/usr/local/bin/fluxa"
TMP_WRAPPER=$(mktemp)
TMP_FILES+=("$TMP_WRAPPER")

cat << 'EOF' > "$TMP_WRAPPER"
#!/usr/bin/env bash
# ==============================================================================
# FLUXA Smart Mobility • CLI Global de Control y Operación Edge
# Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
# ==============================================================================
set -e

SCRIPT_DIR_PATH="__INSTALL_DIR__"

show_help() {
    echo "FLUXA Smart Mobility • Consola Global de Control"
    echo ""
    echo "Subcomandos de Gestión del Ciclo de Vida:"
    echo "  fluxa update [opciones]    Actualiza el sistema con snapshot, migraciones y rollback automático"
    echo "  fluxa check                Verifica si existen actualizaciones remotas o migraciones pendientes"
    echo "  fluxa rollback [opciones]  Revierte al snapshot de seguridad anterior"
    echo "  fluxa version              Muestra la versión del sistema, commit y arquitectura"
    echo "  fluxa status               Muestra el estado de los servicios de control semafórico"
    echo "  fluxa start                Inicia el servicio en segundo plano (fluxa.target)"
    echo "  fluxa stop                 Detiene el servicio en segundo plano"
    echo "  fluxa restart              Reinicia el servicio en segundo plano"
    echo "  fluxa logs                 Monitorea en tiempo real los registros de auditoría y visión"
    echo ""
    echo "Ejecución Directa de la Aplicación:"
    echo "  fluxa --topology 4_way --backend rknn --headless --port 5000"
    echo "  fluxa --topology 4_way --backend cpu --gui"
    echo "  (Cualquier argumento no reconocido como subcomando se reenvía a main.py)"
}

SUBCOMMAND="${1:-}"

case "$SUBCOMMAND" in
    update)
        shift
        cd "$SCRIPT_DIR_PATH" || exit 1
        exec sudo bash "$SCRIPT_DIR_PATH/update.sh" "$@"
        ;;
    check)
        shift
        cd "$SCRIPT_DIR_PATH" || exit 1
        exec bash "$SCRIPT_DIR_PATH/update.sh" --check "$@"
        ;;
    rollback)
        shift
        cd "$SCRIPT_DIR_PATH" || exit 1
        exec sudo bash "$SCRIPT_DIR_PATH/update.sh" --rollback "$@"
        ;;
    version)
        cd "$SCRIPT_DIR_PATH" || exit 1
        COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "release")
        BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
        TAG=$(git describe --tags --exact-match 2>/dev/null || echo "sin-tag")
        echo "FLUXA Smart City • Versión Edge"
        echo " - Commit:       $COMMIT"
        echo " - Rama / Tag:   $BRANCH ($TAG)"
        echo " - Arquitectura: $(uname -m)"
        echo " - Ubicación:    $SCRIPT_DIR_PATH"
        exit 0
        ;;
    status)
        if command -v systemctl &>/dev/null; then
            systemctl status fluxa.target fluxa.service 2>/dev/null || systemctl status fluxa-node0 2>/dev/null || systemctl status fluxa.target
        else
            echo "systemctl no disponible en este entorno."
        fi
        exit 0
        ;;
    start)
        echo "Iniciando FLUXA (fluxa.target)..."
        exec sudo systemctl start fluxa.target
        ;;
    stop)
        echo "Deteniendo FLUXA (fluxa.target)..."
        exec sudo systemctl stop fluxa.target
        ;;
    restart)
        echo "Reiniciando FLUXA (fluxa.target)..."
        exec sudo systemctl restart fluxa.target
        ;;
    logs)
        exec sudo journalctl -u fluxa.target -u "fluxa-node*.service" -u fluxa.service -f
        ;;
    help|--help|-h)
        show_help
        exit 0
        ;;
    *)
        cd "$SCRIPT_DIR_PATH" || exit 1
        if [ -f "$SCRIPT_DIR_PATH/.env" ]; then
            set -a
            # shellcheck disable=SC1091
            . "$SCRIPT_DIR_PATH/.env"
            set +a
        fi
        if [ -f "$SCRIPT_DIR_PATH/.venv/bin/python3" ]; then
            exec "$SCRIPT_DIR_PATH/.venv/bin/python3" "$SCRIPT_DIR_PATH/main.py" "$@"
        else
            exec python3 "$SCRIPT_DIR_PATH/main.py" "$@"
        fi
        ;;
esac
EOF

sed -i "s|__INSTALL_DIR__|$SCRIPT_DIR|g" "$TMP_WRAPPER"

if [ -f "$WRAPPER_PATH" ] && cmp -s "$TMP_WRAPPER" "$WRAPPER_PATH"; then
    echo -e "${C_GREEN} Comando 'fluxa' ya instalado e idéntico en ${WRAPPER_PATH}.${C_RESET}"
    rm -f "$TMP_WRAPPER"
else
    if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
        run_sudo mv "$TMP_WRAPPER" "$WRAPPER_PATH"
        run_sudo chmod +x "$WRAPPER_PATH"
        echo -e "${C_GREEN} Comando global 'fluxa' instalado en ${WRAPPER_PATH}.${C_RESET}"
    else
        rm -f "$TMP_WRAPPER"
    fi
fi

# ------------------------------------------------------------------------------
# 11. Configuración de Servicios Systemd
# ------------------------------------------------------------------------------
echo -e "\n${C_YELLOW}⚙️  [6/6] Configurando servicios en segundo plano (Systemd)...${C_RESET}"

SYSTEMD_DIR="${SYSTEMD_DIR_OVERRIDE:-/etc/systemd/system}"

if [ "$ARCH" = "aarch64" ]; then
    echo -e "${C_CYAN}➡️  Arquitectura aarch64 detectada (Orange Pi 5).${C_RESET}"
    echo -e "${C_CYAN}➡️  Delegando en systemd/install_service.sh (Arquitectura Tri-Core / fluxa.target)...${C_RESET}"
    
    # Invocar install_service.sh heredando el lock y reenviando argumentos (como --migrate)
    FLUXA_LOCK_HELD=1 SYSTEMD_DIR="$SYSTEMD_DIR" run_sudo bash "$SCRIPT_DIR/systemd/install_service.sh" "$@"
else
    echo -e "${C_CYAN}➡️  Arquitectura no-aarch64 ($ARCH). Configurando servicio individual fluxa.service...${C_RESET}"
    
    TARGET_DEST="${SYSTEMD_DIR}/fluxa.target"
    TMP_TARGET=$(mktemp)
    TMP_FILES+=("$TMP_TARGET")
    cat << 'EOF' > "$TMP_TARGET"
[Unit]
Description=FLUXA - Control Semaforico Inteligente
Wants=fluxa.service

[Install]
WantedBy=multi-user.target
EOF

    if [ -f "$TARGET_DEST" ]; then
        if ! cmp -s "$TMP_TARGET" "$TARGET_DEST"; then
            BAK_TARGET="${TARGET_DEST}.bak.$(date +%Y%m%d_%H%M%S)"
            echo -e "${C_YELLOW}⚠️  Aviso: $TARGET_DEST ya existe y difiere. Conservando local. Respaldo: $BAK_TARGET${C_RESET}"
            run_sudo cp -a "$TARGET_DEST" "$BAK_TARGET"
        fi
        rm -f "$TMP_TARGET"
    else
        if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
            run_sudo mv "$TMP_TARGET" "$TARGET_DEST"
            run_sudo chmod 644 "$TARGET_DEST"
        else
            rm -f "$TMP_TARGET"
        fi
    fi

    SERVICE_FILE="${SYSTEMD_DIR}/fluxa.service"
    TMP_SVC=$(mktemp)
    TMP_FILES+=("$TMP_SVC")
    cat << EOF > "$TMP_SVC"
[Unit]
Description=FLUXA - Control Semaforico Inteligente y Telemetria Edge
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
ExecStart=${SCRIPT_DIR}/.venv/bin/python3 ${SCRIPT_DIR}/main.py --topology 4_way --backend cpu --headless --port 5000
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

    if [ -f "$SERVICE_FILE" ]; then
        if ! cmp -s "$TMP_SVC" "$SERVICE_FILE"; then
            BAK_SVC="${SERVICE_FILE}.bak.$(date +%Y%m%d_%H%M%S)"
            echo -e "${C_YELLOW}⚠️  Aviso: $SERVICE_FILE ya existe y difiere de la plantilla.${C_RESET}"
            echo -e "${C_YELLOW}   Conservando versión local. Respaldo registrado en: $BAK_SVC${C_RESET}"
            run_sudo cp -a "$SERVICE_FILE" "$BAK_SVC"
            rm -f "$TMP_SVC"
        else
            echo -e "${C_GREEN} Servicio fluxa.service ya instalado e idéntico.${C_RESET}"
            rm -f "$TMP_SVC"
        fi
    else
        if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
            run_sudo mv "$TMP_SVC" "$SERVICE_FILE"
            run_sudo chmod 644 "$SERVICE_FILE"
            echo -e "${C_GREEN} Servicio systemd creado en ${SERVICE_FILE}.${C_RESET}"
        else
            rm -f "$TMP_SVC"
        fi
    fi

    if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
        run_sudo systemctl daemon-reload
        run_sudo systemctl enable fluxa.target fluxa.service
    fi
fi

# ------------------------------------------------------------------------------
# Resumen Final
# ------------------------------------------------------------------------------
echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "   INSTALACIÓN Y CONFIGURACIÓN DE FLUXA COMPLETADA CON ÉXITO"
echo "   TESCo • División de Ingeniería en Sistemas Computacionales"
echo "======================================================================"
echo -e "${C_RESET}"

echo -e "El sistema está listo para operar:\n"
echo -e "1. ${C_BOLD}Ejecución manual por CLI:${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --headless --port 5000${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --gui${C_RESET}"
if [ "$ARCH" = "aarch64" ]; then
    echo -e "   ${C_CYAN}fluxa --topology 4_way --backend rknn --npu-core all --headless --port 5000${C_RESET}"
    echo -e "   ${C_CYAN}# Despliegue Corredor Tri-Core (3 Cruces en paralelo):${C_RESET}"
    echo -e "   ${C_CYAN}sudo systemctl start fluxa.target${C_RESET}"
fi

echo -e "\n2. ${C_BOLD}Control Centralizado Systemd:${C_RESET}"
echo -e "   Iniciar sistema:     ${C_CYAN}sudo systemctl start fluxa.target${C_RESET}"
echo -e "   Detener sistema:     ${C_CYAN}sudo systemctl stop fluxa.target${C_RESET}"
echo -e "   Estado del target:   ${C_CYAN}sudo systemctl status fluxa.target${C_RESET}"

echo -e "\n3. ${C_BOLD}Interfaces Web y Centros de Mando:${C_RESET}"
echo -e "   Portal Ciudadano:    ${C_GREEN}http://localhost:5000${C_RESET}"
echo -e "   Consola C5 SCADA:    ${C_GREEN}http://localhost:5000/admin${C_RESET}"
echo -e "   (Actualizar credenciales: ${C_CYAN}python3 scripts/set_admin_password.py${C_RESET})"

if [ -f "$SCRIPT_DIR/instance/.admin_initial_pass" ]; then
    echo -e "\n${C_YELLOW}🔑 CREDENCIALES INICIALES DE ADMINISTRADOR C5:${C_RESET}"
    echo -e "   Archivo: ${C_BOLD}$SCRIPT_DIR/instance/.admin_initial_pass${C_RESET} (dueño: ${CURRENT_USER}, permisos 600)"
    echo -e "   ${C_RED}IMPORTANTE: Inicie sesión en http://localhost:5000/admin y elimine este archivo tras el primer login:${C_RESET}"
    echo -e "   ${C_CYAN}rm -f $SCRIPT_DIR/instance/.admin_initial_pass${C_RESET}"
fi

echo -e "\n4. ${C_BOLD}Desinstalación del sistema:${C_RESET}"
echo -e "   ${C_YELLOW}bash uninstall.sh${C_RESET}\n"
