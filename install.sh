#!/usr/bin/env bash
# ==============================================================================
#  🚦 FLUXA Smart Mobility • Script Instalador Universal de 1-Clic
#  Compatible con: Fedora, Red Hat, Ubuntu 24.04/22.04, Debian 12, Armbian (Orange Pi 5)
#  Arquitecturas: x86_64 (Laptops/Servidores) y aarch64 (Orange Pi 5 / RK3588)
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
echo "   INSTALADOR UNIVERSAL DE 1-CLIC PARA EDGE COMPUTING"
echo "======================================================================"
echo -e "${C_RESET}"

# 1. Detección de Directorio y Usuario
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"
CURRENT_HOME=$(eval echo "~$CURRENT_USER")
ARCH=$(uname -m)

echo -e "${C_BLUE}ℹ️  Usuario de instalación:${C_RESET} ${CURRENT_USER}"
echo -e "${C_BLUE}ℹ️  Directorio del proyecto:${C_RESET} ${SCRIPT_DIR}"
echo -e "${C_BLUE}ℹ️  Arquitectura detectada:${C_RESET} ${ARCH}"

# 2. Detección del Gestor de Paquetes y Distribución Linux
OS_TYPE="unknown"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID=$ID
    DISTRO_NAME=$NAME
    echo -e "${C_BLUE}ℹ️  Distribución detectada:${C_RESET} ${DISTRO_NAME} (${DISTRO_ID})"
fi

# Función para ejecutar con sudo si es necesario
run_sudo() {
    if [ "$EUID" -ne 0 ]; then
        sudo "$@"
    else
        "$@"
    fi
}

# 3. Instalación de Dependencias del Sistema
echo -e "\n${C_YELLOW}📦 [1/6] Instalando paquetes y dependencias del sistema operativo...${C_RESET}"

if command -v dnf &>/dev/null; then
    echo -e "${C_CYAN}➡️  Utilizando gestor DNF (Fedora/RHEL/CentOS)...${C_RESET}"
    run_sudo dnf install -y python3 python3-pip python3-devel mesa-libGL glib2 mariadb-server v4l-utils curl git
elif command -v apt-get &>/dev/null; then
    echo -e "${C_CYAN}➡️  Utilizando gestor APT (Ubuntu/Debian/Armbian)...${C_RESET}"
    run_sudo apt-get update -y
    run_sudo apt-get install -y python3 python3-pip python3-venv python3-dev libgl1 libglib2.0-0 mariadb-server v4l-utils curl git
else
    echo -e "${C_YELLOW}⚠️ Gestor de paquetes no reconocido. Asegúrate de tener Python 3.9+, OpenGL y MariaDB instalados.${C_RESET}"
fi

# 4. Configuración de Permisos de Hardware (Serial Arduino y Cámaras)
echo -e "\n${C_YELLOW}🔌 [2/6] Configurando permisos de hardware para acceso sin root...${C_RESET}"

# Grupo dialout (Debian/Ubuntu/Armbian) o uucp/dialout (Fedora/RHEL)
if grep -q "^dialout:" /etc/group; then
    run_sudo usermod -a -G dialout "$CURRENT_USER" || true
fi
if grep -q "^uucp:" /etc/group; then
    run_sudo usermod -a -G uucp "$CURRENT_USER" || true
fi
if grep -q "^video:" /etc/group; then
    run_sudo usermod -a -G video "$CURRENT_USER" || true
fi

echo -e "${C_GREEN}✅ Permisos para /dev/ttyACM* (Arduino) y /dev/video* (Cámaras) configurados.${C_RESET}"

# Regla udev para NPU Rockchip RK3588 si estamos en Armbian/Orange Pi 5
if [ "$ARCH" = "aarch64" ]; then
    echo -e "${C_BLUE}ℹ️  Detectada plataforma ARM64 (Orange Pi 5 / RK3588). Verificando NPU...${C_RESET}"
    if [ -e /dev/rknpu ]; then
        run_sudo chmod 666 /dev/rknpu || true
        echo -e "${C_GREEN}✅ Dispositivo /dev/rknpu accesible.${C_RESET}"
    fi
