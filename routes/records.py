from flask import Blueprint, jsonify, render_template, request, Response

from services import records as records_service
from services.export import stream_records_csv
from utils.formatting import format_number, try_parse_json, unix_to_readable

bp = Blueprint("records", __name__)


@bp.route("/registros")
def registros_page():
    try:
        types = records_service.get_distinct_types()
        worlds = records_service.get_distinct_worlds()
    except Exception:  # noqa: BLE001 - la página debe cargar aunque la BD falle
        types, worlds = [], []
    return render_template("registros.html", types=types, worlds=worlds)


@bp.route("/api/registros")
def api_registros():
    rows, next_cursor = records_service.get_records(request.args)
    for row in rows:
        row["fecha"] = unix_to_readable(row["time"])
    return jsonify({
        "results": rows,
        "next_cursor": next_cursor,
    })


@bp.route("/api/registros/count")
def api_registros_count():
    total = records_service.get_records_count(request.args)
    return jsonify({"total": total, "total_formatted": format_number(total)})


@bp.route("/api/registros/<int:id_pk>")
def api_registro_detail(id_pk):
    row = records_service.get_record_by_pk(id_pk)
    if not row:
        return jsonify({"error": "Registro no encontrado"}), 404
    row["fecha"] = unix_to_readable(row["time"])
    row["data_parsed"] = try_parse_json(row.get("data"))
    return jsonify(row)


@bp.route("/api/registros/export")
def api_registros_export():
    csv_stream = stream_records_csv(request.args)
    return Response(
        csv_stream,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=registros_tianyan.csv"},
    )
