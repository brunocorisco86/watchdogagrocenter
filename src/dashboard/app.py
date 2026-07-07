import os
import sys
from flask import Flask, render_template, jsonify, redirect, url_for, request
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Adiciona o diretório raiz ao path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.watchdog.database import DatabaseManager
from src.watchdog.watchdog_cli import run_check

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute"],
    headers_enabled=True,
    storage_uri="memory://"
)

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
    
    settings = db.get_all_settings()
    check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '3'))
    
    l1_min = int(settings.get('level1_minutes', 15))
    l2_min = int(settings.get('level2_minutes', 60))
    l3_min = int(settings.get('level3_minutes', 150))
    l4_min = int(settings.get('level4_minutes', 720))
    
    def format_time_text(minutes):
        if minutes >= 60:
            h = minutes / 60
            if h == int(h):
                return f"{int(h)} hora" if h == 1 else f"{int(h)} horas"
            return f"{h} horas"
        return f"{minutes} minutos"
        
    render_settings = {
        'l1_min': l1_min, 'l1_fail': max(1, int(l1_min / check_interval)), 'l1_time': format_time_text(l1_min),
        'l2_min': l2_min, 'l2_fail': max(1, int(l2_min / check_interval)), 'l2_time': format_time_text(l2_min),
        'l3_min': l3_min, 'l3_fail': max(1, int(l3_min / check_interval)), 'l3_time': format_time_text(l3_min),
        'l4_min': l4_min, 'l4_fail': max(1, int(l4_min / check_interval)), 'l4_time': format_time_text(l4_min)
    }
    
    return render_template('index.html', kpis=kpis, logs=logs, url=agrocenter_url, settings=render_settings)

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
    """Retorna os dados de latência do período escolhido para alimentar o gráfico"""
    period = request.args.get('period', '6h')
    history = db.get_latency_history_6h(period)
    return jsonify(history)


