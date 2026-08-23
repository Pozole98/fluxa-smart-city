#!/usr/bin/env bash
# ==============================================================================
#  FLUXA Smart Mobility • Script de Instalación Automatizada
#  Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
#  Compatible con: Armbian 24.04 (Orange Pi 5), openSUSE (Tumbleweed/Leap/SLES), Fedora, Ubuntu, Debian
# ==============================================================================

set -e

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

# 1. Elevación de Privilegios con una sola solicitud de contraseña
if [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}🔑 Se requieren permisos de administrador (sudo) para instalar dependencias de sistema y configurar hardware.${C_RESET}"
    sudo -v
    # Mantener sudo activo en segundo plano durante toda la ejecución
    while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &
fi

run_sudo() {
    if [ "$EUID" -ne 0 ]; then
        sudo "$@"
    else
        "$@"
    fi
}

# 2. Detección de Directorio, Usuario y Arquitectura
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"
CURRENT_HOME=$(eval echo "~$CURRENT_USER")
ARCH=$(uname -m)

echo -e "${C_BLUE}ℹ️  Usuario destino:${C_RESET} ${CURRENT_USER}"
echo -e "${C_BLUE}ℹ️  Directorio de FLUXA:${C_RESET} ${SCRIPT_DIR}"
echo -e "${C_BLUE}ℹ️  Arquitectura detectada:${C_RESET} ${ARCH}"

# 3. Detección de Distribución Linux
DISTRO_ID="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID=$ID
    echo -e "${C_BLUE}ℹ️  Sistema Operativo:${C_RESET} ${NAME} (${DISTRO_ID})"
fi

# Crear estructura esencial de directorios
mkdir -p "$SCRIPT_DIR/instance" "$SCRIPT_DIR/data/calibration_images" "$SCRIPT_DIR/logs/violations" "$SCRIPT_DIR/videos" "$SCRIPT_DIR/models" "$SCRIPT_DIR/logos" "$SCRIPT_DIR/static/logos"

# Inicializar config.json local a partir de la plantilla segura
if [ ! -f "$SCRIPT_DIR/config.json" ] && [ -f "$SCRIPT_DIR/config.example.json" ]; then
    cp "$SCRIPT_DIR/config.example.json" "$SCRIPT_DIR/config.json"
fi

# 4. Instalación Automática de Python, MariaDB y Librerías de Sistema
echo -e "\n${C_YELLOW}📦 [1/6] Verificando e instalando Python 3, MariaDB y dependencias del sistema...${C_RESET}"

if command -v zypper &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via ZYPPER (openSUSE Tumbleweed/Leap/MicroOS/SLES)...${C_RESET}"
    run_sudo zypper --non-interactive refresh || true
    
    # Paquetes base del sistema
    SUSE_PKGS="mariadb mariadb-client Mesa-libGL1 libglib-2_0-0 libgthread-2_0-0 v4l-utils curl git udev openssl gcc gcc-c++"
    
    # Detección dinámica de paquetes Python según la versión instalada o disponible
    PY_CANDIDATES=""
    if command -v python3 &>/dev/null; then
        PY_VER_TAG=$(python3 -c "import sys; print(f'python3{sys.version_info.minor}')" 2>/dev/null || true)
        if [ -n "$PY_VER_TAG" ]; then
            PY_CANDIDATES="${PY_VER_TAG}-devel ${PY_VER_TAG}-pip ${PY_VER_TAG}-tk"
        fi
    fi
    PY_CANDIDATES="$PY_CANDIDATES python3-devel python3-pip python3-tk python3-virtualenv python313-devel python313-pip python313-tk python312-devel python312-pip python312-tk python311-devel python311-pip python311-tk"
    
    PKGS_TO_INSTALL="$SUSE_PKGS"
    for candidate in $PY_CANDIDATES; do
        if zypper se -s --match-exact "$candidate" 2>/dev/null | grep -q " paquete "; then
            PKGS_TO_INSTALL="$PKGS_TO_INSTALL $candidate"
        fi
    done
    
    run_sudo zypper --non-interactive install -y $PKGS_TO_INSTALL
elif command -v dnf &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via DNF (Fedora/RHEL/CentOS)...${C_RESET}"
    run_sudo dnf install -y python3 python3-pip python3-devel python3-tkinter mesa-libGL glib2 mariadb-server mariadb v4l-utils curl git udev openssl
elif command -v apt-get &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via APT (Ubuntu/Debian/Armbian)...${C_RESET}"
    run_sudo apt-get update -y
    run_sudo apt-get install -y python3 python3-pip python3-venv python3-dev python3-tk libgl1 libglib2.0-0 mariadb-server mariadb-client v4l-utils curl git udev openssl
