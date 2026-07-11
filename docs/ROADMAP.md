# Roadmap de Desenvolvimento - Watchdog Agrocenter

Planejamento estratégico de melhorias evolutivas e novas funcionalidades para o sistema de monitoramento de alta disponibilidade C.Vale.

---

## 📅 Curto Prazo (Próximas Semanas)
- [ ] **Múltiplos Destinos de Teste**: Monitorar não apenas o Agrocenter principal, mas rotas secundárias ou APIs críticas correlacionadas.
- [ ] **Interface Web de Gerenciamento de Configuração do Telegram**: Adicionar um input no modal hacker de configurações para alterar as credenciais de notificação (Token/Chat IDs) direto pelo frontend com segurança.
- [ ] **Relatórios Mensais de SLA**: Gerar e permitir exportação de arquivos PDF ou CSV contendo as métricas de disponibilidade agregadas e incidentes mensais.

---

## 📅 Médio Prazo (Próximos Meses)
- [ ] **Integração com Gunicorn e Nginx**: Preparar a infraestrutura de deploy do dashboard para cenários com maior número de acessos concorrentes ou exposição externa (HTTPS nativo via Let's Encrypt).
- [ ] **Configuração Dinâmica de Intervalo**: Permitir que o operador configure o intervalo de repetição das checagens do Watchdog diretamente pela interface, alterando o crontab do Raspberry Pi.
- [ ] **Filtros Avançados de Logs**: Adicionar no frontend um campo de pesquisa e ordenação dinâmica para os logs históricos do banco de dados SQLite.

---

## 📅 Longo Prazo (Próximo Semestre)
- [ ] **Alta Disponibilidade Distribuída**: Rodar múltiplas instâncias do Watchdog CLI em diferentes servidores físicos na rede local para evitar que uma indisponibilidade na máquina local impeça a emissão de alertas.
- [ ] **Visão Consolidada de SLAs**: Dashboard central de monitoramento em tempo real englobando outros sistemas internos de TI e Negócios da Cooperativa C.Vale.

---

## 🎯 Entregas Concluídas Recentemente
- [x] **Frequência de Checagem de 3 Minutos**: Crontab e scripts configurados com intervalos de 3 minutos.
- [x] **Nova Política de 4 Níveis de Alerta**: Nível 1 (15m/5 falhas), Nível 2 (1h/20 falhas), Nível 3 (2.5h/50 falhas) e Nível 4 (12h/240 falhas) integrados.
- [x] **Identidade Visual Integrada (Logos)**: Template de e-mail com logos C.Vale e Agrocenter em Base64, e logo Agrocenter em SVG no cabeçalho do Dashboard.
- [x] **Processo e Documentação de Rollback**: Criação do [ROLLBACK_PROCESS.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/11_WATCHDOG_AGROCENTER/docs/ROLLBACK_PROCESS.md) detalhando reversão em produção.

