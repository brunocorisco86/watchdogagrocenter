# Features e Mecanismos Internos do watchdog_cli.py

Mecanismos internos do motor de monitoramento de alta disponibilidade da C.Vale.

---

### [MOTOR 1: DOUBLE CHECK DE ISP LOCAL]
- Testa conectividade TCP básica resolvendo IPs globais (Cloudflare / Google).
- Se falhar: Classifica como "Falha de Internet Local (ISP Offline)", grava no banco e aborta disparo de alarmes.

---

### [MOTOR 2: BYPASS RESILIENTE DE DNS INTERNO]
- Em caso de falha de resolução DNS local, inicia conexões UDP diretas para 1.1.1.1 e 8.8.8.8.
- Obtém o IP público do Agrocenter, injeta no socket e formata requisição HTTP direta ao IP.
- Adiciona cabeçalho manual "Host: prd-agrocenter.cvale.com.br" para bypassar o firewall da Akamai.

---

### [MOTOR 3: MOTOR DE REQUISITOS E REQUISITOS DE CONTEÚDO (HTML SIGNATURES)]
- Exige obrigatoriamente status HTTP 200 OK e metadados com Content-Type: text/html.
- Varre o código-fonte em busca das palavras-chave obrigatórias do portal.
- Identifica e rotula erros de sistema (exposição de logs/warnings do banco de dados).
- Identifica e rotula bloqueios de firewall da CDN (Bloqueios WAF / Access Denied Akamai).

---

### [MOTOR 4: POLÍTICA DE RETRIES E COOLDOWN]
- Em caso de erro inicial, executa automaticamente 3 tentativas sequenciais de requisição.
- Aguarda um cooldown fixo de 2 segundos entre as tentativas antes de declarar queda.

---

### [MOTOR 5: AUTO-PRUNING CONCORRENTE]
- (Desativado) Anteriormente expurgava registros com > 24 horas. Desativado por solicitação do usuário para preservar todo o histórico do banco de dados SQLite para sempre.

---

### [MOTOR 6: ESTRUTURA DO BANCO DE DADOS & MER]
- Mapeado no SQLite local (database.db) e base JSON (contacts.json) com schemas otimizados:
  * `monitor_logs` (id PK, timestamp, status_code, response_time_ms, is_healthy, error_message, check_type)
  * `incidents`    (id PK, start_timestamp, end_timestamp, consecutive_failures, telegram_sent, email_sent, status)
  * `contacts.json` (email PK, name, telegram_id, level, department, enabled)
- Relacionamento: `monitor_logs` [1] ───► [0..1] `incidents` [1] ───► [0..*] `contacts` (alertados conforme falhas)