else
    echo -e "${C_YELLOW}⚠️ Gestor de paquetes no estándar. Asegúrate de contar con Python 3.9+, MariaDB y OpenGL.${C_RESET}"
fi

# 5. Configuración de Reglas Udev para Hardware Inmediato (Sin Reiniciar)
echo -e "\n${C_YELLOW}🔌 [2/6] Configurando reglas de hardware automáticas (Arduino, Cámaras, NPU)...${C_RESET}"

UDEV_RULES_FILE="/etc/udev/rules.d/99-fluxa-hardware.rules"
cat << 'EOF' > /tmp/99-fluxa-hardware.rules
# Reglas de acceso sin root para FLUXA
# Microcontroladores Arduino y adaptadores Serial USB
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"

# Cámaras de video V4L2
KERNEL=="video*", MODE="0666", GROUP="video"

# Acelerador NPU Rockchip RK3588 (Orange Pi 5)
KERNEL=="rknpu*", MODE="0666"
EOF

run_sudo mv /tmp/99-fluxa-hardware.rules "$UDEV_RULES_FILE"
run_sudo chmod 644 "$UDEV_RULES_FILE"

# Aplicar reglas inmediatamente
if command -v udevadm &>/dev/null; then
    run_sudo udevadm control --reload-rules || true
    run_sudo udevadm trigger || true
fi

# Asignar grupos al usuario
if grep -q "^dialout:" /etc/group; then run_sudo usermod -a -G dialout "$CURRENT_USER" || true; fi
if grep -q "^uucp:" /etc/group; then run_sudo usermod -a -G uucp "$CURRENT_USER" || true; fi
if grep -q "^video:" /etc/group; then run_sudo usermod -a -G video "$CURRENT_USER" || true; fi
if grep -q "^render:" /etc/group; then run_sudo usermod -a -G render "$CURRENT_USER" || true; fi

echo -e "${C_GREEN}✅ Hardware habilitado para uso inmediato sin necesidad de reiniciar la sesión.${C_RESET}"

# 6. Creación y Despliegue del Entorno Virtual Aislado (.venv)
echo -e "\n${C_YELLOW}🐍 [3/6] Preparando entorno Python y librerías...${C_RESET}"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv 2>/dev/null || true
fi

PIP_CMD="$SCRIPT_DIR/.venv/bin/pip"
PYTHON_CMD="$SCRIPT_DIR/.venv/bin/python3"

if [ ! -f "$PIP_CMD" ]; then
    PIP_CMD="pip3"
    PYTHON_CMD="python3"
fi

# Actualizar herramientas de empaquetado
if [ "$PIP_CMD" = "pip3" ]; then
    pip3 install --upgrade pip setuptools wheel --break-system-packages --quiet 2>/dev/null || true
    echo -e "${C_CYAN}➡️  Instalando dependencias de IA (PyTorch, YOLOv8, lapx, OpenCV, Flask, PyMySQL, pytest)...${C_RESET}"
    pip3 install -r requirements.txt --break-system-packages --quiet
else
    "$PIP_CMD" install --upgrade pip setuptools wheel --quiet
    echo -e "${C_CYAN}➡️  Instalando dependencias de IA (PyTorch, YOLOv8, lapx, OpenCV, Flask, PyMySQL, pytest)...${C_RESET}"
    "$PIP_CMD" install -r requirements.txt --quiet
fi

echo -e "${C_GREEN}✅ Dependencias de IA y tracking instaladas correctamente.${C_RESET}"

# 7. Configuración Automática y Despliegue de MariaDB con Seguridad
echo -e "\n${C_YELLOW}🗄️ [4/6] Desplegando e inicializando Base de Datos MariaDB...${C_RESET}"

DB_PASS="${DATABASE_PASSWORD:-}"
if [ -z "$DB_PASS" ]; then
    if [ -t 0 ]; then
        echo -e "${C_CYAN}Ingresa una contraseña para el usuario de base de datos 'fluxa' (o presiona ENTER para generar una aleatoria segura):${C_RESET} "
        read -s -r user_db_pass
        echo
        if [ -n "$user_db_pass" ]; then
            DB_PASS="$user_db_pass"
        else
            DB_PASS=$(openssl rand -hex 12 2>/dev/null || echo "fluxa_db_$(date +%s)")
            echo -e "${C_BLUE}ℹ️  Contraseña generada aleatoriamente y guardada en .env protegido.${C_RESET}"
        fi
    else
        DB_PASS=$(openssl rand -hex 12 2>/dev/null || echo "fluxa_db_$(date +%s)")
    fi
