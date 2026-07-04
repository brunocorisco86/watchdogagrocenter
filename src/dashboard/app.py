import os
import sys
from flask import Flask, render_template, jsonify, redirect, url_for, request
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.watchdog.database import DatabaseManager
from src.watchdog.watchdog_cli import run_check

app = Flask(__name__)

# Carrega configurações
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
load_dotenv(os.path.join(base_dir, '.env'))

DB_PATH = os.path.join(base_dir, os.getenv('SQLITE_DB_PATH', 'src/watchdog/database.db'))
db = DatabaseManager(DB_PATH)

@app.route('/')
def index():
    # Carrega KPIs padrão de 30 dias
    kpis = db.get_kpis('30d')
    logs = db.get_latest_logs(limit=30)
    
    # Adicionar status do serviço agrocenter atual
    agrocenter_url = os.getenv('AGROCENTER_URL', 'https://prd-agrocenter.cvale.com.br')
    
    return render_template('index.html', kpis=kpis, logs=logs, url=agrocenter_url)

@app.route('/api/kpis')
def api_kpis():
    period = request.args.get('period', '30d')
    kpis = db.get_kpis(period)
    return jsonify(kpis)

@app.route('/api/logs')
def api_logs():
    logs = db.get_latest_logs(limit=30)
    return jsonify(logs)

@app.route('/api/system-logs')
def api_system_logs():
    """Lê as últimas 50 linhas do arquivo de log físico do sistema"""
    log_file_path = os.path.join(base_dir, 'logs/watchdog.log')
    if not os.path.exists(log_file_path):
        return jsonify(["Arquivo de log do sistema vazio ou inexistente."])
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Pega as últimas 50 linhas e inverte para ficar em ordem cronológica inversa (mais recente no topo) ou normal
        last_lines = [line.strip() for line in lines[-50:]]
        return jsonify(last_lines)
    except Exception as e:
        return jsonify([f"Erro ao ler logs: {str(e)}"])

@app.route('/api/latency-6h')
def api_latency_6h():
    """Retorna os dados de latência das últimas 6 horas para alimentar o gráfico"""
    history = db.get_latency_history_6h()
    return jsonify(history)

@app.route('/api/trigger', methods=['POST'])
def trigger_check():
    """Roda a verificação do watchdog manualmente"""
    try:
        run_check()
        return jsonify({'status': 'success', 'message': 'Verificação executada com sucesso!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=True)
