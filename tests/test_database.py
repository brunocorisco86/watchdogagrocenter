import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from src.watchdog.database import DatabaseManager

@pytest.fixture
def temp_db(tmp_path):
    """Gera um banco de dados SQLite temporário para testes"""
    db_file = tmp_path / "test_database.db"
    return DatabaseManager(str(db_file))

def test_database_creation(temp_db):
    """Verifica se as tabelas fundamentais foram criadas com as colunas corretas"""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    
    # Verifica tabela monitor_logs
    cursor.execute("PRAGMA table_info(monitor_logs)")
    columns = [col[1] for col in cursor.fetchall()]
    assert "id" in columns
    assert "timestamp" in columns
    assert "status_code" in columns
    assert "response_time_ms" in columns
    assert "is_healthy" in columns
    assert "error_message" in columns
    
    # Verifica tabela incidents
    cursor.execute("PRAGMA table_info(incidents)")
    columns = [col[1] for col in cursor.fetchall()]
    assert "id" in columns
    assert "start_timestamp" in columns
    assert "end_timestamp" in columns
    assert "consecutive_failures" in columns
    assert "status" in columns
    
    conn.close()

def test_add_monitor_log(temp_db):
    """Verifica a inserção e recuperação de logs de monitoramento"""
    temp_db.add_monitor_log(200, 150, True, "")
    
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitor_logs")
    row = cursor.fetchone()
    assert row is not None
    assert row[2] == 200 # status_code
    assert row[3] == 150 # response_time_ms
    assert row[4] == 1   # is_healthy
    assert row[5] == ""  # error_message
    conn.close()

def test_prune_logs(temp_db):
    """Testa a exclusão automática de registros de monitoramento com mais de 24 horas"""
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    
    # Injeta log antigo (25 horas atrás)
    old_time = (datetime.now() - timedelta(hours=25)).isoformat().replace('T', ' ')
    cursor.execute(
        "INSERT INTO monitor_logs (timestamp, status_code, response_time_ms, is_healthy, error_message, check_type) VALUES (?, ?, ?, ?, ?, ?)",
        (old_time, 200, 100, 1, "", "HTTP")
    )
    
    # Injeta log recente (1 hora atrás)
    recent_time = (datetime.now() - timedelta(hours=1)).isoformat().replace('T', ' ')
    cursor.execute(
        "INSERT INTO monitor_logs (timestamp, status_code, response_time_ms, is_healthy, error_message, check_type) VALUES (?, ?, ?, ?, ?, ?)",
        (recent_time, 200, 100, 1, "", "HTTP")
    )
    conn.commit()
    conn.close()
    
    # Executa pruning via inserção de novo log
    temp_db.add_monitor_log(200, 120, True, "")
    
    # Verifica que o log antigo foi apagado e o recente persistiu
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp FROM monitor_logs")
    rows = [r[0] for r in cursor.fetchall()]
    assert old_time not in rows
    assert recent_time in rows
    conn.close()

def test_incident_lifecycle(temp_db):
    """Testa o ciclo de criação, incremento e resolução de um incidente"""
    # 1. Cria incidente ativo
    incident_id = temp_db.create_incident()
    assert incident_id is not None
    
    active = temp_db.get_active_incident()
    assert active is not None
    assert active['id'] == incident_id
    assert active['consecutive_failures'] == 1
    assert active['status'] == 'ACTIVE'
    
    # 2. Incrementa falhas
    temp_db.update_incident_failures(incident_id, 3)
    active = temp_db.get_active_incident()
    assert active['consecutive_failures'] == 3
    
    # 3. Resolve incidente
    temp_db.resolve_incident(incident_id)
    active = temp_db.get_active_incident()
    assert active is None # Nenhum incidente ativo
    
    # Verifica registro na tabela de resolvidos
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT status, end_timestamp FROM incidents WHERE id = ?", (incident_id,))
    row = cursor.fetchone()
    assert row[0] == 'RESOLVED'
    assert row[1] is not None
    conn.close()

def test_get_kpis_calculation(temp_db):
    """Testa os cálculos de disponibilidade e latência do método get_kpis"""
    # Injeta logs artificiais (4 saudáveis e 1 com falha)
    now = datetime.now()
    logs = [
        (now.isoformat(), 200, 100, 1, "", "HTTP"),
        ((now - timedelta(minutes=5)).isoformat(), 200, 120, 1, "", "HTTP"),
        ((now - timedelta(minutes=10)).isoformat(), 500, 80, 0, "Internal Server Error", "HTTP"),
        ((now - timedelta(minutes=15)).isoformat(), 200, 150, 1, "", "HTTP"),
        ((now - timedelta(minutes=20)).isoformat(), 200, 100, 1, "", "HTTP")
    ]
    
    conn = sqlite3.connect(temp_db.db_path)
    cursor = conn.cursor()
    for log in logs:
        cursor.execute(
            "INSERT INTO monitor_logs (timestamp, status_code, response_time_ms, is_healthy, error_message, check_type) VALUES (?, ?, ?, ?, ?, ?)",
            log
        )
    conn.commit()
    conn.close()
    
    kpis = temp_db.get_kpis(period_filter='1h')
    
    # Asserts
    # Disponibilidade deve ser 4/5 = 80.0%
    assert kpis['availability'] == 80.0
    # Tempo médio das saudáveis deve ser (100+120+150+100)/4 = 117.5 = 118 ms
    assert kpis['avg_response_time'] == 117.5
    # Total de checagens deve ser 5
    assert kpis['total_checks'] == 5
    # Ocorrências de erros devem estar listadas
    assert len(kpis['error_distribution']) == 1
    assert kpis['error_distribution'][0]['error_message'] == "Internal Server Error"
    assert kpis['error_distribution'][0]['count'] == 1
    assert kpis['error_distribution'][0]['percentage'] == 100.0
