# Watchdog Agrocenter - C.Vale

Watchdog minimalista, resiliente e de baixo consumo de recursos, projetado para monitorar a integridade e disponibilidade do serviço Agrocenter. Executa de forma programada via cron no **Raspberry Pi 3B** rodando **Alpine Linux** (produção) e conta com um dashboard em **Flask** com temática nerd de terminal retrô (desenvolvimento/monitoramento).

---

## 🚀 Pilares da Solução

Como o Agrocenter C.Vale suporta o fluxo de operações logísticas do campo, a prevenção de quedas de serviços é crucial para evitar interrupções de suprimentos. A solução proposta para as falhas na entrega de ração é baseada em três pilares estratégicos:

1. **Comunicação Eficiente (Plataforma Centralizada)**
   - Alertas rápidos de integridade e restabelecimento enviados diretamente ao Telegram (usando `aiogram`).
   - Escalação via e-mail corporativo em HTML (com tema Azul Cobalto e Branco) para contatos definidos em `contacts.json`.
   - Dashboard Flask interativo que emula mini-terminais do Linux mostrando KPIs de integridade de forma centralizada.

2. **Processos Otimizados (Redesenho de Fluxo e Confirmação de Pedidos)**
   - Lógica de incidentes persistentes para evitar disparos repetidos e alarmes falsos durante o fluxo de pedidos.
   - Banco de dados SQLite local mapeando logs de teste e incidentes, garantindo auditoria nas confirmações de pedidos de ração.
   - MER detalhado no arquivo [idea.md](docs/idea.md).

3. **Tecnologia Habilitadora (TMS, Sensores de Nível nos Silos)**
   - Preparação de canais para integração de telemetria (sensores de nível de ração nos silos) e controle logístico de frotas (TMS).
   - Sistema otimizado para rodar de forma extremamente leve em **Alpine Linux** (ideal para o Raspberry Pi 3B com consumo de RAM inferior a 50MB).
   - Validador de premissas HTTP para identificar problemas reais de backend, firewall ou banco de dados offline.

---

## 📂 Estrutura do Repositório

- [COMMISSIONING.md](docs/COMMISSIONING.md) - Manual passo a passo de implantação e comissionamento.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detalhamento da arquitetura física e lógica.
- [CHANGELOG.md](docs/CHANGELOG.md) - Histórico de versões e lançamentos.
- [idea.md](docs/idea.md) - Fluxo de processos original e MER.
- [src/watchdog/](src/watchdog/) - Código-fonte do monitor, banco de dados e envio de notificações.
- [src/dashboard/](src/dashboard/) - Aplicação Web Flask com o mini-terminal nerd de monitoramento.
- [scripts/](scripts/) - Scripts de instalação no Alpine Linux e execução no cron.
- [skills/](skills/) e [.agents/](.agents/) - Configurações de IA, workflows, regras e skills do agente (ex: Graphify).
- [graphify-out/](graphify-out/) - Grafo de conhecimento gerado da estrutura de código do repositório.
- [logs/](logs/) - Registros de execução local.

---

## 🛠️ Stack Tecnológica

- **Backend Daemon (Monitor)**: Python 3.12 (com bibliotecas nativas `urllib.request`, `socket`, `smtplib`).
- **Banco de Dados**: SQLite3 (para persistência de logs, incidentes e limiares dinâmicos de SLA).
- **Interface Web**: Flask 3.0 (Python micro-framework) + HTML5 + CSS3 Vanilla (tema hacker) + JS Vanilla (ES6) + Chart.js (gráficos).
- **Hospedagem & Produção**: Raspberry Pi 3B rodando **Alpine Linux** (modo RAM diskless) e agendamento via **Busybox Crontab**.
- **Testes**: Pytest.

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
O painel estará disponível em [http://localhost:5080](http://localhost:5080). Você pode forçar um teste manual clicando no botão **`> RUN_CHECK`** no console simulado.

Para testar o script de watchdog de forma direta no terminal:
```bash
python3 src/watchdog/watchdog_cli.py
```

Para executar a suíte de testes unitários e testes de integração de rede (Pytest):
```bash
PYTHONPATH=. ./venv/bin/pytest -v
```

---

## 🍓 Implantação e Comissionamento (Raspberry Pi 3B)

Para implantar e ativar o Watchdog Agrocenter em produção usando um Raspberry Pi 3B com Alpine Linux (ou qualquer outra distribuição Linux), consulte o nosso manual de comissionamento completo passo a passo:

👉 **[COMMISSIONING.md](docs/COMMISSIONING.md)**

O manual aborda:
- Requisitos de Hardware e Instalação Diskless do Alpine Linux.
- Diagnóstico interativo de alertas (`verify_notifications.py`).
- Execução isolada da suíte de testes (`run_tests.sh`).
- Provisionamento automatizado via script (`setup_alpine.sh`).
- Explicações e detalhes dos agendamentos Crontab.

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
| Testes Unitários e Integrados | 100% | Concluído |
| Frequência de Checagem a cada 3 min | 100% | Concluído |
| Novo Nível 4 de Alerta (12h) | 100% | Concluído |
| Integração de Logos (C.Vale & Agrocenter) no e-mail e site | 100% | Concluído |

---

## 🔍 Grafo de Conhecimento (Graphify)

Este repositório possui uma base de conhecimento estruturada e indexada com a ferramenta **Graphify**. Ela analisa a AST (árvore de sintaxe abstrata) do código e mapeia as relações de dependências, comunidades de código e fluxos lógicos.

### Como usar e interagir com o Grafo:
Se você utiliza agentes de inteligência artificial compatíveis (como Claude Code, Cursor ou Google Antigravity), a skill instalada em `.agents/skills/graphify` permite responder a perguntas complexas sobre a arquitetura do projeto de forma nativa.

*   **Verificar o Grafo:** O relatório descritivo completo está salvo em [graphify-out/GRAPH_REPORT.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/graphify-out/GRAPH_REPORT.md).
*   **Visualização Interativa:** Abra o arquivo [graphify-out/graph.html](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/graphify-out/graph.html) no navegador para ver uma representação 3D das conexões e classes do projeto.
*   **Atualizar o Grafo:** Sempre que alterar a estrutura lógica do código (novas classes, funções ou imports), atualize o grafo executando:
    ```bash
    venv/bin/graphify . --code-only --update
    venv/bin/graphify cluster-only .
    ```

