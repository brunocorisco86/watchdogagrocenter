import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.watchdog.database import DatabaseManager
from src.watchdog.notifier import Notifier

def load_config():
    # Carrega .env do diretório raiz
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    load_dotenv(os.path.join(base_dir, '.env'))

    return {
        'url': os.getenv('AGROCENTER_URL', 'https://prd-agrocenter.cvale.com.br'),
        'timeout': int(os.getenv('REQUEST_TIMEOUT_SECONDS', '10')),
        'max_failures': int(os.getenv('MAX_CONSECUTIVE_FAILURES_BEFORE_EMAIL', '3')),
        'db_path': os.path.join(base_dir, os.getenv('SQLITE_DB_PATH', 'src/watchdog/database.db')),
        'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
        'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
        'smtp_config': {
            'server': os.getenv('SMTP_SERVER'),
            'port': os.getenv('SMTP_PORT', '587'),
            'user': os.getenv('SMTP_USER'),
            'password': os.getenv('SMTP_PASSWORD'),
            'from': os.getenv('SMTP_FROM', 'watchdog-agrocenter@cvale.com.br')
        },
        'contacts_path': os.path.join(base_dir, 'src/watchdog/contacts.json'),
        'template_path': os.path.join(base_dir, 'src/watchdog/email_template.html'),
        'logs_dir': os.path.join(base_dir, 'logs')
    }

def log_to_file(logs_dir, message):
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, 'watchdog.log')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

def test_http_service(url, timeout):
    """
    Realiza o teste HTTP e valida as premissas de saúde do serviço Agrocenter.
    Retorna (is_healthy, status_code, elapsed_ms, error_message)
    """
    headers = {
        'User-Agent': 'C.Vale Watchdog Agent/1.0 (Raspberry Pi Dev)'
    }
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=timeout, headers=headers)
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Validar Premissas de Saúde:
        # 1. Status HTTP deve ser menor que 400
        if response.status_code >= 400:
            return False, response.status_code, elapsed_ms, f"Erro HTTP Status Code: {response.status_code}"
            
        content_lower = response.text.lower()
        
        # 2. Verificar páginas de erro disfarçadas ou bloqueios (ex: Cloudflare, erro SQL)
        cloudflare_indicators = ["cloudflare", "ray id", "ddos protection", "checking your browser"]
        for indicator in cloudflare_indicators:
            if indicator in content_lower:
                return False, response.status_code, elapsed_ms, "Bloqueio ou página de desafio Cloudflare detectada"
                
        db_error_indicators = ["database connection failed", "sql error", "driver error", "internal server error", "fatal error"]
        for indicator in db_error_indicators:
            if indicator in content_lower:
                return False, response.status_code, elapsed_ms, f"Erro de banco/sistema exposto na resposta: '{indicator}'"
                
        # 3. Premissa de Presença: Deve conter referências à C.Vale ou Agrocenter para atestar que é o portal correto
        expected_keywords = ["c.vale", "cvale", "agrocenter", "login", "portal", "entrar"]
        has_keyword = any(kw in content_lower for kw in expected_keywords)
        if not has_keyword:
            return False, response.status_code, elapsed_ms, "Conteúdo retornado não condiz com o portal Agrocenter (possível falha de DNS ou redirecionamento)"

        return True, response.status_code, elapsed_ms, ""
        
    except requests.exceptions.Timeout:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return False, 0, elapsed_ms, f"Timeout na requisição após {timeout}s"
    except requests.exceptions.ConnectionError:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return False, 0, elapsed_ms, "Falha de conexão / DNS ao tentar acessar o servidor"
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        return False, 0, elapsed_ms, f"Erro inesperado: {str(e)}"

