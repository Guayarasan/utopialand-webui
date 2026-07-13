"""Búsqueda de eventos por proximidad de coordenadas."""

import math

from database import fetch_all
from services.query_builder import TABLE, Filters, build_where_sql, clamp_limit


def search_near(args):
    """
    Busca eventos dentro de un radio esférico alrededor de (x, y, z).

    La consulta SQL usa una caja delimitadora (bounding box) sobre
    pos_x/pos_y/pos_z -- barata y capaz de usar índices -- y luego el
    filtrado por distancia euclidiana exacta y el orden por cercanía se
    hacen en Python sobre ese subconjunto ya acotado.
    """
    filters = Filters(args)
    if not filters.has_radius_filter():
        return [], {"error": "Se requieren x, y, z y radius."}

    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)

    # Traemos un margen extra sobre el límite pedido porque el bounding
    # box (cúbico) siempre contiene más puntos que la esfera real.
    limit = clamp_limit(args.get("limit"), default=100)
    fetch_limit = min(limit * 4, 2000)

    sql = f"""
        SELECT id_pk, uuid, id, name, pos_x, pos_y, pos_z, world,
               obj_id, obj_name, time, type, data, status
        FROM {TABLE}
        {where_sql}
        ORDER BY time DESC
        LIMIT %s
    """
    rows = fetch_all(sql, params + [fetch_limit])

    cx, cy, cz, radius = filters.x, filters.y, filters.z, filters.radius
    results = []
    for row in rows:
        px, py, pz = row.get("pos_x"), row.get("pos_y"), row.get("pos_z")
        if px is None or py is None or pz is None:
            continue
        distance = math.sqrt((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2)
        if distance <= radius:
            row_with_distance = dict(row)
            row_with_distance["distance"] = round(distance, 2)
            results.append(row_with_distance)

    results.sort(key=lambda r: r["distance"])
    return results[:limit], {"scanned": len(rows), "matched": len(results)}
