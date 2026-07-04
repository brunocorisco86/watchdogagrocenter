#!/bin/sh
# setup_alpine.sh - Script de comissionamento minimalista para Alpine Linux no Raspberry Pi 3B.
# Este script deve ser executado como root ou com privilégios equivalentes (doas/sudo).

set -e

echo "=== INICIANDO COMISSIONAMENTO DO WATCHDOG NO ALPINE LINUX ==="

# 1. Atualizar repositórios e pacotes
echo "-> Atualizando pacotes..."
apk update
apk upgrade

# 2. Instalar dependências minimalistas
echo "-> Instalando dependências de runtime (Python, SQLite, Git)..."
apk add python3 py3-pip sqlite sqlite-libs git bash tzdata

# 3. Configurar fuso horário (ex: America/Sao_Paulo)
echo "-> Configurando fuso horário..."
cp /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
echo "America/Sao_Paulo" > /etc/timezone

# 4. Criar estrutura de logs do Watchdog
echo "-> Criando diretório de logs..."
mkdir -p ../logs
touch ../logs/watchdog.log
touch ../logs/cron_execution.log

# 5. Garantir permissões nos scripts
echo "-> Configurando permissões de execução dos scripts..."
chmod +x run_watchdog.sh
chmod +x setup_alpine.sh

# 6. Criar e configurar o ambiente virtual
echo "-> Configurando ambiente virtual Python (venv) no diretório do projeto..."
cd ..
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Ativa venv e instala dependências
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 7. Habilitar e iniciar o serviço de cron (crond) no Alpine
echo "-> Configurando serviço crond (OpenRC)..."
rc-update add crond default
rc-service crond start || echo "Nota: crond já pode estar rodando ou openrc indisponível no momento."

# 8. Adicionar entrada no cron
CRON_PATH="/etc/crontabs/root"
CRON_JOB="*/5 * * * * $(pwd)/scripts/run_watchdog.sh"

if [ -f "$CRON_PATH" ]; then
    if grep -q "run_watchdog.sh" "$CRON_PATH"; then
        echo "-> Tarefa cron já configurada."
    else
        echo "-> Adicionando tarefa cron para rodar a cada 5 minutos..."
        echo "$CRON_JOB" >> "$CRON_PATH"
        # Reinicia o crond para carregar a nova configuração
        rc-service crond restart || killall crond && crond
    fi
else
    echo "-> /etc/crontabs/root não encontrado. Adicione a seguinte linha manualmente no crontab (crontab -e):"
    echo "$CRON_JOB"
fi

echo "=== COMISSIONAMENTO CONCLUÍDO COM SUCESSO! ==="
echo "Por favor, configure as variáveis de ambiente no arquivo '.env' na raiz do projeto antes do primeiro teste."
