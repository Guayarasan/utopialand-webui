"""
Capa de acceso a datos.

Usa un pool de conexiones (DBUtils.PooledDB) sobre PyMySQL para poder
atender muchas peticiones concurrentes sin abrir/cerrar una conexión TCP
por cada consulta, algo crítico cuando la tabla LOGDATA tiene millones
de filas y el hosting corre en Render con arranques en frío.
"""

import logging
import threading

import pymysql
from dbutils.pooled_db import PooledDB

from config import Config

logger = logging.getLogger("utopialand.database")

_pool = None
_pool_lock = threading.Lock()


class DatabaseNotConfigured(Exception):
    """Faltan variables de entorno de conexión a la base de datos."""


def _build_pool():
    connect_kwargs = dict(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=Config.DB_CONNECT_TIMEOUT,
        charset="utf8mb4",
        autocommit=True,
    )

    if Config.DB_SSL_CA:
        connect_kwargs["ssl"] = {"ca": Config.DB_SSL_CA}
    else:
        # Aiven requiere TLS. Si no se entregó un CA explícito, se sigue
        # cifrando el canal sin verificar el certificado (equivalente a
        # sslmode=require). Lo ideal en producción es definir DB_SSL_CA.
        connect_kwargs["ssl"] = {"ssl": True}

    return PooledDB(
        creator=pymysql,
        maxconnections=Config.DB_POOL_SIZE,
        mincached=Config.DB_POOL_MIN_CACHED,
        maxcached=Config.DB_POOL_MAX_CACHED,
        blocking=True,
        ping=1,  # valida la conexión antes de entregarla (evita "MySQL server has gone away")
        **connect_kwargs,
    )


def get_pool():
    global _pool
    if not Config.is_db_configured():
        raise DatabaseNotConfigured(
            "Faltan variables de entorno DB_HOST/DB_NAME/DB_USER/DB_PASSWORD."
        )
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = _build_pool()
    return _pool


def get_connection():
    """Obtiene una conexión del pool (comportamiento tipo pymysql.connect)."""
    return get_pool().connection()


def get_raw_connection():
    """
    Conexión directa fuera del pool, usada para operaciones de streaming
    (exportación masiva) donde conviene un SSCursor dedicado que no debe
    volver al pool hasta agotarse por completo.
    """
    if not Config.is_db_configured():
        raise DatabaseNotConfigured(
            "Faltan variables de entorno DB_HOST/DB_NAME/DB_USER/DB_PASSWORD."
        )
    kwargs = dict(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        connect_timeout=Config.DB_CONNECT_TIMEOUT,
        charset="utf8mb4",
        autocommit=True,
    )
    if Config.DB_SSL_CA:
        kwargs["ssl"] = {"ca": Config.DB_SSL_CA}
    else:
        kwargs["ssl"] = {"ssl": True}
    return pymysql.connect(**kwargs)


def check_connection():
    """Prueba la conexión y devuelve (ok: bool, mensaje: str, latency_ms: float|None)."""
    import time

    if not Config.is_db_configured():
        return False, "Variables de entorno de base de datos incompletas.", None

    start = time.perf_counter()
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        finally:
            conn.close()
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return True, "Conexión establecida correctamente.", latency_ms
    except Exception as exc:  # noqa: BLE001
        logger.exception("Fallo al conectar con la base de datos")
        return False, str(exc), None


def get_total_records():
    return fetch_scalar(f"SELECT COUNT(*) AS total FROM {Config.DB_TABLE}")


def fetch_all(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()
    finally:
        conn.close()


def fetch_scalar(sql, params=None):
    row = fetch_one(sql, params)
    if not row:
        return None
    return next(iter(row.values()))


def stream_rows(sql, params=None, chunk_size=2000):
    """
    Generador que recorre filas usando un cursor de servidor (SSCursor),
    ideal para exportaciones grandes: no carga todo el resultado en
    memoria de golpe.
    """
    conn = get_raw_connection()
    try:
        with conn.cursor(pymysql.cursors.SSDictCursor) as cur:
            cur.execute(sql, params or ())
            while True:
                rows = cur.fetchmany(chunk_size)
                if not rows:
                    break
                for row in rows:
                    yield row
    finally:
        conn.close()
