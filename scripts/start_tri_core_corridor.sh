#!/usr/bin/env bash
# ==============================================================================
# FLUXA - Inicializador de Corredor Vial Tri-Core (3 Cruces en 1 Orange Pi 5)
# Tecnológico de Estudios Superiores de Coacalco (TESCo) • TecNM
# Autor y Desarrollador Principal: Moisés Emilio Martínez Arias
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Detener instancias previas
pkill -9 -f main.py 2>/dev/null || true
sleep 1

mkdir -p logs

echo " [1/3] Iniciando Cruce 01 (Norte) en Core NPU 0 (Puerto 5000)..."
setsid "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/main.py" \
    --topology 4_way \
    --backend rknn \
    --npu-core 0 \
    --port 5000 \
    --video "$SCRIPT_DIR/videos/demo.mp4" \
    --headless </dev/null > "$SCRIPT_DIR/logs/cruce_01.log" 2>&1 &

echo " [2/3] Iniciando Cruce 02 (Centro) en Core NPU 1 (Puerto 5001)..."
setsid "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/main.py" \
    --topology 4_way \
    --backend rknn \
    --npu-core 1 \
    --port 5001 \
    --video "$SCRIPT_DIR/videos/demo.mp4" \
    --headless </dev/null > "$SCRIPT_DIR/logs/cruce_02.log" 2>&1 &

echo " [3/3] Iniciando Cruce 03 (Sur) en Core NPU 2 (Puerto 5002)..."
setsid "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/main.py" \
    --topology 4_way \
    --backend rknn \
    --npu-core 2 \
    --port 5002 \
    --video "$SCRIPT_DIR/videos/demo.mp4" \
    --headless </dev/null > "$SCRIPT_DIR/logs/cruce_03.log" 2>&1 &

sleep 3
echo "Los 3 cruces han sido lanzados en puertos 5000, 5001 y 5002."
