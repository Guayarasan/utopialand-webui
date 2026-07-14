"""
Consola SQL de solo lectura.

Permite a administradores y moderadores ejecutar SELECT/SHOW/EXPLAIN
libremente contra la base de datos para investigaciones puntuales (el
caso de uso típico: "dame todos los block_break de fulano cerca de
tal coordenada en las últimas 3 horas, excluyendo al staff").

No se permiten sentencias de escritura ni DDL: esto NO es un cliente
SQL genérico tipo HeidiSQL, es una consola de *consulta* para no
arriesgar la tabla LOGDATA (ni ninguna otra) ante un error humano o un
query mal copiado. Si en el futuro se necesita escritura, debe ser una
decisión explícita y consciente del administrador del proyecto, no algo
que esta consola habilite por accionar un botón.
"""

import re
import time

import pymysql

from config import Config
from database import fetch_all, get_connection
from utils.formatting import now_unix

ALLOWED_START = ("SELECT", "WITH", "SHOW", "EXPLAIN", "DESC", "DESCRIBE")

FORBIDDEN_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "REPLACE", "CALL", "LOAD", "SET", "LOCK", "RENAME",
    "EXECUTE", "PREPARE", "DEALLOCATE", "OUTFILE", "DUMPFILE", "INFILE",
)


class SQLConsoleError(Exception):
    pass


def validate_readonly(sql_text):
    text = (sql_text or "").strip()
    if not text:
        raise SQLConsoleError("La consulta está vacía.")

    body = text.rstrip(";").strip()
    if ";" in body:
        raise SQLConsoleError("Solo se permite una sentencia por ejecución (sin ';' intermedios).")

    upper = body.upper()
    if not upper.startswith(ALLOWED_START):
        raise SQLConsoleError(
            "Solo se permiten consultas de lectura: SELECT, WITH, SHOW, EXPLAIN o DESCRIBE."
        )

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"(?<![A-Za-z0-9_]){keyword}(?![A-Za-z0-9_])", upper):
            raise SQLConsoleError(
                f"La palabra clave '{keyword}' no está permitida en esta consola de solo lectura."
            )

    return body


def run_query(sql_text, user_id):
    """Ejecuta una consulta validada y registra el resultado en el historial."""
    body = validate_readonly(sql_text)

    start = time.perf_counter()
    columns = []
    rows = []
    truncated = False
    error_message = None
    success = True

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"SET SESSION MAX_EXECUTION_TIME = {Config.SQL_CONSOLE_TIMEOUT_SECONDS * 1000}")
            except Exception:  # noqa: BLE001 - variable no soportada (p.ej. MariaDB), se ignora
                pass

            cur.execute(body)
            fetched = cur.fetchmany(Config.SQL_CONSOLE_MAX_ROWS + 1)
            if cur.description:
                columns = [col[0] for col in cur.description]
            if len(fetched) > Config.SQL_CONSOLE_MAX_ROWS:
                truncated = True
                fetched = fetched[: Config.SQL_CONSOLE_MAX_ROWS]
            rows = fetched
    except pymysql.MySQLError as exc:
        success = False
        error_message = str(exc)
    finally:
        conn.close()

    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    _log_history(user_id, body, duration_ms, len(rows), success, error_message)

    if not success:
        raise SQLConsoleError(error_message)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "duration_ms": duration_ms,
    }


def _log_history(user_id, sql_text, duration_ms, row_count, success, error_message):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_query_history "
                "(user_id, sql_text, executed_at, duration_ms, row_count, success, error_message) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (user_id, sql_text, now_unix(), duration_ms, row_count, 1 if success else 0, error_message),
            )
    finally:
        conn.close()


def get_history(user_id, limit=30):
    return fetch_all(
        "SELECT id, sql_text, executed_at, duration_ms, row_count, success, error_message "
        "FROM webui_query_history WHERE user_id = %s ORDER BY executed_at DESC LIMIT %s",
        [user_id, limit],
    )


def get_favorites(user_id):
    """Ejemplos predefinidos (user_id NULL) + favoritas propias del usuario."""
    return fetch_all(
        "SELECT id, user_id, name, sql_text, is_example, created_at "
        "FROM webui_saved_queries WHERE user_id IS NULL OR user_id = %s "
        "ORDER BY is_example DESC, created_at DESC",
        [user_id],
    )


def save_favorite(user_id, name, sql_text):
    name = (name or "").strip()
    if not name:
        raise SQLConsoleError("El nombre de la consulta guardada no puede estar vacío.")
    validate_readonly(sql_text)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_saved_queries (user_id, name, sql_text, is_example, created_at) "
                "VALUES (%s, %s, %s, 0, %s)",
                (user_id, name, sql_text.strip(), now_unix()),
            )
            return cur.lastrowid
    finally:
        conn.close()


def delete_favorite(favorite_id, user_id):
    """Solo permite borrar consultas propias (nunca las de ejemplo)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM webui_saved_queries WHERE id = %s AND user_id = %s AND is_example = 0",
                (favorite_id, user_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()
