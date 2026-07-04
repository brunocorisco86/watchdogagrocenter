document.addEventListener('DOMContentLoaded', () => {
    const btnTrigger = document.getElementById('btn-trigger');
    const btnText = btnTrigger.querySelector('.btn-text');
    const btnLoader = btnTrigger.querySelector('.btn-loader');
    const terminalBody = document.getElementById('terminal-body');

    // Função para rolar o terminal para baixo
    const scrollToBottom = () => {
        terminalBody.scrollTop = terminalBody.scrollHeight;
    };

    // Rola para baixo inicialmente
    scrollToBottom();

    // Event listener para o gatilho manual do watchdog
    btnTrigger.addEventListener('click', async () => {
        // Bloqueia botão e mostra loading
        btnTrigger.disabled = true;
        btnText.textContent = 'RUNNING...';
        btnLoader.classList.remove('hidden');

        // Cria a linha de comando no terminal de simulação
        appendTerminalLine('pi@cvale-watchdog:~$ python3 src/watchdog/watchdog_cli.py --manual-trigger', 'output-prompt');
        appendTerminalLine('Acessando serviço Agrocenter e validando premissas de integridade...', 'output-system');

        try {
            const response = await fetch('/api/trigger', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();

            if (response.ok) {
                appendTerminalLine(`Sucesso: ${data.message}`, 'output-success');
                // Atualiza a tela
                await updateDashboardData();
            } else {
                appendTerminalLine(`Erro do Servidor: ${data.message}`, 'output-error');
            }
        } catch (error) {
            appendTerminalLine(`Falha de Conectividade Local: ${error.message}`, 'output-error');
        } finally {
            // Desbloqueia botão
            btnTrigger.disabled = false;
            btnText.textContent = '> RUN_CHECK';
            btnLoader.classList.add('hidden');
            scrollToBottom();
        }
    });

    // Função para injetar uma linha no terminal
    function appendTerminalLine(text, className) {
        const line = document.createElement('div');
        line.className = `term-line ${className}`;
        line.textContent = text;
        
        // Insere a linha antes do cursor do prompt (o último elemento '_')
        const cursorLine = terminalBody.querySelector('.blink-cursor');
        terminalBody.insertBefore(line, cursorLine);
        scrollToBottom();
    }

    // Função para atualizar os dados do Dashboard via API
    async function updateDashboardData() {
        try {
            // 1. Atualizar KPIs
            const kpisResponse = await fetch('/api/kpis');
            const kpis = await kpisResponse.ok ? await kpisResponse.json() : null;

            if (kpis) {
                document.querySelector('[data-kpi="availability"] .kpi-value').textContent = `${kpis.availability}%`;
                document.querySelector('[data-kpi="latency"] .kpi-value').textContent = `${kpis.avg_response_time} ms`;
                document.querySelector('[data-kpi="checks"] .kpi-value').textContent = kpis.total_checks;
                
                const incidentCard = document.querySelector('[data-kpi="incidents"]');
                const incidentValue = incidentCard.querySelector('.kpi-value');
                const incidentText = incidentCard.querySelector('p');
                
                incidentValue.textContent = kpis.total_incidents;
                
                // Trata visualmente a queda ativa
                const statusDot = document.querySelector('.status-indicator-dot');
                const statusLabel = document.querySelector('.status-label');

                if (kpis.active_incident) {
                    incidentCard.classList.add('kpi-alert');
                    incidentText.textContent = `1 ativo no momento`;
                    
                    statusDot.className = 'status-indicator-dot status-down-pulse';
                    statusLabel.textContent = 'SISTEMA EM ALERTA (OFFLINE)';
                } else {
                    incidentCard.classList.remove('kpi-alert');
                    incidentText.textContent = `0 incidentes ativos`;
                    
                    statusDot.className = 'status-indicator-dot status-up-pulse';
                    statusLabel.textContent = 'SISTEMA OPERACIONAL';
                }
            }

            // 2. Atualizar Logs do Terminal
            const logsResponse = await fetch('/api/logs');
            const logs = await logsResponse.ok ? await logsResponse.json() : [];

            if (logs.length > 0) {
                // Remove as linhas de log antigas (linhas com output-success ou output-error que não sejam interativas)
                const existingLogs = terminalBody.querySelectorAll('.output-success, .output-error');
                existingLogs.forEach(el => el.remove());

                // Adiciona os novos logs de cima para baixo
                logs.forEach(log => {
                    const statusText = log.is_healthy ? 'OK' : `ERRO: ${log.error_message}`;
                    const lineText = `[${log.timestamp}] - HTTP ${log.status_code} - ${log.response_time_ms}ms - ${statusText}`;
                    const className = log.is_healthy ? 'output-success' : 'output-error';
                    
                    // Injeta antes do cursor
                    const line = document.createElement('div');
                    line.className = `term-line ${className}`;
                    line.textContent = lineText;
                    
                    const cursorLine = terminalBody.querySelector('.blink-cursor');
                    terminalBody.insertBefore(line, cursorLine);
                });
            }
        } catch (err) {
            console.error("Erro ao atualizar o painel: ", err);
        }
    }

    // Loop de auto-atualização de KPIs a cada 30 segundos
    setInterval(updateDashboardData, 30000);
});
