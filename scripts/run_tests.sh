#!/bin/bash
# Script de execução rápida de testes unitários e de integração
set -e

# Navega até o diretório raiz
cd "$(dirname "$0")/.."

# Ativa o ambiente virtual se ele existir
if [ -d "venv" ]; then
    echo "✓ Ativando ambiente virtual (venv)..."
    source venv/bin/activate
else
    echo "⚠ Ambiente virtual não encontrado. Rodando no contexto global."
fi

echo "🧪 Iniciando a execução dos testes via pytest..."
export PYTHONPATH=.
pytest -v
