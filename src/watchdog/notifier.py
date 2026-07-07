import asyncio
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from aiogram import Bot

class Notifier:
    def __init__(self, telegram_token=None, telegram_chat_id=None, smtp_config=None, db_path=None):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.smtp_config = smtp_config or {}
        self.db_path = db_path

    def _get_thresholds(self):
        # Limiares padrão em minutos
        thresholds = {
            'level1': 15,
            'level2': 60,
            'level3': 150,
            'level4': 720
        }
        
        # Carrega o intervalo de checagem do ambiente
        check_interval = 3
        try:
            check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '3'))
        except Exception:
            pass
            
        if self.db_path and os.path.exists(self.db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM settings")
                rows = cursor.fetchall()
                for row in rows:
                    key = row['key']
                    val = row['value']
                    if key in ('level1_minutes', 'level2_minutes', 'level3_minutes', 'level4_minutes'):
                        level_key = key.replace('_minutes', '')
                        thresholds[level_key] = int(val)
                conn.close()
            except Exception as e:
                print(f"Erro ao carregar configurações de nível do banco: {e}")
                
        # Converte minutos para quantidade de falhas consecutivas
        failures = {
            1: max(1, int(thresholds['level1'] / check_interval)),
            2: max(1, int(thresholds['level2'] / check_interval)),
            3: max(1, int(thresholds['level3'] / check_interval)),
            4: max(1, int(thresholds['level4'] / check_interval))
        }
        return failures

    async def _send_telegram(self, text, contacts_path=None, consecutive_failures=1):
        destinatarios = []
        if self.telegram_chat_id:
            destinatarios.append(str(self.telegram_chat_id))
            
        # Lê contatos adicionais do JSON para envio do Telegram
        if contacts_path and os.path.exists(contacts_path):
            try:
                with open(contacts_path, 'r', encoding='utf-8') as f:
                    contacts = json.load(f)
                
                for c in contacts:
                    t_id = c.get('telegram_id')
                    if t_id and c.get('enabled', True):
                        t_id_str = str(t_id).strip()
                        if t_id_str and t_id_str not in destinatarios:
                            destinatarios.append(t_id_str)
            except Exception as e:
                print(f"Erro ao ler contatos adicionais para Telegram: {e}")

        if not destinatarios:
            print("Nenhum destinatário de Telegram configurado.")
            return False

        if not self.telegram_token:
            print("Telegram Token não configurado no .env.")
            return False

        try:
            bot = Bot(token=self.telegram_token)
            for chat_id in destinatarios:
                try:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
                except Exception as ex:
                    print(f"Erro ao enviar telegram para chat_id {chat_id}: {ex}")
            await bot.session.close()
            return True
        except Exception as e:
            print(f"Erro geral ao inicializar bot do Telegram: {e}")
            return False

    def send_telegram_alert(self, text, contacts_path=None, consecutive_failures=1):
        """Dispara mensagem síncrona chamando a rotina assíncrona do aiogram"""
        return asyncio.run(self._send_telegram(text, contacts_path, consecutive_failures))

    def send_email_alert(self, subject, template_vars, contacts_path, template_path):
        """Envia e-mails para a lista de contatos definida no contacts.json conforme nível de acionamento"""
        if not self.smtp_config.get('server') or not self.smtp_config.get('user'):
            print("SMTP não configurado no .env.")
            return False

        try:
            # 1. Carrega os contatos
            if not os.path.exists(contacts_path):
                print(f"Arquivo de contatos não encontrado em: {contacts_path}")
                return False

            with open(contacts_path, 'r', encoding='utf-8') as f:
                contacts = json.load(f)

            # Filtra destinatários baseado nas falhas consecutivas e área
            failures = int(template_vars.get('consecutive_failures', 5))
            
            destinatarios = []
            for c in contacts:
                if c.get('enabled', True):
                    destinatarios.append(c['email'])

            if not destinatarios:
                print("Nenhum destinatário de e-mail ativo cadastrado.")
                return False

            # 2. Carrega e preenche o template de e-mail
            if not os.path.exists(template_path):
                print(f"Template de e-mail não encontrado em: {template_path}")
                return False

            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()

            # Carrega logos e converte para Base64 para embutir inline no e-mail
            import base64
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            assets_dir = os.path.join(base_dir, 'assets')
            
            cvale_path = os.path.join(assets_dir, 'logo_cvale.png')
            agro_path = os.path.join(assets_dir, 'agro_center.svg')
            
            cvale_base64 = ""
            if os.path.exists(cvale_path):
                try:
                    with open(cvale_path, 'rb') as img_f:
                        cvale_base64 = base64.b64encode(img_f.read()).decode('utf-8')
                except Exception as e:
                    print(f"Erro ao carregar logo C.Vale: {e}")
                    
            agro_base64 = ""
            if os.path.exists(agro_path):
                try:
                    with open(agro_path, 'rb') as img_f:
                        agro_base64 = base64.b64encode(img_f.read()).decode('utf-8')
                except Exception as e:
                    print(f"Erro ao carregar logo Agrocenter: {e}")

            # Preenche os placeholders no HTML usando .replace para evitar KeyError com CSS do template
            html_content = template_html
            replacements = {
                '{alert_class}': template_vars.get('alert_class', 'critical'),
                '{alert_summary}': template_vars.get('alert_summary', 'Alerta de Indisponibilidade'),
                '{incident_status}': template_vars.get('incident_status', 'CRÍTICO'),
                '{badge_class}': template_vars.get('badge_class', 'badge-danger'),
                '{status_code}': template_vars.get('status_code', 'N/A'),
                '{response_time_ms}': template_vars.get('response_time_ms', 'N/A'),
                '{timestamp}': template_vars.get('timestamp', 'N/A'),
                '{consecutive_failures}': str(failures),
                '{max_failures}': template_vars.get('max_failures', '3'),
                '{error_message}': template_vars.get('error_message', 'Erro Desconhecido'),
                '{agrocenter_url}': template_vars.get('agrocenter_url', ''),
                '{cvale_logo_base64}': cvale_base64,
                '{agrocenter_logo_base64}': agro_base64
            }
            for placeholder, value in replacements.items():
                html_content = html_content.replace(placeholder, str(value))

            # 3. Envia o e-mail
            server = smtplib.SMTP(self.smtp_config['server'], int(self.smtp_config.get('port', 587)))
            server.starttls()
            server.login(self.smtp_config['user'], self.smtp_config['password'])

            for dest in destinatarios:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.smtp_config.get('from', self.smtp_config['user'])
                msg['To'] = dest

                part = MIMEText(html_content, 'html')
                msg.attach(part)

                server.sendmail(msg['From'], dest, msg.as_string())
                print(f"E-mail de alerta enviado com sucesso para: {dest}")

            server.quit()
            return True
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return False

    def send_email_report(self, subject, template_vars, contacts_path, template_path, target_levels=None):
        """Envia relatórios consolidados em HTML para a lista de contatos do contacts.json"""
        if not self.smtp_config.get('server') or not self.smtp_config.get('user'):
            print("SMTP não configurado no .env.")
            return False

        try:
            # 1. Carrega os contatos
            if not os.path.exists(contacts_path):
                print(f"Arquivo de contatos não encontrado em: {contacts_path}")
                return False

            with open(contacts_path, 'r', encoding='utf-8') as f:
                contacts = json.load(f)

            if target_levels is not None:
                destinatarios = [
                    c['email'] for c in contacts 
                    if c.get('enabled', False) and c.get('level') in target_levels
                ]
            else:
                destinatarios = [c['email'] for c in contacts if c.get('enabled', False)]
            if not destinatarios:
                print("Nenhum contato habilitado para envio de e-mail.")
                return False

            # 2. Carrega e preenche o template de e-mail do relatório
            if not os.path.exists(template_path):
                print(f"Template de e-mail não encontrado em: {template_path}")
                return False

            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()

            # Preenche os placeholders no HTML de forma flexível usando .replace para evitar KeyError com CSS do template
            html_content = template_html
            for key, val in template_vars.items():
                html_content = html_content.replace(f"{{{key}}}", str(val))

            # 3. Envia o e-mail
            server = smtplib.SMTP(self.smtp_config['server'], int(self.smtp_config.get('port', 587)))
            server.starttls()
            server.login(self.smtp_config['user'], self.smtp_config['password'])

            for dest in destinatarios:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.smtp_config.get('from', self.smtp_config['user'])
                msg['To'] = dest

                part = MIMEText(html_content, 'html')
                msg.attach(part)

                server.sendmail(msg['From'], dest, msg.as_string())
                print(f"E-mail de relatório enviado com sucesso para: {dest}")

            server.quit()
            return True
        except Exception as e:
            print(f"Erro ao enviar e-mail de relatório: {e}")
            return False
