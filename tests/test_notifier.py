import os
import json
import pytest
from unittest.mock import MagicMock, patch
from src.watchdog.notifier import Notifier

@pytest.fixture
def temp_contacts(tmp_path):
    """Gera um arquivo de contatos JSON temporário para testes"""
    contacts_data = [
        {"name": "Test User", "email": "test@cvale.com.br", "enabled": True},
        {"name": "Disabled User", "email": "disabled@cvale.com.br", "enabled": False}
    ]
    contacts_file = tmp_path / "contacts_test.json"
    with open(contacts_file, "w", encoding="utf-8") as f:
        json.dump(contacts_data, f)
    return str(contacts_file)

@pytest.fixture
def temp_template(tmp_path):
    """Gera um arquivo de template de e-mail HTML temporário para testes"""
    html_content = "<html><body>{alert_summary} - {error_message}</body></html>"
    template_file = tmp_path / "email_template_test.html"
    with open(template_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    return str(template_file)

@patch("smtplib.SMTP")
def test_send_email_alert_success(mock_smtp_class, temp_contacts, temp_template):
    """Testa o envio de e-mail mockando a classe SMTP para garantir o fluxo lógico correto"""
    # Configura o mock do SMTP
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value = mock_smtp_instance

    smtp_config = {
        "server": "smtp.gmail.com",
        "port": "587",
        "user": "brunocorisco@gmail.com",
        "password": "mock_password",
        "from": "watchdog-agrocenter@cvale.com.br"
    }

    notifier = Notifier(smtp_config=smtp_config)
    
    template_vars = {
        "alert_class": "critical",
        "alert_summary": "Serviço Fora do Ar",
        "incident_status": "CRÍTICO",
        "badge_class": "badge-danger",
        "status_code": "502",
        "response_time_ms": "120",
        "timestamp": "04/07/2026 17:00:00",
        "consecutive_failures": "5",
        "max_failures": "3",
        "error_message": "Bad Gateway",
        "agrocenter_url": "https://prd-agrocenter.cvale.com.br"
    }

    # Executa o envio de e-mail
    success = notifier.send_email_alert(
        subject="[TEST] Alerta de Falha",
        template_vars=template_vars,
        contacts_path=temp_contacts,
        template_path=temp_template
    )

    # Asserts
    assert success is True
    
    # Verifica se os métodos SMTP fundamentais foram chamados
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("brunocorisco@gmail.com", "mock_password")
    
    # Deve enviar e-mail apenas para o destinatário ativo (test@cvale.com.br)
    assert mock_smtp_instance.sendmail.call_count == 1
    mock_smtp_instance.quit.assert_called_once()

def test_send_email_alert_no_config(temp_contacts, temp_template):
    """Testa a falha graciosa caso o SMTP não esteja devidamente configurado"""
    notifier = Notifier(smtp_config={}) # SMTP vazio
    
    success = notifier.send_email_alert(
        subject="[TEST] Sem Config",
        template_vars={},
        contacts_path=temp_contacts,
        template_path=temp_template
    )
    
    assert success is False

@pytest.fixture
def temp_contacts_with_levels(tmp_path):
    """Gera um arquivo de contatos JSON temporário com níveis para testar filtragem"""
    contacts_data = [
        {"name": "L1 User", "email": "l1@cvale.com.br", "enabled": True, "level": 1},
        {"name": "L2 User", "email": "l2@cvale.com.br", "enabled": True, "level": 2},
        {"name": "L3 User", "email": "l3@cvale.com.br", "enabled": True, "level": 3},
        {"name": "L4 User", "email": "l4@cvale.com.br", "enabled": True, "level": 4},
        {"name": "Disabled L1 User", "email": "disabled_l1@cvale.com.br", "enabled": False, "level": 1}
    ]
    contacts_file = tmp_path / "contacts_levels_test.json"
    with open(contacts_file, "w", encoding="utf-8") as f:
        json.dump(contacts_data, f)
    return str(contacts_file)

@patch("smtplib.SMTP")
def test_send_email_report_filtering(mock_smtp_class, temp_contacts_with_levels, temp_template):
    """Testa se o relatório por e-mail filtra corretamente os destinatários com base nos níveis"""
    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value = mock_smtp_instance

    smtp_config = {
        "server": "smtp.gmail.com",
        "port": "587",
        "user": "brunocorisco@gmail.com",
        "password": "mock_password"
    }

    notifier = Notifier(smtp_config=smtp_config)
    
    # 1. Testar enviando para os níveis 1 e 2
    success = notifier.send_email_report(
        subject="[TEST] Relatório Níveis 1 e 2",
        template_vars={"alert_summary": "Summary", "error_message": "Msg"},
        contacts_path=temp_contacts_with_levels,
        template_path=temp_template,
        target_levels=[1, 2]
    )
    
    assert success is True
    # Deve enviar 2 e-mails (l1@cvale.com.br e l2@cvale.com.br)
    assert mock_smtp_instance.sendmail.call_count == 2
    
    # Reset mock para o próximo teste
    mock_smtp_instance.reset_mock()
    
    # 2. Testar enviando sem filtro (todos habilitados: l1, l2, l3, l4)
    success = notifier.send_email_report(
        subject="[TEST] Relatório Sem Filtro",
        template_vars={"alert_summary": "Summary", "error_message": "Msg"},
        contacts_path=temp_contacts_with_levels,
        template_path=temp_template
    )
    
    assert success is True
    # Deve enviar 4 e-mails (l1, l2, l3 e l4)
    assert mock_smtp_instance.sendmail.call_count == 4
