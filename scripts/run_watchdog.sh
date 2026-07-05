#!/bin/sh

# Determina dinamicamente o caminho para a raiz do projeto baseado na localização do próprio script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Navega para o diretório do projeto
cd "$PROJECT_DIR" || { echo "Erro ao acessar o diretório $PROJECT_DIR"; exit 1; }

# Verifica se o ambiente virtual existe
if [ ! -d "venv" ]; then
    echo "Ambiente virtual 'venv' não encontrado. Executando configuração inicial..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Ativa o ambiente virtual e executa o watchdog
. venv/bin/activate
python3 src/watchdog/watchdog_cli.py >> logs/cron_execution.log 2>&1
deactivate
