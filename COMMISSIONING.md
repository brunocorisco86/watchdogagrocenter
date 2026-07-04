# 🍓 Manual de Comissionamento - C.Vale Watchdog Agrocenter

Este manual descreve o passo a passo detalhado para implantar e comissionar o sistema de monitoramento de alta disponibilidade C.Vale Watchdog Agrocenter no **Raspberry Pi 3B** rodando **Alpine Linux** (modo produção) ou em qualquer servidor Linux compatível.

---

## 📋 1. Requisitos Prévios

### Hardware
* Raspberry Pi 3B (ou superior).
* Cartão MicroSD (mínimo de 8GB, de preferência Classe 10 de alta confiabilidade).

### Sistema Operacional (Recomendado)
* **Alpine Linux v3.18+ (arquitetura armv7 ou aarch64)**.
* Recomenda-se a instalação em modo **diskless** (ou `sys` se necessário), pois o consumo reduzido de escrita protege a vida útil do cartão SD.

---

## 🛠️ 2. Guia de Provisionamento e Instalação (Passo a Passo)

### Passo 2.1: Clone do Projeto e Permissões
Acesse o terminal do seu Raspberry Pi e execute o clone do repositório no diretório do usuário:
```bash
git clone <URL_DO_REPOSITORIO> /home/brunoconter/watchdog-agrocenter
cd /home/brunoconter/watchdog-agrocenter
```

Garanta que todos os scripts utilitários do operador possuam permissão executável:
```bash
chmod +x scripts/*.sh scripts/*.py
```

---

### Passo 2.2: Configurações do Ambiente (`.env`)
Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```
Edite o arquivo `.env` com um editor de texto (ex: `nano` ou `vi`) e insira as credenciais de homologação/produção:
```ini
# Agrocenter URL do Portal C.Vale
AGROCENTER_URL=https://prd-agrocenter.cvale.com.br

# SMTP CONFIGURATION (Para envio de e-mails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=brunocorisco@gmail.com
SMTP_PASSWORD=fvjb hyik ekpw ecmy
SMTP_FROM=watchdog-agrocenter@cvale.com.br

# TELEGRAM BOT CONFIGURATION
TELEGRAM_BOT_TOKEN=8646226329:AAGaxxdE1HCwl3cBWGhJ4a2AcPp0I0vsnOk
TELEGRAM_CHAT_ID=1959691903

# CONFIGURAÇÕES DO MONITOR
MAX_CONSECUTIVE_FAILURES=5
CHECK_TIMEOUT_SECONDS=10

# PORTA DO FLASK DASHBOARD
FLASK_PORT=5080
FLASK_HOST=0.0.0.0
```

> [!IMPORTANT]
> A chave `SMTP_PASSWORD` deve ser a senha de aplicativo de 16 caracteres gerada na conta Google do remetente (com 2FA ativo), e não a senha pessoal convencional do Gmail.

---

### Passo 2.3: Configuração Inicial de Destinatários (`contacts.json`)
O arquivo [src/watchdog/contacts.json](src/watchdog/contacts.json) armazena os destinatários de e-mail e Telegram adicionais. Por padrão ele inicia com seus dados:
```json
[
  {
    "name": "Bruno Conter (C.Vale)",
    "email": "bruno.conter@cvale.com.br",
    "enabled": true
  },
  {
    "name": "Bruno Corisco (Gmail)",
    "email": "brunocorisco@gmail.com",
    "enabled": true
  }
]
```
Você pode editar este arquivo manualmente ou, após o comissionamento do Flask, cadastrá-los, editá-los e removê-los diretamente pela interface gráfica do Dashboard na porta `5080`.

---

## 🧪 3. Execução de Testes e Diagnósticos (Garantia de Qualidade)

Antes de colocar o script em execução automática no Crontab, execute as rotinas de diagnósticos descritas no [README de scripts](scripts/README.md):

### Passo 3.1: Diagnóstico de Alertas
Execute o script de diagnóstico de mensageria para confirmar se o bot do Telegram e a credencial SMTP do Gmail conseguem enviar dados com sucesso:
```bash
./scripts/verify_notifications.py
```
*Selecione a opção **3 (Testar AMBOS)** e verifique se as mensagens de homologação chegam no seu celular e caixa de entrada.*

### Passo 3.2: Execução dos Testes Unitários e de Integração
Rode a suíte de testes do Pytest para validar se o código do banco de dados, da pruna de logs, do core do watchdog e da classificação WAF/Akamai opera em 100% de conformidade:
```bash
./scripts/run_tests.sh
```
*Certifique-se de que os 16 casos de teste do pytest retornam com status **PASSED**.*

---

## 🍓 4. Comissionamento do Alpine Linux (Produção)

Execute o script de comissionamento automático como root para instalar dependências do sistema e configurar o crontab:
```bash
sudo ./scripts/setup_alpine.sh
```

### O que o script de provisionamento faz?
1. Instala pacotes do sistema necessários: `python3`, `py3-pip`, `sqlite`, `bash`, e o gerenciador de tarefas `dcron` (se ausente).
2. Cria o ambiente virtual python isolado (`venv`).
3. Instala as dependências listadas no `requirements.txt` (`requests`, `pytest`, `flask`, etc.).
4. Configura as tarefas do Cron no arquivo crontab local do Alpine.

---

## ⏰ 5. Agendamentos no Crontab

O comissionamento automático instala dois agendamentos no Crontab. Caso queira configurá-los manualmente (`crontab -e`), utilize:

```cron
# 1. Checagem regular de integridade do Agrocenter (A cada 5 minutos)
*/5 * * * * /home/brunoconter/watchdog-agrocenter/scripts/run_watchdog.sh > /dev/null 2>&1

# 2. Relatório Diário de Expediente (Diariamente às 18:00h)
0 18 * * * cd /home/brunoconter/watchdog-agrocenter && ./venv/bin/python3 src/watchdog/watchdog_cli.py --daily-report > /dev/null 2>&1
```

---

## 💻 6. Inicialização do Dashboard Web (Flask)

O Dashboard roda em background na porta **`5080`** e serve como painel administrativo.

### Inicialização Manual:
```bash
cd /home/brunoconter/watchdog-agrocenter
./venv/bin/python3 src/dashboard/app.py
```

### Execução em Background Persistente (Alpine Linux):
Para deixar o Dashboard rodando permanentemente no Alpine Linux, você pode usar o utilitário `nohup` ou integrá-lo ao gerenciador OpenRC. Exemplo rápido com `nohup`:
```bash
nohup ./venv/bin/python3 src/dashboard/app.py > /home/brunoconter/watchdog-agrocenter/logs/flask.log 2>&1 &
```
Acesse de qualquer computador da rede local através de `http://<IP_DO_RASPBERRY>:5080`.
