import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME", "student_db"),
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )
