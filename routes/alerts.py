from flask import Blueprint, jsonify, render_template, request

from services import alerts as alerts_service
from services import records as records_service
from utils.formatting import unix_to_readable
from utils.security import current_user, role_required

bp = Blueprint("alerts", __name__)


@bp.route("/alertas")
@role_required("moderator")
def alertas_page():
    try:
        event_types = records_service.get_distinct_types()
    except Exception:  # noqa: BLE001
        event_types = []
    return render_template("alertas.html", event_types=event_types, presets=alerts_service.RULE_PRESETS)


@bp.route("/api/alertas/reglas")
@role_required("moderator")
def api_listar_reglas():
    rows = alerts_service.list_rules(current_user()["id"])
    for row in rows:
        row["event_types_list"] = row["event_types"].split(",") if row["event_types"] else []
        row["last_triggered_fmt"] = unix_to_readable(row.get("last_triggered_at")) if row.get("last_triggered_at") else None
    return jsonify({"results": rows})


@bp.route("/api/alertas/reglas", methods=["POST"])
@role_required("moderator")
def api_crear_regla():
    data = request.get_json(silent=True) or {}
    try:
        rule_id = alerts_service.create_rule(
            current_user()["id"],
            data.get("name"),
            data.get("event_types") or [],
            data.get("block_pattern"),
            data.get("discord_webhook_url"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "id": rule_id})


@bp.route("/api/alertas/reglas/<int:rule_id>/estado", methods=["POST"])
@role_required("moderator")
def api_toggle_regla(rule_id):
    data = request.get_json(silent=True) or {}
    ok = alerts_service.set_rule_enabled(rule_id, current_user()["id"], bool(data.get("enabled")))
    if not ok:
        return jsonify({"error": "No se encontró la regla (o no te pertenece)."}), 404
    return jsonify({"ok": True})


@bp.route("/api/alertas/reglas/<int:rule_id>", methods=["DELETE"])
@role_required("moderator")
def api_borrar_regla(rule_id):
    ok = alerts_service.delete_rule(rule_id, current_user()["id"])
    if not ok:
        return jsonify({"error": "No se encontró la regla (o no te pertenece)."}), 404
    return jsonify({"ok": True})


@bp.route("/api/alertas/reglas/<int:rule_id>/vista-previa")
@role_required("moderator")
def api_vista_previa(rule_id):
    rules = alerts_service.list_rules(current_user()["id"])
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if not rule:
        return jsonify({"error": "No se encontró la regla (o no te pertenece)."}), 404
    hours = request.args.get("hours", default=24, type=int)
    matches = alerts_service.preview_matches(rule, hours=hours, limit=30)
    for row in matches:
        row["fecha"] = unix_to_readable(row["time"])
    return jsonify({"results": matches})
