# Changelog - C.Vale Watchdog Agrocenter

Todo o histórico de desenvolvimento e lançamentos deste projeto de monitoramento de alta disponibilidade será documentado neste arquivo.

A estrutura deste projeto rege-se pelos três pilares da solução: **Comunicação Eficiente** (plataforma centralizada/dashboard), **Processos Otimizados** (redesenho de fluxo e confirmação de testes) e **Tecnologia Habilitadora** (watchdog, resolvedores resilientes, bypass de DNS local e alertas autônomos).

---

## [1.1.0] - 2026-07-05

### 🚀 Ajuste de Frequência, Escalação e Identidade Visual

#### Adicionado
- **Novo Nível 4 de Escalação (12h)**: Criado o Nível 4 na política de alertas. Se a queda persistir por 12 horas consecutivas (240 falhas), todos os contatos ativos de todos os níveis (1, 2, 3 e 4) são notificados via Telegram e e-mail.
- **Identidade Visual no E-mail**: Adicionados os logos oficiais da C.Vale (PNG) e do Agrocenter (SVG) de forma combinada lado a lado no cabeçalho do template HTML do e-mail de alerta (`email_template.html`), usando tabelas HTML para máxima compatibilidade com clientes de e-mail como Microsoft Outlook desktop.
- **Identidade Visual no Dashboard**: Integração do logo do Agrocenter (`agro_center.svg`) no cabeçalho do Dashboard Flask, estilizado de forma elegante com efeito de drop-shadow neon azul brilhante no hover.
- **Resiliência contra WAF no download do Logo**: Download automatizado do SVG do site do Agrocenter usando script Python com `curl_cffi` para simular o handshake TLS do navegador Chrome, contornando o bloqueio HTTP 403 da Akamai.

#### Modificado
- **Frequência de Checagem (3 minutos)**: Alterado o ciclo de checagem do Watchdog de 5 minutos para 3 minutos. As configurações de `.env`, `.env.example`, scripts de deploy e manual de comissionamento foram atualizados para refletir o intervalo de 3 minutos (`*/3 * * * *`).
- **Política Dinâmica de Notificação por Nível**:
  - **Nível 1 (Operacional TI - 15 min off)**: Ativado exatamente no 5º erro consecutivo (as falhas anteriores de 1 a 4 tornaram-se silenciosas).
  - **Nível 2 (Supervisão - 1h off)**: Ativado exatamente no 20º erro consecutivo.
  - **Nível 3 (Diretoria - 2.5h off)**: Ativado exatamente no 50º erro consecutivo.
- **Despoluição e Ordenação do Gráfico de Latência**:
  - Correção na ordenação cronológica dos dados retornados para o gráfico de série temporal de latência no Dashboard.
  - Despoluição visual do eixo X limitando marcações a no máximo 10 ticks com `maxTicksLimit`.
  - Tratamento de Timezone extraindo a hora/minuto (`HH:MM`) diretamente da string de timestamp, garantindo fidelidade com o horário do servidor.
- **Caminho Dinâmico de Execução**: Correção no script `run_watchdog.sh` removendo o caminho absoluto fixo e calculando `PROJECT_DIR` dinamicamente baseado na localização do próprio script, resolvendo o bug de execução de tarefas pelo cron na máquina de produção.
- **Correção de KeyError no Notifier**: Substituição do método `.format()` por substituições manuais de string `.replace()` no `notifier.py` para injetar variáveis nos templates HTML dos e-mails, resolvendo KeyErrors originados de conflitos com as regras de CSS internas dos templates.

---

## [1.0.0] - 2026-07-04

### 🚀 Lançamento Inicial (v1.0.0)

#### Adicionado
- **Core do Watchdog (`watchdog_cli.py`)**:
  - Implementação de laço resiliente com 3 tentativas (`retries`) e pausa de 2 segundos.
  - Sistema inteligente de bypass de DNS local (Pi-hole / Unbound) realizando queries nativas por socket UDP para `1.1.1.1` e `8.8.8.8`. Se o DNS externo resolve, executa chamada HTTPS direta ao IP com header `Host` e certificado desabilitado.
  - Tratamento inteligente de falha de ISP (internet local offline): valida o link antes de acusar falha no portal do Agrocenter, prevenindo disparos de alarmes falsos quando a conectividade local cai.
  - Identificação de bloqueios pelo firewall da CDN Akamai/WAF.

- **Banco de Dados SQLite (`database.py`)**:
  - Modelagem do banco contendo as tabelas `monitor_logs` e `incidents` (quedas ativas e resolvidas).
  - Rotina de **Pruning Automático**: limpeza em tempo de gravação que apaga permanentemente registros de log com mais de 24 horas (1 dia) para poupar hardware do Raspberry Pi.
  - Métodos parametrizados para busca de KPIs com filtros dinâmicos de período (`1h`, `6h`, `1d`, `1w`, `30d`).

- **Dashboard Web Flask (`app.py` & templates)**:
  - Servidor Flask otimizado rodando na porta **`5080`** da LAN (prevenindo conflito com as portas `5000` e `5001`).
  - Layout Nerd Hacker premium (fundo escuro, estrelas pulsantes, consoles em fonte mono, console duplo).
  - **Terminal SQLite (Largura Total)**: Histórico de testes em banco renderizado em formato de console do usuário.
  - **Terminal de Logs do Sistema**: Exibição em tempo real das últimas 50 linhas do arquivo físico `watchdog.log`.
  - **Gráfico de Série Temporal (6 horas)**: Integração do **Chart.js** estilizado como osciloscópio nerd (grade escura, linha verde-hacker e preenchimento gradiente) com as variações de latência do portal.
  - **Filtros Dinâmicos**: Botões que recarregam instantaneamente os KPIs da tela para o período escolhido.

- **Gerenciador de Contatos e Alertas**:
  - Painel interativo de destinatários integrado no Dashboard Flask.
  - Permite **consultar, cadastrar, editar e excluir** e-mails de contatos e IDs de Telegram adicionais com persistência direta no arquivo `contacts.json`.
  - Os alertas do Telegram passam a ser despachados para todos os contatos ativos listados no JSON em paralelo com o administrador do `.env`.

- **Módulo Notifier & Notificações (`notifier.py`)**:
  - Envio efêmero de e-mails em HTML (Azul Cobalto + Branco premium) usando SMTP do Google (`smtp.gmail.com:587`) via TLS e autenticação com senha de aplicativo.
  - Envio de alertas rápidos e alertas de escalação persistentes (após 5 falhas consecutivas) para o Telegram, usando 3 templates distintos baseados na origem do erro (Falha de Servidor/Timeout, Bloqueio de WAF/Akamai ou Instabilidade do DNS Local).

- **Relatório Diário de Fechamento (18h)**:
  - Comando CLI `--daily-report` que compila as estatísticas de uptime, resposta média e incidentes das últimas 24 horas.
  - Envia um e-mail analítico completo com tabelas de incidentes e erros no final do expediente, além de enviar um resumo no Telegram.

- **Ambiente de Testes (`tests/`)**:
  - Configuração do **`pytest`** no ambiente virtual.
  - Testes unitários com mocks do SMTP (`test_notifier.py`) e testes de integração de autenticação real no SMTP do Google (`test_integration_smtp.py`).

- **Documentação e Scripts**:
  - Documentação passo a passo do Crontab ([cron_template.md](cron_template.md)) incluindo agendamentos da checagem a cada 5 min e do relatório analítico diário às 18:00.
  - Script de comissionamento automático para Alpine Linux (`scripts/setup_alpine.sh`).

---
