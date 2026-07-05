import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
import urllib3

try:
    from curl_cffi import requests as impersonate_requests
    HAS_CURL_CFFI = True
except ImportError:
    impersonate_requests = requests
    HAS_CURL_CFFI = False

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
        'logs_dir': os.path.join(base_dir, 'logs'),
        'impersonate_browser': os.getenv('CURL_IMPERSONATE_BROWSER', 'chrome')
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

def test_http_service(url, timeout, impersonate_profile='chrome'):
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
    
    user_agents_map = {
        'chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'firefox': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
        'safari': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'edge': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    }
    
    for attempt in range(1, retries + 1):
        start_time = time.time()
        current_profile = 'requests'
        try:
            if HAS_CURL_CFFI:
                profiles = [impersonate_profile, "firefox", "safari", "edge"]
                profiles = list(dict.fromkeys([p for p in profiles if p]))
                current_profile = profiles[(attempt - 1) % len(profiles)]
                
                req_headers = headers.copy()
                req_headers['User-Agent'] = user_agents_map.get(current_profile, headers['User-Agent'])
                
                response = impersonate_requests.get(url, timeout=timeout, headers=req_headers, impersonate=current_profile)
            else:
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
                    if attempt < retries:
                        print(f"[WAF Bypass] Tentativa {attempt} com perfil '{current_profile}' bloqueada pela Akamai. Rotacionando perfil...")
                        raise requests.exceptions.RequestException("WAF Blocked")
                    return False, response.status_code, elapsed_ms, "Bloqueio de Firewall (Akamai WAF)"
                return False, response.status_code, elapsed_ms, f"Erro HTTP Status Code: {response.status_code}"
                
            content_lower = response.text.lower()
            
            # 3. Verificar páginas de erro disfarçadas ou bloqueios Akamai
            if any(x in content_lower for x in ["access denied", "reference #", "akamai"]):
                if "loading..." not in content_lower:
                    if attempt < retries:
                        print(f"[WAF Bypass] Tentativa {attempt} com perfil '{current_profile}' bloqueada pela Akamai (página de erro disfarçada). Rotacionando perfil...")
                        raise requests.exceptions.RequestException("WAF Blocked")
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
        smtp_config=config['smtp_config'],
        db_path=config['db_path']
    )

    log_to_file(config['logs_dir'], "Iniciando verificação de rotina...")
    is_healthy, status_code, elapsed_ms, error_msg = test_http_service(
        config['url'], 
        config['timeout'],
        impersonate_profile=config.get('impersonate_browser', 'chrome')
    )
    
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
            notifier.send_telegram_alert(msg, config['contacts_path'], consecutive_failures=0)
            log_to_file(config['logs_dir'], "Alerta de restabelecimento enviado via Telegram.")
            
    else:
        log_to_file(config['logs_dir'], f"Serviço Agrocenter COM FALHA! Motivo: {error_msg}")
        
        if not active_incident:
            # Primeiro erro: cria incidente silencioso (para contabilizar Uptime)
            incident_id = db.create_incident()
            log_to_file(config['logs_dir'], "Serviço Agrocenter COM FALHA! Criando novo incidente (contagem de falhas iniciada).")
        else:
            # Erro persistente: atualiza falhas consecutivas
            incident_id = active_incident['id']
            new_failures = active_incident['consecutive_failures'] + 1
            db.update_incident_failures(incident_id, new_failures)
            
            log_to_file(config['logs_dir'], f"Falha persistente. Total de erros consecutivos: {new_failures}")

            # Verifica se atingiu os limites exatos de escalação (Nível 1, 2, 3 ou 4) dinamicamente
            settings = db.get_all_settings()
            check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '3'))
            
            l1_min = int(settings.get('level1_minutes', '15'))
            l2_min = int(settings.get('level2_minutes', '60'))
            l3_min = int(settings.get('level3_minutes', '150'))
            l4_min = int(settings.get('level4_minutes', '720'))
            
            l1_fail = max(1, int(l1_min / check_interval))
            l2_fail = max(1, int(l2_min / check_interval))
            l3_fail = max(1, int(l3_min / check_interval))
            l4_fail = max(1, int(l4_min / check_interval))
            
            def format_time_off(minutes):
                if minutes >= 60:
                    hours = minutes / 60
                    if hours == int(hours):
                        return f"{int(hours)} hora" if hours == 1 else f"{int(hours)} horas"
                    return f"{hours} horas"
                return f"{minutes} minutos"

            limiares = {
                l1_fail: ("NÍVEL 1 (Operacional TI)", format_time_off(l1_min), "Operacional TI"),
                l2_fail: ("NÍVEL 2 (Analista / Coordenação)", format_time_off(l2_min), "Analista / Coordenação"),
                l3_fail: ("NÍVEL 3 (Gerência)", format_time_off(l3_min), "Gerência"),
                l4_fail: ("NÍVEL 4 (Diretoria)", format_time_off(l4_min), "Diretoria")
            }
            
            if new_failures in limiares:
                nivel_nome, tempo_off, gravidade = limiares[new_failures]
                
                # 1. Seleção e envio de Template do Telegram específico para o nível e falha
                if "Akamai" in error_msg:
                    telegram_escalation_msg = (
                        f"🛡️ <b>ALERTA DE SEGURANÇA: {nivel_nome} - Bloqueio Akamai WAF há {tempo_off}</b>\n"
                        f"<i>O tráfego do Watchdog está sendo barrado pelo WAF da C.Vale.</i>\n\n"
                        f"<b>Serviço:</b> C.Vale Agrocenter\n"
                        f"<b>Status HTTP:</b> {status_code} (Forbidden/Access Denied)\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n"
                        f"<b>Mensagem de Erro:</b> <code>{error_msg}</code>\n"
                        f"<b>Gravidade:</b> {gravidade}\n\n"
                        f"⚠️ <i>Nota: Possível bloqueio de IP público da LAN ou mudança de regras no WAF.</i>"
                    )
                elif "DNS Local" in error_msg:
                    telegram_escalation_msg = (
                        f"⚙️ <b>ALERTA LOCAL: {nivel_nome} - Falha de DNS Local (Pi-hole/Unbound) há {tempo_off}</b>\n"
                        f"<i>Detecção de instabilidade nos resolvedores locais da LAN.</i>\n\n"
                        f"<b>Serviço de Origem:</b> Unbound + Pi-hole Local\n"
                        f"<b>Erro:</b> Falha ao resolver o domínio do Agrocenter\n"
                        f"<b>Resultado do DNS Fallback:</b> DNS público (1.1.1.1/8.8.8.8) resolveu com sucesso!\n"
                        f"<b>Status do Link Externo:</b> Funcional (requisição via IP respondeu)\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n"
                        f"<b>Gravidade:</b> {gravidade}\n\n"
                        f"⚠️ <i>Atenção: O portal está online na rede externa, mas inacessível dentro da LAN.</i>"
                    )
                else:
                    telegram_escalation_msg = (
                        f"🚨 <b>ALERTA ESCALADO: {nivel_nome} - Agrocenter Offline há {tempo_off}</b>\n"
                        f"<i>Falha consecutiva persistente detectada pelo Watchdog C.Vale.</i>\n\n"
                        f"<b>Serviço:</b> C.Vale Agrocenter\n"
                        f"<b>URL:</b> {config['url']}\n"
                        f"<b>Status HTTP:</b> {status_code}\n"
                        f"<b>Tempo de Resposta:</b> {elapsed_ms} ms\n"
                        f"<b>Erros Consecutivos:</b> {new_failures} tentativas\n"
                        f"<b>Mensagem de Erro:</b> <code>{error_msg}</code>\n"
                        f"<b>Gravidade:</b> {gravidade}\n\n"
                        f"⚠️ <i>Atenção: O serviço falhou de forma contínua e requer inspeção do backend.</i>"
                    )
                
                # Envia o alerta especial de escalação via Telegram
                notifier.send_telegram_alert(telegram_escalation_msg, config['contacts_path'], consecutive_failures=new_failures)
                log_to_file(config['logs_dir'], f"Alerta {nivel_nome} do Telegram enviado.")

                # 2. Dispara notificação por e-mail (Escalação)
                subject = f"[{nivel_nome}] Falha Persistente - Watchdog C.Vale Agrocenter"
                template_vars = {
                    'alert_class': 'critical',
                    'alert_summary': f"O Agrocenter falhou {new_failures} vezes consecutivas ({tempo_off} off) e requer atenção imediata.",
                    'incident_status': f'CRÍTICO - {nivel_nome}',
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
                    log_to_file(config['logs_dir'], f"E-mail de escalação {nivel_nome} enviado com sucesso.")

def run_daily_report():
    config = load_config()
    db = DatabaseManager(config['db_path'])
    notifier = Notifier(
        telegram_token=config['telegram_token'],
        telegram_chat_id=config['telegram_chat_id'],
        smtp_config=config['smtp_config'],
        db_path=config['db_path']
    )
    
    log_to_file(config['logs_dir'], "Iniciando geração de relatório diário...")
    
    # 1. Coleta os KPIs das últimas 24 horas usando get_kpis
    kpis = db.get_kpis(period_filter='1d')
    
    # 2. Coleta a lista de incidentes que ocorreram nas últimas 24 horas
    import sqlite3
    conn = sqlite3.connect(config['db_path'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, start_timestamp, end_timestamp, consecutive_failures, status
        FROM incidents
        WHERE start_timestamp >= datetime('now', 'localtime', '-24 hours')
        ORDER BY start_timestamp DESC
    """)
    incidents = cursor.fetchall()
    
    # Monta a tabela HTML de incidentes
    if incidents:
        table_rows = ""
        for inc in incidents:
            status_badge = ""
            if inc['status'] == 'RESOLVED':
                status_badge = '<span class="incident-badge badge-resolved">Resolvido</span>'
            else:
                status_badge = '<span class="incident-badge badge-active">Ativo</span>'
                
            start_dt = datetime.fromisoformat(inc['start_timestamp'])
            end_time_str = "N/A"
            duration_str = "N/A"
            if inc['end_timestamp']:
                end_dt = datetime.fromisoformat(inc['end_timestamp'])
                end_time_str = end_dt.strftime('%d/%m/%Y %H:%M:%S')
                duration_str = f"{round((end_dt - start_dt).total_seconds() / 60, 1)} min"
            elif inc['status'] == 'ACTIVE':
                duration_str = f"{round((datetime.now() - start_dt).total_seconds() / 60, 1)} min (em andamento)"
                
            table_rows += f"""
                <tr>
                    <td>#{inc['id']}</td>
                    <td>{start_dt.strftime('%d/%m/%Y %H:%M:%S')}</td>
                    <td>{end_time_str}</td>
                    <td>{duration_str}</td>
                    <td>{status_badge}</td>
                </tr>
            """
        incident_table_html = f"""
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Início</th>
                        <th>Resolução</th>
                        <th>Duração</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        """
    else:
        incident_table_html = "<p style='font-size: 13px; color: #475569;'>Nenhum incidente registrado nas últimas 24 horas.</p>"

    # 3. Monta a tabela HTML de distribuição de falhas
    if kpis.get('error_distribution'):
        error_rows = ""
        for err in kpis['error_distribution']:
            error_rows += f"""
                <tr>
                    <td><b>{err['error_message']}</b></td>
                    <td style="text-align: right;">{err['count']} ocor.</td>
                    <td style="text-align: right;"><b>{err['percentage']}%</b></td>
                </tr>
            """
        error_distribution_html = f"""
            <table>
                <thead>
                    <tr>
                        <th>Mensagem de Erro</th>
                        <th style="text-align: right;">Frequência</th>
                        <th style="text-align: right;">Proporção</th>
                    </tr>
                </thead>
                <tbody>
                    {error_rows}
                </tbody>
            </table>
        """
    else:
        error_distribution_html = "<p style='font-size: 13px; color: #475569;'>Nenhuma falha de serviço registrada no período.</p>"
        
    # Cores de KPI baseadas no status
    availability = float(kpis.get('availability', 100))
    uptime_color = "#16a34a" if availability >= 99.0 else ("#d97706" if availability >= 95.0 else "#dc2626")
    
    total_incidents = int(kpis.get('total_incidents', 0))
    incident_color = "#475569" if total_incidents == 0 else "#dc2626"
    
    # Total de falhas no período
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM monitor_logs 
        WHERE is_healthy = 0 AND timestamp >= datetime('now', 'localtime', '-24 hours')
    """)
    failures_count = cursor.fetchone()['cnt']
    conn.close()

    # Variáveis do Template
    template_vars = {
        'generation_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'availability': str(availability),
        'uptime_color': uptime_color,
        'avg_response_time': str(kpis.get('avg_response_time', 0)),
        'total_checks': str(kpis.get('total_checks', 0)),
        'failures_count': str(failures_count),
        'total_incidents': str(total_incidents),
        'incident_color': incident_color,
        'incident_table_html': incident_table_html,
        'error_distribution_html': error_distribution_html,
        'agrocenter_url': config['url']
    }

    # Caminho do template de relatório diário
    daily_template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'daily_report_template.html'))

    # 5. Envia o relatório por E-mail
    subject = f"[RELATÓRIO DIÁRIO] Fechamento de Expediente - Watchdog Agrocenter"
    email_sent = notifier.send_email_report(
        subject=subject,
        template_vars=template_vars,
        contacts_path=config['contacts_path'],
        template_path=daily_template_path
    )
    
    # 6. Envia resumo via Telegram
    telegram_msg = (
        f"📊 <b>RELATÓRIO DIÁRIO: C.Vale Agrocenter</b>\n"
        f"<i>Consolidado das últimas 24 horas (Fechamento às 18h).</i>\n\n"
        f"<b>Disponibilidade (Uptime):</b> {availability}%\n"
        f"<b>Latência Média:</b> {kpis.get('avg_response_time', 0)} ms\n"
        f"<b>Total de Verificações:</b> {kpis.get('total_checks', 0)} (Falhas: {failures_count})\n"
        f"<b>Incidentes Registrados:</b> {total_incidents}\n\n"
        f"📨 <i>O relatório analítico detalhado de incidentes e erros foi enviado com sucesso para o e-mail dos administradores!</i>"
    )
    
    telegram_sent = notifier.send_telegram_alert(telegram_msg, config['contacts_path'], consecutive_failures=0)
    
    if email_sent or telegram_sent:
        log_to_file(config['logs_dir'], "Relatório diário enviado com sucesso.")
        print("Relatório diário enviado com sucesso.")
    else:
        log_to_file(config['logs_dir'], "Erro ao enviar relatório diário.")
        print("Erro ao enviar relatório diário.")

