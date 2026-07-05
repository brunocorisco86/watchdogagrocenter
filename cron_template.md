# Modelo de Configuração do Cron - Watchdog Agrocenter C.Vale

Este guia orienta como configurar a execução automática e periódica do script de watchdog via **cron** em sistemas Linux (Raspberry Pi OS, Alpine Linux, etc.).

---

## 🛠️ Preparação Prévia

Antes de adicionar o agendamento no Cron, certifique-se de que os scripts de execução possuem as permissões corretas de execução.

Execute na raiz do projeto:
```bash
chmod +x scripts/run_watchdog.sh
chmod +x scripts/setup_alpine.sh
```

---

## ⏱️ Agendamento do Cron

Para configurar a tarefa periódica para rodar a cada **3 minutos** (ou o intervalo que você preferir), siga as etapas abaixo:

### 1. Editar o Crontab
Abra o agendador de tarefas cron do seu usuário atual:
```bash
crontab -e
```

*Nota: Se for a primeira vez executando, selecione seu editor de texto preferido (por exemplo, `nano`).*

### 2. Adicionar a Tarefa
Insira a seguinte linha no final do arquivo (certifique-se de usar caminhos absolutos correspondentes à instalação no Raspberry Pi):

```cron
# Rodar o Watchdog do Agrocenter a cada 3 minutos e registrar os logs de execução
*/3 * * * * /home/brunoconter/Documentos/1_C.VALE/2\ -\ PROJETOS/11_WATCHDOG_AGROCENTER/scripts/run_watchdog.sh
```

> [!IMPORTANT]  
> Se o caminho do seu repositório contiver espaços (como em `1_C.VALE/2 - PROJETOS/`), certifique-se de escapar o espaço usando a barra invertida `\` (como mostrado acima) ou envolva o caminho completo entre aspas:
> `*/3 * * * * "/home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/11_WATCHDOG_AGROCENTER/scripts/run_watchdog.sh"`

### 3. Verificar o Agendamento
Para listar e confirmar que o cron foi configurado corretamente, execute:
```bash
crontab -l
```

---

## 📊 Agendamento do Relatório Diário (Fechamento às 18h)

Para receber o relatório analítico de performance consolidado por e-mail e Telegram pontualmente às **18:00** (final de expediente), adicione o seguinte agendamento no seu `crontab -e`:

```cron
# Relatório Diário de Uptime e Incidentes consolidado do dia às 18:00
0 18 * * * cd "/home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/11_WATCHDOG_AGROCENTER" && ./venv/bin/python3 src/watchdog/watchdog_cli.py --daily-report >> logs/daily_report.log 2>&1
```

*Nota: Garanta que o diretório `logs/` exista na raiz para a gravação da saída de erros do relatório.*

---

## 📅 Agendamento do Relatório Mensal (Todo dia 30 às 18:00h)

Para receber o relatório com o consolidado de SLA/Uptime e incidentes do mês fechado por e-mail e Telegram pontualmente às **18:00** do dia **30** de cada mês, adicione o seguinte agendamento:

```cron
# Relatório Mensal de SLA consolidado do mês todo dia 30 às 18:00
0 18 30 * * cd "/home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/11_WATCHDOG_AGROCENTER" && ./venv/bin/python3 src/watchdog/watchdog_cli.py --monthly-report >> logs/monthly_report.log 2>&1
```

---

## 🛡️ Script de Resiliência e Keepalive (Watchdog do Dashboard)

Para garantir que o Dashboard Flask continue de pé na LAN do Agrocenter no Raspberry Pi, implementamos um script de **keepalive**. Ele é agendado no cron para rodar a cada **1 minuto** e realiza um double-check: tenta conectar via HTTP na porta `5080`. Se o site estiver offline ou travado, encerra qualquer processo zumbi que esteja prendendo a porta e reinicia o Flask no background.

### 1. Dar Permissão de Execução
```bash
chmod +x scripts/keepalive_dashboard.sh
```

### 2. Adicionar no Crontab (`crontab -e`)
Adicione a seguinte linha no seu agendador:
```cron
# Monitorar e reerguer o Dashboard Flask automaticamente a cada minuto se ele cair
*/1 * * * * "/home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/11_WATCHDOG_AGROCENTER/scripts/keepalive_dashboard.sh"
```

---

## 📋 Diagnóstico e Logs do Cron

Qualquer saída gerada pela tarefa agendada no cron será registrada no seguinte arquivo:
- **Caminho dos logs**: `logs/cron_execution.log`

Você pode monitorar as execuções do cron em tempo real utilizando:
```bash
tail -f logs/cron_execution.log
```
Ou ver os logs principais do watchdog em:
```bash
tail -f logs/watchdog.log
```

---

## 🍓 Nota específica para Alpine Linux (Modo Produção)

No Alpine Linux, o serviço `crond` gerencia os agendamentos.
Se você utilizou o script [setup_alpine.sh](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/scripts/setup_alpine.sh), o cron do **root** já foi configurado e o serviço habilitado de forma automática no boot.

Para ver as execuções no Alpine, você pode inspecionar o arquivo local `/etc/crontabs/root`.
