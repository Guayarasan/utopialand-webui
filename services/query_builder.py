"""
Constructor de consultas para LOGDATA.

Centraliza cómo se arman las cláusulas WHERE / ORDER BY / paginación a
partir de filtros que llegan desde el frontend, para que registros,
jugadores, bloques, coordenadas y estadísticas compartan exactamente la
misma lógica de filtrado (y las mismas protecciones contra inyección
SQL) en lugar de reimplementarla cada uno a su manera.

Columnas reales de LOGDATA (no inventar otras):
    id_pk, uuid, id, name, pos_x, pos_y, pos_z, world,
    obj_id, obj_name, time, type, data, status
"""

from config import Config

TABLE = Config.DB_TABLE

# Columnas por las que se permite ordenar (whitelist obligatoria: ORDER BY
# no se puede parametrizar con placeholders de PyMySQL).
SORTABLE_COLUMNS = {
    "time": "time",
    "name": "name",
    "type": "type",
    "world": "world",
    "obj_name": "obj_name",
    "status": "status",
}

DEFAULT_SORT = "time"
DEFAULT_ORDER = "DESC"


class Filters:
    """Representa y valida los filtros aceptados por la tabla LOGDATA."""

    def __init__(self, args):
        self.player = _clean_str(args.get("player"))
        self.types = _clean_list(args.get("type"))
        self.world = _clean_str(args.get("world"))
        self.block = _clean_str(args.get("block"))
        self.status = _clean_str(args.get("status"))
        self.date_from = _clean_int(args.get("date_from"))
        self.date_to = _clean_int(args.get("date_to"))

        self.x = _clean_float(args.get("x"))
        self.y = _clean_float(args.get("y"))
        self.z = _clean_float(args.get("z"))
        self.radius = _clean_float(args.get("radius"))

    def where(self):
        clauses = []
        params = []

        if self.player:
            clauses.append("name LIKE %s")
            params.append(f"%{self.player}%")

        if self.types:
            placeholders = ", ".join(["%s"] * len(self.types))
            clauses.append(f"type IN ({placeholders})")
            params.extend(self.types)

        if self.world:
            clauses.append("world = %s")
            params.append(self.world)

        if self.block:
            clauses.append("obj_name LIKE %s")
            params.append(f"%{self.block}%")

        if self.status not in (None, ""):
            clauses.append("status = %s")
            params.append(self.status)

        if self.date_from is not None:
            clauses.append("time >= %s")
            params.append(self.date_from)

        if self.date_to is not None:
            clauses.append("time <= %s")
            params.append(self.date_to)

        if self.x is not None and self.y is not None and self.z is not None and self.radius is not None:
            # Bounding box: usa índices en pos_x/pos_y/pos_z de forma
            # eficiente. El filtrado por distancia euclidiana exacta se
            # aplica después, en memoria, sobre el conjunto ya acotado.
            clauses.append("pos_x BETWEEN %s AND %s")
            clauses.append("pos_y BETWEEN %s AND %s")
            clauses.append("pos_z BETWEEN %s AND %s")
            params += [
                self.x - self.radius, self.x + self.radius,
                self.y - self.radius, self.y + self.radius,
                self.z - self.radius, self.z + self.radius,
            ]

        return clauses, params

    def has_radius_filter(self):
        return None not in (self.x, self.y, self.z, self.radius)


def build_where_sql(clauses):
    if not clauses:
        return ""
    return "WHERE " + " AND ".join(clauses)


def resolve_sort(sort_key, order):
    column = SORTABLE_COLUMNS.get(sort_key, DEFAULT_SORT)
    direction = "ASC" if str(order).upper() == "ASC" else "DESC"
    return column, direction


def clamp_limit(raw_limit, default=None, maximum=None):
    default = default or Config.DEFAULT_PAGE_SIZE
    maximum = maximum or Config.MAX_PAGE_SIZE
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return default
    if limit <= 0:
        return default
    return min(limit, maximum)


def clamp_offset(raw_offset):
    try:
        offset = int(raw_offset)
    except (TypeError, ValueError):
        return 0
    return max(offset, 0)


def _clean_str(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _clean_list(value):
    """Acepta tanto `type=a&type=b` (MultiDict.getlist) como `type=a,b`."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = value
    else:
        items = str(value).split(",")
    cleaned = [str(v).strip() for v in items if str(v).strip()]
    return cleaned


def _clean_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _clean_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
