from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from services import users as users_service
from utils.security import current_user, login_required, login_user, logout_user, verify_password

bp = Blueprint("auth", __name__)


@bp.route("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html", next_url=request.args.get("next", ""))


@bp.route("/login", methods=["POST"])
def login_submit():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    next_url = request.form.get("next") or url_for("dashboard.dashboard")

    user = users_service.authenticate(username, password)
    if not user:
        return render_template(
            "login.html",
            error="Usuario o contraseña incorrectos, o la cuenta está desactivada.",
            next_url=next_url,
            prefill_username=username,
        ), 401

    login_user(user)
    users_service.touch_last_login(user["id"])

    if not next_url.startswith("/"):
        next_url = url_for("dashboard.dashboard")
    return redirect(next_url)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))


@bp.route("/api/auth/cambiar-password", methods=["POST"])
@login_required
def api_change_password():
    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    user_row = users_service.get_user_by_username(current_user()["username"])
    if not user_row or not verify_password(current_password, user_row["password_hash"]):
        return jsonify({"error": "La contraseña actual no es correcta."}), 400

    if len(new_password) < 8:
        return jsonify({"error": "La nueva contraseña debe tener al menos 8 caracteres."}), 400

    users_service.change_password(user_row["id"], new_password)
    return jsonify({"ok": True, "message": "Contraseña actualizada correctamente."})
