import pymysql
from config import Config

def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )

def get_total_records():
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM LOGDATA")
            return cur.fetchone()["total"]
    finally:
        conn.close()