@app.route('/api/trigger', methods=['POST'])
@limiter.limit("10 per minute")
def trigger_check():
    """Roda a verificação do watchdog manualmente"""
    try:
        run_check()
        return jsonify({'status': 'success', 'message': 'Verificação executada com sucesso!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

CONTACTS_PATH = os.path.join(base_dir, 'src/watchdog/contacts.json')

@app.route('/api/contacts', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def api_contacts():
    if request.method == 'GET':
        if not os.path.exists(CONTACTS_PATH):
            return jsonify([])
        try:
            import json
            with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
                contacts = json.load(f)
            return jsonify(contacts)
        except Exception as e:
            return jsonify({"error": f"Erro ao ler contatos: {str(e)}"}), 500
            
    elif request.method == 'POST':
        data = request.json
        name = data.get('name')
        email = data.get('email')
        telegram_id = data.get('telegram_id', '').strip()
        level = int(data.get('level', 1))
        department = data.get('department', 'TI').strip().upper()
        
        if not name or not email:
            return jsonify({"error": "Nome e e-mail são obrigatórios"}), 400
            
        if level not in [1, 2, 3, 4]:
            return jsonify({"error": "O nível de acionamento deve ser 1 (Operacional TI), 2 (Analista / Coordenação), 3 (Gerência) ou 4 (Diretoria)"}), 400
            
        if department not in ['TI', 'NEGOCIO']:
            return jsonify({"error": "O departamento deve ser 'TI' ou 'NEGOCIO'"}), 400
            
        try:
            import json
            contacts = []
            if os.path.exists(CONTACTS_PATH):
                with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
                    contacts = json.load(f)
            
            # Verifica duplicados
            if any(c['email'].lower() == email.lower() for c in contacts):
                return jsonify({"error": "E-mail já cadastrado"}), 400
                
            new_contact = {
                "name": name,
                "email": email,
                "telegram_id": telegram_id if telegram_id else None,
                "level": level,
                "department": department,
                "enabled": True
            }
            contacts.append(new_contact)
            
            with open(CONTACTS_PATH, 'w', encoding='utf-8') as f:
                json.dump(contacts, f, indent=2, ensure_ascii=False)
                
            return jsonify({"message": "Contato adicionado com sucesso!", "contact": new_contact})
        except Exception as e:
            return jsonify({"error": f"Erro ao salvar contato: {str(e)}"}), 500

@app.route('/api/contacts/delete', methods=['POST'])
@limiter.limit("10 per minute")
def api_delete_contact():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "E-mail é obrigatório"}), 400
        
    try:
        import json
        if not os.path.exists(CONTACTS_PATH):
            return jsonify({"error": "Arquivo de contatos não encontrado"}), 404
            
        with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
            
        # Filtra removendo o email
        new_contacts = [c for c in contacts if c['email'].lower() != email.lower()]
        
        if len(new_contacts) == len(contacts):
            return jsonify({"error": "Contato não encontrado"}), 404
            
        with open(CONTACTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_contacts, f, indent=2, ensure_ascii=False)
            
        return jsonify({"message": "Contato removido com sucesso!"})
    except Exception as e:
        return jsonify({"error": f"Erro ao excluir contato: {str(e)}"}), 500

@app.route('/api/contacts/update', methods=['POST'])
@limiter.limit("10 per minute")
def api_update_contact():
    data = request.json
    original_email = data.get('original_email')
    name = data.get('name')
    email = data.get('email')
    telegram_id = data.get('telegram_id', '').strip()
    level = int(data.get('level', 1))
    department = data.get('department', 'TI').strip().upper()
    
    if not original_email or not name or not email:
        return jsonify({"error": "Nome, e-mail e e-mail original são obrigatórios"}), 400
        
    if level not in [1, 2, 3, 4]:
        return jsonify({"error": "O nível de acionamento deve ser 1 (Operacional TI), 2 (Analista / Coordenação), 3 (Gerência) ou 4 (Diretoria)"}), 400
        
    if department not in ['TI', 'NEGOCIO']:
        return jsonify({"error": "O departamento deve ser 'TI' ou 'NEGOCIO'"}), 400
        
    try:
        import json
        if not os.path.exists(CONTACTS_PATH):
            return jsonify({"error": "Arquivo de contatos não encontrado"}), 404
            
        with open(CONTACTS_PATH, 'r', encoding='utf-8') as f:
            contacts = json.load(f)
            
        # Acha o contato sendo editado
        target_contact = None
        for c in contacts:
            if c['email'].lower() == original_email.lower():
                target_contact = c
                break
                
        if not target_contact:
            return jsonify({"error": "Contato não encontrado"}), 404
            
        # Verifica se o novo e-mail já existe em OUTRO contato
        if email.lower() != original_email.lower():
            if any(c['email'].lower() == email.lower() for c in contacts):
                return jsonify({"error": "O novo e-mail informado já está cadastrado em outro contato"}), 400
                
        # Atualiza campos
        target_contact['name'] = name
        target_contact['email'] = email
        target_contact['telegram_id'] = telegram_id if telegram_id else None
        target_contact['level'] = level
        target_contact['department'] = department
        
        with open(CONTACTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
            
        return jsonify({"message": "Contato atualizado com sucesso!", "contact": target_contact})
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar contato: {str(e)}"}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=["POST"])
def api_settings():
    if request.method == 'GET':
        try:
            settings = db.get_all_settings()
            return jsonify(settings)
        except Exception as e:
            return jsonify({"error": f"Erro ao obter configurações: {str(e)}"}), 500
    elif request.method == 'POST':
        try:
            data = request.json
            settings_to_update = {}
            for key in ('level1_minutes', 'level2_minutes', 'level3_minutes', 'level4_minutes'):
                if key in data:
                    val = int(data[key])
                    if val <= 0:
                        return jsonify({"error": "O tempo deve ser maior que 0 minutos"}), 400
                    settings_to_update[key] = val
            db.update_settings(settings_to_update)
            return jsonify({"message": "Configurações atualizadas com sucesso!", "settings": settings_to_update})
        except ValueError:
            return jsonify({"error": "Valor de tempo inválido (deve ser número inteiro)"}), 400
        except Exception as e:
            return jsonify({"error": f"Erro ao salvar configurações: {str(e)}"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    # e.description will usually contain the limit string like '100 per 1 minute'
    response = jsonify({
        "error": "Too Many Requests",
        "message": f"Rate limit exceeded: {e.description}"
    })
    response.status_code = 429
    if hasattr(e, 'get_headers'):
        for key, value in e.get_headers():
            if key == 'Retry-After':
                response.headers[key] = value
    return response


@app.route('/api/docs/<path:filename>')
def api_get_doc(filename):
    # Security check: prevent directory traversal
    if '..' in filename or filename.startswith('/') or filename.startswith('.'):
        return jsonify({"error": "Acesso não autorizado"}), 400
        
    # Suffix safety
    if not filename.endswith('.md'):
        return jsonify({"error": "Formato de arquivo inválido"}), 400
        
    doc_path = os.path.join(base_dir, filename)
    if not os.path.exists(doc_path):
        return jsonify({"error": f"Arquivo não encontrado: {filename}"}), 404
        
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            "filename": os.path.basename(filename),
            "content": content
        })
    except Exception as e:
        return jsonify({"error": f"Erro ao ler documentação: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5080))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    # Só ativa debug se FLASK_ENV for development ou FLASK_DEBUG for True
    debug_mode = os.getenv('FLASK_ENV', 'production') == 'development' or os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1')
    app.run(host=host, port=port, debug=debug_mode)

