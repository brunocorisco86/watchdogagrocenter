# Benchmark de Uso de Recursos - Raspberry Pi 3B (Alpine Linux)

Documentação do perfil de consumo de recursos computacionais medidos em ambiente de produção homologado.

---

## 📊 1. Estatísticas Gerais da Máquina (Produção: `peixe`)
- **Arquitetura**: ARMv7 Processor rev 4 (v7l)
- **Núcleos de CPU**: 4 Cores
- **Memória RAM Total**: ~907 MB
- **Espaço em Disco**: ~14.2 GB (Partição SD Card)

---

## 📈 2. Perfil de Consumo dos Processos do Watchdog

### A. Dashboard Flask (`src/dashboard/app.py` - Werkzeug)
- **Consumo de Memória (RSS)**: ~25 MB a ~30 MB por instância ativa.
- **Consumo de CPU (Idle)**: < 0.1% de uso.
- **Uso Concorrente**: Leve, ideal para o número atual de operadores em rede LAN.

### B. Motor do Watchdog (`src/watchdog/watchdog_cli.py`)
- **Consumo de Memória (Burst)**: ~15 MB a ~20 MB durante a execução pontual (acionada a cada 3/5 minutos).
- **Consumo de CPU (Processamento)**: ~1% a ~3% durante o processamento da requisição HTTP e validação das assinaturas WAF/Akamai.
- **Tempo de Execução Médio**: ~0.8s a ~1.5s por ciclo de monitoramento.

### C. Banco de Dados SQLite (`database.db`)
- **Tamanho do Arquivo**: ~1.2 MB a ~5 MB (crescimento muito lento, perfeitamente compatível com armazenamento Flash/SD Card).
- **Escrita de Logs**: Escrita pontual de 1 registro a cada checagem, sem impacto de I/O em disco.

---

## 🛡️ 3. Conclusão sobre Infraestrutura
A atual arquitetura do Watchdog Agrocenter é **extremamente eficiente**. Ela utiliza menos de **10% da RAM total disponível** e mantém a média de processamento (*load average*) em níveis confortáveis para o Raspberry Pi, assegurando que o sistema permaneça operacional e resiliente por tempo indeterminado sem a necessidade de upgrades de hardware.
