"""
Widgets del Dashboard: agregados ligeros y consultas de "últimos N"
pensadas para refrescarse solas en el frontend sin recargar la página.

Reutiliza `services.stats` para los números ya calculados (overview,
serie diaria) y añade aquí solo lo que faltaba: listados de actividad
reciente por categoría.
"""

from config import Config
from database import fetch_all
from services.query_builder import TABLE
from utils.cache import cached
from utils.formatting import now_unix

# Vista previa de "eventos importantes": explosiones, muertes de
# entidades y colocación de bloques sensibles (TNT / lava). La Fase 3
# (Alertas) convertirá esto en reglas configurables por el usuario;
# por ahora es una selección fija razonable para vigilancia rápida.
IMPORTANT_PLACED_BLOCKS = ("minecraft:tnt", "minecraft:lava", "minecraft:flowing_lava")

RECENT_COLUMNS = "id_pk, name, type, obj_name, obj_id, world, pos_x, pos_y, pos_z, time, status"


@cached(Config.CACHE_TTL_SECONDS)
def get_recent_activity(limit=15):
    sql = f"""
        SELECT {RECENT_COLUMNS}
        FROM {TABLE}
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_active_players_today(limit=8):
    since = now_unix() - 86400
    sql = f"""
        SELECT name, COUNT(*) AS total
        FROM {TABLE}
        WHERE time >= %s AND name IS NOT NULL
        GROUP BY name
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [since, limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_most_modified_blocks_today(limit=8):
    since = now_unix() - 86400
    sql = f"""
        SELECT
            COALESCE(NULLIF(obj_name, ''), obj_id) AS obj_name,
            obj_id,
            COUNT(*) AS total
        FROM {TABLE}
        WHERE time >= %s
          AND type IN ('block_break', 'block_place', 'block_break_bomb')
          AND COALESCE(NULLIF(obj_name, ''), obj_id) IS NOT NULL
        GROUP BY obj_name, obj_id
        ORDER BY total DESC
        LIMIT %s
    """
    return fetch_all(sql, [since, limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_latest_explosions(limit=8):
    sql = f"""
        SELECT {RECENT_COLUMNS}
        FROM {TABLE}
        WHERE type = 'block_break_bomb'
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_latest_deaths(limit=8):
    sql = f"""
        SELECT {RECENT_COLUMNS}
        FROM {TABLE}
        WHERE type = 'entity_die'
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_important_events(limit=10):
    placeholders = ", ".join(["%s"] * len(IMPORTANT_PLACED_BLOCKS))
    sql = f"""
        SELECT {RECENT_COLUMNS}
        FROM {TABLE}
        WHERE type IN ('block_break_bomb', 'entity_die')
           OR (type = 'block_place' AND obj_name IN ({placeholders}))
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return fetch_all(sql, list(IMPORTANT_PLACED_BLOCKS) + [limit])


@cached(Config.CACHE_TTL_SECONDS)
def get_today_calendar_count():
    sql = f"""
        SELECT COUNT(*) AS total
        FROM {TABLE}
        WHERE DATE(FROM_UNIXTIME(time)) = CURDATE()
    """
    rows = fetch_all(sql)
    return rows[0]["total"] if rows else 0
