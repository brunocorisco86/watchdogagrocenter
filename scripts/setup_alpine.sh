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
echo "-> Instalando dependências de runtime (Python, SQLite, Git, curl, lsof)..."
apk add python3 py3-pip sqlite sqlite-libs git bash tzdata curl lsof

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
chmod +x keepalive_dashboard.sh

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

# 8. Adicionar entradas de tarefas no cron
CRON_PATH="/etc/crontabs/root"
PWD_DIR=$(pwd)

JOB_CHECK="*/3 * * * * $PWD_DIR/scripts/run_watchdog.sh > /dev/null 2>&1"
JOB_DAILY="0 18 * * * cd $PWD_DIR && ./venv/bin/python3 src/watchdog/watchdog_cli.py --daily-report > /dev/null 2>&1"
JOB_MONTHLY="0 18 30 * * cd $PWD_DIR && ./venv/bin/python3 src/watchdog/watchdog_cli.py --monthly-report > /dev/null 2>&1"
JOB_KEEPALIVE="*/1 * * * * $PWD_DIR/scripts/keepalive_dashboard.sh > /dev/null 2>&1"
JOB_REBOOT="@reboot sleep 10 && $PWD_DIR/scripts/keepalive_dashboard.sh > /dev/null 2>&1"

if [ -f "$CRON_PATH" ]; then
    for JOB in "$JOB_CHECK" "$JOB_DAILY" "$JOB_MONTHLY" "$JOB_KEEPALIVE" "$JOB_REBOOT"; do
        # Determinar termo único ou expressão regular para busca no crontab
        if echo "$JOB" | grep -q -- "--daily-report"; then
            if grep -Fq "watchdog_cli.py --daily-report" "$CRON_PATH"; then
                echo "-> Tarefa diaria ja configurada no cron."
                continue
            fi
        elif echo "$JOB" | grep -q -- "--monthly-report"; then
            if grep -Fq "watchdog_cli.py --monthly-report" "$CRON_PATH"; then
                echo "-> Tarefa mensal ja configurada no cron."
                continue
            fi
        elif echo "$JOB" | grep -q "@reboot" && echo "$JOB" | grep -q "keepalive_dashboard.sh"; then
            if grep -q "@reboot" "$CRON_PATH" && grep -q "keepalive_dashboard.sh" "$CRON_PATH" && grep -E "@reboot.*keepalive_dashboard\.sh" "$CRON_PATH" > /dev/null 2>&1; then
                echo "-> Tarefa de reboot ja configurada no cron."
                continue
            fi
        else
            # Para os demais, extrai o script específico ou padrão para verificação
            if echo "$JOB" | grep -q "run_watchdog.sh"; then
                SEARCH="run_watchdog.sh"
            elif echo "$JOB" | grep -q "keepalive_dashboard.sh"; then
                # Verifica se é a tarefa periódica de keepalive (que no crontab não contém @reboot)
                if grep -v "@reboot" "$CRON_PATH" | grep -Fq "keepalive_dashboard.sh"; then
                    echo "-> Tarefa keepalive periodica ja configurada no cron."
                    continue
                fi
                SEARCH="keepalive_dashboard.sh"
            else
                SEARCH=$(echo "$JOB" | awk '{print $6}')
            fi

            if grep -Fq "$SEARCH" "$CRON_PATH"; then
                echo "-> Tarefa com '$SEARCH' ja configurada no cron."
                continue
            fi
        fi

        echo "-> Adicionando ao cron: $JOB"
        echo "$JOB" >> "$CRON_PATH"
    done
    # Reinicia o crond para carregar a nova configuração
    rc-service crond restart || killall -HUP crond || echo "Nota: Serviço cron reiniciado."
else
    echo "-> /etc/crontabs/root não encontrado. Adicione as seguintes linhas manualmente no crontab (crontab -e):"
    echo "$JOB_CHECK"
    echo "$JOB_DAILY"
    echo "$JOB_MONTHLY"
    echo "$JOB_KEEPALIVE"
    echo "$JOB_REBOOT"
fi


echo "=== COMISSIONAMENTO CONCLUÍDO COM SUCESSO! ==="
echo "Por favor, configure as variáveis de ambiente no arquivo '.env' na raiz do projeto antes do primeiro teste."
