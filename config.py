import os
from decimal import Decimal
from dotenv import load_dotenv

# Load .env file from the repository directory
basedir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base application configuration."""
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "student_app")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "student_db")
    DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", 5))

    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    TESTING = False

    # Academic result calculation rules
    PASS_THRESHOLD_PERCENT = Decimal("35.00")
    GRADE_SCALE = [
        (Decimal("90.00"), "A+"),
        (Decimal("80.00"), "A"),
        (Decimal("70.00"), "B"),
        (Decimal("60.00"), "C"),
        (Decimal("50.00"), "D"),
    ]
    DEFAULT_FAIL_GRADE = "F"


class TestConfig(Config):
    """Configuration for testing."""
    TESTING = True
    DB_NAME = os.environ.get("TEST_DB_NAME", "student_test_db")
    FLASK_DEBUG = False
