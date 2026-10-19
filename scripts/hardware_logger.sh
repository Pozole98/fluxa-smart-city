#!/bin/bash
# Script de Logging Histórico de Hardware para FLUXA
# Registra Timestamp, CPU%, RAM(MB), Temp SoC, Temp NPU, Temp BigCore, Temp LittleCore, LoadAvg, y Carga de Nucleos NPU
LOG_FILE="/home/fluxa/fluxa-smart-city/logs/hardware_log_$(date +%Y-%m).csv"

# Si el archivo no existe, crear los encabezados
if [ ! -f "$LOG_FILE" ]; then
    echo "Timestamp,CPU_Usado_Pct,RAM_Usada_MB,Temp_SoC_C,Temp_NPU_C,Temp_BigCore_C,Temp_LittleCore_C,LoadAvg_1m,NPU_Core0_Pct,NPU_Core1_Pct,NPU_Core2_Pct" > "$LOG_FILE"
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Calcular uso de CPU (usando mpstat o top)
CPU_IDLE=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}')
CPU_USED=$(awk "BEGIN {print 100 - $CPU_IDLE}")

# Memoria RAM Usada en MB
RAM_USED=$(free -m | awk '/Mem:/ {print $3}')

# Temperaturas (dividiendo por 1000)
TEMP_SOC=$(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')
TEMP_LITTLE=$(cat /sys/class/thermal/thermal_zone4/temp | awk '{print $1/1000}')
TEMP_BIG=$(cat /sys/class/thermal/thermal_zone5/temp | awk '{print $1/1000}')
TEMP_NPU=$(cat /sys/class/thermal/thermal_zone6/temp | awk '{print $1/1000}')

# Load Average
LOAD_AVG=$(cat /proc/loadavg | awk '{print $1}')

# Carga NPU
NPU_OUTPUT=$(echo 55050 | sudo -S cat /sys/kernel/debug/rknpu/load 2>/dev/null)
NPU_C0=$(echo "$NPU_OUTPUT" | grep -oP 'Core0: \K[0-9]+' || echo "0")
NPU_C1=$(echo "$NPU_OUTPUT" | grep -oP 'Core1: \K[0-9]+' || echo "0")
NPU_C2=$(echo "$NPU_OUTPUT" | grep -oP 'Core2: \K[0-9]+' || echo "0")

# Escribir al CSV
echo "$TIMESTAMP,$CPU_USED,$RAM_USED,$TEMP_SOC,$TEMP_NPU,$TEMP_BIG,$TEMP_LITTLE,$LOAD_AVG,$NPU_C0,$NPU_C1,$NPU_C2" >> "$LOG_FILE"
