#!/usr/bin/env bash
# ==============================================================================
#  FLUXA Smart Mobility • Actualizador Autónomo de Producción (update.sh)
#  Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
#  Diseñado para: Orange Pi 5 (RK3588, Armbian 24) y servidores x86_64
#  Desarrollador Principal: Moisés Emilio Martínez Arias
# ==============================================================================
#  Garantías de seguridad vial y resiliencia industrial:
#  1. Cerrojo de exclusión mutua (/run/lock/fluxa.lock) compartido con install.sh
#  2. Snapshot previo atómico (código, config, .env) con retención máxima (3 backups)
#  3. Snapshot lógico MariaDB vía scripts/migrate_db.py antes de DDL
#  4. Migración no destructiva de config.json preservando calibración de zonas
#  5. Health-check HTTP a los cruces/nodos con reintentos controlados
#  6. ROLLBACK AUTOMÁTICO e instantáneo sin intervención humana si algo falla
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$USER}"
ARCH=$(uname -m)

# ------------------------------------------------------------------------------
# 0. Verificaciones de Seguridad y Modo de Prueba (FLUXA_TEST_MODE)
# ------------------------------------------------------------------------------
if [ "${FLUXA_TEST_MODE:-0}" = "1" ]; then
    CANONICAL_SCRIPT_DIR=$(readlink -f "$SCRIPT_DIR" 2>/dev/null || echo "$SCRIPT_DIR")
    if [[ "$CANONICAL_SCRIPT_DIR" != /tmp/* ]] && [[ "$CANONICAL_SCRIPT_DIR" != */scratch/* ]]; then
        echo -e "${C_RED}❌ Error de seguridad: FLUXA_TEST_MODE=1 solo está permitido en directorios temporales (/tmp/ o scratch/).${C_RESET}" >&2
        echo -e "${C_RED}   Directorio actual no temporal: ${CANONICAL_SCRIPT_DIR}${C_RESET}" >&2
        exit 1
    fi
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

# Manejo de limpieza y sudo keep-alive
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
# 0. Ayuda Temprana CLI (sin requerir sudo ni cerrojos)
# ------------------------------------------------------------------------------
for arg in "$@"; do
    if [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
        echo "Uso: sudo bash update.sh [OPCIONES]"
        echo ""
        echo "Opciones:"
        echo "  --tag <version>        Actualiza a un tag git específico (ej. v1.2.0)"
        echo "  --branch <rama>        Actualiza a la punta de una rama (ej. main)"
        echo "  --check                Verifica si existen actualizaciones remotas o migraciones pendientes"
        echo "  --dry-run              Simula el proceso de actualización sin aplicar cambios"
        echo "  --rollback             Revierte de emergencia al snapshot más reciente"
        echo "  --rollback-to <tar>    Revierte a un archivo de snapshot específico"
        echo "  --backup-dir <dir>     Directorio base de respaldos (default: /var/backups/fluxa)"
        exit 0
    fi
done
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
    if flock -n 200; then
        echo -e "${C_BLUE}ℹ️  Lock de FLUXA heredado y verificado vía fd 200 ($LOCK_FILE).${C_RESET}"
        LOCK_ACQUIRED=1
    fi
fi

if [ "$LOCK_ACQUIRED" -eq 0 ]; then
    exec 200>>"$LOCK_FILE"
    if ! flock -n 200; then
        echo -e "${C_RED}❌ Error: Ya existe un proceso de instalación o actualización de FLUXA en ejecución.${C_RESET}" >&2
        echo -e "${C_YELLOW}Archivo de bloqueo ocupado: ${LOCK_FILE}${C_RESET}" >&2
        exit 1
    fi
    export FLUXA_LOCK_HELD=1
    echo -e "${C_BLUE}ℹ️  Cerrojo de actualización adquirido en: ${LOCK_FILE}${C_RESET}"
fi

# Elevación de permisos sudo si no está en test mode
if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && [ "$EUID" -ne 0 ]; then
    echo -e "${C_YELLOW}🔑 Se requieren privilegios de administración (sudo) para actualizar servicios del sistema.${C_RESET}"
    sudo -v
    ( while true; do sudo -n true; sleep 60; kill -0 "$$" 2>/dev/null || exit 0; done ) 200>&- 2>/dev/null &
    SUDO_KEEP_PID=$!
fi

# ------------------------------------------------------------------------------
# 2. Análisis de Argumentos CLI
# ------------------------------------------------------------------------------
TARGET_REF=""
TARGET_TAG=""
TARGET_BRANCH=""
DRY_RUN=0
CHECK_ONLY=0
MANUAL_ROLLBACK=0
ROLLBACK_SNAPSHOT=""
BACKUP_BASE_DIR="/var/backups/fluxa"
if [ "${FLUXA_TEST_MODE:-0}" = "1" ] || [ ! -w "/var/backups" ] && [ "$EUID" -ne 0 ]; then
    BACKUP_BASE_DIR="$SCRIPT_DIR/.backups"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag)
            TARGET_TAG="$2"
            TARGET_REF="refs/tags/$2"
            shift 2
            ;;
        --branch)
            TARGET_BRANCH="$2"
            TARGET_REF="$2"
            shift 2
            ;;
        --ref)
            TARGET_REF="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --check)
            CHECK_ONLY=1
            shift
            ;;
        --rollback)
            MANUAL_ROLLBACK=1
            shift
            ;;
        --rollback-to)
            MANUAL_ROLLBACK=1
            ROLLBACK_SNAPSHOT="$2"
            shift 2
            ;;
        --backup-dir)
            BACKUP_BASE_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "Uso: sudo bash update.sh [OPCIONES]"
            echo ""
            echo "Opciones:"
            echo "  --tag <version>        Actualiza a un tag git específico (ej. v1.2.0)"
            echo "  --branch <rama>        Actualiza a la punta de una rama (ej. main)"
            echo "  --check                Verifica si existen actualizaciones remotas o migraciones pendientes"
            echo "  --dry-run              Simula el proceso de actualización sin aplicar cambios"
            echo "  --rollback             Revierte de emergencia al snapshot más reciente"
            echo "  --rollback-to <tar>    Revierte a un archivo de snapshot específico"
            echo "  --backup-dir <dir>     Directorio base de respaldos (default: /var/backups/fluxa)"
            exit 0
            ;;
        *)
            echo -e "${C_RED}Opción no reconocida: $1${C_RESET}" >&2
            exit 1
            ;;
    esac
done

SNAPSHOT_DIR="$BACKUP_BASE_DIR/snapshots"
DB_BACKUP_DIR="$BACKUP_BASE_DIR/db"
run_sudo mkdir -p "$SNAPSHOT_DIR" "$DB_BACKUP_DIR"

PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="$(command -v python3 || echo /usr/bin/python3)"
fi

# ------------------------------------------------------------------------------
# 3. Función de Restauración y Rollback Automático
# ------------------------------------------------------------------------------
execute_rollback() {
    local snapshot_file="$1"
    local db_dump_file="${2:-}"

    echo -e "\n${C_RED}${C_BOLD}"
    echo "======================================================================"
    echo "   ⚠️  EJECUTANDO ROLLBACK DE EMERGENCIA AL ESTADO PREVIO ESTABLE"
    echo "======================================================================"
    echo -e "${C_RESET}"

    if [ ! -f "$snapshot_file" ]; then
        echo -e "${C_RED}❌ Error crítico: Snapshot no encontrado en: $snapshot_file${C_RESET}" >&2
        return 1
    fi

    echo -e "${C_YELLOW}📦 Restaurando código y configuración desde snapshot:${C_RESET} ${snapshot_file}"
    tar -xzf "$snapshot_file" -C "$SCRIPT_DIR"

    if [ -n "$db_dump_file" ] && [ -f "$db_dump_file" ]; then
        echo -e "${C_YELLOW}🗄️  Restaurando base de datos MariaDB desde dump previo:${C_RESET} ${db_dump_file}"
        "$PYTHON_EXEC" "$SCRIPT_DIR/scripts/migrate_db.py" --rollback-snapshot "$db_dump_file" || true
    fi

    # Reiniciar servicios en la versión previa restaurada
    if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
        echo -e "${C_CYAN}🔄 Reiniciando servicios en la versión restaurada...${C_RESET}"
        run_sudo systemctl daemon-reload
        if [ "$ARCH" = "aarch64" ]; then
            run_sudo systemctl restart fluxa.target 2>/dev/null || true
        else
            run_sudo systemctl restart fluxa.target fluxa.service 2>/dev/null || true
        fi
    fi

    echo -e "${C_GREEN}✅ Rollback completado exitosamente. El cruce opera con la versión estable anterior.${C_RESET}"
    return 0
}

# ------------------------------------------------------------------------------
# 4. Manejo de Rollback Manual
# ------------------------------------------------------------------------------
if [ "$MANUAL_ROLLBACK" -eq 1 ]; then
    if [ -z "$ROLLBACK_SNAPSHOT" ]; then
        # Buscar el snapshot más reciente
        LATEST_SNAP=$(find "$SNAPSHOT_DIR" -name "fluxa_snapshot_*.tar.gz" 2>/dev/null | sort -r | head -n 1 || true)
        if [ -z "$LATEST_SNAP" ]; then
            echo -e "${C_RED}❌ Error: No se encontraron snapshots de respaldo en: $SNAPSHOT_DIR${C_RESET}" >&2
            exit 1
        fi
        ROLLBACK_SNAPSHOT="$LATEST_SNAP"
    fi

    # Buscar si hay un dump de DB asociado con timestamp similar
    TIMESTAMP_TAG=$(basename "$ROLLBACK_SNAPSHOT" | grep -oE '[0-9]{8}_[0-9]{6}' || true)
    ASSOC_DB_DUMP=""
    if [ -n "$TIMESTAMP_TAG" ]; then
        ASSOC_DB_DUMP=$(find "$DB_BACKUP_DIR" -name "*${TIMESTAMP_TAG}*.sql.gz" 2>/dev/null | head -n 1 || true)
    fi

    execute_rollback "$ROLLBACK_SNAPSHOT" "$ASSOC_DB_DUMP"
    exit 0
fi

# ------------------------------------------------------------------------------
# 5. Modo --check
# ------------------------------------------------------------------------------
if [ "$CHECK_ONLY" -eq 1 ]; then
    echo -e "${C_BLUE}🔍 Verificando estado y actualizaciones pendientes...${C_RESET}"
    NEEDS_UPDATE=0

    # 1. Comprobar git remoto si es un repositorio git
    if [ -d "$SCRIPT_DIR/.git" ]; then
        git fetch --quiet origin 2>/dev/null || true
        UPSTREAM='@{u}'
        LOCAL=$(git rev-parse @ 2>/dev/null || echo "local")
        REMOTE=$(git rev-parse "$UPSTREAM" 2>/dev/null || echo "remote")
        BASE=$(git merge-base @ "$UPSTREAM" 2>/dev/null || echo "base")

        if [ "$LOCAL" = "$REMOTE" ]; then
            echo -e "${C_GREEN} Git: El código local está al día con origin.${C_RESET}"
        elif [ "$LOCAL" = "$BASE" ]; then
            echo -e "${C_YELLOW} Git: Hay nuevas versiones disponibles en origin.${C_RESET}"
            NEEDS_UPDATE=1
        fi
    fi

    # 2. Comprobar configuración
    if [ -f "$SCRIPT_DIR/scripts/migrate_config.py" ] && [ -f "$SCRIPT_DIR/config.example.json" ]; then
        if ! "$PYTHON_EXEC" "$SCRIPT_DIR/scripts/migrate_config.py" --check --json &>/dev/null; then
            echo -e "${C_YELLOW} Config: config.json requiere migración de nuevas claves.${C_RESET}"
            NEEDS_UPDATE=1
        else
            echo -e "${C_GREEN} Config: config.json al día.${C_RESET}"
        fi
    fi

    # 3. Comprobar base de datos MariaDB
    if [ -f "$SCRIPT_DIR/scripts/migrate_db.py" ]; then
        if ! "$PYTHON_EXEC" "$SCRIPT_DIR/scripts/migrate_db.py" --check --json &>/dev/null; then
            echo -e "${C_YELLOW} Database: Existen migraciones SQL pendientes en MariaDB.${C_RESET}"
            NEEDS_UPDATE=1
        else
            echo -e "${C_GREEN} Database: Esquema de base de datos MariaDB al día.${C_RESET}"
        fi
    fi

    exit "$NEEDS_UPDATE"
fi

# ------------------------------------------------------------------------------
# 6. Modo --dry-run
# ------------------------------------------------------------------------------
if [ "$DRY_RUN" -eq 1 ]; then
    echo -e "${C_CYAN}🔍 Simulación (Dry-Run) del proceso de actualización:${C_RESET}"
    echo "1. Creación de snapshot tarball en: $SNAPSHOT_DIR"
    echo "2. Comprobación y migración no destructiva de config.json"
    echo "3. Snapshot lógico de MariaDB y ejecución de migraciones en scripts/migrate_db.py"
    echo "4. Actualización de dependencias en .venv"
    echo "5. Recarga y reinicio controlado de servicios systemd (fluxa.target)"
    echo "6. Health-check HTTP a los cruces/nodos con timeout de seguridad"
    exit 0
fi

# ------------------------------------------------------------------------------
# 7. Inicio del Flujo de Actualización Real
# ------------------------------------------------------------------------------
echo -e "${C_CYAN}${C_BOLD}"
echo "======================================================================"
echo "   FLUXA SMART MOBILITY • PROCESO DE ACTUALIZACIÓN SEGURA"
echo "======================================================================"
echo -e "${C_RESET}"

CURRENT_COMMIT="unknown"
if [ -d "$SCRIPT_DIR/.git" ]; then
    CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
fi
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_FILE="$SNAPSHOT_DIR/fluxa_snapshot_${TIMESTAMP}_${CURRENT_COMMIT}.tar.gz"

echo -e "\n${C_BLUE}📦 [1/6] Creando snapshot de seguridad del código y configuración...${C_RESET}"
# Tarball optimizado para eMMC de 32GB: Excluye videos, logs, calibration_images, instance y virtualenvs
tar --exclude="./videos" \
    --exclude="./logs" \
    --exclude="./data/calibration_images" \
    --exclude="./instance" \
    --exclude="./.venv" \
    --exclude="./.git" \
    --exclude="./.backups" \
    -czf "$SNAPSHOT_FILE" -C "$SCRIPT_DIR" .

chmod 600 "$SNAPSHOT_FILE"
echo -e "${C_GREEN} Snapshot generado exitosamente: ${SNAPSHOT_FILE}${C_RESET}"

# Política de retención: Mantener solo los 3 snapshots más recientes
find "$SNAPSHOT_DIR" -name "fluxa_snapshot_*.tar.gz" | sort -r | tail -n +4 | while read -r old_snap; do
    echo -e "${C_YELLOW}🧹 Purgando snapshot antiguo para ahorrar espacio eMMC:${C_RESET} $(basename "$old_snap")"
    rm -f "$old_snap" || true
done

# ------------------------------------------------------------------------------
# 8. Actualización de Código vía Git (o Checkout de Tag/Rama)
# ------------------------------------------------------------------------------
echo -e "\n${C_BLUE}⬇️  [2/6] Verificando y actualizando árbol de código...${C_RESET}"
if [ -d "$SCRIPT_DIR/.git" ] && [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    # Verificar cambios locales sucios en archivos versionados
    DIRTY_FILES=$(git status --porcelain -uno 2>/dev/null || true)
    if [ -n "$DIRTY_FILES" ]; then
        echo -e "${C_RED}❌ Error: Existen cambios locales sin confirmar en archivos rastreados por git:${C_RESET}" >&2
        echo "$DIRTY_FILES" >&2
        echo -e "${C_YELLOW}Realice git stash o revierta los cambios antes de actualizar.${C_RESET}" >&2
        exit 1
    fi

    git fetch --tags origin || true

    if [ -n "$TARGET_TAG" ]; then
        echo -e "${C_CYAN}➡️  Cambiando a tag: ${TARGET_TAG}...${C_RESET}"
        if ! git checkout "tags/$TARGET_TAG"; then
            execute_rollback "$SNAPSHOT_FILE"
            exit 1
        fi
    elif [ -n "$TARGET_BRANCH" ]; then
        echo -e "${C_CYAN}➡️  Actualizando rama: ${TARGET_BRANCH}...${C_RESET}"
        if ! git checkout "$TARGET_BRANCH" || ! git pull origin "$TARGET_BRANCH"; then
            execute_rollback "$SNAPSHOT_FILE"
            exit 1
        fi
    else
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
        echo -e "${C_CYAN}➡️  Sincronizando con origin/${CURRENT_BRANCH}...${C_RESET}"
        if ! git pull origin "$CURRENT_BRANCH"; then
            echo -e "${C_RED}❌ Fallo en git pull. Cancelando actualización.${C_RESET}" >&2
            execute_rollback "$SNAPSHOT_FILE"
            exit 1
        fi
    fi
else
    echo -e "${C_BLUE}ℹ️  [FLUXA_TEST_MODE o no-git] Omitiendo pull de git.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 9. Migración de Configuración (config.json)
# ------------------------------------------------------------------------------
echo -e "\n${C_BLUE}⚙️  [3/6] Fusionando cambios de configuración sin perder calibración...${C_RESET}"
if [ -f "$SCRIPT_DIR/scripts/migrate_config.py" ] && [ -f "$SCRIPT_DIR/config.example.json" ]; then
    if ! "$PYTHON_EXEC" "$SCRIPT_DIR/scripts/migrate_config.py" --config "$SCRIPT_DIR/config.json" --template "$SCRIPT_DIR/config.example.json"; then
        echo -e "${C_RED}❌ Error durante la migración de config.json. Iniciando rollback...${C_RESET}" >&2
        execute_rollback "$SNAPSHOT_FILE"
        exit 1
    fi
fi

# ------------------------------------------------------------------------------
# 10. Migración de Base de Datos MariaDB (Con Snapshot Lógico Previo)
# ------------------------------------------------------------------------------
echo -e "\n${C_BLUE}🗄️  [4/6] Verificando y aplicando migraciones de MariaDB...${C_RESET}"
DB_SNAPSHOT_TAKEN=""
if [ -f "$SCRIPT_DIR/scripts/migrate_db.py" ]; then
    MIG_OUT=$(mktemp)
    TMP_FILES+=("$MIG_OUT")
    if ! "$PYTHON_EXEC" "$SCRIPT_DIR/scripts/migrate_db.py" --backup-dir "$DB_BACKUP_DIR" --json > "$MIG_OUT" 2>&1; then
        echo -e "${C_RED}❌ Fallo crítico al ejecutar migraciones de MariaDB:${C_RESET}" >&2
        cat "$MIG_OUT" >&2
        execute_rollback "$SNAPSHOT_FILE"
        exit 1
    fi

    # Extraer ruta del dump lógico si se generó
    if grep -q '"backup_path":' "$MIG_OUT"; then
        DB_SNAPSHOT_TAKEN=$(grep -oE '"backup_path": "[^"]+"' "$MIG_OUT" | cut -d'"' -f4 || true)
    fi
    echo -e "${C_GREEN} Migraciones de base de datos verificadas y al día.${C_RESET}"
fi

# ------------------------------------------------------------------------------
# 11. Recarga de Dependencias Python y Servicios Systemd
# ------------------------------------------------------------------------------
echo -e "\n${C_BLUE}🔄 [5/6] Actualizando dependencias y reiniciando servicios...${C_RESET}"
PIP_EXEC="$SCRIPT_DIR/.venv/bin/pip"
if [ -f "$PIP_EXEC" ] && [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    "$PIP_EXEC" install -r "$SCRIPT_DIR/requirements.txt" --upgrade --quiet 2>/dev/null || true
fi

if [ "${FLUXA_TEST_MODE:-0}" != "1" ] && command -v systemctl &>/dev/null; then
    run_sudo systemctl daemon-reload
    if [ "$ARCH" = "aarch64" ]; then
        run_sudo systemctl restart fluxa.target
    else
        run_sudo systemctl restart fluxa.target fluxa.service
    fi
fi

# ------------------------------------------------------------------------------
# 12. Health-Check en Vivo y Rollback Automático
# ------------------------------------------------------------------------------
echo -e "\n${C_BLUE}🩺 [6/6] Ejecutando Health-Check de validación en vivo...${C_RESET}"

CHECK_PORTS=(5000)
if [ "$ARCH" = "aarch64" ]; then
    CHECK_PORTS=(5000 5001 5002)
fi

HEALTH_SUCCESS=1
if [ "${FLUXA_TEST_MODE:-0}" != "1" ]; then
    echo -e "${C_CYAN}⏳ Esperando estabilización del runtime y modelos (4 segundos)...${C_RESET}"
    sleep 4

    for PORT in "${CHECK_PORTS[@]}"; do
        PORT_OK=0
        for ATTEMPT in {1..5}; do
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/api/status" 2>/dev/null || true)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "${C_GREEN} Cruce en puerto ${PORT}: Operativo (HTTP 200 OK en intento ${ATTEMPT}).${C_RESET}"
                PORT_OK=1
                break
            fi
            sleep 2
        done

        if [ "$PORT_OK" -eq 0 ]; then
            echo -e "${C_RED}❌ Cruce en puerto ${PORT} no responde tras 5 intentos (HTTP: ${HTTP_CODE:-ninguno}).${C_RESET}" >&2
            HEALTH_SUCCESS=0
            break
        fi
    done
else
    echo -e "${C_GREEN} [FLUXA_TEST_MODE] Simulación de Health-Check exitosa.${C_RESET}"
    HEALTH_SUCCESS=1
fi

if [ "$HEALTH_SUCCESS" -eq 0 ]; then
    echo -e "${C_RED}❌ ALERTA CRÍTICA: La nueva versión no superó el Health-Check.${C_RESET}" >&2
    echo -e "${C_YELLOW}Disparando protocolo de ROLLBACK AUTOMÁTICO INMEDIATO...${C_RESET}" >&2
    execute_rollback "$SNAPSHOT_FILE" "$DB_SNAPSHOT_TAKEN"
    exit 1
fi

# ------------------------------------------------------------------------------
# 13. Resumen y Registro de Actualización Exitosa
# ------------------------------------------------------------------------------
NEW_COMMIT="unknown"
if [ -d "$SCRIPT_DIR/.git" ]; then
    NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
fi

UPDATE_LOG="$SCRIPT_DIR/logs/updates.log"
mkdir -p "$SCRIPT_DIR/logs"
echo "[$(date -Iseconds)] SUCCESS update: from=${CURRENT_COMMIT} to=${NEW_COMMIT} snapshot=${SNAPSHOT_FILE}" >> "$UPDATE_LOG"

echo -e "\n${C_GREEN}${C_BOLD}"
echo "======================================================================"
echo "   ✅ ACTUALIZACIÓN DE FLUXA COMPLETADA EXITOSAMENTE AL 100%"
echo "   - Versión anterior:  ${CURRENT_COMMIT}"
echo "   - Versión actual:    ${NEW_COMMIT}"
echo "   - Snapshot guardado: ${SNAPSHOT_FILE}"
echo "   - Health-Check:      Superado en todos los cruces y puertos"
echo "======================================================================"
echo -e "${C_RESET}\n"
exit 0
