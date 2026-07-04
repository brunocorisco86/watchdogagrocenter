import os
import sys
from flask import Flask, render_code, render_template, jsonify, redirect, url_for
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
    kpis = db.get_kpis()
    logs = db.get_latest_logs(limit=30)
    
    # Adicionar status do serviço agrocenter atual
    agrocenter_url = os.getenv('AGROCENTER_URL', 'https://prd-agrocenter.cvale.com.br')
    
    return render_template('index.html', kpis=kpis, logs=logs, url=agrocenter_url)

@app.route('/api/kpis')
def api_kpis():
    kpis = db.get_kpis()
    return jsonify(kpis)

@app.route('/api/logs')
def api_logs():
    logs = db.get_latest_logs(limit=30)
    return jsonify(logs)

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
