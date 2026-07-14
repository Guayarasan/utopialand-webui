from flask import Blueprint, jsonify, render_template, request, Response, send_file

from services import records as records_service
from services import saved_filters as saved_filters_service
from services.export import build_records_xlsx, stream_records_csv, stream_records_json
from utils.formatting import format_number, try_parse_json, unix_to_readable
from utils.security import current_user, login_required

bp = Blueprint("records", __name__)

PAGE_KEY = "registros"


@bp.route("/registros")
@login_required
def registros_page():
    try:
        types = records_service.get_distinct_types()
        worlds = records_service.get_distinct_worlds()
    except Exception:  # noqa: BLE001 - la página debe cargar aunque la BD falle
        types, worlds = [], []
    return render_template("registros.html", types=types, worlds=worlds)


@bp.route("/api/registros")
@login_required
def api_registros():
    data = records_service.get_records_page(request.args)
    for row in data["results"]:
        row["fecha"] = unix_to_readable(row["time"])
    data["total_formatted"] = format_number(data["total"])
    return jsonify(data)


@bp.route("/api/registros/<int:id_pk>")
@login_required
def api_registro_detail(id_pk):
    row = records_service.get_record_by_pk(id_pk)
    if not row:
        return jsonify({"error": "Registro no encontrado"}), 404
    row["fecha"] = unix_to_readable(row["time"])
    row["data_parsed"] = try_parse_json(row.get("data"))
    return jsonify(row)


@bp.route("/api/registros/exportar/csv")
@login_required
def api_export_csv():
    return Response(
        stream_records_csv(request.args),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=registros_tianyan.csv"},
    )


@bp.route("/api/registros/exportar/json")
@login_required
def api_export_json():
    return Response(
        stream_records_json(request.args),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=registros_tianyan.json"},
    )


@bp.route("/api/registros/exportar/xlsx")
@login_required
def api_export_xlsx():
    buffer = build_records_xlsx(request.args)
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="registros_tianyan.xlsx",
    )


# ---------- Filtros favoritos ----------

@bp.route("/api/registros/filtros-favoritos")
@login_required
def api_listar_filtros():
    rows = saved_filters_service.list_saved_filters(current_user()["id"], PAGE_KEY)
    return jsonify({"results": rows})


@bp.route("/api/registros/filtros-favoritos", methods=["POST"])
@login_required
def api_guardar_filtro():
    data = request.get_json(silent=True) or {}
    try:
        filter_id = saved_filters_service.save_filter(
            current_user()["id"], PAGE_KEY, data.get("name"), data.get("filters") or {}
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "id": filter_id})


@bp.route("/api/registros/filtros-favoritos/<int:filter_id>", methods=["DELETE"])
@login_required
def api_borrar_filtro(filter_id):
    ok = saved_filters_service.delete_saved_filter(filter_id, current_user()["id"])
    if not ok:
        return jsonify({"error": "No se encontró el filtro (o no te pertenece)."}), 404
    return jsonify({"ok": True})
