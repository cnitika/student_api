import os
import sys
import pymysql
from dotenv import load_dotenv

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


def get_db_credentials(target_db=None):
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = int(os.environ.get("DB_PORT", 3306))
    user = os.environ.get("DB_USER", "student_app")
    password = os.environ.get("DB_PASSWORD", "")
    database = target_db or os.environ.get("DB_NAME", "student_db")
    return host, port, user, password, database


def init_database(target_db=None):
    host, port, user, password, database = get_db_credentials(target_db)
    print(f"Initializing database '{database}' on {host}:{port}...")

    schema_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database",
        "schema.sql"
    )

    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # Split SQL statements safely
    raw_statements = schema_sql.split(";")
    statements = []
    for stmt in raw_statements:
        # Strip comments and whitespace
        lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if clean_stmt:
            statements.append(clean_stmt)

    connection = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
        print(f"Schema successfully applied to '{database}'.")

        # Verify tables
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print(f"Tables in '{database}': {[list(t.values())[0] for t in tables]}")
    finally:
        connection.close()


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    init_database(target)