def run_monthly_report():
    config = load_config()
    db = DatabaseManager(config['db_path'])
    notifier = Notifier(
        telegram_token=config['telegram_token'],
        telegram_chat_id=config['telegram_chat_id'],
        smtp_config=config['smtp_config'],
        db_path=config['db_path']
    )
    
    log_to_file(config['logs_dir'], "Iniciando geração de relatório mensal...")
    
    # 1. Coleta os KPIs dos últimos 30 dias usando get_kpis
    kpis = db.get_kpis(period_filter='30d')
    
    # 2. Coleta a lista de incidentes que ocorreram nos últimos 30 dias
    import sqlite3
    conn = sqlite3.connect(config['db_path'])
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, start_timestamp, end_timestamp, consecutive_failures, status
        FROM incidents
        WHERE start_timestamp >= datetime('now', 'localtime', '-30 days')
        ORDER BY start_timestamp DESC
    """)
    incidents = cursor.fetchall()
    
    # Monta a tabela HTML de incidentes
    if incidents:
        table_rows = ""
        for inc in incidents:
            status_badge = ""
            if inc['status'] == 'RESOLVED':
                status_badge = '<span class="incident-badge badge-resolved">Resolvido</span>'
            else:
                status_badge = '<span class="incident-badge badge-active">Ativo</span>'
                
            start_dt = datetime.fromisoformat(inc['start_timestamp'])
            end_time_str = "N/A"
            duration_str = "N/A"
            if inc['end_timestamp']:
                end_dt = datetime.fromisoformat(inc['end_timestamp'])
                end_time_str = end_dt.strftime('%d/%m/%Y %H:%M:%S')
                duration_str = f"{round((end_dt - start_dt).total_seconds() / 60, 1)} min"
            elif inc['status'] == 'ACTIVE':
                duration_str = f"{round((datetime.now() - start_dt).total_seconds() / 60, 1)} min (em andamento)"
                
            table_rows += f"""
                <tr>
                    <td>#{inc['id']}</td>
                    <td>{start_dt.strftime('%d/%m/%Y %H:%M:%S')}</td>
                    <td>{end_time_str}</td>
                    <td>{duration_str}</td>
                    <td>{status_badge}</td>
                </tr>
            """
        incident_table_html = f"""
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Início</th>
                        <th>Resolução</th>
                        <th>Duração</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        """
    else:
        incident_table_html = "<p style='font-size: 13px; color: #475569;'>Nenhum incidente registrado nos últimos 30 dias.</p>"

    # 3. Monta a tabela HTML de distribuição de falhas
    if kpis.get('error_distribution'):
        error_rows = ""
        for err in kpis['error_distribution']:
            error_rows += f"""
                <tr>
                    <td><b>{err['error_message']}</b></td>
                    <td style="text-align: right;">{err['count']} ocor.</td>
                    <td style="text-align: right;"><b>{err['percentage']}%</b></td>
                </tr>
            """
        error_distribution_html = f"""
            <table>
                <thead>
                    <tr>
                        <th>Mensagem de Erro</th>
                        <th style="text-align: right;">Frequência</th>
                        <th style="text-align: right;">Proporção</th>
                    </tr>
                </thead>
                <tbody>
                    {error_rows}
                </tbody>
            </table>
        """
    else:
        error_distribution_html = "<p style='font-size: 13px; color: #475569;'>Nenhuma falha de serviço registrada no período.</p>"
        
    # Cores de KPI baseadas no status
    availability = float(kpis.get('availability', 100))
    uptime_color = "#16a34a" if availability >= 99.0 else ("#d97706" if availability >= 95.0 else "#dc2626")
    
    total_incidents = int(kpis.get('total_incidents', 0))
    incident_color = "#475569" if total_incidents == 0 else "#dc2626"
    
    # Total de falhas no período
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM monitor_logs 
        WHERE is_healthy = 0 AND timestamp >= datetime('now', 'localtime', '-30 days')
    """)
    failures_count = cursor.fetchone()['cnt']
    conn.close()

    # Variáveis do Template
    template_vars = {
        'generation_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'availability': str(availability),
        'uptime_color': uptime_color,
        'avg_response_time': str(kpis.get('avg_response_time', 0)),
        'total_checks': str(kpis.get('total_checks', 0)),
        'failures_count': str(failures_count),
        'total_incidents': str(total_incidents),
        'incident_color': incident_color,
        'incident_table_html': incident_table_html,
        'error_distribution_html': error_distribution_html,
        'agrocenter_url': config['url']
    }

    # Caminho do template de relatório diário (podemos usar o mesmo template visual)
    daily_template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'daily_report_template.html'))

    # 5. Envia o relatório por E-mail
    subject = f"[RELATÓRIO MENSAL] Fechamento de Ciclo (30 dias) - Watchdog Agrocenter"
    email_sent = notifier.send_email_report(
        subject=subject,
        template_vars=template_vars,
        contacts_path=config['contacts_path'],
        template_path=daily_template_path
    )
    
    # 6. Envia resumo via Telegram
    telegram_msg = (
        f"📊 <b>RELATÓRIO MENSAL: C.Vale Agrocenter</b>\n"
        f"<i>Consolidado dos últimos 30 dias (Fechamento Mensal).</i>\n\n"
        f"<b>Disponibilidade (SLA Mensal):</b> {availability}%\n"
        f"<b>Latência Média:</b> {kpis.get('avg_response_time', 0)} ms\n"
        f"<b>Total de Verificações:</b> {kpis.get('total_checks', 0)} (Falhas: {failures_count})\n"
        f"<b>Incidentes Registrados:</b> {total_incidents}\n\n"
        f"📨 <i>O relatório mensal analítico detalhado com o SLA consolidado foi enviado com sucesso para o e-mail dos administradores!</i>"
    )
    
    telegram_sent = notifier.send_telegram_alert(telegram_msg, config['contacts_path'], consecutive_failures=0)
    
    if email_sent or telegram_sent:
        log_to_file(config['logs_dir'], "Relatório mensal enviado com sucesso.")
        print("Relatório mensal enviado com sucesso.")
    else:
        log_to_file(config['logs_dir'], "Erro ao enviar relatório mensal.")
        print("Erro ao enviar relatório mensal.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--daily-report':
            run_daily_report()
        elif sys.argv[1] == '--monthly-report':
            run_monthly_report()
        else:
            run_check()
    else:
        run_check()
