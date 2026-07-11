# Graph Report - .  (2026-07-10)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 221 nodes · 302 edges · 19 communities (12 shown, 7 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b13e5ddf`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- watchdog_cli.py
- app.py
- Watchdog Logical Architecture
- notifier.py
- Graphify Skill
- DatabaseManager
- verify_notifications.py
- main.js
- test_database.py
- Graphify Skill Documentation
- Watchdog Agrocenter
- Agrocenter Logo Image File
- test_google_smtp_authentication
- C.Vale Corporate Brand
- C.Vale Brand / Logo
- log_resources.sh
- HTML Payload Signature Matching
- Incident Retry & Cooldown Mechanics
- Memory & Performance Benchmark Profiles

## God Nodes (most connected - your core abstractions)
1. `DatabaseManager` - 24 edges
2. `Notifier` - 19 edges
3. `Graphify Skill` - 19 edges
4. `Graphify Skill Documentation` - 10 edges
5. `Watchdog Agrocenter` - 9 edges
6. `load_config()` - 8 edges
7. `run_check()` - 8 edges
8. `Watchdog Logical Architecture` - 8 edges
9. `main()` - 6 edges
10. `test_isp_connectivity()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Resilient IP Resolution Bypass` --semantically_similar_to--> `Resilient Resolver & DNS Bypass Mechanism`  [INFERRED] [semantically similar]
  /home/brunoconter/Documentos/1_C.VALE/2 - PROPOSS/11_WATCHDOG_AGROCENTER/docs/features_watchdog.md → docs/ARCHITECTURE.md
- `Double Check ISP Connectivity` --semantically_similar_to--> `ISP vs Remote Portal Fault Differentiation Strategy`  [INFERRED] [semantically similar]
  /home/brunoconter/Documentos/1_C.VALE/2 - PROPOSS/11_WATCHDOG_AGROCENTER/docs/features_watchdog.md → docs/ARCHITECTURE.md
- `Database Engine Table Schema` --semantically_similar_to--> `SQLite Database Design & KPI Timezone Strategies`  [INFERRED] [semantically similar]
  /home/brunoconter/Documentos/1_C.VALE/2 - PROPOSS/11_WATCHDOG_AGROCENTER/docs/features_watchdog.md → docs/ARCHITECTURE.md
- `Ideation & Architecture Agent` --conceptually_related_to--> `Watchdog Logical Architecture`  [INFERRED]
  agents/README.md → docs/ARCHITECTURE.md
- `main()` --calls--> `Notifier`  [EXTRACTED]
  scripts/verify_notifications.py → src/watchdog/notifier.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Graphify Skill & References** — _agents_skills_graphify_skill_main, _agents_skills_graphify_references_add_watch_ref, _agents_skills_graphify_references_exports_ref, _agents_skills_graphify_references_extraction_spec_ref, _agents_skills_graphify_references_github_and_merge_ref, _agents_skills_graphify_references_hooks_ref, _agents_skills_graphify_references_query_ref, _agents_skills_graphify_references_transcribe_ref, _agents_skills_graphify_references_update_ref [EXTRACTED 1.00]
- **Watchdog Resilience Mechanisms** — docs_features_watchdog_double_check, docs_features_watchdog_dns_bypass, docs_features_watchdog_html_signatures, docs_features_watchdog_retries_cooldown [EXTRACTED 1.00]
- **Watchdog Project Subagents** — agents_readme_ideationagent, agents_readme_raspberryagent, agents_readme_devopsagent [EXTRACTED 1.00]
- **Watchdog Database Schema Components** — docs_idea_monitor_log, docs_idea_incident, docs_idea_contact [EXTRACTED 1.00]
- **Graphify Query System Flow** — skills_graphify_references_query_expansion, skills_graphify_references_query_traversal, skills_graphify_references_query_feedback_loop [EXTRACTED 1.00]
- **Watchdog Alerting and Reporting Templates** — src_dashboard_templates_index_view, src_watchdog_daily_report_template_view, src_watchdog_email_template_view [INFERRED 0.85]

## Communities (19 total, 7 thin omitted)

### Community 0 - "watchdog_cli.py"
Cohesion: 0.06
Nodes (38): run_tests(), Notifier, Dispara mensagem síncrona chamando a rotina assíncrona do aiogram, Envia e-mails para a lista de contatos definida no contacts.json conforme nível, Envia relatórios consolidados em HTML para a lista de contatos do contacts.json, load_config(), log_to_file(), Testa a conectividade com a internet externa (ISP local) acessando     serviços (+30 more)

