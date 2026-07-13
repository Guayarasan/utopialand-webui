"""Consultas sobre registros individuales (tabla LOGDATA completa)."""

from config import Config
from database import fetch_all, fetch_scalar
from services.query_builder import (
    TABLE, Filters, build_where_sql, clamp_limit, resolve_sort,
)
from utils.cache import cached

RECORD_COLUMNS = """
    id_pk, uuid, id, name, pos_x, pos_y, pos_z, world,
    obj_id, obj_name, time, type, data, status
"""


def get_records(args, limit=None):
    """
    Lista paginada de registros con paginación por keyset (cursor), que
    escala bien en tablas de millones de filas a diferencia de
    LIMIT/OFFSET (cuyo costo crece con el offset).

    El cursor viaja en los parámetros `cursor_time` y `cursor_id` y
    representa el último registro visto por el cliente. El orden es
    siempre por `time` (más reciente primero por defecto); `order=ASC`
    invierte la dirección tanto del ORDER BY como de la comparación del
    cursor para mantener la paginación consistente.
    """
    filters = Filters(args)
    clauses, params = filters.where()

    ascending = str(args.get("order", "")).upper() == "ASC"
    cmp_op = ">" if ascending else "<"
    direction = "ASC" if ascending else "DESC"

    cursor_time = args.get("cursor_time")
    cursor_id = args.get("cursor_id")
    if cursor_time not in (None, "") and cursor_id not in (None, ""):
        clauses.append(f"(time {cmp_op} %s OR (time = %s AND id_pk {cmp_op} %s))")
        params += [cursor_time, cursor_time, cursor_id]

    where_sql = build_where_sql(clauses)
    limit = clamp_limit(limit or args.get("limit"))

    sql = f"""
        SELECT {RECORD_COLUMNS}
        FROM {TABLE}
        {where_sql}
        ORDER BY time {direction}, id_pk {direction}
        LIMIT %s
    """
    rows = fetch_all(sql, params + [limit])

    next_cursor = None
    if len(rows) == limit:
        last = rows[-1]
        next_cursor = {"time": last["time"], "id_pk": last["id_pk"]}

    return rows, next_cursor


def get_records_count(args):
    filters = Filters(args)
    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)
    sql = f"SELECT COUNT(*) AS total FROM {TABLE} {where_sql}"
    return fetch_scalar(sql, params)


def get_latest_records(limit=100):
    """Compatibilidad: usada por el dashboard para el resumen rápido."""
    sql = f"""
        SELECT {RECORD_COLUMNS}
        FROM {TABLE}
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


def get_record_by_pk(id_pk):
    sql = f"SELECT {RECORD_COLUMNS} FROM {TABLE} WHERE id_pk = %s"
    rows = fetch_all(sql, [id_pk])
    return rows[0] if rows else None


@cached(Config.CACHE_TTL_LONG_SECONDS)
def get_distinct_types():
    sql = f"SELECT DISTINCT type FROM {TABLE} WHERE type IS NOT NULL ORDER BY type"
    return [row["type"] for row in fetch_all(sql)]


@cached(Config.CACHE_TTL_LONG_SECONDS)
def get_distinct_worlds():
    sql = f"SELECT DISTINCT world FROM {TABLE} WHERE world IS NOT NULL ORDER BY world"
    return [row["world"] for row in fetch_all(sql)]
