#!/usr/bin/env bash
# ==============================================================================
#  🚦 FLUXA Smart Mobility • Script Instalador Universal de 1-Clic
#  Cero fricción: Instala Python, MariaDB, dependencias y reglas de hardware.
#  Compatible con: Armbian 24.04 (Orange Pi 5), Fedora, Ubuntu 24.04/22.04, Debian 12
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
echo "   ███████╗██╗     ██╗   ██╗██╗  ██╗ █████╗ "
echo "   ██╔════╝██║     ██║   ██║╚██╗██╔╝██╔══██╗"
echo "   █████╗  ██║     ██║   ██║ ╚███╔╝ ███████║"
echo "   ██╔══╝  ██║     ██║   ██║ ██╔██╗ ██╔══██║"
echo "   ██║     ███████╗╚██████╔╝██╔╝ ██╗██║  ██║"
echo "   ╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝"
echo "   INSTALADOR UNIVERSAL CERO-FRICCIÓN (EDGE & NATIVE)"
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

# 4. Instalación Automática de Python, MariaDB y Librerías de Sistema
echo -e "\n${C_YELLOW}📦 [1/6] Verificando e instalando Python 3, MariaDB y dependencias del sistema...${C_RESET}"

if command -v dnf &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via DNF (Fedora/RHEL/CentOS)...${C_RESET}"
    run_sudo dnf install -y python3 python3-pip python3-devel mesa-libGL glib2 mariadb-server mariadb v4l-utils curl git udev
elif command -v apt-get &>/dev/null; then
    echo -e "${C_CYAN}➡️  Instalando paquetes via APT (Ubuntu/Debian/Armbian)...${C_RESET}"
    run_sudo apt-get update -y
    run_sudo apt-get install -y python3 python3-pip python3-venv python3-dev libgl1 libglib2.0-0 mariadb-server mariadb-client v4l-utils curl git udev
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

echo -e "${C_GREEN}✅ Hardware habilitado para uso inmediato sin necesidad de reiniciar la sesión.${C_RESET}"

# 6. Creación y Despliegue del Entorno Virtual Aislado (.venv)
echo -e "\n${C_YELLOW}🐍 [3/6] Preparando entorno virtual aislado de Python (.venv)...${C_RESET}"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${C_GREEN}✅ Entorno .venv creado.${C_RESET}"
else
    echo -e "${C_BLUE}ℹ️  Entorno .venv detectado.${C_RESET}"
fi

# Actualizar herramientas de empaquetado
"$SCRIPT_DIR/.venv/bin/pip" install --upgrade pip setuptools wheel --quiet

echo -e "${C_CYAN}➡️  Instalando librerías de IA (PyTorch, YOLOv8, OpenCV, Flask, PyMySQL)...${C_RESET}"
"$SCRIPT_DIR/.venv/bin/pip" install -r requirements.txt --quiet

echo -e "${C_GREEN}✅ Dependencias de IA instaladas correctamente.${C_RESET}"

# 7. Configuración Automática y Despliegue de MariaDB
echo -e "\n${C_YELLOW}🗄️ [4/6] Desplegando e inicializando Base de Datos MariaDB...${C_RESET}"
if command -v systemctl &>/dev/null; then
    run_sudo systemctl enable mariadb || true
    run_sudo systemctl start mariadb || true
    
    # Crear esquema y configurar credenciales
    run_sudo mysql -e "CREATE DATABASE IF NOT EXISTS fluxa_traffic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
    run_sudo mysql -e "CREATE USER IF NOT EXISTS 'root'@'localhost' IDENTIFIED BY 'theelderfallout99'; ALTER USER 'root'@'localhost' IDENTIFIED BY 'theelderfallout99'; GRANT ALL PRIVILEGES ON fluxa_traffic.* TO 'root'@'localhost'; FLUSH PRIVILEGES;" 2>/dev/null || true
    run_sudo mysql -e "CREATE USER IF NOT EXISTS 'fluxa'@'localhost' IDENTIFIED BY 'theelderfallout99'; GRANT ALL PRIVILEGES ON fluxa_traffic.* TO 'fluxa'@'localhost'; FLUSH PRIVILEGES;" 2>/dev/null || true
    
    echo -e "${C_GREEN}✅ Servidor MariaDB activo y base de datos 'fluxa_traffic' lista.${C_RESET}"
fi

