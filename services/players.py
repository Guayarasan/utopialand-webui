"""Consultas agregadas de jugadores."""

from database import fetch_all, fetch_one
from services.query_builder import (
    TABLE, Filters, build_where_sql, clamp_limit, clamp_offset,
)


PLAYER_SORT_COLUMNS = {
    "name": "name",
    "total": "total",
    "last_seen": "last_seen",
}


def get_players(args):
    """
    Lista de jugadores agregados desde LOGDATA agrupando por `name`,
    con conteos por tipo de acción más comunes y última actividad.
    """
    search = (args.get("search") or "").strip()
    sort_key = args.get("sort", "total")
    order = "ASC" if str(args.get("order", "")).upper() == "ASC" else "DESC"
    sort_col = PLAYER_SORT_COLUMNS.get(sort_key, "total")

    limit = clamp_limit(args.get("limit"), default=50)
    offset = clamp_offset(args.get("offset"))

    where_sql = ""
    params = []
    if search:
        where_sql = "WHERE name LIKE %s"
        params.append(f"%{search}%")

    sql = f"""
        SELECT
            name,
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN type IN ('entity_die', 'entity_damage', 'damage', 'entity_bomb') THEN 1 ELSE 0 END) AS combat,
            MAX(time) AS last_seen,
            MIN(time) AS first_seen
        FROM {TABLE}
        {where_sql}
        AND name IS NOT NULL
        GROUP BY name
        ORDER BY {sort_col} {order}
        LIMIT %s OFFSET %s
    """.replace("AND name IS NOT NULL", ("AND" if where_sql else "WHERE") + " name IS NOT NULL")

    rows = fetch_all(sql, params + [limit, offset])

    count_sql = f"""
        SELECT COUNT(DISTINCT name) AS total
        FROM {TABLE}
        {where_sql}
        {"AND" if where_sql else "WHERE"} name IS NOT NULL
    """
    total = fetch_one(count_sql, params)["total"]

    return rows, total


def get_player_summary(name):
    sql = f"""
        SELECT
            name,
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            MAX(time) AS last_seen,
            MIN(time) AS first_seen,
            COUNT(DISTINCT world) AS worlds_visited
        FROM {TABLE}
        WHERE name = %s
        GROUP BY name
    """
    return fetch_one(sql, [name])


def get_player_activity(name, args, limit=None):
    """Actividad reciente de un jugador puntual, reutilizando los filtros comunes."""
    filters = Filters(args)
    filters.player = None  # el nombre exacto se aplica aparte (igualdad, no LIKE)
    clauses, params = filters.where()
    clauses.insert(0, "name = %s")
    params.insert(0, name)

    where_sql = build_where_sql(clauses)
    limit = clamp_limit(limit or args.get("limit"), default=50)

    sql = f"""
        SELECT id_pk, uuid, id, name, pos_x, pos_y, pos_z, world,
               obj_id, obj_name, time, type, data, status
        FROM {TABLE}
        {where_sql}
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, params + [limit])


def get_player_type_breakdown(name):
    sql = f"""
        SELECT type, COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s
        GROUP BY type
        ORDER BY total DESC
    """
    return fetch_all(sql, [name])