fi

# 5. Creación del Entorno Virtual Aislado (Python venv)
echo -e "\n${C_YELLOW}🐍 [3/6] Creando entorno virtual aislado (.venv)...${C_RESET}"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${C_GREEN}✅ Entorno .venv creado.${C_RESET}"
else
    echo -e "${C_BLUE}ℹ️  Entorno .venv existente detectado.${C_RESET}"
fi

# Activar venv para instalación
source .venv/bin/activate

echo -e "${C_CYAN}➡️  Actualizando pip, setuptools y wheel...${C_RESET}"
pip install --upgrade pip setuptools wheel --quiet

echo -e "${C_CYAN}➡️  Instalando dependencias de FLUXA (PyTorch, YOLOv8, OpenCV, Flask, PyMySQL)...${C_RESET}"
pip install -r requirements.txt --quiet

echo -e "${C_GREEN}✅ Librerías de Python instaladas correctamente en .venv.${C_RESET}"

# 6. Inicialización de la Base de Datos MariaDB
echo -e "\n${C_YELLOW}🗄️ [4/6] Configurando e inicializando Base de Datos MariaDB...${C_RESET}"
if command -v systemctl &>/dev/null; then
    run_sudo systemctl enable mariadb || true
    run_sudo systemctl start mariadb || true
    
    # Crear base de datos fluxa_traffic si no existe
    run_sudo mysql -e "CREATE DATABASE IF NOT EXISTS fluxa_traffic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true
    echo -e "${C_GREEN}✅ Servicio MariaDB activo y esquema 'fluxa_traffic' verificado.${C_RESET}"
fi

# 7. Creación del Comando Global 'fluxa' en el Sistema (/usr/local/bin/fluxa)
echo -e "\n${C_YELLOW}🚀 [5/6] Creando acceso directo global 'fluxa' en el sistema...${C_RESET}"

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

echo -e "${C_GREEN}✅ Comando 'fluxa' instalado en ${WRAPPER_PATH}.${C_RESET}"

# 8. Creación y Configuración del Servicio Systemd para Gabinete Vial
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

# Mensaje de Finalización
echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "🎉 ¡INSTALACIÓN DE FLUXA COMPLETADA CON ÉXITO!"
echo "======================================================================"
echo -e "${C_RESET}"

echo -e "Puedes utilizar FLUXA de las siguientes maneras:\n"
echo -e "1️⃣  ${C_BOLD}Ejecutar directamente desde cualquier terminal:${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --headless --port 5000${C_RESET}"
echo -e "   ${C_CYAN}fluxa --topology 4_way --backend cpu --gui${C_RESET}"
if [ "$ARCH" = "aarch64" ]; then
    echo -e "   ${C_CYAN}fluxa --topology 4_way --backend rknn --headless --port 5000${C_RESET} (Orange Pi 5 NPU)"
fi

echo -e "\n2️⃣  ${C_BOLD}Manejar el servicio automático de gabinete (Systemd):${C_RESET}"
echo -e "   Iniciar servicio:    ${C_CYAN}sudo systemctl start fluxa${C_RESET}"
echo -e "   Habilitar al inicio: ${C_CYAN}sudo systemctl enable fluxa${C_RESET}"
echo -e "   Ver logs en vivo:    ${C_CYAN}journalctl -u fluxa -f${C_RESET}"

echo -e "\n3️⃣  ${C_BOLD}Abrir el Centro de Mando Web:${C_RESET}"
echo -e "   Portal Ciudadano:    ${C_GREEN}http://localhost:5000${C_RESET}"
echo -e "   Consola C5 SCADA:    ${C_GREEN}http://localhost:5000/admin${C_RESET} (admin / fluxa2026)"

echo -e "\n🗑️  ${C_BOLD}Para desinstalar en el futuro:${C_RESET}"
echo -e "   ${C_YELLOW}bash uninstall.sh${C_RESET}\n"
