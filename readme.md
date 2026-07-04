# Watchdog Agrocenter - C.Vale

Watchdog minimalista, resiliente e de baixo consumo de recursos, projetado para monitorar a integridade e disponibilidade do serviço Agrocenter. Executa de forma programada via cron no **Raspberry Pi 3B** rodando **Alpine Linux** (produção) e conta com um dashboard em **Flask** com temática nerd de terminal retrô (desenvolvimento/monitoramento).

---

## 🚀 Pilares da Solução

1. **Comunicação Eficiente (Plataforma Centralizada)**
   - Alertas rápidos de falha e restabelecimento enviados diretamente ao Telegram (usando `aiogram`).
   - Escalação via e-mail corporativo em HTML (com tema Azul Cobalto e Branco) para contatos definidos em `contacts.json`.
   - Dashboard Flask interativo que emula mini-terminais do Linux mostrando KPIs de integridade.

2. **Processos Otimizados**
   - Lógica de incidentes persistentes para evitar disparos repetidos.
   - Banco de dados SQLite local mapeando logs de teste e incidentes.
   - MER detalhado no arquivo [idea.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/idea.md).

3. **Tecnologia Habilitadora**
   - Sistema otimizado para rodar de forma extremamente leve em **Alpine Linux** (ideal para o Raspberry Pi 3B com consumo de RAM inferior a 50MB).
   - Validador de premissas HTTP para identificar problemas reais de backend, firewall ou banco de dados offline, mesmo quando o servidor responde com código status 200.

---

## 📂 Estrutura do Repositório

- [idea.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/idea.md) - Arquitetura, fluxo de processos e MER.
- [src/watchdog/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/src/watchdog/) - Código-fonte do monitor, banco de dados e envio de notificações.
- [src/dashboard/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/src/dashboard/) - Aplicação Web Flask com o mini-terminal nerd de monitoramento.
- [scripts/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/scripts/) - Scripts de instalação no Alpine Linux e execução no cron.
- [logs/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/logs/) - Registros de execução local.

---

## 🛠️ Configuração do Ambiente de Desenvolvimento

### 1. Requisitos Prévios
- Python 3.9+
- SQLite3

### 2. Configurando o Projeto Local
Na pasta raiz do projeto, execute:

```bash
# 1. Crie o ambiente virtual
python3 -m venv venv

# 2. Ative o ambiente virtual
source venv/bin/activate  # No Linux/macOS
# ou venv\Scripts\activate  # No Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Agora, edite o arquivo .env com suas credenciais de teste do Telegram e e-mail.
```

### 3. Rodando o Dashboard e Executando Testes
Para subir o site Flask de desenvolvimento local:

```bash
python3 src/dashboard/app.py
```
O painel estará disponível em [http://localhost:5000](http://localhost:5000). Você pode forçar um teste manual clicando no botão **`> RUN_CHECK`** no console simulado.

Para testar o script de watchdog de forma direta no terminal:
```bash
python3 src/watchdog/watchdog_cli.py
```

---

## 🍓 Comissionamento no Raspberry Pi 3B (Alpine Linux)

O Alpine Linux é escolhido para produção devido ao seu consumo de memória extremamente reduzido e arquitetura read-only opcional que protege o cartão SD do Raspberry Pi.

1. Clone este repositório no Raspberry Pi:
   ```bash
   git clone <URL_DO_SEU_REPOSITORIO> /home/brunoconter/watchdog-agrocenter
   cd /home/brunoconter/watchdog-agrocenter
   ```
2. Configure o arquivo `.env` com os dados de produção.
3. Configure os contatos de e-mail em `src/watchdog/contacts.json`.
4. Entre no diretório de scripts e execute o script de comissionamento automatizado como root:
   ```bash
   cd scripts
   chmod +x setup_alpine.sh run_watchdog.sh
   sudo ./setup_alpine.sh
   ```
5. O script irá configurar as dependências, criar o venv, instalar o requirements, iniciar o daemon de cron e adicionar a tarefa para rodar o watchdog a cada 5 minutos.

---

## 🗺️ Roadmap de Implementação

| Recurso / Etapa | % Completo | Status |
|:---|:---:|:---|
| Definição de Arquitetura e Ideação | 100% | Concluído |
| Estrutura de Pastas e Repositório Git | 100% | Concluído |
| Banco de Dados SQLite & MER | 100% | Concluído |
| Core Watchdog com Validador de Premissas | 100% | Concluído |
| Notificações Telegram (`aiogram`) e E-mail | 100% | Concluído |
| Template HTML de E-mail (Azul Cobalto + Branco) | 100% | Concluído |
| Dashboard Flask Estilo Terminal Nerd | 100% | Concluído |
| Scripts de Comissionamento (Alpine Linux) | 100% | Concluído |
| Download do Logo Oficial C.Vale nos `assets` | 100% | Concluído |
| Testes Unitários e Integrados | 0% | Pendente |
