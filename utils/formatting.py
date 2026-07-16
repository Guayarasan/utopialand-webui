"""Helpers de formato compartidos entre servicios y plantillas Jinja."""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ_NAME = "UTC"
_ZONEINFO_CACHE = {}


def _get_zoneinfo(name):
    if name not in _ZONEINFO_CACHE:
        try:
            _ZONEINFO_CACHE[name] = ZoneInfo(name)
        except Exception:  # noqa: BLE001 -- nombre inválido -> UTC de vuelta
            _ZONEINFO_CACHE[name] = ZoneInfo("UTC")
    return _ZONEINFO_CACHE[name]


def _current_tz_name():
    """Zona horaria resuelta para la petición actual (ver
    services/timezone_settings.py y el before_request de app.py). Fuera
    de un contexto de petición (scripts, tareas manuales) cae a UTC."""
    try:
        from flask import g, has_request_context
        if has_request_context() and hasattr(g, "tz_name"):
            return g.tz_name
    except Exception:  # noqa: BLE001
        pass
    return DEFAULT_TZ_NAME


def unix_to_iso(ts):
    """Siempre en UTC a propósito: es un formato pensado para máquinas
    (exportaciones, APIs), no para mostrarse al usuario."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def unix_to_readable(ts, tz_name=None):
    """Formatea un Unix timestamp (siempre UTC en la base de datos) en la
    zona horaria de visualización -- la resuelta para la petición actual
    por defecto, o `tz_name` si se pasa explícitamente."""
    if ts is None:
        return "-"
    try:
        tz = _get_zoneinfo(tz_name or _current_tz_name())
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone(tz)
        label = dt.tzname() or tz.key
        return dt.strftime("%Y-%m-%d %H:%M:%S") + f" {label}"
    except (ValueError, OSError, OverflowError):
        return "-"


def current_utc_offset_sql(tz_name=None):
    """
    Offset fijo '+HH:MM' de la zona horaria de visualización, listo para
    usarse como segundo argumento de CONVERT_TZ() en consultas SQL que
    agrupan por día/hora (series diarias, heatmap semana×hora, "hoy").

    Sin esto, DATE(FROM_UNIXTIME(time)) y CURDATE() usan la zona horaria
    de la SESIÓN de MySQL (normalmente la del servidor, no la que el
    usuario configuró en la WebUI), así que "hoy" o un bucket diario
    podían quedar desplazados. Se evalúa el offset "ahora" -- una
    aproximación razonable; no se reajusta minuto a minuto por cada
    cambio histórico de horario de verano en datos antiguos.
    """
    tz = _get_zoneinfo(tz_name or _current_tz_name())
    offset = datetime.now(tz).utcoffset()
    if offset is None:
        return "+00:00"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    return f"{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def now_unix():
    return int(datetime.now(tz=timezone.utc).timestamp())


def format_number(n):
    if n is None:
        return "-"
    return f"{n:,}".replace(",", ".")


def try_parse_json(raw):
    """Intenta interpretar la columna `data` como JSON para mostrarla legible."""
    if raw in (None, ""):
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def coord_label(x, y, z):
    def fmt(v):
        if v is None:
            return "?"
        try:
            return f"{float(v):.0f}"
        except (TypeError, ValueError):
            return "?"

    return f"{fmt(x)} / {fmt(y)} / {fmt(z)}"
