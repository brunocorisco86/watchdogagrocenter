import os
import pytest
from flask import Flask
import base64

# Add the src directory to the sys path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.dashboard.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_no_auth_env_vars(client, monkeypatch):
    # Ensure environment variables are not set
    monkeypatch.delenv('DASHBOARD_USERNAME', raising=False)
    monkeypatch.delenv('DASHBOARD_PASSWORD', raising=False)

    response = client.get('/')
    assert response.status_code == 200

def test_auth_env_vars_no_credentials(client, monkeypatch):
    # Set environment variables
    monkeypatch.setenv('DASHBOARD_USERNAME', 'admin')
    monkeypatch.setenv('DASHBOARD_PASSWORD', 'secret')

    response = client.get('/')
    assert response.status_code == 401
    assert 'WWW-Authenticate' in response.headers

def test_auth_env_vars_wrong_credentials(client, monkeypatch):
    # Set environment variables
    monkeypatch.setenv('DASHBOARD_USERNAME', 'admin')
    monkeypatch.setenv('DASHBOARD_PASSWORD', 'secret')

    auth_str = "admin:wrongpassword"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {'Authorization': f'Basic {b64_auth}'}

    response = client.get('/', headers=headers)
    assert response.status_code == 401
    assert 'WWW-Authenticate' in response.headers

def test_auth_env_vars_correct_credentials(client, monkeypatch):
    # Set environment variables
    monkeypatch.setenv('DASHBOARD_USERNAME', 'admin')
    monkeypatch.setenv('DASHBOARD_PASSWORD', 'secret')

    auth_str = "admin:secret"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {'Authorization': f'Basic {b64_auth}'}

    response = client.get('/', headers=headers)
    assert response.status_code == 200
