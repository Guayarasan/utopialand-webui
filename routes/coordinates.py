from flask import Blueprint, jsonify, render_template, request

from services import coordinates as coordinates_service
from services import records as records_service
from utils.formatting import unix_to_readable
from utils.security import current_user, login_required

bp = Blueprint("coordinates", __name__)


@bp.route("/coordenadas")
def coordenadas_page():
    try:
        worlds = records_service.get_distinct_worlds()
    except Exception:  # noqa: BLE001
        worlds = []
    return render_template("coordenadas.html", worlds=worlds)


@bp.route("/api/coordenadas/buscar")
def api_coordenadas_buscar():
    results, meta = coordinates_service.search_near(request.args)
    if "error" in meta:
        return jsonify({"error": meta["error"]}), 400
    for row in results:
        row["fecha"] = unix_to_readable(row["time"])
    return jsonify({"results": results, "meta": meta})


# ---------- Ubicaciones favoritas ----------

@bp.route("/api/coordenadas/favoritos")
@login_required
def api_listar_favoritos():
    rows = coordinates_service.list_favorite_locations(current_user()["id"])
    return jsonify({"results": rows})


@bp.route("/api/coordenadas/favoritos", methods=["POST"])
@login_required
def api_guardar_favorito():
    data = request.get_json(silent=True) or {}
    try:
        location_id = coordinates_service.save_favorite_location(
            current_user()["id"],
            data.get("name"),
            data.get("world"),
            data.get("x"),
            data.get("y"),
            data.get("z"),
            data.get("icon"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "id": location_id})


@bp.route("/api/coordenadas/favoritos/<int:location_id>", methods=["DELETE"])
@login_required
def api_borrar_favorito(location_id):
    ok = coordinates_service.delete_favorite_location(location_id, current_user()["id"])
    if not ok:
        return jsonify({"error": "No se encontró el lugar (o no te pertenece)."}), 404
    return jsonify({"ok": True})
