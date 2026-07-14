"""Estadísticas agregadas para el dashboard y la página de estadísticas."""

from config import Config
from database import fetch_all, fetch_one, fetch_scalar
from services.query_builder import TABLE
from utils.cache import cached
from utils.formatting import now_unix

ENTITY_TYPES = ("entity_damage", "entity_die", "entity_bomb", "player_right_click_entity", "damage")
BLOCK_TYPES = ("block_break", "block_place", "block_break_bomb")


@cached(Config.CACHE_TTL_SECONDS)
def get_overview():
    total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE}")

    now = now_unix()
    day_ago = now - 86400
    week_ago = now - 7 * 86400
    month_ago = now - 30 * 86400

    today_total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE} WHERE time >= %s", [day_ago])
    week_total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE} WHERE time >= %s", [week_ago])
    month_total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE} WHERE time >= %s", [month_ago])

    distinct_players = fetch_scalar(
        f"SELECT COUNT(DISTINCT name) AS total FROM {TABLE} WHERE name IS NOT NULL"
    )
    distinct_worlds = fetch_scalar(
        f"SELECT COUNT(DISTINCT world) AS total FROM {TABLE} WHERE world IS NOT NULL"
    )

    last_event = fetch_one(f"SELECT MAX(time) AS last_time FROM {TABLE}")

    return {
        "total": total or 0,
        "today": today_total or 0,
        "last_7_days": week_total or 0,
        "last_30_days": month_total or 0,
        "avg_daily_30d": round((month_total or 0) / 30, 1),
        "distinct_players": distinct_players or 0,
        "distinct_worlds": distinct_worlds or 0,
        "last_event_time": last_event["last_time"] if last_event else None,
    }


@cached(Config.CACHE_TTL_SECONDS)
def get_type_breakdown(limit=12):
    sql = f"""
        SELECT type, COUNT(*) AS total
        FROM {TABLE}
        WHERE type IS NOT NULL
        GROUP BY type
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_world_breakdown(limit=10):
    sql = f"""
        SELECT world, COUNT(*) AS total
        FROM {TABLE}
        WHERE world IS NOT NULL
        GROUP BY world
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_top_players(limit=10):
    sql = f"""
        SELECT name, COUNT(*) AS total
        FROM {TABLE}
        WHERE name IS NOT NULL
        GROUP BY name
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_top_blocks(limit=10):
    placeholders = ", ".join(["%s"] * len(BLOCK_TYPES))
    sql = f"""
        SELECT COALESCE(NULLIF(obj_name, ''), obj_id) AS obj_name, COUNT(*) AS total
        FROM {TABLE}
        WHERE type IN ({placeholders}) AND COALESCE(NULLIF(obj_name, ''), obj_id) IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, list(BLOCK_TYPES) + [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_top_entities(limit=10):
    placeholders = ", ".join(["%s"] * len(ENTITY_TYPES))
    sql = f"""
        SELECT COALESCE(NULLIF(obj_name, ''), obj_id) AS obj_name, COUNT(*) AS total
        FROM {TABLE}
        WHERE type IN ({placeholders}) AND COALESCE(NULLIF(obj_name, ''), obj_id) IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, list(ENTITY_TYPES) + [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_activity_timeseries(days=30):
    """
    Actividad diaria de los últimos N días usando FROM_UNIXTIME + DATE(),
    agregada en el propio motor MySQL (no en Python) para que escale con
    la tabla.
    """
    since = now_unix() - days * 86400
    sql = f"""
        SELECT
            DATE(FROM_UNIXTIME(time)) AS day,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE time >= %s
        GROUP BY day
        ORDER BY day ASC
    """
    rows = fetch_all(sql, [since])
    return [{"day": str(r["day"]), "total": r["total"]} for r in rows]


@cached(Config.CACHE_TTL_SECONDS)
def get_hourly_activity(days=30):
    """Distribución de actividad por hora del día (0-23), últimos N días."""
    since = now_unix() - days * 86400
    sql = f"""
        SELECT HOUR(FROM_UNIXTIME(time)) AS hour, COUNT(*) AS total
        FROM {TABLE}
        WHERE time >= %s
        GROUP BY hour
        ORDER BY hour ASC
    """
    rows = fetch_all(sql, [since])
    by_hour = {r["hour"]: r["total"] for r in rows}
    return [{"hour": h, "total": by_hour.get(h, 0)} for h in range(24)]


@cached(Config.CACHE_TTL_SECONDS)
def get_heatmap(days=30):
    """
    Mapa de calor día-de-semana x hora, últimos N días. Devuelve una
    matriz plana [{weekday, hour, total}] -- weekday 0=lunes..6=domingo
    (se normaliza el WEEKDAY() de MySQL, que ya usa ese orden).
    """
    since = now_unix() - days * 86400
    sql = f"""
        SELECT
            WEEKDAY(FROM_UNIXTIME(time)) AS weekday,
            HOUR(FROM_UNIXTIME(time)) AS hour,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE time >= %s
        GROUP BY weekday, hour
    """
    rows = fetch_all(sql, [since])
    lookup = {(r["weekday"], r["hour"]): r["total"] for r in rows}
    return [
        {"weekday": wd, "hour": h, "total": lookup.get((wd, h), 0)}
        for wd in range(7)
        for h in range(24)
    ]
