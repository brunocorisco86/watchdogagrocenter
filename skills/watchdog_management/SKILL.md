---
name: watchdog_management
description: Guia de comissionamento, testes de premissas HTTP e gerenciamento de deploys (CI/CD) para o Watchdog do Agrocenter.
---

# Habilidade: Gerenciamento de Watchdog no Raspberry Pi 3B (Alpine Linux)

Esta skill define as melhores práticas e instruções de comissionamento, automação e execução do monitor do Agrocenter.

## 🛠️ Comissionamento (Raspberry Pi & Alpine Linux)
1. **Instalação do Sistema**:
   - Utilize Alpine Linux "Standard" ou "Extended" para arquitetura `armv7` ou `aarch64` correspondente ao Raspberry Pi 3B.
   - Configure o disco no modo `sys` ou `diskless` (modo RAM com `lbu commit` para persistir alterações).
2. **Dependências do OS**:
   - `python3`, `py3-pip`, `sqlite`, `git`, `bash`, `tzdata`, `crond`.
3. **Persistência de Logs**:
   - Direcione os logs para `/var/log/watchdog/` ou mantenha local no projeto `/home/bruno/watchdog-agrocenter/logs/` caso esteja rodando em modo `sys` com escrita livre.
   - Em Alpine no modo `diskless`, logs muito dinâmicos devem ser enviados a um syslog externo ou gravados em tmpfs para poupar o cartão SD.

## ⚙️ Cron e Execução
A tarefa cron é definida no crontab do root ou usuário dedicado na máquina de produção (`ssh peixe`):
```cron
*/3 * * * * /home/bruno/watchdog-agrocenter/scripts/run_watchdog.sh
```
Certifique-se de que o script `run_watchdog.sh` possui permissões `+x` e executa dinamicamente o Python da `venv` correspondente. O fluxo de alertas respeita a escala de incidentes baseada no tempo off: Nível 1 (15m/5 falhas), Nível 2 (1h/20 falhas), Nível 3 (2.5h/50 falhas) e Nível 4 (12h/240 falhas).

## 🛡️ Validação de Premissas HTTP & WAF Bypass
Quando monitorar a API do Agrocenter, siga estas diretrizes:
- **Verificação Básica**: Código de status HTTP (`< 400`).
- **Bypass de TLS Fingerprinting (Akamai WAF)**: Em caso de bloqueio WAF (HTTP 403), o motor executa requisições impersonadas de TLS do Chrome/Firefox usando `curl_cffi` para contornar o bloqueio de assinatura de handshake da Akamai.
- **Verificação de Latência**: A requisição deve ser concluída antes do `timeout` configurado (padrão 10s).
- **Verificação de Conteúdo**:
  - Procurar por strings de firewall/desafio (ex: `Akamai WAF`, `Bloqueio de Firewall`). Caso encontradas, classificar como falha de segurança/bloqueio.
  - Procurar por erros de banco (ex: `database connection failed`, `sql error`).
  - Validar a presença de palavras-chave da marca (ex: `c.vale`, `agrocenter`). A ausência delas indica falha de resolução DNS, sequestro de rota ou página padrão do provedor de hospedagem.

## 🔄 Fluxo de CI/CD (Desenvolvimento -> Produção)
1. **Máquina de Desenvolvimento (Local)**:
   - Edições de código, criação de novas rotinas, desenvolvimento do Dashboard Flask.
   - Testes unitários na pasta `tests/`.
   - `git add`, `git commit` e `git push` para o repositório remoto.
2. **Máquina de Produção (Raspberry Pi - LAN - ssh root@192.168.1.99 / ssh peixe)**:
   - Conecte via SSH usando `ssh root@192.168.1.99` ou simplesmente pelo alias `ssh peixe`.
   - O projeto em produção está localizado no diretório `/home/bruno/watchdog-agrocenter`.
   - Execute o Git Pull na pasta do projeto.
   - Ativação do venv: `. venv/bin/activate`.
   - Execução manual de teste rápido para atestar funcionamento: `python3 src/watchdog/watchdog_cli.py`.
   - Logs são monitorados em tempo real via terminal ou através do Dashboard Flask do watchdog exposto localmente na porta `5080`.