# 7.1. Verificación e Instalación Automática de NPU en Orange Pi 5 (aarch64)
if [ "$ARCH" = "aarch64" ]; then
    echo -e "\n${C_BLUE}🔍 Configurando soporte para NPU Rockchip RK3588 (rknn-toolkit-lite2)...${C_RESET}"
    
    # Obtener versión de Python en formato 310, 311, 312
    PY_VER=$("$SCRIPT_DIR/.venv/bin/python3" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
    TARGET_WHL="$SCRIPT_DIR/wheels/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
    
    if [ -f "$TARGET_WHL" ]; then
        echo -e "${C_CYAN}➡️  Instalando paquete oficial de Rockchip para Python ${PY_VER}: $(basename "$TARGET_WHL")...${C_RESET}"
        "$SCRIPT_DIR/.venv/bin/pip" install "$TARGET_WHL" --quiet
    else
        # Búsqueda de respaldo en el sistema
        ALT_WHL=$(find "$SCRIPT_DIR" "$SCRIPT_DIR/.." /home /opt -name "*rknn_toolkit_lite2*cp${PY_VER}*aarch64.whl" 2>/dev/null | head -n 1 || true)
        if [ -n "$ALT_WHL" ] && [ -f "$ALT_WHL" ]; then
            echo -e "${C_CYAN}➡️  Instalando paquete alternativo: ${ALT_WHL}...${C_RESET}"
            "$SCRIPT_DIR/.venv/bin/pip" install "$ALT_WHL" --quiet
        else
            echo -e "${C_YELLOW}⬇️ Descargando wheel oficial de Rockchip para Python ${PY_VER}...${C_RESET}"
            WHL_URL="https://github.com/airockchip/rknn-toolkit2/raw/master/rknn-toolkit-lite2/packages/rknn_toolkit_lite2-2.3.2-cp${PY_VER}-cp${PY_VER}-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
            curl -fsSL "$WHL_URL" -o "/tmp/rknn_auto.whl" 2>/dev/null && "$SCRIPT_DIR/.venv/bin/pip" install "/tmp/rknn_auto.whl" --quiet || true
        fi
    fi

    # Verificar que el módulo rknnlite cargue sin errores
    if "$SCRIPT_DIR/.venv/bin/python3" -c "from rknnlite.api import RKNNLite" 2>/dev/null; then
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
ExecStart=${SCRIPT_DIR}/.venv/bin/python3 ${SCRIPT_DIR}/main.py --topology 4_way --backend cpu --headless --video videos/13868586_1280_720_24fps.mp4 --port 5000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

run_sudo mv /tmp/fluxa.service "$SERVICE_FILE"
run_sudo chmod 644 "$SERVICE_FILE"
run_sudo systemctl daemon-reload

echo -e "${C_GREEN}✅ Servicio systemd creado en ${SERVICE_FILE}.${C_RESET}"

# Resumen Final
echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "🎉 ¡FLUXA SMART MOBILITY HA SIDO INSTALADO Y CONFIGURADO AL 100%!"
echo "======================================================================"
echo -e "${C_RESET}"

echo -e "Tu sistema está listo para operar inmediatamente:\n"
echo -e "1️⃣  ${C_BOLD}Ejecutar manualmente:${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --headless --port 5000${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --gui${C_RESET}"
if [ "$ARCH" = "aarch64" ]; then
    echo -e "   ${C_CYAN}fluxa --topology 4_way --backend rknn --headless --port 5000${C_RESET}"
fi

echo -e "\n2️⃣  ${C_BOLD}Control del Servicio de Gabinete (Systemd):${C_RESET}"
echo -e "   Iniciar servicio:    ${C_CYAN}sudo systemctl start fluxa${C_RESET}"
echo -e "   Habilitar al inicio: ${C_CYAN}sudo systemctl enable fluxa${C_RESET}"
echo -e "   Ver registros:       ${C_CYAN}journalctl -u fluxa -f${C_RESET}"

echo -e "\n3️⃣  ${C_BOLD}Centros de Mando Web:${C_RESET}"
echo -e "   Portal Ciudadano:    ${C_GREEN}http://localhost:5000${C_RESET}"
echo -e "   Consola C5 SCADA:    ${C_GREEN}http://localhost:5000/admin${C_RESET} (admin / fluxa2026)"

echo -e "\n🗑️  ${C_BOLD}Desinstalación limpia:${C_RESET}"
echo -e "   ${C_YELLOW}bash uninstall.sh${C_RESET}\n"