fi

if command -v systemctl &>/dev/null; then
    run_sudo systemctl enable mariadb 2>/dev/null || run_sudo systemctl enable mysql 2>/dev/null || true
    run_sudo systemctl start mariadb 2>/dev/null || run_sudo systemctl start mysql 2>/dev/null || true
    
    MYSQL_EXEC="mysql"
    if ! command -v mysql &>/dev/null && command -v mariadb &>/dev/null; then
        MYSQL_EXEC="mariadb"
    fi
    
    # Crear esquema y configurar usuario fluxa
    run_sudo $MYSQL_EXEC -e "CREATE DATABASE IF NOT EXISTS fluxa_traffic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
    run_sudo $MYSQL_EXEC -e "CREATE USER IF NOT EXISTS 'fluxa'@'localhost' IDENTIFIED BY '$DB_PASS'; ALTER USER 'fluxa'@'localhost' IDENTIFIED BY '$DB_PASS'; GRANT ALL PRIVILEGES ON fluxa_traffic.* TO 'fluxa'@'localhost'; FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Persistir en archivo .env local
    ENV_FILE="$SCRIPT_DIR/.env"
    cat << EOF > "$ENV_FILE"
DATABASE_HOST=localhost
DATABASE_USER=fluxa
DATABASE_PASSWORD=$DB_PASS
DATABASE_NAME=fluxa_traffic
DATABASE_PORT=3306
EOF
    chmod 600 "$ENV_FILE"
    
    echo -e "${C_GREEN}✅ Servidor MariaDB activo y base de datos 'fluxa_traffic' lista con credenciales configuradas en .env.${C_RESET}"
fi

# 7.1. Inicializar Credenciales de Administrador C5 si no existen
if [ ! -f "$SCRIPT_DIR/instance/admin_credentials.json" ]; then
    echo -e "\n${C_BLUE}🔐 Configurando credenciales de Operador Administrador C5...${C_RESET}"
    if [ -t 0 ]; then
        $PYTHON_CMD "$SCRIPT_DIR/scripts/set_admin_password.py"
    else
        AUTO_ADMIN_PASS=$(openssl rand -hex 8 2>/dev/null || echo "admin1234")
        $PYTHON_CMD "$SCRIPT_DIR/scripts/set_admin_password.py" --username admin --password "$AUTO_ADMIN_PASS" --force 2>/dev/null || true
    fi
fi

# 7.2. Verificación e Instalación Automática de NPU en Orange Pi 5 (aarch64)
if [ "$ARCH" = "aarch64" ]; then
    echo -e "\n${C_BLUE}🔍 Configurando soporte para NPU Rockchip RK3588 (rknn-toolkit-lite2)...${C_RESET}"
    
    # Obtener versión de Python en formato 310, 311, 312
    PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
    TARGET_WHL="$SCRIPT_DIR/wheels/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
    
    INSTALL_FLAG=""
    if [ "$PIP_CMD" = "pip3" ]; then
        INSTALL_FLAG="--break-system-packages"
    fi
    
    if [ -f "$TARGET_WHL" ]; then
        echo -e "${C_CYAN}➡️  Instalando paquete oficial de Rockchip para Python ${PY_VER}: $(basename "$TARGET_WHL")...${C_RESET}"
        $PIP_CMD install "$TARGET_WHL" $INSTALL_FLAG --quiet
    else
        # Búsqueda de respaldo en el sistema
        ALT_WHL=$(find "$SCRIPT_DIR" "$SCRIPT_DIR/.." /home /opt -name "*rknn_toolkit_lite2*cp${PY_VER}*aarch64.whl" 2>/dev/null | head -n 1 || true)
        if [ -n "$ALT_WHL" ] && [ -f "$ALT_WHL" ]; then
            echo -e "${C_CYAN}➡️  Instalando paquete alternativo: ${ALT_WHL}...${C_RESET}"
            $PIP_CMD install "$ALT_WHL" $INSTALL_FLAG --quiet
        else
            echo -e "${C_YELLOW}⬇️ Descargando wheel oficial de Rockchip para Python ${PY_VER}...${C_RESET}"
            WHL_URL="https://github.com/airockchip/rknn-toolkit2/raw/master/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
            curl -fsSL "$WHL_URL" -o "/tmp/rknn_auto.whl" 2>/dev/null && $PIP_CMD install "/tmp/rknn_auto.whl" $INSTALL_FLAG --quiet || true
        fi
    fi

    # Verificar que el módulo rknnlite cargue sin errores
    if $PYTHON_CMD -c "from rknnlite.api import RKNNLite" 2>/dev/null; then
        echo -e "${C_GREEN}✅ Soporte de NPU Rockchip RK3588 (rknnlite) verificado y activo.${C_RESET}"
    else
        echo -e "${C_YELLOW}⚠️ Advertencia: rknnlite no pudo cargarse en este momento. El sistema usará el motor CPU de respaldo.${C_RESET}"
    fi
