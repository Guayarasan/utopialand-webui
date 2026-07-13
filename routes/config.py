from flask import Blueprint, jsonify, render_template

from config import Config
from database import check_connection
from utils.cache import cache_clear

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
    return render_template(
        "configuracion.html",
        db_info=db_info,
        app_name=Config.APP_NAME,
        app_version=Config.APP_VERSION,
    )


@bp.route("/api/config/test-conexion", methods=["POST"])
def api_test_conexion():
    ok, message, latency_ms = check_connection()
    return jsonify({"ok": ok, "message": message, "latency_ms": latency_ms})


@bp.route("/api/config/limpiar-cache", methods=["POST"])
def api_limpiar_cache():
    cache_clear()
    return jsonify({"ok": True, "message": "Caché de agregados limpiada."})
