# Processo de Rollback e Reversão de Deploy - Watchdog Agrocenter

Este documento define os procedimentos operacionais padrão (SOP) para reverter alterações no ambiente de produção (Raspberry Pi 3B) em caso de falha nos testes de integridade, erros críticos de inicialização ou comportamento inesperado após uma nova entrega.

---

## 🛡️ 1. Medidas Preventivas (Pré-Deploy)

Antes de cada deploy ou pull na produção:
1. **Backup do Banco de Dados**:
   Sempre crie uma cópia do banco de dados SQLite de produção.
   ```bash
   cp /home/bruno/watchdog-agrocenter/src/watchdog/database.db /home/bruno/watchdog-agrocenter/src/watchdog/database.db.bak
   ```
2. **Snapshot do Commit Atual**:
   Anote o hash SHA do commit ativo em produção antes da atualização:
   ```bash
   git rev-parse HEAD > /home/bruno/watchdog-agrocenter/pre_deploy_commit.txt
   ```

---

## 🚨 2. Critérios para Acionamento de Rollback

O processo de rollback deve ser iniciado imediatamente se:
- A suíte de testes `./scripts/run_tests.sh` falhar após o deploy.
- O daemon `watchdog_cli.py` lançar exceções não tratadas no log do cron (`logs/cron_execution.log`).
- O dashboard Flask não iniciar ou falhar no monitoramento do keepalive (porta `5080` inacessível).
- As notificações (Telegram/E-mail) pararem de funcionar.

---

## 🔄 3. Procedimento de Rollback (Passo a Passo)

Siga estas instruções caso necessite reverter a produção:

### Passo 1: Reverter a Base de Código para o Estado Anterior
Restaure o repositório git local para o commit estável imediatamente anterior (ou use o hash salv no pré-deploy):
```bash
cd /home/bruno/watchdog-agrocenter
# Caso tenha o arquivo pre_deploy_commit.txt:
git reset --hard $(cat pre_deploy_commit.txt)
# Ou simplesmente desfaça o último pull:
# git reset --hard HEAD@{1}
```

### Passo 2: Restaurar o Banco de Dados (Se necessário)
Se a alteração envolveu migração de esquema ou corrupção de dados:
```bash
cp /home/bruno/watchdog-agrocenter/src/watchdog/database.db.bak /home/bruno/watchdog-agrocenter/src/watchdog/database.db
```

### Passo 3: Reexecutar Testes na Produção
Garantir que a versão restaurada está 100% funcional:
```bash
./scripts/run_tests.sh
```

### Passo 4: Reiniciar os Serviços de Produção
Force o reinício do dashboard e recarregamento do cron:
```bash
# Encerrar processos Flask pendentes
pkill -f "app.py" || true

# O script de keepalive configurado no cron iniciará o app Flask em 1 minuto.
# Para subir manualmente de imediato no venv de produção:
source venv/bin/activate
setsid python3 src/dashboard/app.py > /dev/null 2>&1 &
```

---

## 📈 4. Pós-Rollback e Auditoria

1. Analise o arquivo de logs (`logs/watchdog.log`) para identificar a causa raiz da falha.
2. Registre o incidente de deploy no canal de TI.
3. Não tente um novo deploy sem antes validar a correção no ambiente de homologação/desenvolvimento local.