fi

# 8. Instalación del Comando Global 'fluxa' (/usr/local/bin/fluxa)
echo -e "\n${C_YELLOW}🚀 [5/6] Instalando acceso directo global 'fluxa'...${C_RESET}"

WRAPPER_PATH="/usr/local/bin/fluxa"
cat << 'EOF' > /tmp/fluxa_wrapper.sh
#!/usr/bin/env bash
SCRIPT_DIR_PATH="__INSTALL_DIR__"
cd "$SCRIPT_DIR_PATH"
if [ -f "$SCRIPT_DIR_PATH/.env" ]; then
    set -a
    . "$SCRIPT_DIR_PATH/.env"
    set +a
fi
if [ -f "$SCRIPT_DIR_PATH/.venv/bin/python3" ]; then
    exec "$SCRIPT_DIR_PATH/.venv/bin/python3" "$SCRIPT_DIR_PATH/main.py" "$@"
else
    exec python3 "$SCRIPT_DIR_PATH/main.py" "$@"
fi
EOF

sed -i "s|__INSTALL_DIR__|$SCRIPT_DIR|g" /tmp/fluxa_wrapper.sh
run_sudo mv /tmp/fluxa_wrapper.sh "$WRAPPER_PATH"
run_sudo chmod +x "$WRAPPER_PATH"

echo -e "${C_GREEN}✅ Comando 'fluxa' disponible globalmente.${C_RESET}"

# 9. Configuración del Servicio Systemd de Gabinete
echo -e "\n${C_YELLOW}⚙️  [6/6] Configurando servicio en segundo plano (Systemd)...${C_RESET}"

BACKEND_DEFAULT="cpu"
if [ "$ARCH" = "aarch64" ]; then
    BACKEND_DEFAULT="rknn"
fi

SERVICE_FILE="/etc/systemd/system/fluxa.service"
cat << EOF > /tmp/fluxa.service
[Unit]
Description=FLUXA - Control Semaforico Inteligente y Telemetria Edge
After=network.target mariadb.service
Wants=mariadb.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
EnvironmentFile=-${SCRIPT_DIR}/.env
ExecStart=${SCRIPT_DIR}/.venv/bin/python3 ${SCRIPT_DIR}/main.py --topology 4_way --backend ${BACKEND_DEFAULT} --headless --port 5000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

if [ ! -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    sed -i "s|${SCRIPT_DIR}/.venv/bin/python3|/usr/bin/python3|g" /tmp/fluxa.service
fi

run_sudo mv /tmp/fluxa.service "$SERVICE_FILE"
run_sudo chmod 644 "$SERVICE_FILE"
run_sudo systemctl daemon-reload

echo -e "${C_GREEN}✅ Servicio systemd creado en ${SERVICE_FILE} (Backend: ${BACKEND_DEFAULT}).${C_RESET}"

# Resumen Final
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
    echo -e "   ${C_CYAN}fluxa --topology 4_way --backend rknn --headless --port 5000${C_RESET}"
fi

echo -e "\n2. ${C_BOLD}Control del Servicio de Gabinete (Systemd):${C_RESET}"
echo -e "   Iniciar servicio:    ${C_CYAN}sudo systemctl start fluxa${C_RESET}"
echo -e "   Habilitar al inicio: ${C_CYAN}sudo systemctl enable fluxa${C_RESET}"
echo -e "   Ver registros:       ${C_CYAN}journalctl -u fluxa -f${C_RESET}"

echo -e "\n3. ${C_BOLD}Interfaces Web y Centros de Mando:${C_RESET}"
echo -e "   Portal Ciudadano:    ${C_GREEN}http://localhost:5000${C_RESET}"
echo -e "   Consola C5 SCADA:    ${C_GREEN}http://localhost:5000/admin${C_RESET}"
echo -e "   (Actualizar credenciales: ${C_CYAN}python3 scripts/set_admin_password.py${C_RESET})"

echo -e "\n4. ${C_BOLD}Desinstalación del sistema:${C_RESET}"
echo -e "   ${C_YELLOW}bash uninstall.sh${C_RESET}\n"
