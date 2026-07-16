"""
Zona horaria de visualización.

La base de datos SIEMPRE guarda los tiempos en UTC -- la columna `time`
de LOGDATA es un Unix timestamp y eso no cambia con esta funcionalidad.
Este módulo controla únicamente CÓMO se muestra esa hora en la WebUI:

- Hay una zona horaria por defecto de la aplicación (Configuración,
  cualquier administrador puede cambiarla), que aplica a todo el mundo
  que no haya elegido la suya propia.
- Cada usuario puede además fijar su propia zona horaria personal
  (Configuración > Mi cuenta), que tiene prioridad sobre la de la
  aplicación si está definida.

`utils/formatting.unix_to_readable` (usado en absolutamente todas las
fechas mostradas: Registros, Dashboard, Estadísticas, modales, Alertas,
etc.) lee la zona horaria resuelta para la petición actual desde
`flask.g.tz_name`, que `app.py` fija una vez por request en
`before_request`. Así no hace falta tocar cada punto de la aplicación
que ya formatea fechas -- se corrige en un solo lugar.
"""

from zoneinfo import available_timezones

from database import fetch_one, get_connection
from utils.cache import cache_clear, cached

DEFAULT_TIMEZONE = "UTC"

_VALID_TIMEZONES = None


def is_valid_timezone(name):
    global _VALID_TIMEZONES
    if _VALID_TIMEZONES is None:
        _VALID_TIMEZONES = available_timezones()
    return bool(name) and name in _VALID_TIMEZONES


# Lista corta y curada para el selector -- available_timezones() trae
# cientos de nombres, la enorme mayoría irrelevantes aquí. Todos son
# nombres IANA válidos y reconocidos por zoneinfo.
TIMEZONE_CHOICES = [
    ("UTC", "UTC"),
    ("America/Mexico_City", "Ciudad de México"),
    ("America/Bogota", "Bogotá"),
    ("America/Lima", "Lima"),
    ("America/Santiago", "Santiago de Chile"),
    ("America/Argentina/Buenos_Aires", "Buenos Aires"),
    ("America/Caracas", "Caracas"),
    ("America/New_York", "Nueva York"),
    ("America/Chicago", "Chicago"),
    ("America/Denver", "Denver"),
    ("America/Los_Angeles", "Los Ángeles"),
    ("Europe/Madrid", "Madrid"),
    ("Europe/London", "Londres"),
    ("Europe/Paris", "París"),
    ("Europe/Berlin", "Berlín"),
    ("Europe/Lisbon", "Lisboa"),
    ("Africa/Casablanca", "Casablanca"),
    ("Asia/Dubai", "Dubái"),
    ("Asia/Kolkata", "Bombay / Nueva Delhi"),
    ("Asia/Shanghai", "Shanghái"),
    ("Asia/Tokyo", "Tokio"),
    ("Australia/Sydney", "Sídney"),
    ("Pacific/Auckland", "Auckland"),
]


@cached(120)
def get_app_timezone():
    row = fetch_one("SELECT value FROM webui_app_settings WHERE setting_key = 'timezone'")
    if row and is_valid_timezone(row["value"]):
        return row["value"]
    return DEFAULT_TIMEZONE


def set_app_timezone(tz_name):
    if not is_valid_timezone(tz_name):
        raise ValueError("Zona horaria no válida.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO webui_app_settings (setting_key, value) VALUES ('timezone', %s) "
                "ON DUPLICATE KEY UPDATE value = VALUES(value)",
                (tz_name,),
            )
    finally:
        conn.close()
    cache_clear(prefix="services.timezone_settings.get_app_timezone")
    return tz_name


def get_effective_timezone(user):
    """Zona horaria a usar para mostrar fechas: la personal del usuario
    si la tiene, si no la de la aplicación."""
    if user and user.get("timezone") and is_valid_timezone(user["timezone"]):
        return user["timezone"]
    try:
        return get_app_timezone()
    except Exception:  # noqa: BLE001 -- nunca romper el render de fechas por esto
        return DEFAULT_TIMEZONE


def set_user_timezone(user_id, tz_name):
    """tz_name vacío/None = "usar la de la aplicación" (quita la personal)."""
    tz_name = (tz_name or "").strip() or None
    if tz_name and not is_valid_timezone(tz_name):
        raise ValueError("Zona horaria no válida.")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE webui_users SET timezone = %s WHERE id = %s", (tz_name, user_id))
    finally:
        conn.close()
    return tz_name
