"""Consultas agregadas de bloques (obj_name / obj_id)."""

from database import fetch_all, fetch_one
from services.query_builder import TABLE, Filters, build_where_sql, clamp_limit, clamp_offset

BLOCK_TYPES = ("block_break", "block_place", "block_break_bomb")

BLOCK_SORT_COLUMNS = {
    "obj_name": "obj_name",
    "total": "total",
    "breaks": "breaks",
    "places": "places",
    "last_event": "last_event",
}


def get_top_blocks(args):
    filters = Filters(args)
    clauses, params = filters.where()
    if not filters.types:
        # Sin filtro explícito, restringimos a eventos de bloque para que
        # el ranking tenga sentido (no mezclar con damage/pickup/etc).
        placeholders = ", ".join(["%s"] * len(BLOCK_TYPES))
        clauses.append(f"type IN ({placeholders})")
        params.extend(BLOCK_TYPES)

    where_sql = build_where_sql(clauses)

    sort_key = args.get("sort", "total")
    order = "ASC" if str(args.get("order", "")).upper() == "ASC" else "DESC"
    sort_col = BLOCK_SORT_COLUMNS.get(sort_key, "total")

    limit = clamp_limit(args.get("limit"), default=50)
    offset = clamp_offset(args.get("offset"))

    sql = f"""
        SELECT
            obj_name,
            obj_id,
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN type = 'block_break_bomb' THEN 1 ELSE 0 END) AS explosions,
            COUNT(DISTINCT name) AS distinct_players,
            MAX(time) AS last_event
        FROM {TABLE}
        {where_sql}
        AND obj_name IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY {sort_col} {order}
        LIMIT %s OFFSET %s
    """.replace("AND obj_name IS NOT NULL", ("AND" if where_sql else "WHERE") + " obj_name IS NOT NULL")

    rows = fetch_all(sql, params + [limit, offset])

    count_sql = f"""
        SELECT COUNT(DISTINCT obj_name) AS total
        FROM {TABLE}
        {where_sql}
        {"AND" if where_sql else "WHERE"} obj_name IS NOT NULL
    """
    total = fetch_one(count_sql, params)["total"]

    return rows, total


def get_block_activity(obj_name, args, limit=None):
    filters = Filters(args)
    filters.block = None
    clauses, params = filters.where()
    clauses.insert(0, "obj_name = %s")
    params.insert(0, obj_name)

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
