document.addEventListener('DOMContentLoaded', () => {
    const btnTrigger = document.getElementById('btn-trigger');
    const btnText = btnTrigger ? btnTrigger.querySelector('.btn-text') : null;
    const btnLoader = btnTrigger ? btnTrigger.querySelector('.btn-loader') : null;
    const terminalBody = document.getElementById('terminal-body');
    const sysLogBody = document.getElementById('sys-log-body');
    
    let currentPeriod = '30d';
    let latencyChart = null;

    // Função para rolar os terminais para baixo
    const scrollToBottom = (element) => {
        if (element) {
            element.scrollTop = element.scrollHeight;
        }
    };

    // Rola para baixo inicialmente
    scrollToBottom(terminalBody);
    scrollToBottom(sysLogBody);

    // Event listener para os botões de filtro de período
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            
            // Injeta comando de filtro no terminal
            appendTerminalLine(`pi@cvale-watchdog:~$ watchdog --filter-period ${currentPeriod.toUpperCase()}`, 'output-prompt');
            appendTerminalLine(`Filtrando métricas do banco SQLite para o período de ${currentPeriod.toUpperCase()}...`, 'output-system');
            
            await updateDashboardData();
        });
    });

    // Event listener para o gatilho manual do watchdog
    if (btnTrigger) {
        btnTrigger.addEventListener('click', async () => {
            btnTrigger.disabled = true;
            if (btnText) btnText.textContent = 'RUNNING...';
            if (btnLoader) btnLoader.classList.remove('hidden');

            appendTerminalLine('pi@cvale-watchdog:~$ python3 src/watchdog/watchdog_cli.py --manual-trigger', 'output-prompt');
            appendTerminalLine('Acessando serviço Agrocenter e validando premissas de integridade...', 'output-system');

            try {
                const response = await fetch('/api/trigger', { method: 'POST' });
                const data = await response.json();

                if (response.ok) {
                    appendTerminalLine(`Sucesso: ${data.message}`, 'output-success');
                    await updateDashboardData();
                } else {
                    appendTerminalLine(`Erro do Servidor: ${data.message}`, 'output-error');
                }
            } catch (error) {
                appendTerminalLine(`Falha de Conectividade Local: ${error.message}`, 'output-error');
            } finally {
                btnTrigger.disabled = false;
                if (btnText) btnText.textContent = '> RUN_CHECK';
                if (btnLoader) btnLoader.classList.add('hidden');
                scrollToBottom(terminalBody);
            }
        });
    }

    // Função para injetar uma linha no terminal SQLite
    function appendTerminalLine(text, className) {
        if (!terminalBody) return;
        const line = document.createElement('div');
        line.className = `term-line ${className}`;
        line.textContent = text;
        
        const cursorLine = terminalBody.querySelector('.blink-cursor');
        if (cursorLine) {
            terminalBody.insertBefore(line, cursorLine);
        } else {
            terminalBody.appendChild(line);
        }
        scrollToBottom(terminalBody);
    }

    // Função para atualizar os logs do sistema físico (watchdog.log)
    async function updateSystemLogs() {
        if (!sysLogBody) return;
        try {
            const response = await fetch('/api/system-logs');
            const logs = await response.json();
            
            // Remove linhas antigas do terminal de sistema
            const existingLines = sysLogBody.querySelectorAll('.term-line:not(.blink-cursor)');
            existingLines.forEach(el => el.remove());
            
            if (Array.isArray(logs) && logs.length > 0) {
                const cursorLine = sysLogBody.querySelector('.blink-cursor');
                logs.forEach(logLine => {
                    const line = document.createElement('div');
                    line.className = 'term-line output-system';
                    line.textContent = logLine;
                    
                    if (cursorLine) {
                        sysLogBody.insertBefore(line, cursorLine);
                    } else {
                        sysLogBody.appendChild(line);
                    }
                });
            }
            scrollToBottom(sysLogBody);
        } catch (err) {
            console.error("Erro ao carregar logs do sistema: ", err);
        }
    }

    // Função para renderizar/atualizar o gráfico de latência
    async function updateLatencyChart() {
        const ctx = document.getElementById('latencyChart');
        if (!ctx) return;

        try {
            const response = await fetch('/api/latency-6h');
            const data = await response.json();

            // Extrai as labels (horas formatadas) e dados (latência em ms)
            const labels = [];
            const values = [];
            
            data.forEach(item => {
                // Formata timestamp ISO para 'HH:MM:SS'
                try {
                    const dt = new Date(item.timestamp);
                    const formattedTime = dt.toLocaleTimeString('pt-BR', { hour12: false });
                    labels.push(formattedTime);
                } catch {
                    labels.push(item.timestamp);
                }
                values.push(item.is_healthy ? item.response_time_ms : null);
            });

            // Se o gráfico já existe, destrói para evitar sobreposição
            if (latencyChart) {
                latencyChart.destroy();
            }

            // Inicializa Chart.js com tema nerd/hacker
            latencyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Tempo de Resposta (ms)',
                        data: values,
                        borderColor: '#00ff66',
                        backgroundColor: 'rgba(0, 255, 102, 0.08)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.2,
                        pointRadius: 3,
                        pointBackgroundColor: '#00ff66',
                        spanGaps: true // Ignora falhas para não quebrar a linha do gráfico
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { family: 'Fira Code', size: 10 }
                            }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.03)' },
                            ticks: {
                                color: '#94a3b8',
                                font: { family: 'Fira Code', size: 10 }
                            },
                            suggestedMin: 0
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        } catch (err) {
            console.error("Erro ao carregar o gráfico: ", err);
        }
    }

    // Função para atualizar os dados gerais do Dashboard via API
    async function updateDashboardData() {
        try {
            // 1. Atualizar KPIs com filtro de período ativo
            const kpisResponse = await fetch(`/api/kpis?period=${currentPeriod}`);
            const kpis = kpisResponse.ok ? await kpisResponse.json() : null;

            if (kpis) {
                document.querySelector('[data-kpi="availability"] .kpi-value').textContent = `${kpis.availability}%`;
                document.querySelector('[data-kpi="latency"] .kpi-value').textContent = `${kpis.avg_response_time} ms`;
                document.querySelector('[data-kpi="checks"] .kpi-value').textContent = kpis.total_checks;
                
                const incidentCard = document.querySelector('[data-kpi="incidents"]');
                const incidentValue = incidentCard.querySelector('.kpi-value');
                const incidentText = incidentCard.querySelector('p');
                
                incidentValue.textContent = kpis.total_incidents;
                
                const statusDot = document.querySelector('.status-indicator-dot');
                const statusLabel = document.querySelector('.status-label');

                if (kpis.active_incident) {
                    if (incidentCard) incidentCard.classList.add('kpi-alert');
                    if (incidentText) incidentText.textContent = `1 ativo no momento`;
                    
                    if (statusDot) statusDot.className = 'status-indicator-dot status-down-pulse';
                    if (statusLabel) statusLabel.textContent = 'SISTEMA EM ALERTA (OFFLINE)';
                } else {
                    if (incidentCard) incidentCard.classList.remove('kpi-alert');
                    if (incidentText) incidentText.textContent = `0 incidentes ativos`;
                    
                    if (statusDot) statusDot.className = 'status-indicator-dot status-up-pulse';
                    if (statusLabel) statusLabel.textContent = 'SISTEMA OPERACIONAL';
                }

                // Atualizar o Painel de Distribuição de Erros
                const errorStatsBody = document.getElementById('error-stats-body');
                if (errorStatsBody) {
                    if (kpis.error_distribution && kpis.error_distribution.length > 0) {
                        errorStatsBody.innerHTML = '';
                        kpis.error_distribution.forEach(err => {
                            const item = document.createElement('div');
                            item.className = 'error-stat-item';
                            item.innerHTML = `
                                <div class="error-stat-meta">
                                    <span class="error-name" title="${err.error_message}">${err.error_message}</span>
                                    <span class="error-pct">${err.percentage}%</span>
                                </div>
                                <div class="error-bar-container">
                                    <div class="error-bar-fill" style="width: ${err.percentage}%"></div>
                                </div>
                                <div class="error-count">${err.count} ocorrências</div>
                            `;
                            errorStatsBody.appendChild(item);
                        });
                    } else {
                        errorStatsBody.innerHTML = `
                            <div class="no-errors-message">
                                Nenhum erro registrado no período.<br>Sistema 100% operacional.
                            </div>
                        `;
                    }
                }
            }

            // 2. Atualizar Logs do Terminal SQLite
            const logsResponse = await fetch('/api/logs');
            const logs = logsResponse.ok ? await logsResponse.json() : [];

            if (logs.length > 0 && terminalBody) {
                const existingLogs = terminalBody.querySelectorAll('.term-line:not(.output-system):not(.output-prompt):not(.blink-cursor)');
                existingLogs.forEach(el => el.remove());

                const cursorLine = terminalBody.querySelector('.blink-cursor');
                logs.forEach(log => {
                    const statusText = log.is_healthy ? 'OK' : `ERRO: ${log.error_message}`;
                    const lineText = `[${log.timestamp}] - HTTP ${log.status_code} - ${log.response_time_ms}ms - ${statusText}`;
                    const className = log.is_healthy ? 'output-success' : 'output-error';
                    
                    const line = document.createElement('div');
                    line.className = `term-line ${className}`;
                    line.textContent = lineText;
                    
                    if (cursorLine) {
                        terminalBody.insertBefore(line, cursorLine);
                    } else {
                        terminalBody.appendChild(line);
                    }
                });
                scrollToBottom(terminalBody);
            }

            // 3. Atualizar logs do sistema de arquivos e gráfico temporal
            await updateSystemLogs();
            await updateLatencyChart();
        } catch (err) {
            console.error("Erro ao atualizar o painel: ", err);
        }
    }

    // === GERENCIADOR DE CONTATOS (Nova Feature) ===
    const contactsTbody = document.getElementById('contacts-tbody');
    const contactsForm = document.getElementById('contacts-form');
    const formError = document.getElementById('form-error');

    async function loadContacts() {
        if (!contactsTbody) return;
        try {
            const response = await fetch('/api/contacts');
            const contacts = await response.json();
            
            contactsTbody.innerHTML = '';
            
            if (Array.isArray(contacts) && contacts.length > 0) {
                contacts.forEach(c => {
                    const row = document.createElement('tr');
                    
                    const nameTd = document.createElement('td');
                    nameTd.textContent = c.name;
                    
                    const emailTd = document.createElement('td');
                    emailTd.textContent = c.email;
                    
                    const telegramTd = document.createElement('td');
                    telegramTd.textContent = c.telegram_id ? c.telegram_id : 'N/A';
                    
                    const statusTd = document.createElement('td');
                    statusTd.innerHTML = c.enabled ? '<span class="badge-active-status">● ATIVO</span>' : 'INATIVO';
                    
                    const actionsTd = document.createElement('td');
                    actionsTd.style.textAlign = 'center';
                    
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'btn-delete-contact';
                    deleteBtn.textContent = '[ REMOVER ]';
                    deleteBtn.addEventListener('click', () => deleteContact(c.email));
                    
                    actionsTd.appendChild(deleteBtn);
                    
                    row.appendChild(nameTd);
                    row.appendChild(emailTd);
                    row.appendChild(telegramTd);
                    row.appendChild(statusTd);
                    row.appendChild(actionsTd);
                    
                    contactsTbody.appendChild(row);
                });
            } else {
                contactsTbody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; color: var(--text-secondary);">
                            Nenhum contato cadastrado.
                        </td>
                    </tr>
                `;
            }
        } catch (err) {
            console.error("Erro ao carregar contatos: ", err);
        }
    }

    async function deleteContact(email) {
        if (!confirm(`Deseja realmente remover o contato ${email}?`)) return;
        
        try {
            const response = await fetch('/api/contacts/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json();
            
            if (response.ok) {
                appendTerminalLine(`pi@cvale-watchdog:~$ contacts --delete ${email}`, 'output-prompt');
                appendTerminalLine(`Sucesso: ${data.message}`, 'output-success');
                await loadContacts();
            } else {
                alert(`Erro: ${data.error}`);
            }
        } catch (err) {
            console.error("Erro ao excluir contato: ", err);
        }
    }

    if (contactsForm) {
        contactsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            formError.classList.add('hidden');
            
            const name = document.getElementById('contact-name').value;
            const email = document.getElementById('contact-email').value;
            const telegram_id = document.getElementById('contact-telegram').value;
            
            try {
                const response = await fetch('/api/contacts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, email, telegram_id })
                });
                const data = await response.json();
                
                if (response.ok) {
                    appendTerminalLine(`pi@cvale-watchdog:~$ contacts --add "${name}" --email ${email}`, 'output-prompt');
                    appendTerminalLine(`Sucesso: ${data.message}`, 'output-success');
                    
                    contactsForm.reset();
                    await loadContacts();
                } else {
                    formError.textContent = data.error || 'Erro ao adicionar contato.';
                    formError.classList.remove('hidden');
                }
            } catch (err) {
                console.error("Erro ao adicionar contato: ", err);
                formError.textContent = 'Falha de comunicação com o servidor.';
                formError.classList.remove('hidden');
            }
        });
    }

    // Inicialização geral
    updateDashboardData();
    loadContacts();

    // Auto-atualização de logs e gráficos a cada 30 segundos
    setInterval(updateDashboardData, 30000);
});
