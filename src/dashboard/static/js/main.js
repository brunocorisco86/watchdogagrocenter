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

        // Atualiza dinamicamente o título do gráfico com base no filtro
        const chartTitleElement = document.querySelector('.chart-title');
        if (chartTitleElement) {
            const labelMap = {
                '1h': 'ÚLTIMA 1 HORA',
                '6h': 'ÚLTIMAS 6 HORAS',
                '1d': 'ÚLTIMO 1 DIA',
                '1w': 'ÚLTIMA 1 SEMANA',
                '30d': 'ÚLTIMO MÊS'
            };
            const periodLabel = labelMap[currentPeriod] || 'ÚLTIMAS 6 HORAS';
            chartTitleElement.textContent = `[SÉRIE TEMPORAL: LATÊNCIA DO PORTAL (${periodLabel})]`;
        }

        try {
            const response = await fetch(`/api/latency-6h?period=${currentPeriod}`);
            let data = await response.json();

            if (!Array.isArray(data)) {
                data = [];
            }

            // Ordena os logs de forma cronológica garantida (do mais antigo para o mais recente)
            data.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

            // Extrai as labels (horas formatadas HH:MM) e dados (latência em ms)
            const labels = [];
            const values = [];
            
            data.forEach(item => {
                // Extrai a hora HH:MM diretamente do timestamp (evita flutuações de fuso horário)
                try {
                    const timePart = item.timestamp.split(' ')[1] || item.timestamp;
                    const hhmm = timePart.substring(0, 5); // Pega apenas 'HH:MM'
                    labels.push(hhmm);
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
                        pointRadius: 2,
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
                                font: { family: 'Fira Code', size: 10 },
                                maxTicksLimit: 10 // Limita a quantidade de marcações no eixo X para evitar poluição visual
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
    const formTitle = document.getElementById('form-title');
    const contactOriginalEmail = document.getElementById('contact-original-email');
    const btnSubmitContact = document.getElementById('btn-submit-contact');
    const btnCancelEdit = document.getElementById('btn-cancel-edit');

    let settingsCache = {
        level1_minutes: 15,
        level2_minutes: 60,
        level3_minutes: 150,
        level4_minutes: 720
    };

    function formatMinutesText(minutes) {
        if (minutes >= 60) {
            const h = minutes / 60;
            if (h === parseInt(h)) {
                return `${parseInt(h)}h`;
            }
            return `${h}h`;
        }
        return `${minutes}m`;
    }

    async function loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            if (response.ok) {
                settingsCache = data;
                applySettingsToDOM();
            }
        } catch (err) {
            console.error("Erro ao carregar configurações: ", err);
        }
    }

    function applySettingsToDOM() {
        const formatLongText = (minutes) => {
            if (minutes >= 60) {
                const h = minutes / 60;
                if (h === parseInt(h)) {
                    return `${parseInt(h)} ${parseInt(h) === 1 ? 'hora' : 'horas'}`;
                }
                return `${h} horas`;
            }
            return `${minutes} minutos`;
        };
        
        const checkInterval = 3;
        const l1_fail = Math.max(1, Math.floor(settingsCache.level1_minutes / checkInterval));
        const l2_fail = Math.max(1, Math.floor(settingsCache.level2_minutes / checkInterval));
        const l3_fail = Math.max(1, Math.floor(settingsCache.level3_minutes / checkInterval));
        const l4_fail = Math.max(1, Math.floor(settingsCache.level4_minutes / checkInterval));
        
        const options = document.querySelectorAll('#contact-level option');
        if (options.length === 4) {
            options[0].textContent = `Nível 1 - Operacional TI (Após ${formatLongText(settingsCache.level1_minutes)} off / ${l1_fail} ${l1_fail === 1 ? 'falha' : 'falhas'})`;
            options[1].textContent = `Nível 2 - Analista / Coordenação (Após ${formatLongText(settingsCache.level2_minutes)} off / ${l2_fail} ${l2_fail === 1 ? 'falha' : 'falhas'})`;
            options[2].textContent = `Nível 3 - Gerência (Após ${formatLongText(settingsCache.level3_minutes)} off / ${l3_fail} ${l3_fail === 1 ? 'falha' : 'falhas'})`;
            options[3].textContent = `Nível 4 - Diretoria (Após ${formatLongText(settingsCache.level4_minutes)} off / ${l4_fail} ${l4_fail === 1 ? 'falha' : 'falhas'})`;
        }
    }

    async function loadContacts() {
        if (!contactsTbody) return;
        try {
            await loadSettings();
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
                    
                    // Coluna Nível dinâmico
                    const levelTd = document.createElement('td');
                    let levelText = `Nível 1 - Operacional TI (${formatMinutesText(settingsCache.level1_minutes)} off)`;
                    if (c.level === 2) levelText = `Nível 2 - Analista / Coordenação (${formatMinutesText(settingsCache.level2_minutes)} off)`;
                    else if (c.level === 3) levelText = `Nível 3 - Gerência (${formatMinutesText(settingsCache.level3_minutes)} off)`;
                    else if (c.level === 4) levelText = `Nível 4 - Diretoria (${formatMinutesText(settingsCache.level4_minutes)} off)`;
                    levelTd.textContent = levelText;
                    
                    // Coluna Departamento
                    const deptTd = document.createElement('td');
                    deptTd.textContent = c.department === 'NEGOCIO' ? 'NEGÓCIO' : 'TI';
                    
                    const statusTd = document.createElement('td');
                    statusTd.innerHTML = c.enabled ? '<span class="badge-active-status">● ATIVO</span>' : 'INATIVO';
                    
                    const actionsTd = document.createElement('td');
                    actionsTd.style.textAlign = 'center';
                    
                    // Botão Editar
                    const editBtn = document.createElement('button');
                    editBtn.className = 'btn-edit-contact';
                    editBtn.textContent = '[ EDITAR ]';
                    editBtn.addEventListener('click', () => editContact(c));
                    
                    // Botão Remover
                    const deleteBtn = document.createElement('button');
                    deleteBtn.className = 'btn-delete-contact';
                    deleteBtn.textContent = '[ REMOVER ]';
                    deleteBtn.addEventListener('click', () => deleteContact(c.email));
                    
                    actionsTd.appendChild(editBtn);
                    actionsTd.appendChild(deleteBtn);
                    
                    row.appendChild(nameTd);
                    row.appendChild(emailTd);
                    row.appendChild(telegramTd);
                    row.appendChild(levelTd);
                    row.appendChild(deptTd);
                    row.appendChild(statusTd);
                    row.appendChild(actionsTd);
                    
                    contactsTbody.appendChild(row);
                });
            } else {
                contactsTbody.innerHTML = `
                    <tr>
                        <td colspan="7" style="text-align: center; color: var(--text-secondary);">
                            Nenhum contato cadastrado.
                        </td>
                    </tr>
                `;
            }
        } catch (err) {
            console.error("Erro ao carregar contatos: ", err);
        }
    }

    function editContact(c) {
        if (!contactsForm) return;
        
        // Ativa o modo de edição preenchendo os dados
        contactOriginalEmail.value = c.email;
        document.getElementById('contact-name').value = c.name;
        document.getElementById('contact-email').value = c.email;
        document.getElementById('contact-telegram').value = c.telegram_id || '';
        document.getElementById('contact-level').value = c.level || 1;
        document.getElementById('contact-dept').value = c.department || 'TI';
        
        // Altera títulos e botões
        formTitle.textContent = '✎ EDITAR DESTINATÁRIO';
        btnSubmitContact.textContent = '> SALVAR ALTERAÇÕES';
        btnSubmitContact.style.borderColor = 'var(--blue-glow)';
        btnSubmitContact.style.color = 'var(--blue-glow)';
        btnCancelEdit.classList.remove('hidden');
        
        // Rola até o formulário para facilidade do usuário
        contactsForm.scrollIntoView({ behavior: 'smooth' });
    }

    function resetFormState() {
        if (!contactsForm) return;
        contactsForm.reset();
        contactOriginalEmail.value = '';
        document.getElementById('contact-level').value = "1";
        document.getElementById('contact-dept').value = "TI";
        formTitle.textContent = '+ NOVO DESTINATÁRIO';
        btnSubmitContact.textContent = '> CADASTRAR';
        btnSubmitContact.style.borderColor = 'var(--green-hacker)';
        btnSubmitContact.style.color = 'var(--green-hacker)';
        btnCancelEdit.classList.add('hidden');
        formError.classList.add('hidden');
    }

    if (btnCancelEdit) {
        btnCancelEdit.addEventListener('click', resetFormState);
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
                // Se o contato removido for o que estava sendo editado, reseta o formulário
                if (contactOriginalEmail.value === email) {
                    resetFormState();
                }
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
            
            const originalEmail = contactOriginalEmail.value;
            const name = document.getElementById('contact-name').value;
            const email = document.getElementById('contact-email').value;
            const telegram_id = document.getElementById('contact-telegram').value;
            const level = parseInt(document.getElementById('contact-level').value);
            const department = document.getElementById('contact-dept').value;
            
            const isEditMode = originalEmail && originalEmail.trim() !== '';
            const endpoint = isEditMode ? '/api/contacts/update' : '/api/contacts';
            const payload = isEditMode 
                ? { original_email: originalEmail, name, email, telegram_id, level, department }
                : { name, email, telegram_id, level, department };
            
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                
                if (response.ok) {
                    const termCmd = isEditMode 
                        ? `contacts --update ${originalEmail} --email ${email}`
                        : `contacts --add "${name}" --email ${email}`;
                    
                    appendTerminalLine(`pi@cvale-watchdog:~$ ${termCmd}`, 'output-prompt');
                    appendTerminalLine(`Sucesso: ${data.message}`, 'output-success');
                    
                    resetFormState();
                    await loadContacts();
                } else {
                    formError.textContent = data.error || 'Erro ao processar contato.';
                    formError.classList.remove('hidden');
                }
            } catch (err) {
                console.error("Erro ao processar contato: ", err);
                formError.textContent = 'Falha de comunicação com o servidor.';
                formError.classList.remove('hidden');
            }
        });
    }

    // === CONFIGURAÇÃO DE LIMIARES (Modal Popup) ===
    const btnOpenSettings = document.getElementById('btn-open-settings');
    const btnCloseSettings = document.getElementById('btn-close-settings');
    const btnCancelSettings = document.getElementById('btn-cancel-settings');
    const settingsModal = document.getElementById('settings-modal');
    const settingsForm = document.getElementById('settings-form');
    const settingsError = document.getElementById('settings-error');
    const settingsSuccess = document.getElementById('settings-success');

    if (btnOpenSettings) {
        btnOpenSettings.addEventListener('click', async () => {
            if (settingsError) settingsError.classList.add('hidden');
            if (settingsSuccess) settingsSuccess.classList.add('hidden');
            
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();
                
                if (response.ok) {
                    document.getElementById('settings-level1').value = settings.level1_minutes || 15;
                    document.getElementById('settings-level2').value = settings.level2_minutes || 60;
                    document.getElementById('settings-level3').value = settings.level3_minutes || 150;
                    document.getElementById('settings-level4').value = settings.level4_minutes || 720;
                    
                    settingsModal.classList.remove('hidden');
                } else {
                    alert('Erro ao carregar configurações.');
                }
            } catch (err) {
                console.error("Erro ao obter configurações: ", err);
                alert('Erro de comunicação com o servidor.');
            }
        });
    }

    const closeSettingsModal = () => {
        if (settingsModal) {
            settingsModal.classList.add('hidden');
        }
    };

    if (btnCloseSettings) btnCloseSettings.addEventListener('click', closeSettingsModal);
    if (btnCancelSettings) btnCancelSettings.addEventListener('click', closeSettingsModal);

    window.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            closeSettingsModal();
        }
    });

    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (settingsError) settingsError.classList.add('hidden');
            if (settingsSuccess) settingsSuccess.classList.add('hidden');
            
            const level1_minutes = parseInt(document.getElementById('settings-level1').value);
            const level2_minutes = parseInt(document.getElementById('settings-level2').value);
            const level3_minutes = parseInt(document.getElementById('settings-level3').value);
            const level4_minutes = parseInt(document.getElementById('settings-level4').value);
            
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        level1_minutes,
                        level2_minutes,
                        level3_minutes,
                        level4_minutes
                    })
                });
                const data = await response.json();
                
                if (response.ok) {
                    if (settingsSuccess) {
                        settingsSuccess.textContent = data.message;
                        settingsSuccess.classList.remove('hidden');
                    }
                    
                    appendTerminalLine(`pi@cvale-watchdog:~$ watchdog-config --set L1=${level1_minutes} L2=${level2_minutes} L3=${level3_minutes} L4=${level4_minutes}`, 'output-prompt');
                    appendTerminalLine('Limiares de SLA atualizados com sucesso no banco SQLite de produção!', 'output-success');
                    
                    await loadSettings();
                    await loadContacts();
                    
                    setTimeout(closeSettingsModal, 1200);
                } else {
                    if (settingsError) {
                        settingsError.textContent = data.error || 'Erro ao salvar configurações.';
                        settingsError.classList.remove('hidden');
                    }
                }
            } catch (err) {
                console.error("Erro ao salvar configurações: ", err);
                if (settingsError) {
                    settingsError.textContent = 'Falha de comunicação com o servidor.';
                    settingsError.classList.remove('hidden');
                }
            }
        });
    }

    // === CONTROLE DA ABA DE DOCUMENTAÇÕES ===
    const btnToggleDocs = document.getElementById('btn-toggle-docs');
    const dashboardTabContent = document.getElementById('dashboard-tab-content');
    const docsTabContent = document.getElementById('docs-tab-content');
    
    // Armazena o HTML inicial da arquitetura (Terminal 3) para podermos restaurá-lo
    const defaultArchTerminalHtml = document.getElementById('docs-terminal-body') ? document.getElementById('docs-terminal-body').innerHTML : '';
    const defaultArchTerminalTitle = document.getElementById('docs-terminal-title') ? document.getElementById('docs-terminal-title').textContent : '';

    if (btnToggleDocs && dashboardTabContent && docsTabContent) {
        btnToggleDocs.addEventListener('click', () => {
            const isDocsHidden = docsTabContent.classList.contains('hidden');
            if (isDocsHidden) {
                // Ir para a aba de documentação
                dashboardTabContent.classList.add('hidden');
                docsTabContent.classList.remove('hidden');
                btnToggleDocs.classList.add('active-tab-btn');
                btnToggleDocs.title = "Voltar para o Painel Principal";
                appendTerminalLine('pi@cvale-watchdog:~$ docs --view', 'output-prompt');
                appendTerminalLine('Aba de documentações ativada com sucesso.', 'output-success');
            } else {
                // Voltar para o painel principal
                docsTabContent.classList.add('hidden');
                dashboardTabContent.classList.remove('hidden');
                btnToggleDocs.classList.remove('active-tab-btn');
                btnToggleDocs.title = "Visualizar Documentação (docs/)";
                appendTerminalLine('pi@cvale-watchdog:~$ docs --close', 'output-prompt');
                appendTerminalLine('Aba de documentações fechada. Retornando ao dashboard.', 'output-success');
            }
        });
    }

    const docButtons = document.querySelectorAll('.doc-select-btn');
    const docsTerminalTitle = document.getElementById('docs-terminal-title');
    const docsTerminalBody = document.getElementById('docs-terminal-body');

    function escapeHtml(text) {
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatMarkdownToRetroTerminal(mdText) {
        const lines = mdText.split('\n');
        let formattedHtml = '';
        let insideCodeBlock = false;
        
        lines.forEach(line => {
            const trimmed = line.trim();
            
            // Código/Code blocks toggles
            if (trimmed.startsWith('```')) {
                insideCodeBlock = !insideCodeBlock;
                return;
            }
            
            if (insideCodeBlock) {
                formattedHtml += `<div class="term-line output-success" style="font-family: var(--font-mono); margin-left: 10px; white-space: pre;">${escapeHtml(line)}</div>`;
            } else if (trimmed.startsWith('#')) {
                // Headers
                const level = (line.match(/#/g) || []).length;
                const cleanText = line.replace(/#/g, '').trim();
                let sizeStyle = 'font-weight: bold; margin-top: 15px; margin-bottom: 5px;';
                if (level === 1) sizeStyle += ' color: var(--blue-glow); font-size: 1.1rem; border-bottom: 1px dashed rgba(59, 130, 246, 0.4); padding-bottom: 2px;';
                else if (level === 2) sizeStyle += ' color: #60a5fa; font-size: 0.95rem;';
                else sizeStyle += ' color: #93c5fd; font-size: 0.85rem;';
                
                formattedHtml += `<div class="term-line" style="${sizeStyle}">[ ${cleanText} ]</div>`;
            } else if (trimmed.startsWith('-') || trimmed.startsWith('*') || trimmed.startsWith('+') || /^\d+\./.test(trimmed)) {
                // Lists
                formattedHtml += `<div class="term-line output-system" style="margin-left: 15px;">${escapeHtml(line)}</div>`;
            } else if (trimmed.startsWith('>')) {
                // Blockquotes/Alerts
                const cleanQuote = line.replace(/^>\s*/, '').trim();
                formattedHtml += `<div class="term-line" style="color: #a7f3d0; background-color: rgba(16, 185, 129, 0.05); padding: 5px; border-left: 3px solid #10b981; margin: 5px 0 5px 10px; font-style: italic;">${escapeHtml(cleanQuote)}</div>`;
            } else if (trimmed === '') {
                formattedHtml += '<div class="term-line" style="height: 8px;"></div>';
            } else {
                // Normal line
                formattedHtml += `<div class="term-line" style="color: var(--text-primary); opacity: 0.95;">${escapeHtml(line)}</div>`;
            }
        });
        
        return formattedHtml;
    }

    docButtons.forEach(btn => {
        btn.addEventListener('click', async () => {
            // Remove classe active de todos
            docButtons.forEach(b => b.classList.remove('active-doc-btn'));
            btn.classList.add('active-doc-btn');
            
            const docPath = btn.getAttribute('data-doc');
            
            if (docPath === 'architecture') {
                // Restaurar Arquitetura Padrão (ASCII Art)
                if (docsTerminalTitle) docsTerminalTitle.textContent = defaultArchTerminalTitle;
                if (docsTerminalBody) docsTerminalBody.innerHTML = defaultArchTerminalHtml;
                return;
            }
            
            // Caso seja um documento markdown
            const filename = docPath.split('/').pop();
            if (docsTerminalTitle) {
                docsTerminalTitle.textContent = `[DOCUMENTO: ${filename.toUpperCase()}]`;
            }
            
            if (docsTerminalBody) {
                docsTerminalBody.innerHTML = `
                    <div class="term-line output-system">pi@cvale-watchdog:~$ cat ${docPath}</div>
                    <div class="term-line output-success">Carregando conteúdo do arquivo ${filename}...</div>
                    <div class="term-line output-prompt" style="margin-top: 10px; margin-bottom: 10px;">> LENDO BUFFER DE MEMÓRIA...</div>
                    <div id="doc-loading" class="term-line" style="color: var(--text-secondary);">Aguardando resposta do servidor...</div>
                `;
            }
            
            try {
                const response = await fetch(`/api/docs/${docPath}`);
                const data = await response.json();
                
                if (response.ok && docsTerminalBody) {
                    const formattedHtml = formatMarkdownToRetroTerminal(data.content);
                    docsTerminalBody.innerHTML = `
                        <div class="term-line output-system">pi@cvale-watchdog:~$ cat ${docPath}</div>
                        <div class="term-line output-success">Documento ${filename} carregado com sucesso.</div>
                        <hr style="border: none; border-top: 1px dashed rgba(59, 130, 246, 0.2); margin: 10px 0;">
                        <div class="doc-markdown-content" style="padding: 5px;">
                            ${formattedHtml}
                        </div>
                        <hr style="border: none; border-top: 1px dashed rgba(59, 130, 246, 0.2); margin: 10px 0;">
                        <div class="term-line output-system" style="margin-top: 10px;">pi@cvale-watchdog:~$ <span class="blink-cursor">_</span></div>
                    `;
                    docsTerminalBody.scrollTop = 0;
                } else {
                    if (docsTerminalBody) {
                        docsTerminalBody.innerHTML = `
                            <div class="term-line output-system">pi@cvale-watchdog:~$ cat ${docPath}</div>
                            <div class="term-line output-error">ERRO: Não foi possível carregar o arquivo. ${data.error || ''}</div>
                        `;
                    }
                }
            } catch (err) {
                console.error("Erro ao carregar documentação: ", err);
                if (docsTerminalBody) {
                    docsTerminalBody.innerHTML = `
                        <div class="term-line output-system">pi@cvale-watchdog:~$ cat ${docPath}</div>
                        <div class="term-line output-error">ERRO: Falha de conectividade HTTP com o servidor do dashboard.</div>
                    `;
                }
            }
        });
    });

    // Inicialização geral
    updateDashboardData();
    loadContacts();

    // Auto-atualização de logs e gráficos a cada 30 segundos
    setInterval(updateDashboardData, 30000);
});
