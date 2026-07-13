"""Estadísticas agregadas para el dashboard y la página de estadísticas."""

from config import Config
from database import fetch_all, fetch_one, fetch_scalar
from services.query_builder import TABLE
from utils.cache import cached
from utils.formatting import now_unix


@cached(Config.CACHE_TTL_SECONDS)
def get_overview():
    total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE}")

    day_ago = now_unix() - 86400
    week_ago = now_unix() - 7 * 86400

    today_total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE} WHERE time >= %s", [day_ago])
    week_total = fetch_scalar(f"SELECT COUNT(*) AS total FROM {TABLE} WHERE time >= %s", [week_ago])

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
def get_activity_timeseries(days=30):
    """
    Actividad diaria de los últimos N días usando FROM_UNIXTIME +
    DATE(), agregada en el propio motor MySQL (no en Python) para que
    escale con la tabla.
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
