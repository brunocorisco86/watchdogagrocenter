# 📂 Índice de Scripts do Operador - C.Vale Watchdog

Este diretório contém os scripts utilitários voltados ao comissionamento, diagnósticos de conexões, suite de testes e execução do monitor.

---

## 📋 Guia de Ordem de Execução Recomendado

Ao efetuar o clone do projeto ou realizar manutenção corretiva/preventiva, o operador deve seguir a ordem sugerida abaixo para garantir a conformidade dos serviços e canais:

### 1º Passo: Validar Conectividade e Alertas
Execute o script de diagnóstico de mensageria para testar se as chaves e credenciais do Telegram e do SMTP Gmail estão integradas e despachando mensagens de teste:
```bash
./scripts/verify_notifications.py
```
- **Objetivo**: Testar se o token do Telegram, o Chat ID do administrador e as senhas de aplicativo SMTP conseguem estabelecer comunicação TCP com a internet externa.

### 2º Passo: Executar a Suite de Testes
Rode a suíte de testes locais para blindar a integridade do código e atestar se todas as regras de premissas HTTP, queries SQLite e retries operam como projetado:
```bash
./scripts/run_tests.sh
```
- **Objetivo**: Executar a suite completa do `pytest` de forma nativa e isolada com 100% de sucesso.

### 3º Passo: Comissionamento em Produção (Raspberry Pi 3B)
Com as credenciais homologadas e os testes de código passando, execute o script de provisionamento automatizado do Alpine Linux como root:
```bash
sudo ./scripts/setup_alpine.sh
```
- **Objetivo**: Criar o ambiente virtual de produção, instalar dependências do `requirements.txt`, ativar o daemon do Cron local (`dcron`/`crond`) e agendar a checagem a cada 5 min.

### 4º Passo: Execução e Fallback do Crontab
Este script é executado silenciosamente pelo crontab a cada 5 minutos e contém o tratamento para salvar a saída das verificações no log do sistema `/home/brunoconter/watchdog-agrocenter/logs/watchdog.log`:
```bash
./scripts/run_watchdog.sh
```

### 5º Passo: Habilitar o Keepalive do Dashboard (Watchdog do Dashboard)
Para garantir a alta disponibilidade do dashboard Flask e sua inicialização resiliente automática em caso de falhas na LAN do Agrocenter, ative o script de keepalive a cada minuto:
```bash
chmod +x scripts/keepalive_dashboard.sh
```
*Nota: Agende a execução automática no cron conforme detalhado no modelo.*

---

## 🛠️ Descrição Detalhada dos Arquivos

| # | Arquivo | Idioma/Tipo | Objetivo |
|:---:|:---|:---:|:---|
| `01` | [verify_notifications.py](verify_notifications.py) | Python 3 | CLI interativo para testar notificações reais de Telegram e E-mail de homologação. |
| `02` | [run_tests.sh](run_tests.sh) | Bash Shell | Atalho para ativar o venv e executar a suite `pytest -v` na raiz do projeto. |
| `03` | [setup_alpine.sh](setup_alpine.sh) | Bash Shell | Provedor de instalação automática das libs do sistema, venv, requirements e crontab no Alpine Linux. |
| `04` | [run_watchdog.sh](run_watchdog.sh) | Bash Shell | Wrapper do crontab que ativa o venv, executa a checagem HTTPS e anexa saídas no log físico. |
| `05` | [keepalive_dashboard.sh](keepalive_dashboard.sh) | Bash Shell | Script de resiliência e monitoramento que reinicia o Flask se ele cair na LAN. |
