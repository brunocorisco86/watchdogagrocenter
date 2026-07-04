import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import urllib3

# Desativa avisos de requisições HTTPS inseguras (usado nas validações por IP direto)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def resolve_dns_udp(domain, dns_server):
    """
    Realiza uma consulta DNS UDP (tipo A) de forma nativa (sem dependências externas)
    para o servidor DNS informado (1.1.1.1 ou 8.8.8.8).
    """
    import socket
    import struct
    
    # Cabeçalho DNS Query simples (ID=0x1234, Flags=0x0100, QDCOUNT=1)
    packet = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    for part in domain.split('.'):
        packet += struct.pack("B", len(part)) + part.encode('utf-8')
    packet += b'\x00' # Final do nome
    packet += struct.pack(">HH", 1, 1) # Tipo A (IPv4), Classe IN (Internet)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        sock.sendto(packet, (dns_server, 53))
        data, _ = sock.recvfrom(512)
        sock.close()
        
        # Pula cabeçalho (12 bytes) e a query para encontrar a resposta
        idx = 12
        while data[idx] != 0:
            idx += data[idx] + 1
        idx += 5 # Pula byte 0, tipo e classe (4 bytes)
        
        # Leitura da resposta
        if (data[idx] & 0xc0) == 0xc0:
            idx += 2 # Nome compactado
        else:
            while data[idx] != 0:
                idx += data[idx] + 1
            idx += 1
            
        rdlength = struct.unpack(">H", data[idx+8:idx+10])[0]
        ip_bytes = data[idx+10:idx+10+rdlength]
        if rdlength == 4:
            return ".".join(str(b) for b in ip_bytes)
    except Exception:
        pass
    return None

def test_isp_connectivity():
    """
    Testa a conectividade com a internet externa (ISP local) acessando
    serviços mundiais altamente estáveis. Retorna True se houver conexão, False caso contrário.
    """
    if os.getenv("FORCE_ISP_OFFLINE") == "1":
        return False
    test_urls = ["https://1.1.1.1", "https://8.8.8.8"]
    for url in test_urls:
        try:
            response = requests.head(url, timeout=2.0, verify=False)
            if response.status_code < 400:
                return True
        except Exception:
            continue
    return False

