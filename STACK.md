# 🛠️ Stack Tecnológica - Watchdog Agrocenter C.Vale

Este arquivo detalha todas as ferramentas, linguagens, bibliotecas e ambientes de execução adotados no projeto **Watchdog Agrocenter**.

---

## 🐍 1. Backend Core (Monitoramento / CLI Daemon)
* **Linguagem**: Python 3.12 (compatível com 3.9+)
* **Módulos Nativos Utilizados (Sem dependência externa)**:
  * `urllib.request`: Para validação HTTP/HTTPS segura de endpoints.
  * `socket`: Utilizado para bypass de DNS local e checagem de integridade via sockets UDP nos resolvedores globais (`1.1.1.1` e `8.8.8.8`).
  * `smtplib` e `email`: Implementação do envio de e-mails em formato multipart (HTML).
  * `sqlite3`: Driver nativo de persistência SQL.
  * `asyncio`: Controle assíncrono das tarefas de simulação de teste.
* **Bibliotecas Externas (Pip)**:
  * `requests`: Utilizada para chamadas do webhook do Telegram.
  * `aiogram`: SDK assíncrono para a automação do bot do Telegram.

---

## 🗄️ 2. Banco de Dados (Persistência)
* **SQLite 3**:
  * Banco de dados relacional leve em arquivo único, ideal para o hardware modesto do Raspberry Pi 3B.
  * **Tabelas**:
    * `monitor_logs`: Armazena o histórico das checagens (tempo de resposta, status HTTP, etc.).
    * `incidents`: Controla o estado de incidentes de queda ativos.
    * `settings`: Configurações de SLA editáveis dinamicamente a partir do dashboard.

---

## 💻 3. Dashboard Web de Monitoramento
* **Flask 3.0+**: Micro-framework para disponibilização da API de logs/KPIs e renderização de templates Jinja2.
* **Front-End**:
  * **HTML5 Semântico**: Estruturação limpa do console.
  * **CSS3 Vanilla**: Estilização rica inspirada em terminais de computador retro-futuristas com tema hacker (dark mode, efeitos neon, painéis em grid responsivo).
  * **Javascript Vanilla (ES6)**: Lógica cliente de auto-atualização assíncrona (Fetch API), CRUD de contatos e controle dos modais.
  * **Chart.js**: Renderização baseada em HTML5 Canvas para os gráficos de tempo de resposta.

---

## 🍓 4. Infraestrutura e Hospedagem (Produção)
* **Hardware**: Raspberry Pi 3B.
* **Sistema Operacional**: Alpine Linux v3.20 rodando em modo RAM diskless (imune a falhas de escrita e corrupções no cartão SD).
* **Agendador de Tarefas**: BusyBox Crontab nativo para execução automatizada a cada 3 minutos.

---

## 🧪 5. Testes e Qualidade de Código
* **Pytest**: Suíte de execução de testes unitários e de integração locais.
