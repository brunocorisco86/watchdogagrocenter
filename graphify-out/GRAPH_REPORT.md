# Graph Report - .  (2026-07-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 148 nodes · 211 edges · 13 communities (7 shown, 6 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4c5f6cb4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- watchdog_cli.py
- Notifier
- app.py
- DatabaseManager
- main.js
- test_database.py
- verify_notifications.py
- run_tests.sh
- test_google_smtp_authentication
- keepalive_dashboard.sh
- log_resources.sh
- run_watchdog.sh
- setup_alpine.sh

## God Nodes (most connected - your core abstractions)
1. `DatabaseManager` - 24 edges
2. `Notifier` - 19 edges
3. `load_config()` - 8 edges
4. `run_check()` - 8 edges
5. `main()` - 6 edges
6. `test_isp_connectivity()` - 6 edges
7. `test_http_service()` - 6 edges
8. `loadContacts()` - 5 edges
9. `run_daily_report()` - 5 edges
10. `run_monthly_report()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `run_tests()` --calls--> `load_config()`  [EXTRACTED]
  scripts/test_all_levels.py → src/watchdog/watchdog_cli.py
- `main()` --calls--> `Notifier`  [EXTRACTED]
  scripts/verify_notifications.py → src/watchdog/notifier.py
- `main()` --calls--> `load_config()`  [EXTRACTED]
  scripts/verify_notifications.py → src/watchdog/watchdog_cli.py
- `temp_db()` --calls--> `DatabaseManager`  [EXTRACTED]
  tests/test_database.py → src/watchdog/database.py
- `run_tests()` --calls--> `Notifier`  [EXTRACTED]
  scripts/test_all_levels.py → src/watchdog/notifier.py

## Import Cycles
- None detected.

## Communities (13 total, 6 thin omitted)

### Community 0 - "watchdog_cli.py"
Cohesion: 0.08
Nodes (33): load_config(), log_to_file(), Testa a conectividade com a internet externa (ISP local) acessando     serviços, Realiza o teste HTTP com sistema de retry (3 tentativas) e fallback     de DNS p, Realiza uma consulta DNS UDP (tipo A) de forma nativa (sem dependências externas, resolve_dns_udp(), run_check(), run_daily_report() (+25 more)

### Community 1 - "Notifier"
Cohesion: 0.10
Nodes (17): run_tests(), Notifier, Dispara mensagem síncrona chamando a rotina assíncrona do aiogram, Envia e-mails para a lista de contatos definida no contacts.json conforme nível, Envia relatórios consolidados em HTML para a lista de contatos do contacts.json, Testa se o relatório por e-mail filtra corretamente os destinatários com base no, Gera um arquivo de template de e-mail HTML temporário para testes, Testa o envio de e-mail mockando a classe SMTP para garantir o fluxo lógico corr (+9 more)

### Community 2 - "app.py"
Cohesion: 0.09
Nodes (6): api_latency_6h(), api_system_logs(), Retorna os dados de latência do período escolhido para alimentar o gráfico, Roda a verificação do watchdog manualmente, Lê as últimas 50 linhas do arquivo de log físico do sistema, trigger_check()

### Community 3 - "DatabaseManager"
Cohesion: 0.20
Nodes (3): DatabaseManager, Retorna os registros de latência de acordo com o período para a série temporal, Retorna estatísticas filtradas por período para exibir no dashboard

### Community 4 - "main.js"
Cohesion: 0.25
Nodes (13): appendTerminalLine(), applySettingsToDOM(), deleteContact(), editContact(), escapeHtml(), formatMarkdownToRetroTerminal(), formatMinutesText(), loadContacts() (+5 more)

### Community 5 - "test_database.py"
Cohesion: 0.17
Nodes (10): Verifica se as tabelas fundamentais foram criadas com as colunas corretas, Verifica a inserção e recuperação de logs de monitoramento, Testa o ciclo de criação, incremento e resolução de um incidente, Testa os cálculos de disponibilidade e latência do método get_kpis, Gera um banco de dados SQLite temporário para testes, temp_db(), test_add_monitor_log(), test_database_creation() (+2 more)

### Community 6 - "verify_notifications.py"
Cohesion: 0.70
Nodes (4): main(), print_header(), test_email(), test_telegram()

## Knowledge Gaps
- **6 isolated node(s):** `keepalive_dashboard.sh script`, `log_resources.sh script`, `run_tests.sh script`, `PYTHONPATH`, `run_watchdog.sh script` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatabaseManager` connect `DatabaseManager` to `watchdog_cli.py`, `app.py`, `test_database.py`?**
  _High betweenness centrality (0.241) - this node is a cross-community bridge._
- **Why does `Notifier` connect `Notifier` to `watchdog_cli.py`, `verify_notifications.py`?**
  _High betweenness centrality (0.200) - this node is a cross-community bridge._
- **Why does `run_check()` connect `watchdog_cli.py` to `Notifier`, `app.py`, `DatabaseManager`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **What connects `keepalive_dashboard.sh script`, `log_resources.sh script`, `run_tests.sh script` to the rest of the system?**
  _40 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `watchdog_cli.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07899159663865546 - nodes in this community are weakly interconnected._
- **Should `Notifier` be split into smaller, more focused modules?**
  _Cohesion score 0.09846153846153846 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08695652173913043 - nodes in this community are weakly interconnected._