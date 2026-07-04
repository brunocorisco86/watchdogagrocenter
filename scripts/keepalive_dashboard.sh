#!/bin/bash

# 🛡️ C.Vale Agrocenter Watchdog - Keepalive do Dashboard
# Script de resiliência para monitorar se o dashboard local Flask caiu e reiniciá-lo automaticamente.

PROJECT_DIR="/home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/11_WATCHDOG_AGROCENTER"
LOG_FILE="$PROJECT_DIR/logs/keepalive.log"

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# Verifica se o dashboard responde na porta 5080
if ! curl -s --head --connect-timeout 3 http://localhost:5080/ > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [ALERTA] Dashboard Flask offline ou travado! Iniciando recuperacao..." >> "$LOG_FILE"
    
    # Localiza e encerra qualquer processo python zumbi escutando na porta 5080
    ZOMBIE_PID=$(lsof -t -i:5080 2>/dev/null)
    if [ ! -z "$ZOMBIE_PID" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - [INFO] Terminando processo zumbi $ZOMBIE_PID na porta 5080" >> "$LOG_FILE"
        kill -9 $ZOMBIE_PID 2>/dev/null
    fi
    
    # Inicia o servidor Flask em background usando o ambiente virtual
    cd "$PROJECT_DIR"
    nohup ./venv/bin/python3 src/dashboard/app.py >> "$PROJECT_DIR/logs/dashboard_error.log" 2>&1 &
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [SUCESSO] Servidor Flask reiniciado em background." >> "$LOG_FILE"
else
    # Registro de integridade silencioso
    # echo "$(date '+%Y-%m-%d %H:%M:%S') - Dashboard OK." >> "$LOG_FILE"
    :
fi
