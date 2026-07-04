#!/usr/bin/env python3
import os
import sys
import asyncio
from datetime import datetime

# Adiciona o diretório raiz ao path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.watchdog.watchdog_cli import load_config
from src.watchdog.notifier import Notifier

# Cores de terminal
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
END = "\033[0m"

def print_header(title):
    print(f"\n{BLUE}=================================================={END}")
    print(f"{BLUE} {title}{END}")
    print(f"{BLUE}=================================================={END}")

async def test_telegram(notifier, config):
    print(f"\n{YELLOW}[1/2] Iniciando Teste de Alerta via Telegram...{END}")
    test_msg = (
        f"🤖 <b>Watchdog C.Vale - Teste Manual de Mensageria</b>\n\n"
        f"<b>Ambiente:</b> Homologação/Operador\n"
        f"<b>Status:</b> Canal Operacional\n"
        f"<b>Horário:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
        f"<i>Se você recebeu esta mensagem, as variáveis TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID estão devidamente integradas!</i>"
    )
    
    # Envia passando o caminho dos contatos para testar o envio múltiplo
    success = await notifier._send_telegram(test_msg, config['contacts_path'])
    if success:
        print(f"{GREEN}✓ Sucesso: Mensagem de teste despachada para o Telegram!{END}")
    else:
        print(f"{RED}✗ Falha: Não foi possível enviar a mensagem para o Telegram.{END}")
        print(f"{RED}Verifique se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID estão corretos no .env.{END}")

def test_email(notifier, config):
    print(f"\n{YELLOW}[2/2] Iniciando Teste de Alerta via E-mail (Gmail SMTP)...{END}")
    subject = f"[TESTE DE ALERTAS] Watchdog C.Vale - Integração SMTP"
    
    template_vars = {
        'alert_class': 'healthy',
        'alert_summary': "Esta é uma mensagem de verificação manual dos servidores de e-mail.",
        'incident_status': 'HOMOLOGAÇÃO',
        'badge_class': 'badge-resolved',
        'status_code': '200',
        'response_time_ms': '100',
        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        'consecutive_failures': '0',
        'max_failures': str(config['max_failures']),
        'error_message': 'Teste de Conexão Ativo',
        'agrocenter_url': config['url']
    }
    
    success = notifier.send_email_alert(
        subject=subject,
        template_vars=template_vars,
        contacts_path=config['contacts_path'],
        template_path=config['template_path']
    )
    
    if success:
        print(f"{GREEN}✓ Sucesso: E-mail de teste enviado para todos os destinatários ativos em contacts.json!{END}")
    else:
        print(f"{RED}✗ Falha: Erro ao autenticar ou despachar e-mail via SMTP.{END}")
        print(f"{RED}Verifique as configurações de SMTP no seu .env e garanta que a senha de aplicativo esteja correta.{END}")

async def main():
    print_header("SCRIPT DE DIAGNÓSTICO E VALIDAÇÃO DE ALERTAS C.VALE")
    
    try:
        config = load_config()
    except Exception as e:
        print(f"{RED}Erro ao carregar o arquivo .env: {e}{END}")
        sys.exit(1)
        
    notifier = Notifier(
        telegram_token=config['telegram_token'],
        telegram_chat_id=config['telegram_chat_id'],
        smtp_config=config['smtp_config']
    )
    
    print(f"{BLUE}Destinatários do .env e contacts.json:{END}")
    print(f" - Telegram Token: {config['telegram_token'][:15]}... (ocultado)")
    print(f" - Telegram Admin Chat ID: {config['telegram_chat_id']}")
    print(f" - SMTP User: {config['smtp_config'].get('user')}")
    print(f" - SMTP Server: {config['smtp_config'].get('server')}:{config['smtp_config'].get('port')}")
    
    print("\nEscolha os testes que deseja executar:")
    print("1) Testar apenas Telegram")
    print("2) Testar apenas E-mail")
    print("3) Testar AMBOS (Recomendado)")
    print("4) Sair")
    
    choice = input("\nDigite a opção desejada (1-4): ").strip()
    
    if choice == '1':
        await test_telegram(notifier, config)
    elif choice == '2':
        test_email(notifier, config)
    elif choice == '3':
        await test_telegram(notifier, config)
        test_email(notifier, config)
    else:
        print("Saindo do diagnóstico.")
        
    print_header("DIAGNÓSTICO CONCLUÍDO")

if __name__ == '__main__':
    asyncio.run(main())
