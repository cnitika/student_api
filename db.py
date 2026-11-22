import pymysql
import os
from contextlib import contextmanager
from config import Config


def _get_val(cfg, key, default=None):
    """Safely extract setting from class, dict, or Flask config object."""
    if hasattr(cfg, "get"):
        val = cfg.get(key)
        if val is not None:
            return val
    return getattr(cfg, key, default)


def get_connection(config_class=None, database=None):
    """
    Establish a connection to the MySQL database.
    Config-driven with support for custom configuration and database overriding.
    """
    cfg = config_class or Config
    db_name = database or _get_val(cfg, "DB_NAME", "student_db")
    host = _get_val(cfg, "DB_HOST", "127.0.0.1")
    port = int(_get_val(cfg, "DB_PORT", 3306))
    user = _get_val(cfg, "DB_USER", "student_app")
    password = _get_val(cfg, "DB_PASSWORD", "")
    timeout = int(_get_val(cfg, "DB_CONNECT_TIMEOUT", 5))

    return pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name,
        connect_timeout=timeout,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


@contextmanager
def get_db_cursor(commit=False, config_class=None, database=None):
    """
    Context manager that yields a database cursor.
    Guarantees connection and cursor are always closed,
    with automatic rollback on error and commit on success if commit=True.
    """
    connection = get_connection(config_class=config_class, database=database)
    cursor = connection.cursor()
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
