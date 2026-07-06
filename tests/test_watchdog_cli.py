import pytest
import requests
from unittest.mock import MagicMock, patch
# Renomeamos o import para evitar que o Pytest tente executar 'test_http_service' diretamente
from src.watchdog.watchdog_cli import test_http_service as run_http_check, test_isp_connectivity
from src.watchdog import watchdog_cli
watchdog_cli.HAS_CURL_CFFI = False

@patch("requests.get")
def test_http_service_healthy(mock_get):
    """Testa o caso em que o serviço Agrocenter está 100% saudável"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.text = ("A" * 200) + "<html><body>content=\"agro center\" eaware.io agrocenter</body></html>"
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is True
    assert status_code == 200
    assert error_msg == ""

@patch("requests.get")
def test_http_service_invalid_metadata(mock_get):
    """Testa falha de validação quando o Content-Type retornado não é HTML"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = '{"status": "ok"}'
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "Tipo de conteúdo inválido nos metadados HTTP" in error_msg

@patch("requests.get")
def test_http_service_akamai_block_status(mock_get):
    """Testa detecção de bloqueio do WAF Akamai via status code de erro e assinatura"""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = ("A" * 200) + "<html><body>Access Denied. Reference #18.2736.1827361872.182736 Akamai WAF</body></html>"
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "Bloqueio de Firewall (Akamai WAF)" in error_msg

@patch("requests.get")
def test_http_service_db_exposure(mock_get):
    """Testa detecção de falha interna/banco de dados exposta na resposta HTML"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = ("A" * 200) + "<html><body>Fatal Error: Database connection failed. driver error.</body></html>"
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "Erro de banco/sistema exposto na resposta" in error_msg

@patch("requests.get")
def test_http_service_signature_mismatch(mock_get):
    """Testa falha quando a resposta HTML não condiz com nenhuma assinatura do Agrocenter"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    # HTML genérico sem as palavras-chave necessárias (cuidado: não pode conter a palavra 'agrocenter')
    mock_response.text = ("A" * 200) + "<html><body>Este e um site generico que nao possui nenhuma assinatura do portal monitorado.</body></html>"
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "não condiz com o portal Agrocenter" in error_msg

@patch("requests.get")
def test_http_service_ssl_error(mock_get):
    """Testa detecção de erro de SSL"""
    mock_get.side_effect = requests.exceptions.SSLError("SSL: CERTIFICATE_VERIFY_FAILED")

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "Erro de SSL/Certificado" in error_msg

@patch("requests.get")
def test_http_service_too_short(mock_get):
    """Testa falha quando a resposta é excessivamente curta"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = "<html><body>Short</body></html>"
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "Resposta excessivamente curta" in error_msg

@patch("requests.get")
def test_http_service_incomplete_signature(mock_get):
    """Testa falha quando apenas parte da assinatura está presente"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    # Tem 'agrocenter' mas não tem nenhuma das secundárias
    mock_response.text = "A" * 200 + " agrocenter " + "B" * 100
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is False
    assert "assinatura incompleta ou incorreta" in error_msg

@patch("requests.get")
def test_http_service_healthy_long_enough(mock_get):
    """Testa sucesso com assinaturas completas e tamanho suficiente"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.text = "A" * 200 + " agrocenter " + 'content="agro center"'
    mock_get.return_value = mock_response

    is_healthy, status_code, elapsed_ms, error_msg = run_http_check("https://prd-agrocenter.cvale.com.br", timeout=5)

    assert is_healthy is True
    assert error_msg == ""

@patch("requests.head")
def test_isp_connectivity_online(mock_head):
    """Testa a checagem de ISP retornando online"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response

    assert test_isp_connectivity() is True

@patch("requests.head")
def test_isp_connectivity_offline(mock_head):
    """Testa a checagem de ISP falhando por completo"""
    mock_head.side_effect = Exception("Conexão falhou")

    assert test_isp_connectivity() is False
