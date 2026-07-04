import os
import smtplib
import pytest
from dotenv import load_dotenv

# Carrega o .env local
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
load_dotenv(os.path.join(base_dir, '.env'))

@pytest.mark.skipif(
    not os.getenv("SMTP_USER") or not os.getenv("SMTP_PASSWORD"),
    reason="Credenciais SMTP do .env não encontradas para teste de integração."
)
def test_google_smtp_authentication():
    """
    Teste de Integração Real: Conecta e autentica diretamente no SMTP do Google (smtp.gmail.com)
    utilizando as credenciais fornecidas no arquivo .env para comprovar a validade da
    Senha de Aplicativo (App Password).
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    print(f"\n[Integração] Conectando a {smtp_server}:{smtp_port}...")
    try:
        # 1. Cria conexão SMTP
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10.0)
        
        # 2. Envia comando EHLO
        server.ehlo()
        
        # 3. Inicia TLS (Segurança)
        server.starttls()
        server.ehlo()
        
        # 4. Tenta Login real no Google com a App Password
        print(f"[Integração] Autenticando usuário: {smtp_user}...")
        server.login(smtp_user, smtp_password)
        
        print("[Integração] Autenticação no Gmail SMTP efetuada com SUCESSO!")
        
        # 5. Encerra conexão
        server.quit()
        assert True
        
    except smtplib.SMTPAuthenticationError as auth_err:
        pytest.fail(f"Falha de Autenticação no Google SMTP. Verifique a senha de aplicativo: {auth_err}")
    except Exception as e:
        pytest.fail(f"Erro ao conectar ao SMTP do Google: {str(e)}")
