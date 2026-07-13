from flask import Blueprint, jsonify, render_template, request

from services import coordinates as coordinates_service
from services import records as records_service
from utils.formatting import unix_to_readable

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
