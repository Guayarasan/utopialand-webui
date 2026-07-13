from database import get_connection

def get_latest_records(limit=100):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            name,
            obj_name,
            type,
            world,
            pos_x,
            pos_y,
            pos_z,
            FROM_UNIXTIME(time) AS fecha
        FROM LOGDATA
        ORDER BY time DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