### Community 1 - "app.py"
Cohesion: 0.09
Nodes (6): api_latency_6h(), api_system_logs(), Retorna os dados de latência do período escolhido para alimentar o gráfico, Roda a verificação do watchdog manualmente, Lê as últimas 50 linhas do arquivo de log físico do sistema, trigger_check()

### Community 2 - "Watchdog Logical Architecture"
Cohesion: 0.11
Nodes (19): DevOps & Git CI/CD Agent, Ideation & Architecture Agent, Commissioning & Raspberry Agent, Functional Cohesion Sub-networks, SQLite Database Design & KPI Timezone Strategies, Resilient Resolver & DNS Bypass Mechanism, Multi-tier SLA Escalation Rules, ISP vs Remote Portal Fault Differentiation Strategy (+11 more)

### Community 3 - "notifier.py"
Cohesion: 0.11
Nodes (17): Agrocenter Logo, Agrocenter C.Vale Portal, Project Dependencies, Daily Report Email Template, Incident Alert Email Template, Testa se o relatório por e-mail filtra corretamente os destinatários com base no, Gera um arquivo de template de e-mail HTML temporário para testes, Testa o envio de e-mail mockando a classe SMTP para garantir o fluxo lógico corr (+9 more)

### Community 4 - "Graphify Skill"
Cohesion: 0.12
Nodes (19): Graphify Ingestion Feature, Graphify Watch Feature, Graphify Token Reduction Benchmark, Graphify FalkorDB Export, Graphify MCP Server, Graphify Neo4j Export, Graphify Wiki Export, Graphify Extraction Rules (+11 more)

### Community 5 - "DatabaseManager"
Cohesion: 0.20
Nodes (3): DatabaseManager, Retorna os registros de latência de acordo com o período para a série temporal, Retorna estatísticas filtradas por período para exibir no dashboard

### Community 6 - "verify_notifications.py"
Cohesion: 0.16
Nodes (10): keepalive_dashboard.sh script, Operators Script Guide, PYTHONPATH, run_tests.sh script, run_watchdog.sh script, setup_alpine.sh script, main(), print_header() (+2 more)

### Community 7 - "main.js"
Cohesion: 0.25
Nodes (13): appendTerminalLine(), applySettingsToDOM(), deleteContact(), editContact(), escapeHtml(), formatMarkdownToRetroTerminal(), formatMinutesText(), loadContacts() (+5 more)

### Community 8 - "test_database.py"
Cohesion: 0.17
Nodes (10): Verifica se as tabelas fundamentais foram criadas com as colunas corretas, Verifica a inserção e recuperação de logs de monitoramento, Testa o ciclo de criação, incremento e resolução de um incidente, Testa os cálculos de disponibilidade e latência do método get_kpis, Gera um banco de dados SQLite temporário para testes, temp_db(), test_add_monitor_log(), test_database_creation() (+2 more)

### Community 9 - "Graphify Skill Documentation"
Cohesion: 0.18
Nodes (11): Graphify Knowledge Graph Rules, Graphify Ingestion & Directory Watching, Graphify Export Formats & MCP Specification, Graphify AST & LLM Extraction Guidelines, Graphify Multi-repository & Monorepo Support, Graphify Hooks & Editor Integrations, Graphify BFS & DFS Query Engines, Graphify Whisper Transcription Mechanics (+3 more)

### Community 10 - "Watchdog Agrocenter"
Cohesion: 0.57
Nodes (8): contacts Database, Escalation Rules, incidents Table, monitor_logs Table, Watchdog Agrocenter, Watchdog Agrocenter Readme, Watchdog Management Skill, Dashboard Template

### Community 11 - "Agrocenter Logo Image File"
Cohesion: 0.67
Nodes (3): Agrocenter Brand, e-aware Brand, Agrocenter Logo Image File

## Knowledge Gaps
- **39 isolated node(s):** `keepalive_dashboard.sh script`, `log_resources.sh script`, `run_tests.sh script`, `PYTHONPATH`, `run_watchdog.sh script` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DatabaseManager` connect `DatabaseManager` to `test_database.py`, `app.py`, `watchdog_cli.py`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `Notifier` connect `watchdog_cli.py` to `notifier.py`, `verify_notifications.py`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `Graphify Skill` connect `Graphify Skill` to `Watchdog Agrocenter`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **What connects `keepalive_dashboard.sh script`, `log_resources.sh script`, `run_tests.sh script` to the rest of the system?**
  _82 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `watchdog_cli.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061979648473635525 - nodes in this community are weakly interconnected._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08695652173913043 - nodes in this community are weakly interconnected._
- **Should `Watchdog Logical Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._