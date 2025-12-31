from flask import Blueprint, request

from database import DatabaseManager


maintenance_bp = Blueprint('maintenance', __name__)


def log_maintenance_operation(user_id, operation, details, status='success', error_msg=None, file_size=None, duration=None):
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO maintenance_logs 
                (user_id, operation, details, status, error_message, ip_address, file_size, duration, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (user_id, operation, details, status, error_msg, request.remote_addr, file_size, duration),
            )
            conn.commit()
    except Exception:
        pass


def get_maintenance_mode():
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT config_value FROM system_config 
                WHERE config_key = 'maintenance_mode'
                """
            )
            result = cursor.fetchone()
            cursor.close()
            return result[0] == '1' if result else False
    except Exception:
        return False


def set_maintenance_mode(enabled, user_id):
    try:
        db_manager = DatabaseManager()
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE system_config 
                SET config_value = %s, updated_by = %s, updated_at = NOW()
                WHERE config_key = 'maintenance_mode'
                """,
                ('1' if enabled else '0', user_id),
            )
            conn.commit()
            cursor.close()
            return True
    except Exception:
        return False


def check_mysqldump_available():
    import subprocess

    try:
        subprocess.run(['mysqldump', '--version'], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        return False


# 将各个维护相关路由拆分到独立模块中
from . import (
    backup,
    optimize,
    stats,
    logs,
    backups,
    restore,
    health,
    mode,
    cleanup,
)

__all__ = [
    'maintenance_bp',
    'log_maintenance_operation',
    'get_maintenance_mode',
    'set_maintenance_mode',
    'check_mysqldump_available',
]
