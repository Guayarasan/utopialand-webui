"""Consultas agregadas de jugadores."""

from database import fetch_all, fetch_one
from services.query_builder import (
    TABLE, Filters, build_where_sql, clamp_limit, clamp_offset,
)
from utils.formatting import current_utc_offset_sql

# Mismos tipos que ya se usaban para el contador "combat" en get_players.
# Si tu instalación de Tianyan usa nombres de evento distintos para
# combate, ajusta esta lista -- son los únicos 4 nombres que el proyecto
# original asumía, no hay forma de confirmarlos sin acceso a la BD real.
COMBAT_TYPES = ("entity_die", "entity_damage", "damage", "entity_bomb")

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
    tz_offset = current_utc_offset_sql()
    sql = f"""
        SELECT
            name,
            COUNT(*) AS total,
            SUM(CASE WHEN type = 'block_break' THEN 1 ELSE 0 END) AS breaks,
            SUM(CASE WHEN type = 'block_place' THEN 1 ELSE 0 END) AS places,
            SUM(CASE WHEN type IN ({", ".join(["%s"] * len(COMBAT_TYPES))}) THEN 1 ELSE 0 END) AS combat,
            MAX(time) AS last_seen,
            MIN(time) AS first_seen,
            COUNT(DISTINCT world) AS worlds_visited,
            COUNT(DISTINCT DATE(CONVERT_TZ(FROM_UNIXTIME(time), '+00:00', %s))) AS active_days
        FROM {TABLE}
        WHERE name = %s
        GROUP BY name
    """
    return fetch_one(sql, list(COMBAT_TYPES) + [tz_offset, name])


def get_player_activity(name, args, limit=None):
    """Actividad reciente de un jugador puntual (línea de tiempo), reutilizando los filtros comunes."""
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


def get_player_daily_activity(name, days=30):
    """Serie diaria de actividad (para el gráfico de línea de la ficha),
    en la zona horaria de visualización."""
    tz_offset = current_utc_offset_sql()
    sql = f"""
        SELECT DATE(CONVERT_TZ(FROM_UNIXTIME(time), '+00:00', %s)) AS day, COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s AND time >= UNIX_TIMESTAMP(NOW()) - (%s * 86400)
        GROUP BY day
        ORDER BY day ASC
    """
    return fetch_all(sql, [tz_offset, name, days])


def get_player_hourly_activity(name):
    """Distribución de actividad por hora del día (0-23), todo el
    historial, en la zona horaria de visualización."""
    tz_offset = current_utc_offset_sql()
    sql = f"""
        SELECT HOUR(CONVERT_TZ(FROM_UNIXTIME(time), '+00:00', %s)) AS hour, COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s
        GROUP BY hour
        ORDER BY hour ASC
    """
    rows = fetch_all(sql, [tz_offset, name])
    by_hour = {r["hour"]: r["total"] for r in rows}
    return [{"hour": h, "total": by_hour.get(h, 0)} for h in range(24)]


def get_player_top_blocks(name, action_type, limit=8):
    """Bloques más rotos o colocados por el jugador (action_type: 'block_break' o 'block_place')."""
    sql = f"""
        SELECT
            COALESCE(NULLIF(obj_name, ''), obj_id) AS obj_name,
            obj_id,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s AND type = %s
          AND COALESCE(NULLIF(obj_name, ''), obj_id) IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [name, action_type, limit])


def get_player_entities_attacked(name, limit=8):
    placeholders = ", ".join(["%s"] * len(COMBAT_TYPES))
    sql = f"""
        SELECT
            COALESCE(NULLIF(obj_name, ''), obj_id) AS obj_name,
            obj_id,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s AND type IN ({placeholders})
          AND COALESCE(NULLIF(obj_name, ''), obj_id) IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [name] + list(COMBAT_TYPES) + [limit])


def get_player_worlds(name):
    sql = f"""
        SELECT world, COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s AND world IS NOT NULL
        GROUP BY world
        ORDER BY total DESC
    """
    return fetch_all(sql, [name])


def get_player_frequent_coords(name, limit=10, bucket=100):
    """
    Agrupa la actividad del jugador en 'zonas' cuadradas de `bucket`
    bloques (por defecto 100x100) para encontrar dónde pasa más tiempo,
    sin necesitar coordenadas exactas idénticas.
    """
    sql = f"""
        SELECT
            world,
            ROUND(pos_x / %s) * %s AS zone_x,
            ROUND(pos_z / %s) * %s AS zone_z,
            AVG(pos_y) AS avg_y,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE name = %s AND pos_x IS NOT NULL AND pos_z IS NOT NULL
        GROUP BY world, zone_x, zone_z
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [bucket, bucket, bucket, bucket, name, limit])
