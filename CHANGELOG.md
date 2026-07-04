# Changelog - C.Vale Watchdog Agrocenter

Todo o histórico de desenvolvimento e lançamentos deste projeto de monitoramento de alta disponibilidade será documentado neste arquivo.

A estrutura deste projeto rege-se pelos três pilares da solução: **Comunicação Eficiente** (plataforma centralizada/dashboard), **Processos Otimizados** (redesenho de fluxo e confirmação de testes) e **Tecnologia Habilitadora** (watchdog, resolvedores resilientes, bypass de DNS local e alertas autônomos).

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
