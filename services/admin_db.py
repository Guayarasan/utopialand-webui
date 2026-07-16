"""
Tablas propias de la WebUI (usuarios, consultas guardadas, historial,
filtros favoritos).

Importante: estas tablas son metadata de la aplicación, completamente
independientes de LOGDATA (la tabla de Tianyan). Crearlas con
`CREATE TABLE IF NOT EXISTS` es una operación aditiva y segura -- no
toca ni modifica la tabla de logging del servidor bajo ninguna
circunstancia.
"""

import logging
import secrets
import threading

from config import Config
from database import fetch_all, fetch_one, fetch_scalar, get_connection
from utils.security import hash_password

logger = logging.getLogger("utopialand.admin_db")

_bootstrapped = False
_bootstrap_lock = threading.Lock()

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS webui_users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'viewer',
        active TINYINT(1) NOT NULL DEFAULT 1,
        created_at INT NOT NULL,
        last_login INT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_saved_queries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        name VARCHAR(120) NOT NULL,
        sql_text TEXT NOT NULL,
        is_example TINYINT(1) NOT NULL DEFAULT 0,
        created_at INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_query_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        sql_text TEXT NOT NULL,
        executed_at INT NOT NULL,
        duration_ms INT NULL,
        row_count INT NULL,
        success TINYINT(1) NOT NULL DEFAULT 1,
        error_message TEXT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_saved_filters (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        page VARCHAR(40) NOT NULL DEFAULT 'registros',
        name VARCHAR(120) NOT NULL,
        filters_json TEXT NOT NULL,
        created_at INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_favorite_locations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(120) NOT NULL,
        world VARCHAR(80) NULL,
        pos_x DOUBLE NOT NULL,
        pos_y DOUBLE NOT NULL,
        pos_z DOUBLE NOT NULL,
        icon VARCHAR(8) NULL,
        created_at INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_alert_rules (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        name VARCHAR(120) NOT NULL,
        event_types VARCHAR(255) NOT NULL,
        block_pattern VARCHAR(120) NULL,
        enabled TINYINT(1) NOT NULL DEFAULT 1,
        discord_webhook_url VARCHAR(500) NULL,
        last_triggered_at INT NULL,
        created_at INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_appearance_settings (
        user_id INT PRIMARY KEY,
        settings_json TEXT NOT NULL,
        updated_at INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
    CREATE TABLE IF NOT EXISTS webui_app_settings (
        setting_key VARCHAR(60) PRIMARY KEY,
        value VARCHAR(255) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]

# Columnas añadidas a tablas ya existentes en instalaciones previas.
# CREATE TABLE IF NOT EXISTS no modifica una tabla que ya existe, así
# que las columnas nuevas necesitan una migración explícita e
# idempotente (se revisa INFORMATION_SCHEMA antes de cada ALTER).
COLUMN_MIGRATIONS = [
    ("webui_saved_queries", "category", "VARCHAR(60) NULL DEFAULT NULL AFTER name"),
    ("webui_users", "timezone", "VARCHAR(60) NULL DEFAULT NULL AFTER role"),
]

EXAMPLE_QUERIES = [
    (
        "Actividad reciente (últimas 24h)",
        "Actividad general",
        "SELECT name, type, obj_name, world, FROM_UNIXTIME(time) AS fecha\n"
        f"FROM {Config.DB_TABLE}\nWHERE time >= UNIX_TIMESTAMP(NOW()) - 86400\n"
        "ORDER BY time DESC\nLIMIT 200",
    ),
    (
        "Posible grief (bloques rotos, excluyendo staff)",
        "Investigación",
        f"SELECT name, obj_name, world, pos_x, pos_y, pos_z, FROM_UNIXTIME(time) AS fecha\n"
        f"FROM {Config.DB_TABLE}\nWHERE type = 'block_break'\n"
        "  AND name NOT IN ('Admin1', 'Mod1')\n"
        "ORDER BY time DESC\nLIMIT 200",
    ),
    (
        "Posible robo (recogida de items de cofres/entidades)",
        "Investigación",
        f"SELECT name, obj_name, world, pos_x, pos_y, pos_z, FROM_UNIXTIME(time) AS fecha\n"
        f"FROM {Config.DB_TABLE}\nWHERE type = 'player_pickup_item'\n"
        "ORDER BY time DESC\nLIMIT 200",
    ),
    (
        "Actividad por coordenadas (radio de 50 bloques)",
        "Investigación",
        f"SELECT name, type, obj_name, pos_x, pos_y, pos_z, FROM_UNIXTIME(time) AS fecha\n"
        f"FROM {Config.DB_TABLE}\n"
        "WHERE pos_x BETWEEN 0 AND 100 AND pos_y BETWEEN 0 AND 100 AND pos_z BETWEEN 0 AND 100\n"
        "ORDER BY time DESC\nLIMIT 200",
    ),
    (
        "Actividad entre dos fechas",
        "Actividad general",
        f"SELECT name, type, obj_name, world, FROM_UNIXTIME(time) AS fecha\n"
        f"FROM {Config.DB_TABLE}\n"
        "WHERE time BETWEEN UNIX_TIMESTAMP('2026-01-01 00:00:00')\n"
        "                AND UNIX_TIMESTAMP('2026-01-31 23:59:59')\n"
        "ORDER BY time DESC\nLIMIT 200",
    ),
    (
        "Jugadores con más bloques rotos (top 20)",
        "Rankings",
        f"SELECT name, COUNT(*) AS total_breaks\nFROM {Config.DB_TABLE}\n"
        "WHERE type = 'block_break'\nGROUP BY name\nORDER BY total_breaks DESC\nLIMIT 20",
    ),
]


def ensure_bootstrapped():
    """Crea las tablas propias y el usuario admin inicial (una sola vez)."""
    global _bootstrapped
    if _bootstrapped:
        return
    with _bootstrap_lock:
        if _bootstrapped:
            return
        if not Config.is_db_configured():
            return
        try:
            _create_schema()
            _ensure_default_admin()
            _ensure_example_queries()
            _bootstrapped = True
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo inicializar las tablas propias de la WebUI")


def _create_schema():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for statement in SCHEMA_STATEMENTS:
                cur.execute(statement)
            for table, column, ddl in COLUMN_MIGRATIONS:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
                    (table, column),
                )
                exists = (cur.fetchone() or {}).get("total", 0)
                if not exists:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    logger.info("Migración aplicada: %s.%s", table, column)
    finally:
        conn.close()


def _ensure_default_admin():
    count = fetch_scalar("SELECT COUNT(*) AS total FROM webui_users")
    if count:
        return

    username = Config.ADMIN_USERNAME
    password = Config.ADMIN_PASSWORD or secrets.token_urlsafe(9)

    from utils.formatting import now_unix
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_users (username, password_hash, role, active, created_at) "
                "VALUES (%s, %s, 'admin', 1, %s)",
                (username, hash_password(password), now_unix()),
            )
    finally:
        conn.close()

    if not Config.ADMIN_PASSWORD:
        logger.warning(
            "=" * 70 + "\n"
            "Se creó el usuario administrador inicial automáticamente:\n"
            "  Usuario:  %s\n"
            "  Password: %s\n"
            "Guarda esta contraseña y cámbiala desde Configuración -> "
            "Cambiar contraseña. Para fijar una contraseña propia desde el "
            "arranque, define la variable de entorno ADMIN_PASSWORD.\n" + "=" * 70,
            username, password,
        )


def _ensure_example_queries():
    count = fetch_scalar("SELECT COUNT(*) AS total FROM webui_saved_queries WHERE is_example = 1")
    if count:
        return
    from utils.formatting import now_unix
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for name, category, sql_text in EXAMPLE_QUERIES:
                cur.execute(
                    "INSERT INTO webui_saved_queries (user_id, name, category, sql_text, is_example, created_at) "
                    "VALUES (NULL, %s, %s, %s, 1, %s)",
                    (name, category, sql_text, now_unix()),
                )
    finally:
        conn.close()
