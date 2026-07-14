"""Consultas agregadas de bloques (obj_name / obj_id)."""

from database import fetch_all, fetch_one
from services.query_builder import TABLE, Filters, build_where_sql, clamp_limit, clamp_offset

BLOCK_TYPES = ("block_break", "block_place", "block_break_bomb")

# COALESCE(NULLIF(obj_name, ''), obj_id) es la clave de agrupación real.
# Motivo del bug histórico "Desconocido": algunos eventos de Tianyan
# (sobre todo block_break_bomb / explosiones) llegan con obj_name como
# cadena vacía ('') en vez de NULL, pero obj_id sí viene poblado. La
# consulta anterior solo filtraba `obj_name IS NOT NULL`, así que esas
# filas SÍ entraban al ranking con obj_name = '' -- y el frontend, al
# recibir una cadena vacía (falsy en JS), caía a un literal
# "desconocido" que luego se pintaba en Title Case. El dato real
# siempre estuvo en la base de datos, solo que en obj_id.
DISPLAY_KEY_EXPR = "COALESCE(NULLIF(obj_name, ''), obj_id)"

BLOCK_SORT_COLUMNS = {
    "obj_name": "display_key",
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
    has_where = bool(where_sql)

    sort_key = args.get("sort", "total")
    order = "ASC" if str(args.get("order", "")).upper() == "ASC" else "DESC"
    sort_col = BLOCK_SORT_COLUMNS.get(sort_key, "total")

    limit = clamp_limit(args.get("limit"), default=50)
    offset = clamp_offset(args.get("offset"))

    sql = f"""
        SELECT
            obj_name,
            obj_id,
            {DISPLAY_KEY_EXPR} AS display_key,
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN type = 'block_break_bomb' THEN 1 ELSE 0 END) AS explosions,
            COUNT(DISTINCT name) AS distinct_players,
            MAX(time) AS last_event
        FROM {TABLE}
        {where_sql}
        {"AND" if has_where else "WHERE"} {DISPLAY_KEY_EXPR} IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY {sort_col} {order}
        LIMIT %s OFFSET %s
    """
    rows = fetch_all(sql, params + [limit, offset])

    count_sql = f"""
        SELECT COUNT(DISTINCT {DISPLAY_KEY_EXPR}) AS total
        FROM {TABLE}
        {where_sql}
        {"AND" if has_where else "WHERE"} {DISPLAY_KEY_EXPR} IS NOT NULL
    """
    total = fetch_one(count_sql, params)["total"]

    return rows, total


def _identity_clause(obj_name, obj_id):
    """Cláusula + parámetros para localizar todos los eventos de un
    mismo bloque, sea cual sea el campo donde Tianyan haya guardado el
    identificador real (obj_name u obj_id)."""
    if obj_name:
        return "obj_name = %s", [obj_name]
    if obj_id not in (None, ""):
        return "obj_id = %s", [obj_id]
    return "(obj_name IS NULL OR obj_name = '') AND obj_id IS NULL", []


def get_block_activity(obj_name, obj_id, args, limit=None):
    filters = Filters(args)
    filters.block = None
    clauses, params = filters.where()

    identity_clause, identity_params = _identity_clause(obj_name, obj_id)
    clauses.insert(0, identity_clause)
    params = identity_params + params

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


def get_block_summary(obj_name, obj_id, args):
    """Resumen completo de un bloque para el modal de detalle: totales,
    distribución por mundo y jugadores más activos sobre ese bloque."""
    filters = Filters(args)
    filters.block = None
    clauses, params = filters.where()

    identity_clause, identity_params = _identity_clause(obj_name, obj_id)
    clauses.insert(0, identity_clause)
    params = identity_params + params

    where_sql = build_where_sql(clauses)
    has_where = bool(where_sql)

    totals_sql = f"""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN type = 'block_break_bomb' THEN 1 ELSE 0 END) AS explosions,
            COUNT(DISTINCT name) AS distinct_players,
            COUNT(DISTINCT world) AS distinct_worlds,
            MIN(time) AS first_event,
            MAX(time) AS last_event
        FROM {TABLE}
        {where_sql}
    """
    totals = fetch_one(totals_sql, params) or {}

    worlds_sql = f"""
        SELECT world, COUNT(*) AS total
        FROM {TABLE}
        {where_sql}
        {"AND" if has_where else "WHERE"} world IS NOT NULL
        GROUP BY world
        ORDER BY total DESC
        LIMIT 5
    """
    worlds = fetch_all(worlds_sql, params)

    top_players_sql = f"""
        SELECT name, COUNT(*) AS total
        FROM {TABLE}
        {where_sql}
        {"AND" if has_where else "WHERE"} name IS NOT NULL
        GROUP BY name
        ORDER BY total DESC
        LIMIT 5
    """
    top_players = fetch_all(top_players_sql, params)

    return {"totals": totals, "worlds": worlds, "top_players": top_players}
