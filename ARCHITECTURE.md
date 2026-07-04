# 📐 Documento de Arquitetura - C.Vale Watchdog Agrocenter

Este documento detalha o desenho de arquitetura de software, fluxos de dados e as tecnologias adotadas para garantir que o Watchdog monitore com segurança e resiliência o portal **Agrocenter C.Vale**.

---

## 🏛️ 1. Arquitetura Lógica Geral

O sistema é construído sobre três pilares de negócio:
1. **Comunicação Eficiente**: Plataforma com Dashboard centralizado e alertas nos canais Telegram e E-mail de forma efêmera (apenas em quedas reais e restabelecimentos).
2. **Processos Otimizados**: Redesenho do fluxo de confirmação e escalação. Os alertas só escalam para o Telegram após 5 falhas consecutivas de requisição, prevenindo falsos positivos por flutuações rápidas.
3. **Tecnologia Habilitadora**: Arquitetura extremamente leve baseada em Cron (execução episódica, zero RAM em idle) em vez de um daemon perpétuo, ideal para o Raspberry Pi 3B (Alpine Linux).

---

## 🔄 2. Fluxo Geral de Dados e Processos

O diagrama abaixo ilustra o ciclo de vida de uma verificação do Watchdog:

```text
[ CRONTAB ] (A cada 5 minutos)
    │
    ▼
[ watchdog_cli.py ]
    │
    ├──► 1. Checa Link Local (ISP Offline?) ──► [SIM] ──► Grava log "ISP Offline" e suspende alertas (Bypass)
    │
    ├──► 2. Checa Resolução DNS do Agrocenter
    │         │
    │         └──► [FALHA] ──► Consulta sockets UDP externos (1.1.1.1 / 8.8.8.8)
    │                                │
    │                                └──► [RESOLVE] ──► HTTPS direto via IP (Bypass de DNS Local)
    │
    ▼
[ Validação HTTP e de Assinaturas ]
    │
    ├──► Status Code 200 OK + Assinaturas Válidas (agrocenter, eaware.io, simbolo.png)
    │         │
    │         └──► [SIM] ──► Registra Log "Saudável" ──► Se havia incidente ativo, resolve e alerta
    │
    └──► [NÃO] (Erro WAF/Akamai, Erro de Banco ou Timeout)
              │
              └──► Incrementa contador de falhas consecutivas no SQLite
                        │
                        └──► Atingiu 5 Falhas? ──► Dispara Alertas Telegram (escalação) & E-mail HTML
```

---

## ⚙️ 3. Componentes Detalhados

### 3.1. Resolvedor Resiliente e Bypass de DNS
Caso o resolvedor de DNS local (Pi-hole, Unbound ou DNS interno da filial) apresente instabilidade, o monitor não acusa falha de forma ingênua.
1. O CLI tenta obter a IP da URL `prd-agrocenter.cvale.com.br`.
2. Se falhar, realiza uma query direta via socket UDP nativo para servidores externos do Cloudflare (`1.1.1.1`) ou Google (`8.8.8.8`).
3. Ao resolver o IP externamente, a chamada HTTPS é feita diretamente ao IP obtido. Para passar pelo WAF da Akamai, injetamos manualmente o cabeçalho `Host: prd-agrocenter.cvale.com.br` na requisição e desativamos o alerta SSL de nome incorreto.

### 3.2. Diferenciação de Falhas (ISP Local vs Portal Remoto)
- **Falha de ISP (Internet Local Caída)**: O Watchdog faz um teste inicial enviando uma requisição `HEAD` rápida para sites globais (Cloudflare/Google). Se esses sites estiverem inacessíveis, presume-se que a internet do Raspberry Pi caiu. O log é gravado no banco SQLite como `"Falha de Conectividade Local (Sem Internet - ISP Offline)"`, mas **nenhum e-mail ou alerta de Telegram é disparado**.
- **Falha Remota (Agrocenter Fora do Ar)**: Se a internet local estiver ativa mas o Agrocenter não responder ou violar as assinaturas, o sistema inicia o ciclo de abertura de incidente e escalação.

### 3.3. Banco de Dados e Pruning Automático (SQLite)
Usamos o SQLite em modo concorrente. O banco armazena logs detalhados e o controle de incidentes.
- Para evitar sobrecarga do cartão SD do Raspberry Pi, a função `add_monitor_log` executa o **Pruning Automático** a cada inserção.
- Todos os registros com mais de 24 horas são apagados permanentemente através da query parametrizada em Python: `DELETE FROM monitor_logs WHERE timestamp < ?`.

### 3.4. Notificações Inteligentes
- **Telegram**: Utiliza o bot corporativo para despachar alertas rápidos. Se cadastrados novos contatos no `contacts.json`, o Notifier envia alertas adicionais a todos os IDs de Telegram ativos de forma assíncrona.
- **SMTP**: Envio via Gmail SMTP corporativo usando templates HTML ricos e responsivos com estilização Azul Cobalto e assinaturas técnicas de infraestrutura.
