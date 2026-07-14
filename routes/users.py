from flask import Blueprint, jsonify, render_template, request

from services import users as users_service
from services.users import UserError
from utils.formatting import unix_to_readable
from utils.security import ROLE_LABELS, current_user, role_required

bp = Blueprint("users", __name__)


@bp.route("/usuarios")
@role_required("admin")
def usuarios_page():
    return render_template("usuarios.html", role_labels=ROLE_LABELS)


@bp.route("/api/usuarios")
@role_required("admin")
def api_usuarios():
    rows = users_service.list_users()
    for row in rows:
        row["created_at_fmt"] = unix_to_readable(row["created_at"])
        row["last_login_fmt"] = unix_to_readable(row["last_login"]) if row["last_login"] else "Nunca"
    return jsonify({"results": rows})


@bp.route("/api/usuarios", methods=["POST"])
@role_required("admin")
def api_crear_usuario():
    data = request.get_json(silent=True) or {}
    try:
        user_id = users_service.create_user(data.get("username"), data.get("password"), data.get("role"))
    except UserError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "id": user_id})


@bp.route("/api/usuarios/<int:user_id>/rol", methods=["POST"])
@role_required("admin")
def api_cambiar_rol(user_id):
    data = request.get_json(silent=True) or {}
    if user_id == current_user()["id"] and data.get("role") != "admin":
        return jsonify({"error": "No puedes quitarte tu propio rol de administrador."}), 400
    try:
        users_service.update_user_role(user_id, data.get("role"))
    except UserError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


@bp.route("/api/usuarios/<int:user_id>/estado", methods=["POST"])
@role_required("admin")
def api_cambiar_estado(user_id):
    data = request.get_json(silent=True) or {}
    if user_id == current_user()["id"]:
        return jsonify({"error": "No puedes desactivar tu propia cuenta."}), 400
    users_service.set_user_active(user_id, bool(data.get("active")))
    return jsonify({"ok": True})


@bp.route("/api/usuarios/<int:user_id>", methods=["DELETE"])
@role_required("admin")
def api_eliminar_usuario(user_id):
    if user_id == current_user()["id"]:
        return jsonify({"error": "No puedes eliminar tu propia cuenta."}), 400
    if users_service.count_admins() <= 1:
        target = users_service.get_user_by_id(user_id)
        if target and target["role"] == "admin":
            return jsonify({"error": "Debe quedar al menos un administrador activo."}), 400
    users_service.delete_user(user_id)
    return jsonify({"ok": True})


@bp.route("/api/usuarios/<int:user_id>/password", methods=["POST"])
@role_required("admin")
def api_resetear_password(user_id):
    data = request.get_json(silent=True) or {}
    try:
        users_service.change_password(user_id, data.get("password"))
    except UserError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})
