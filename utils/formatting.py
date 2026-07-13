"""Helpers de formato compartidos entre servicios y plantillas Jinja."""

import json
from datetime import datetime, timezone


def unix_to_iso(ts):
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def unix_to_readable(ts):
    if ts is None:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, OSError, OverflowError):
        return "-"


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
