import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        # Garante que o diretório do banco existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Tabela de logs do monitoramento
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS monitor_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status_code INTEGER,
                    response_time_ms INTEGER,
                    is_healthy BOOLEAN,
                    error_message TEXT,
                    check_type TEXT
                )
            ''')
            # Tabela de incidentes ativos/resolvidos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    end_timestamp DATETIME,
                    consecutive_failures INTEGER,
                    telegram_sent BOOLEAN DEFAULT 0,
                    email_sent BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE'
                )
            ''')
            conn.commit()

    def add_monitor_log(self, status_code, response_time_ms, is_healthy, error_message, check_type='HTTP'):
        query = '''
            INSERT INTO monitor_logs (timestamp, status_code, response_time_ms, is_healthy, error_message, check_type)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(query, (now, status_code, response_time_ms, int(is_healthy), error_message, check_type))
            conn.commit()

    def get_latest_logs(self, limit=50):
        query = 'SELECT * FROM monitor_logs ORDER BY timestamp DESC LIMIT ?'
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_active_incident(self):
        query = "SELECT * FROM incidents WHERE status = 'ACTIVE' ORDER BY start_timestamp DESC LIMIT 1"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_incident(self):
        query = '''
            INSERT INTO incidents (start_timestamp, consecutive_failures, telegram_sent, email_sent, status)
            VALUES (?, 1, 0, 0, 'ACTIVE')
        '''
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (now,))
            conn.commit()
            return cursor.lastrowid

    def update_incident_failures(self, incident_id, consecutive_failures):
        query = 'UPDATE incidents SET consecutive_failures = ? WHERE id = ?'
        with self._get_connection() as conn:
            conn.execute(query, (consecutive_failures, incident_id))
            conn.commit()

    def mark_telegram_sent(self, incident_id):
        query = 'UPDATE incidents SET telegram_sent = 1 WHERE id = ?'
        with self._get_connection() as conn:
            conn.execute(query, (incident_id,))
            conn.commit()

    def mark_email_sent(self, incident_id):
        query = 'UPDATE incidents SET email_sent = 1 WHERE id = ?'
        with self._get_connection() as conn:
            conn.execute(query, (incident_id,))
            conn.commit()

    def resolve_incident(self, incident_id):
        query = "UPDATE incidents SET status = 'RESOLVED', end_timestamp = ? WHERE id = ?"
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(query, (now, incident_id))
            conn.commit()

    def get_kpis(self):
        """Retorna estatísticas para exibir no dashboard"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de verificações
            cursor.execute("SELECT COUNT(*) FROM monitor_logs")
            total_checks = cursor.fetchone()[0]

            # Verificações bem sucedidas vs falhas
            cursor.execute("SELECT COUNT(*) FROM monitor_logs WHERE is_healthy = 1")
            healthy_checks = cursor.fetchone()[0]
            
            # Tempo médio de resposta
            cursor.execute("SELECT AVG(response_time_ms) FROM monitor_logs WHERE is_healthy = 1")
            avg_response_time = cursor.fetchone()[0] or 0.0

            # Incidentes totais
            cursor.execute("SELECT COUNT(*) FROM incidents")
            total_incidents = cursor.fetchone()[0]

            # Incidente ativo
            active_incident = self.get_active_incident()

            # Histórico de incidentes resolvidos (últimos 10)
            cursor.execute("SELECT * FROM incidents WHERE status = 'RESOLVED' ORDER BY end_timestamp DESC LIMIT 10")
            resolved_incidents = [dict(row) for row in cursor.fetchall()]

            # Disponibilidade (%)
            availability = (healthy_checks / total_checks * 100) if total_checks > 0 else 100.0

            return {
                'total_checks': total_checks,
                'healthy_checks': healthy_checks,
                'failed_checks': total_checks - healthy_checks,
                'avg_response_time': round(avg_response_time, 2),
                'total_incidents': total_incidents,
                'active_incident': active_incident,
                'resolved_incidents': resolved_incidents,
                'availability': round(availability, 2)
            }
