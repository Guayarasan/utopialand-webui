"""
Modo Investigación: genera un informe cronológico de actividad para un
jugador y/o una zona (coordenadas + radio), combinando todos los tipos
de evento en una sola línea de tiempo -- para investigar griefs sin
escribir SQL a mano. Reutiliza `Filters` (el mismo motor de filtros de
Registros/Jugadores/Coordenadas), así que hereda sus mismas protecciones
contra inyección SQL.
"""

import math

from database import fetch_all
from services.query_builder import TABLE, Filters, build_where_sql

# Categorización best-effort a partir del nombre real de `type` (no se
# inventan tipos de evento -- se buscan palabras clave dentro de los
# valores que realmente existan en tu instalación de Tianyan).
CATEGORY_RULES = [
    ("explosion", ("bomb", "explod", "explos")),
    ("break", ("break",)),
    ("place", ("place",)),
    ("container", ("open", "container", "chest", "shulker", "hopper", "inventory")),
    ("entity", ("die", "damage", "attack", "kill")),
    ("interaction", ("interact", "use", "click", "pickup", "drop")),
]

CATEGORY_LABELS = {
    "explosion": "Explosiones",
    "break": "Bloques rotos",
    "place": "Bloques colocados",
    "container": "Contenedores abiertos",
    "entity": "Entidades (combate/muertes)",
    "interaction": "Interacciones",
    "other": "Otros eventos",
}


def categorize(event_type):
    t = (event_type or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(k in t for k in keywords):
            return category
    return "other"


def generate_report(args, limit=1000):
    filters = Filters(args)
    if not filters.player and not filters.has_radius_filter():
        raise ValueError(
            "Selecciona al menos un jugador, o unas coordenadas con radio, para generar el informe."
        )

    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)

    # Si hay filtro de radio, el bounding box SQL siempre trae de más
    # (es un cubo, no una esfera) -- pedimos margen extra y recortamos
    # por distancia euclidiana exacta en Python, igual que en Coordenadas.
    fetch_limit = min(limit * 3, 5000) if filters.has_radius_filter() else limit

    sql = f"""
        SELECT id_pk, uuid, id, name, pos_x, pos_y, pos_z, world,
               obj_id, obj_name, time, type, data, status
        FROM {TABLE}
        {where_sql}
        ORDER BY time ASC
        LIMIT %s
    """
    rows = fetch_all(sql, params + [fetch_limit])

    if filters.has_radius_filter():
        cx, cy, cz, radius = filters.x, filters.y, filters.z, filters.radius
        filtered = []
        for row in rows:
            px, py, pz = row.get("pos_x"), row.get("pos_y"), row.get("pos_z")
            if px is None or py is None or pz is None:
                continue
            distance = math.sqrt((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2)
            if distance <= radius:
                row = dict(row)
                row["distance"] = round(distance, 2)
                filtered.append(row)
        rows = filtered

    truncated = len(rows) > limit
    rows = rows[:limit]

    by_category = {}
    players, worlds = set(), set()
    for row in rows:
        cat = categorize(row["type"])
        row["category"] = cat
        by_category[cat] = by_category.get(cat, 0) + 1
        if row.get("name"):
            players.add(row["name"])
        if row.get("world"):
            worlds.add(row["world"])

    summary = {
        "total": len(rows),
        "by_category": [
            {"category": cat, "label": CATEGORY_LABELS.get(cat, cat), "total": total}
            for cat, total in sorted(by_category.items(), key=lambda kv: -kv[1])
        ],
        "players": sorted(players),
        "worlds": sorted(worlds),
        "first_event": rows[0]["time"] if rows else None,
        "last_event": rows[-1]["time"] if rows else None,
        "truncated": truncated,
    }

    return rows, summary