def run_check():
    config = load_config()
    db = DatabaseManager(config['db_path'])
    notifier = Notifier(
        telegram_token=config['telegram_token'],
        telegram_chat_id=config['telegram_chat_id'],
        smtp_config=config['smtp_config']
    )

    log_to_file(config['logs_dir'], "Iniciando verificação de rotina...")
    is_healthy, status_code, elapsed_ms, error_msg = test_http_service(config['url'], config['timeout'])
    
    # Salva no histórico SQLite
    db.add_monitor_log(status_code, elapsed_ms, is_healthy, error_msg)

    # Gerenciamento de Incidentes
    active_incident = db.get_active_incident()

    if is_healthy:
        log_to_file(config['logs_dir'], f"Serviço Agrocenter SAUDÁVEL. Tempo: {elapsed_ms}ms, Status: {status_code}")
        
        # Se havia uma queda ativa, resolvemos ela
        if active_incident:
            db.resolve_incident(active_incident['id'])
            duration_minutes = round((datetime.now() - datetime.fromisoformat(active_incident['start_timestamp'])).total_seconds() / 60, 1)
            
            # Notifica restabelecimento
            msg = (
                f"✅ <b>RESOLVIDO: C.Vale Agrocenter está Online!</b>\n\n"
                f"<b>URL:</b> {config['url']}\n"
                f"<b>Duração da queda:</b> {duration_minutes} minutos\n"
                f"<b>Tempo de Resposta:</b> {elapsed_ms} ms\n"
                f"<b>Horário:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
            notifier.send_telegram_alert(msg)
            log_to_file(config['logs_dir'], "Alerta de restabelecimento enviado via Telegram.")
            
    else:
        log_to_file(config['logs_dir'], f"Serviço Agrocenter COM FALHA! Motivo: {error_msg}")
        
        if not active_incident:
            # Primeiro erro: cria incidente
            incident_id = db.create_incident()
            
            # Envia Telegram imediato
            msg = (
                f"🚨 <b>ALERTA: C.Vale Agrocenter está Offline!</b>\n\n"
                f"<b>URL:</b> {config['url']}\n"
                f"<b>Status Code:</b> {status_code}\n"
                f"<b>Tempo de Resposta:</b> {elapsed_ms} ms\n"
                f"<b>Erro:</b> {error_msg}\n"
                f"<b>Horário:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"<b>Gravidade:</b> Inicial (Notificação Telegram)"
            )
            sent = notifier.send_telegram_alert(msg)
            if sent:
                db.mark_telegram_sent(incident_id)
                log_to_file(config['logs_dir'], "Notificação de novo incidente enviada via Telegram.")
        else:
            # Erro persistente: atualiza falhas consecutivas
            incident_id = active_incident['id']
            new_failures = active_incident['consecutive_failures'] + 1
            db.update_incident_failures(incident_id, new_failures)
            
            log_to_file(config['logs_dir'], f"Falha persistente. Total de erros consecutivos: {new_failures}")

            # Se atingiu o limite e o e-mail não foi enviado
            if new_failures >= config['max_failures'] and not active_incident['email_sent']:
                # Dispara notificação por e-mail (Escalação)
                subject = f"[CRÍTICO] Falha Persistente - Watchdog C.Vale Agrocenter"
                template_vars = {
                    'alert_class': 'critical',
                    'alert_summary': f"O Agrocenter falhou {new_failures} vezes consecutivas e requer atenção imediata.",
                    'incident_status': 'CRÍTICO - ESCALADO',
                    'badge_class': 'badge-danger',
                    'status_code': str(status_code),
                    'response_time_ms': str(elapsed_ms),
                    'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                    'consecutive_failures': str(new_failures),
                    'max_failures': str(config['max_failures']),
                    'error_message': error_msg,
                    'agrocenter_url': config['url']
                }
                
                email_sent = notifier.send_email_alert(
                    subject=subject,
                    template_vars=template_vars,
                    contacts_path=config['contacts_path'],
                    template_path=config['template_path']
                )
                if email_sent:
                    db.mark_email_sent(incident_id)
                    log_to_file(config['logs_dir'], "E-mail de escalação de incidente enviado com sucesso.")
                
                # Opcional: Atualiza o Telegram com status de escalação
                msg_escalation = (
                    f"⚠️ <b>ALERTA ESCALADO: Agrocenter offline há mais de {new_failures} verificações!</b>\n"
                    f"E-mails de escalação foram enviados aos administradores."
                )
                notifier.send_telegram_alert(msg_escalation)

if __name__ == '__main__':
    run_check()
