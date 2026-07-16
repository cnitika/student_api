import pymysql

def get_connection():
    return pymysql.connect(
        host="host.docker.internal",
        user="root",
        password="2810Nitik@",
        database="student_db",
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )
