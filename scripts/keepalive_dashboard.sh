#!/bin/bash

# 🛡️ C.Vale Agrocenter Watchdog - Keepalive do Dashboard
# Script de resiliência para monitorar se o dashboard local Flask caiu e reiniciá-lo automaticamente.

# Obtém o diretório do script e sobe um nível para encontrar a raiz do projeto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
LOG_FILE="$PROJECT_DIR/logs/keepalive.log"

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# Verifica se o dashboard responde na porta 5080
if ! curl -s --head --connect-timeout 3 http://localhost:5080/ > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [ALERTA] Dashboard Flask offline ou travado! Iniciando recuperacao..." >> "$LOG_FILE"
    
    # Localiza qualquer PID escutando na porta 5080 usando métodos seguros e portáteis
    ZOMBIE_PID=""
    
    # 1. Tenta usando netstat (altamente compatível com Alpine/BusyBox e Linux padrão)
    if [ -z "$ZOMBIE_PID" ]; then
        ZOMBIE_PID=$(netstat -tpln 2>/dev/null | grep -E ':5080\b' | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$')
    fi
    
    # 2. Tenta usando ss
    if [ -z "$ZOMBIE_PID" ]; then
        ZOMBIE_PID=$(ss -tulpn 2>/dev/null | grep -E ':5080\b' | grep -oE 'pid=[0-9]+' | cut -d= -f2 | head -n1)
    fi
    
    # 3. Tenta usando lsof (apenas se for o lsof real e suportar a porta)
    if [ -z "$ZOMBIE_PID" ] && lsof -i :5080 -t >/dev/null 2>&1; then
        ZOMBIE_PID=$(lsof -t -i:5080 2>/dev/null)
    fi

    # Garante que encontramos um PID numérico válido antes de tentar matar
    if [ ! -z "$ZOMBIE_PID" ] && echo "$ZOMBIE_PID" | grep -E -q '^[0-9]+$'; then
        # Proteção extra: apenas mata se o processo for Python ou Flask
        if ps -p "$ZOMBIE_PID" -o comm= 2>/dev/null | grep -q -E 'python|flask'; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - [INFO] Terminando processo zumbi $ZOMBIE_PID na porta 5080" >> "$LOG_FILE"
            kill -9 "$ZOMBIE_PID" 2>/dev/null
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - [AVISO] PID $ZOMBIE_PID encontrado na porta 5080, mas nao e Python/Flask. Operacao abortada por seguranca." >> "$LOG_FILE"
        fi
    fi
    
    # Inicia o servidor Flask em background usando o ambiente virtual desacoplado (setsid)
    cd "$PROJECT_DIR"
    setsid ./venv/bin/python3 src/dashboard/app.py >> "$PROJECT_DIR/logs/dashboard_error.log" 2>&1 &
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - [SUCESSO] Servidor Flask reiniciado em background." >> "$LOG_FILE"
else
    # Registro de integridade silencioso
    # echo "$(date '+%Y-%m-%d %H:%M:%S') - Dashboard OK." >> "$LOG_FILE"
    :
fi
