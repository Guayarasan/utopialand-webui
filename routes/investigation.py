from flask import Blueprint, jsonify, render_template, request

from services import investigation as investigation_service
from services import records as records_service
from utils.formatting import unix_to_readable

bp = Blueprint("investigation", __name__)


@bp.route("/investigacion")
def investigacion_page():
    try:
        worlds = records_service.get_distinct_worlds()
    except Exception:  # noqa: BLE001
        worlds = []
    return render_template("investigacion.html", worlds=worlds)


@bp.route("/api/investigacion/informe")
def api_generar_informe():
    try:
        rows, summary = investigation_service.generate_report(request.args)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    for row in rows:
        row["fecha"] = unix_to_readable(row["time"])
    summary["first_event_fmt"] = unix_to_readable(summary["first_event"]) if summary["first_event"] else None
    summary["last_event_fmt"] = unix_to_readable(summary["last_event"]) if summary["last_event"] else None

    return jsonify({"results": rows, "summary": summary})
