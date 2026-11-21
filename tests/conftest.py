import pytest
import pymysql
from config import TestConfig
from db import get_connection
from init_db import init_database
from app import create_app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-level fixture:
    Verifies that student_test_db is reachable (fails loudly if not),
    and initializes its schema using database/schema.sql.
    """
    try:
        conn = get_connection(config_class=TestConfig)
        conn.close()
    except Exception as e:
        raise RuntimeError(
            f"FATAL: student_test_db is not reachable on {TestConfig.DB_HOST}:{TestConfig.DB_PORT}. "
            f"Integration tests require a live MySQL database. Error: {e}"
        ) from e

    # Apply schema to student_test_db
    init_database(target_db=TestConfig.DB_NAME)


@pytest.fixture
def app():
    """Application configured for testing against student_test_db."""
    application = create_app(config_class=TestConfig)
    return application


@pytest.fixture
def client(app):
    """Flask test client."""
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_test_db():
    """
    Clean all tables in student_test_db before each integration test,
    ensuring complete isolation between tests.
    """
    conn = get_connection(config_class=TestConfig)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE marks;")
            cursor.execute("TRUNCATE TABLE subjects;")
            cursor.execute("TRUNCATE TABLE students;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
    finally:
        conn.close()
