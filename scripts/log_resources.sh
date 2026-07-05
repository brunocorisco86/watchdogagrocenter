#!/bin/bash
# Script de monitoramento de recursos para o Watchdog Agrocenter (Raspberry Pi / Alpine Linux)
# Roda via cron ou manualmente e salva estatísticas de CPU, RAM e Disco no arquivo de logs.

# Diretório base
BASE_DIR="$(dirname "$0")/.."
LOG_FILE="$BASE_DIR/logs/resource_usage.log"

# Garante que o diretório de logs existe
mkdir -p "$BASE_DIR/logs"

# Obter data atual
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Obter carga de CPU (Load Average - 1 minuto)
CPU_LOAD=$(cat /proc/loadavg | awk '{print $1}')

# Obter uso de Memória RAM (em Megabytes)
RAM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
RAM_USED=$(free -m | awk '/Mem:/ {print $3}')
RAM_FREE=$(free -m | awk '/Mem:/ {print $4}')
RAM_PCT=$(( RAM_USED * 100 / RAM_TOTAL ))

# Obter uso de Disco da partição raiz (/)
DISK_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
DISK_USED=$(df -h / | awk 'NR==2 {print $3}')
DISK_FREE=$(df -h / | awk 'NR==2 {print $4}')
DISK_PCT=$(df -h / | awk 'NR==2 {print $5}')

# Obter quantidade de processos Python ativos
PYTHON_PROC_COUNT=$(ps aux | grep python | grep -v grep | wc -l)

# Escrever no log
echo "[$TIMESTAMP] CPU Load (1m): $CPU_LOAD | RAM: ${RAM_USED}MB/${RAM_TOTAL}MB (${RAM_PCT}%) | Disco: ${DISK_USED}/${DISK_TOTAL} (${DISK_PCT}) | Proc Python: $PYTHON_PROC_COUNT" >> "$LOG_FILE"
