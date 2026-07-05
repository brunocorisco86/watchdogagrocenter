import sqlite3
import os
from datetime import datetime, timedelta

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
            # Tabela de configurações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            # Valores padrão de limites dos níveis (em minutos)
            defaults = [
                ('level1_minutes', '15'),
                ('level2_minutes', '60'),
                ('level3_minutes', '150'),
                ('level4_minutes', '720')
            ]
            for key, val in defaults:
                cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, val))
            conn.commit()

    def get_setting(self, key, default=None):
        query = "SELECT value FROM settings WHERE key = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (key,))
            row = cursor.fetchone()
            return row['value'] if row else default

    def get_all_settings(self):
        query = "SELECT * FROM settings"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return {row['key']: row['value'] for row in cursor.fetchall()}

    def update_settings(self, settings_dict):
        query = "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)"
        with self._get_connection() as conn:
            for key, val in settings_dict.items():
                conn.execute(query, (key, str(val)))
            conn.commit()

    def add_monitor_log(self, status_code, response_time_ms, is_healthy, error_message, check_type='HTTP'):
        query = '''
            INSERT INTO monitor_logs (timestamp, status_code, response_time_ms, is_healthy, error_message, check_type)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        now = datetime.now().isoformat().replace('T', ' ')
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
        now = datetime.now().isoformat().replace('T', ' ')
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
        now = datetime.now().isoformat().replace('T', ' ')
        with self._get_connection() as conn:
            conn.execute(query, (now, incident_id))
            conn.commit()

    def get_latency_history_6h(self, period_filter='6h'):
        """Retorna os registros de latência de acordo com o período para a série temporal"""
        filter_map = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '1d': timedelta(days=1),
            '1w': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        delta = filter_map.get(period_filter, timedelta(hours=6))
        limit_time = (datetime.now() - delta).isoformat().replace('T', ' ')
        query = """
            SELECT timestamp, response_time_ms, is_healthy 
            FROM monitor_logs 
            WHERE timestamp >= ? 
            ORDER BY timestamp ASC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit_time,))
            return [dict(row) for row in cursor.fetchall()]


    def get_kpis(self, period_filter='30d'):
        """Retorna estatísticas filtradas por período para exibir no dashboard"""
        filter_map = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '1d': timedelta(days=1),
            '1w': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        delta = filter_map.get(period_filter, timedelta(days=30))
        limit_time = (datetime.now() - delta).isoformat().replace('T', ' ')

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de verificações no período
            cursor.execute("SELECT COUNT(*) FROM monitor_logs WHERE timestamp >= ?", (limit_time,))
            total_checks = cursor.fetchone()[0]

            # Verificações bem sucedidas vs falhas no período
            cursor.execute("SELECT COUNT(*) FROM monitor_logs WHERE is_healthy = 1 AND timestamp >= ?", (limit_time,))
            healthy_checks = cursor.fetchone()[0]
            
            # Tempo médio de resposta no período
            cursor.execute("SELECT AVG(response_time_ms) FROM monitor_logs WHERE is_healthy = 1 AND timestamp >= ?", (limit_time,))
            avg_response_time = cursor.fetchone()[0] or 0.0

            # Incidentes totais iniciados no período
            cursor.execute("SELECT COUNT(*) FROM incidents WHERE start_timestamp >= ?", (limit_time,))
            total_incidents = cursor.fetchone()[0]

            # Incidente ativo (sempre o último ativo, indepentende de filtro)
            active_incident = self.get_active_incident()

            # Histórico de incidentes resolvidos (últimos 10)
            cursor.execute("SELECT * FROM incidents WHERE status = 'RESOLVED' ORDER BY end_timestamp DESC LIMIT 10")
            resolved_incidents = [dict(row) for row in cursor.fetchall()]

            # Disponibilidade (%) no período
            availability = (healthy_checks / total_checks * 100) if total_checks > 0 else 100.0

            # Distribuição de erros (%) no período
            failed_checks = total_checks - healthy_checks
            cursor.execute("""
                SELECT error_message, COUNT(*) as count 
                FROM monitor_logs 
                WHERE is_healthy = 0 AND error_message IS NOT NULL AND error_message != ''
                  AND timestamp >= ?
                GROUP BY error_message
            """, (limit_time,))
            error_rows = cursor.fetchall()
            error_distribution = []
            for row in error_rows:
                err_msg = row['error_message']
                count = row['count']
                pct = round((count / failed_checks * 100), 1) if failed_checks > 0 else 0.0
                error_distribution.append({
                    'error_message': err_msg,
                    'count': count,
                    'percentage': pct
                })

            return {
                'total_checks': total_checks,
                'healthy_checks': healthy_checks,
                'failed_checks': failed_checks,
                'avg_response_time': round(avg_response_time, 2),
                'total_incidents': total_incidents,
                'active_incident': active_incident,
                'resolved_incidents': resolved_incidents,
                'availability': round(availability, 2),
                'error_distribution': error_distribution
            }
