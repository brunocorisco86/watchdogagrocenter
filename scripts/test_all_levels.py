#!/usr/bin/env python3
import os
import sys
import asyncio
from datetime import datetime

# Adiciona o diretório raiz ao path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.watchdog.watchdog_cli import load_config
from src.watchdog.notifier import Notifier

async def run_tests():
    print("Iniciando simulação de teste para todos os 4 níveis de SLA...")
    
    config = load_config()
    notifier = Notifier(
        telegram_token=config['telegram_token'],
        telegram_chat_id=config['telegram_chat_id'],
        smtp_config=config['smtp_config'],
        db_path=config['db_path']
    )
    
    # Obtém limiares dinâmicos
    thresholds = notifier._get_thresholds()
    print(f"Limiares carregados (em quantidade de falhas):")
    print(f" - Nível 1: {thresholds[1]} falhas")
    print(f" - Nível 2: {thresholds[2]} falhas")
    print(f" - Nível 3: {thresholds[3]} falhas")
    print(f" - Nível 4: {thresholds[4]} falhas")
    
    level_names = {
        1: "Operacional TI",
        2: "Analista / Coordenação",
        3: "Gerência",
        4: "Diretoria"
    }
    
    # Vamos rodar o teste para cada um dos níveis
    for level in [1, 2, 3, 4]:
        failures_count = thresholds[level]
        name = level_names[level]
        
        # O tempo off correspondente
        check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '3'))
        minutes_off = failures_count * check_interval
        
        print(f"\n==================================================")
        print(f"Simulando Notificação: Nível {level} - {name} ({failures_count} falhas / {minutes_off} min)")
        print(f"==================================================")
        
        # 1. Enviar Alerta do Telegram
        telegram_msg = (
            f"🧪 <b>TESTE DE ESCALAÇÃO: NÍVEL {level} - {name}</b>\n"
            f"<i>Esta é uma mensagem de simulação enviada para homologar este canal.</i>\n\n"
            f"<b>Serviço:</b> C.Vale Agrocenter (Simulado)\n"
            f"<b>Tempo de queda simulado:</b> {minutes_off} minutos\n"
            f"<b>Erros consecutivos simulados:</b> {failures_count} tentativas\n"
            f"<b>Grupo de escalação:</b> {name}\n"
        )
        
        tg_success = await notifier._send_telegram(telegram_msg, config['contacts_path'], consecutive_failures=failures_count)
        if tg_success:
            print(f" -> [Telegram] Mensagem do Nível {level} enviada.")
        else:
            print(f" -> [Telegram] Falha ao enviar para o Nível {level}.")
            
        # 2. Enviar Alerta de E-mail
        subject = f"[TESTE NÍVEL {level}] Simulação de Falha - Watchdog C.Vale"
        template_vars = {
            'alert_class': 'critical',
            'alert_summary': f"Este é um teste de homologação do envio de e-mails para o Nível {level} - {name}.",
            'incident_status': f'TESTE - NÍVEL {level} ({name})',
            'badge_class': 'badge-danger',
            'status_code': '503',
            'response_time_ms': '0',
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'consecutive_failures': str(failures_count),
            'max_failures': '3',
            'error_message': f'Simulação de queda de serviço (Nível {level})',
            'agrocenter_url': config['url']
        }
        
        email_success = notifier.send_email_alert(
            subject=subject,
            template_vars=template_vars,
            contacts_path=config['contacts_path'],
            template_path=config['template_path']
        )
        if email_success:
            print(f" -> [E-mail] Relatório do Nível {level} enviado.")
        else:
            print(f" -> [E-mail] Falha ao enviar ou nenhum destinatário elegível para o Nível {level}.")
            
    print("\nTeste concluído para todos os níveis!")

if __name__ == '__main__':
    asyncio.run(run_tests())
