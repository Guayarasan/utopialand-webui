from flask import Blueprint, jsonify, render_template, request

from services import sql_console as sql_service
from services.sql_console import SQLConsoleError
from utils.formatting import unix_to_readable
from utils.security import current_user, role_required

bp = Blueprint("sql_console", __name__)


@bp.route("/sql")
@role_required("moderator")
def sql_page():
    return render_template("sql.html")


@bp.route("/api/sql/ejecutar", methods=["POST"])
@role_required("moderator")
def api_ejecutar():
    data = request.get_json(silent=True) or {}
    try:
        result = sql_service.run_query(data.get("sql", ""), current_user()["id"])
    except SQLConsoleError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.route("/api/sql/historial")
@role_required("moderator")
def api_historial():
    rows = sql_service.get_history(current_user()["id"])
    for row in rows:
        row["executed_at_fmt"] = unix_to_readable(row["executed_at"])
    return jsonify({"results": rows})


@bp.route("/api/sql/favoritas")
@role_required("moderator")
def api_favoritas():
    rows = sql_service.get_favorites(current_user()["id"])
    return jsonify({"results": rows})


@bp.route("/api/sql/favoritas", methods=["POST"])
@role_required("moderator")
def api_guardar_favorita():
    data = request.get_json(silent=True) or {}
    try:
        fav_id = sql_service.save_favorite(
            current_user()["id"], data.get("name"), data.get("sql", ""), data.get("category")
        )
    except SQLConsoleError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "id": fav_id})


@bp.route("/api/sql/favoritas/<int:favorite_id>", methods=["DELETE"])
@role_required("moderator")
def api_borrar_favorita(favorite_id):
    ok = sql_service.delete_favorite(favorite_id, current_user()["id"])
    if not ok:
        return jsonify({"error": "No se encontró la consulta guardada (o no te pertenece)."}), 404
    return jsonify({"ok": True})