def test_http_service(url, timeout):
    """
    Realiza o teste HTTP com sistema de retry (3 tentativas) e fallback
    de DNS para 1.1.1.1/8.8.8.8 no caso de erros de conexão/DNS.
    """
    import urllib3
    from urllib.parse import urlparse
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    headers = {
        'User-Agent': 'C.Vale Watchdog Agent/1.0 (Raspberry Pi Dev)'
    }
    
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    
    retries = 3
    sleep_seconds = 2
    
    for attempt in range(1, retries + 1):
        start_time = time.time()
        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # 1. Validação de Metadados de Cabeçalhos HTTP
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                return False, response.status_code, elapsed_ms, f"Tipo de conteúdo inválido nos metadados HTTP: '{content_type}'"

            # 2. Status HTTP de Erro
            if response.status_code >= 400:
                content_lower = response.text.lower()
                if any(x in content_lower for x in ["access denied", "reference #", "akamai"]):
                    return False, response.status_code, elapsed_ms, "Bloqueio de Firewall (Akamai WAF)"
                return False, response.status_code, elapsed_ms, f"Erro HTTP Status Code: {response.status_code}"
                
            content_lower = response.text.lower()
            
            # 3. Verificar páginas de erro disfarçadas ou bloqueios Akamai
            if any(x in content_lower for x in ["access denied", "reference #", "akamai"]):
                if "loading..." not in content_lower:
                    return False, response.status_code, elapsed_ms, "Bloqueio de Firewall (Akamai WAF)"
                
            # 4. Verificar falhas de backend/banco de dados
            db_error_indicators = ["database connection failed", "sql error", "driver error", "internal server error", "fatal error"]
            for indicator in db_error_indicators:
                if indicator in content_lower:
                    return False, response.status_code, elapsed_ms, f"Erro de banco/sistema exposto na resposta: '{indicator}'"
                    
            # 5. Premissa de Presença e Assinatura do Portal React
            expected_keywords = [
                'content="agro center"',
                'eaware.io',
                'assets/images/geral/simbolo.png',
                'loading...',
                'agrocenter'
            ]
            has_keyword = any(kw in content_lower for kw in expected_keywords)
            if not has_keyword:
                return False, response.status_code, elapsed_ms, "Conteúdo retornado não condiz com o portal Agrocenter (possível falha de DNS ou sequestro de rota)"

            return True, response.status_code, elapsed_ms, ""
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Se for a última tentativa, executa a checagem de ISP e o DNS fallback
            if attempt == retries:
                # 1. Checa a conectividade geral com a internet (ISP local)
                if not test_isp_connectivity():
                    return False, 0, elapsed_ms, "Falha de Conectividade Local (Sem Internet - ISP Offline)"

                # 2. Se temos internet, tentamos o fallback de DNS
                resolved_ip = None
                for public_dns in ["1.1.1.1", "8.8.8.8"]:
                    resolved_ip = resolve_dns_udp(hostname, public_dns)
                    if resolved_ip:
                        break
                
                if resolved_ip:
                    # O DNS público resolveu. Indica falha no Unbound / Pi-hole local!
                    try:
                        fallback_url = url.replace(hostname, resolved_ip)
                        fallback_headers = headers.copy()
                        fallback_headers['Host'] = hostname
                        
                        fb_start = time.time()
                        fb_response = requests.get(fallback_url, headers=fallback_headers, timeout=timeout, verify=False)
                        fb_elapsed = int((time.time() - fb_start) * 1000)
                        
                        if fb_response.status_code < 400:
                            return False, 0, fb_elapsed, "Falha de DNS Local (Pi-hole / Unbound)"
                        else:
                            return False, fb_response.status_code, fb_elapsed, "Erro de Rede Externo (DNS local com falha, rota com erro)"
                    except Exception:
                        return False, 0, elapsed_ms, "Falha de DNS Local (Unbound inativo / Sem resolução local)"
                else:
                    # ISP está online, mas o DNS público também não resolveu (domínio inexistente/fora do ar)
                    return False, 0, elapsed_ms, "Falha de Resolução DNS Geral (Dominio inacessivel)"
            
            time.sleep(sleep_seconds)
            
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            if attempt == retries:
                return False, 0, elapsed_ms, f"Erro inesperado após retentativas: {str(e)}"
            time.sleep(sleep_seconds)

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

    # Se for falha nossa de infra local (ISP Offline), registramos o log acima mas suspendemos alertas
    if not is_healthy and error_msg == "Falha de Conectividade Local (Sem Internet - ISP Offline)":
        log_to_file(config['logs_dir'], "Falha classificada como INFRAESTRUTURA LOCAL (ISP Offline). Alertas e incidentes suspensos.")
        return

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

            # Se atingiu o limite de 5 falhas consecutivas e os alertas de escalação ainda não foram disparados
            if new_failures >= config['max_failures'] and not active_incident['email_sent']:
                downtime_minutes = round((datetime.now() - datetime.fromisoformat(active_incident['start_timestamp'])).total_seconds() / 60, 1)
                
                # 1. Seleção e envio de Template do Telegram específico para a falha
                if "Akamai" in error_msg:
                    # Template 2: Bloqueio do WAF / Akamai
                    telegram_escalation_msg = (
                        f"🛡️ <b>ALERTA DE SEGURANÇA: Bloqueio Akamai WAF há {downtime_minutes} min</b>\n"
                        f"<i>O tráfego do Watchdog está sendo barrado pelo WAF da C.Vale.</i>\n\n"
                        f"<b>Serviço:</b> C.Vale Agrocenter\n"
                        f"<b>Status HTTP:</b> {status_code} (Forbidden/Access Denied)\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n"
                        f"<b>Mensagem de Erro:</b> <code>{error_msg}</code>\n\n"
                        f"⚠️ <i>Nota: Possível bloqueio de IP público da LAN ou mudança de regras no WAF.</i>"
                    )
                elif "DNS Local" in error_msg:
                    # Template 3: Problema no DNS Local (Pi-hole / Unbound)
                    telegram_escalation_msg = (
                        f"⚙️ <b>ALERTA LOCAL: Falha de DNS Local (Pi-hole/Unbound)</b>\n"
                        f"<i>Detecção de instabilidade nos resolvedores locais da LAN.</i>\n\n"
                        f"<b>Serviço de Origem:</b> Unbound + Pi-hole Local\n"
                        f"<b>Erro:</b> Falha ao resolver o domínio do Agrocenter\n"
                        f"<b>Resultado do DNS Fallback:</b> DNS público (1.1.1.1/8.8.8.8) resolveu com sucesso!\n"
                        f"<b>Status do Link Externo:</b> Funcional (requisição via IP respondeu)\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n\n"
                        f"⚠️ <i>Atenção: O portal está online na rede externa, mas inacessível dentro da LAN.</i>"
                    )
                else:
                    # Template 1: Falha Geral de Servidor / Timeout / HTTP Erro
                    telegram_escalation_msg = (
                        f"🚨 <b>ALERTA ESCALADO: Agrocenter Offline há {downtime_minutes} min</b>\n"
                        f"<i>Falha consecutiva persistente detectada pelo Watchdog C.Vale.</i>\n\n"
                        f"<b>Serviço:</b> C.Vale Agrocenter\n"
                        f"<b>URL:</b> {config['url']}\n"
                        f"<b>Status HTTP:</b> {status_code}\n"
                        f"<b>Tempo de Resposta:</b> {elapsed_ms} ms\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n"
                        f"<b>Mensagem de Erro:</b> <code>{error_msg}</code>\n"
                        f"<b>Uptime:</b> Sem Uptime no período\n\n"
                        f"⚠️ <i>Atenção: O serviço falhou de forma contínua e requer inspeção do backend.</i>"
                    )
                
                # Envia o alerta especial de escalação via Telegram
                notifier.send_telegram_alert(telegram_escalation_msg)
                log_to_file(config['logs_dir'], "Alerta escalado do Telegram com template específico enviado.")

                # 2. Dispara notificação por e-mail (Escalação)
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

if __name__ == '__main__':
    run_check()
