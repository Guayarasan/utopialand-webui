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


def get_records_page(args):
    """
    Página de registros con paginación clásica por número de página,
    ordenable por cualquier columna de la whitelist. Es intencionalmente
    más simple que un cursor keyset porque el pedido explícito era poder
    saltar a una página concreta y elegir cuántos resultados mostrar;
    para no perder rendimiento en tablas de millones de filas, el número
    de página está acotado (ver `MAX_JUMPABLE_PAGE` más abajo) y se anima
    a mantener filtros que acoten bien el rango antes de paginar en
    profundidad.
    """
    filters = Filters(args)
    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)

    sort_col, direction = resolve_sort(args.get("sort"), args.get("order"))
    limit = clamp_limit(args.get("limit"))
    page = _clamp_page(args.get("page"))
    offset = (page - 1) * limit

    sql = f"""
        SELECT {RECORD_COLUMNS}
        FROM {TABLE}
        {where_sql}
        ORDER BY {sort_col} {direction}, id_pk {direction}
        LIMIT %s OFFSET %s
    """
    rows = fetch_all(sql, params + [limit, offset])
    total = get_records_count(args)
    total_pages = max(1, -(-total // limit)) if total else 1

    return {
        "results": rows,
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages,
    }


MAX_JUMPABLE_PAGE = 20000


def _clamp_page(raw_page):
    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        return 1
    return max(1, min(page, MAX_JUMPABLE_PAGE))


def get_records_count(args):
    filters = Filters(args)
    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)
    sql = f"SELECT COUNT(*) AS total FROM {TABLE} {where_sql}"
    return fetch_scalar(sql, params) or 0


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
