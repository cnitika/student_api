import pymysql
import os
from contextlib import contextmanager
from config import Config


def get_connection(config_class=None, database=None):
    """
    Establish a connection to the MySQL database.
    Config-driven with support for custom configuration and database overriding.
    """
    cfg = config_class or Config
    db_name = database or cfg.DB_NAME

    return pymysql.connect(
        host=cfg.DB_HOST,
        port=cfg.DB_PORT,
        user=cfg.DB_USER,
        password=cfg.DB_PASSWORD,
        database=db_name,
        connect_timeout=cfg.DB_CONNECT_TIMEOUT,
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
