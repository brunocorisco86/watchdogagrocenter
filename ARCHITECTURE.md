# 📐 Documento de Arquitetura - C.Vale Watchdog Agrocenter

Este documento detalha o desenho de arquitetura de software, fluxos de dados e as tecnologias adotadas para garantir que o Watchdog monitore com segurança e resiliência o portal **Agrocenter C.Vale**.

---

## 🏛️ 1. Arquitetura Lógica Geral

O sistema é construído sobre três pilares de negócio:
1. **Comunicação Eficiente**: Plataforma com Dashboard centralizado e alertas nos canais Telegram e E-mail. A comunicação segue uma política rígida de **Nível de Acionamento** para evitar sobrecarga de alertas no primeiro sinal de erro.
2. **Processos Otimizados**: Escalação segmentada por falhas consecutivas e distinção clara entre contatos de **TI** e **NEGÓCIO**. Contatos de gerência e diretoria (como o Chefe da TI) só são importunados quando os incidentes persistirem e escalarem de gravidade.
3. **Tecnologia Habilitadora**: Arquitetura leve baseada em Cron (execução episódica, zero RAM em idle) rodando no Alpine Linux.

---

## 🔄 2. Fluxo Geral de Dados e Processos

O diagrama abaixo ilustra o ciclo de vida de uma verificação e o fluxo de escalação multinível:

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
    │         └──► [FALHA] ──► Consulta sockets UDP externos (1.1.1.1 / 8.8.8.8) ──► HTTPS via IP
    │
    ▼
[ Validação HTTP e de Assinaturas ]
    │
    ├──► Status Code 200 OK + Assinaturas Válidas
    │         │
    │         └──► [SIM] ──► Registra Log "Saudável" ──► Se havia incidente ativo, resolve e notifica TODOS
    │
    └──► [NÃO] (Erro WAF/Akamai, Erro de Banco ou Timeout)
              │
              └──► Incrementa contador de falhas consecutivas no SQLite
                        │
                        ▼
            [ AVALIAÇÃO DA POLÍTICA DE ESCALAÇÃO ]
                        │
                        ├──► Falha Inicial (5 a 14 erros / ~25 min)
                        │         └──► Notifica apenas Nível 1 - TI (Suporte Técnico/Plantão)
                        │
                        ├──► Falha Intermediária (15 a 29 erros / ~1h a 2h)
                        │         └──► Notifica Nível 1 e Nível 2 (Supervisores de TI e Negócios)
                        │
                        └──► Falha Crítica / Grave (30+ erros / 2.5h+)
                                  └──► Notifica Níveis 1, 2 e 3 (Diretores, Gerentes e Chefe da TI)
```

---

## ⚙️ 3. Componentes Detalhados

### 3.1. Resolvedor Resiliente e Bypass de DNS
Caso o resolvedor de DNS local (Pi-hole, Unbound ou DNS interno da filial) apresente instabilidade, o monitor não acusa falha de forma ingênua.
1. O CLI tenta obter o IP da URL `prd-agrocenter.cvale.com.br`.
2. Se falhar, realiza uma query direta via socket UDP nativo para servidores externos do Cloudflare (`1.1.1.1`) ou Google (`8.8.8.8`).
3. Ao resolver o IP externamente, a chamada HTTPS é feita diretamente ao IP obtido. Para passar pelo WAF da Akamai, injetamos manualmente o cabeçalho `Host: prd-agrocenter.cvale.com.br` na requisição e desativamos o alerta SSL de nome incorreto.

### 3.2. Diferenciação de Falhas (ISP Local vs Portal Remoto)
- **Falha de ISP (Internet Local Caída)**: O Watchdog faz um teste inicial enviando uma requisição `HEAD` rápida para sites globais (Cloudflare/Google). Se esses sites estiverem inacessíveis, presume-se que a internet do Raspberry Pi caiu. O log é gravado no banco SQLite como `"Falha de Conectividade Local (Sem Internet - ISP Offline)"`, mas **nenhum e-mail ou alerta de Telegram é disparado**.
- **Falha Remota (Agrocenter Fora do Ar)**: Se a internet local estiver ativa mas o Agrocenter não responder ou violar as assinaturas, o sistema inicia o ciclo de abertura de incidente e escalação.

### 3.3. Banco de Dados e Pruning Automático (SQLite)
Usamos o SQLite em modo concorrente. O banco armazena logs detalhados e o controle de incidentes.
- A data e a hora limite do período de pruning e das buscas de KPIs são calculadas em Python e passadas como parâmetros nas queries para evitar qualquer conflito de timezone entre o fuso do sistema operacional e o SQLite.
- A função `add_monitor_log` apaga logs mais antigos que 24 horas a cada execução (`DELETE FROM monitor_logs WHERE timestamp < ?`).

### 3.4. Escalação por Níveis de Acionamento e Segmentação de Áreas
A lista de destinatários em `contacts.json` contém campos de controle adicionais:
- `level` (Nível de Acionamento):
  - **Nível 1 (Suporte Operacional)**: Recebe alertas de falha imediatamente (após 5 erros consecutivos).
  - **Nível 2 (Supervisão/Coordenação)**: Recebe alertas após 15 erros consecutivos (~1 hora de indisponibilidade).
  - **Nível 3 (Diretoria/Chefe da TI)**: Recebe alertas após 30 erros consecutivos (~2.5 horas de indisponibilidade).
- `department` (Departamento/Área):
  - **TI**: Notificado sobre instabilidades de infraestrutura (falhas de DNS local, bloqueios de WAF, timeouts).
  - **NEGOCIO**: Notificado em indisponibilidades severas que afetem a operação direta de negócios da Cooperativa C.Vale.

> [!NOTE]
> Quando um incidente é **RESOLVIDO**, a mensagem de restabelecimento é enviada de volta para **todos** os contatos habilitados que foram afetados, garantindo o alinhamento de normalização do portal para toda a equipe.
