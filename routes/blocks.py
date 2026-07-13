from flask import Blueprint, jsonify, render_template, request

from services import blocks as blocks_service
from services import records as records_service
from utils.formatting import unix_to_readable

bp = Blueprint("blocks", __name__)


@bp.route("/bloques")
def bloques_page():
    try:
        worlds = records_service.get_distinct_worlds()
    except Exception:  # noqa: BLE001
        worlds = []
    return render_template("bloques.html", worlds=worlds)


@bp.route("/api/bloques")
def api_bloques():
    rows, total = blocks_service.get_top_blocks(request.args)
    for row in rows:
        row["last_event_fmt"] = unix_to_readable(row["last_event"])
    return jsonify({"results": rows, "total": total})


@bp.route("/api/bloques/<path:obj_name>/actividad")
def api_bloque_actividad(obj_name):
    rows = blocks_service.get_block_activity(obj_name, request.args)
    for row in rows:
        row["fecha"] = unix_to_readable(row["time"])
    return jsonify({"results": rows})
