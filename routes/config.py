from flask import Blueprint, jsonify, render_template, request

from config import Config
from database import check_connection
from services import timezone_settings
from utils.cache import cache_clear
from utils.security import current_user, login_required, role_required, update_session_timezone

bp = Blueprint("config_routes", __name__)


def _mask(value, keep=2):
    if not value:
        return "-"
    value = str(value)
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)


@bp.route("/configuracion")
def configuracion_page():
    db_info = {
        "host": _mask(Config.DB_HOST, keep=4),
        "port": Config.DB_PORT,
        "database": _mask(Config.DB_NAME, keep=2),
        "user": _mask(Config.DB_USER, keep=2),
        "table": Config.DB_TABLE,
        "pool_size": Config.DB_POOL_SIZE,
    }
    try:
        app_timezone = timezone_settings.get_app_timezone()
    except Exception:  # noqa: BLE001
        app_timezone = timezone_settings.DEFAULT_TIMEZONE
    return render_template(
        "configuracion.html",
        db_info=db_info,
        app_name=Config.APP_NAME,
        app_version=Config.APP_VERSION,
        timezone_choices=timezone_settings.TIMEZONE_CHOICES,
        app_timezone=app_timezone,
        user_timezone=(current_user() or {}).get("timezone") or "",
    )


@bp.route("/api/config/test-conexion", methods=["POST"])
def api_test_conexion():
    ok, message, latency_ms = check_connection()
    return jsonify({"ok": ok, "message": message, "latency_ms": latency_ms})


@bp.route("/api/config/limpiar-cache", methods=["POST"])
def api_limpiar_cache():
    cache_clear()
    return jsonify({"ok": True, "message": "Caché de agregados limpiada."})


@bp.route("/api/config/zona-horaria/app", methods=["POST"])
@role_required("admin")
def api_set_app_timezone():
    data = request.get_json(silent=True) or {}
    try:
        tz = timezone_settings.set_app_timezone(data.get("timezone"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "timezone": tz})


@bp.route("/api/config/zona-horaria/mia", methods=["POST"])
@login_required
def api_set_user_timezone():
    data = request.get_json(silent=True) or {}
    try:
        tz = timezone_settings.set_user_timezone(current_user()["id"], data.get("timezone"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    update_session_timezone(tz)
    return jsonify({"ok": True, "timezone": tz})
