"""
Autenticación y control de acceso por roles.

La WebUI tiene 3 roles con permisos crecientes:
    viewer     -> solo lectura de todas las páginas de consulta
    moderator  -> viewer + consola SQL (solo lectura) + filtros/consultas guardadas
    admin      -> moderator + gestión de subusuarios + cambios de configuración

No se usa Flask-Login para no sumar una dependencia más: la sesión de
Flask (firmada con SECRET_KEY) ya es suficiente para este caso de uso.
"""

from functools import wraps

from flask import jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

ROLE_LEVELS = {"viewer": 1, "moderator": 2, "admin": 3}
ROLE_LABELS = {"viewer": "Solo lectura", "moderator": "Moderador", "admin": "Administrador"}

# Endpoints accesibles sin sesión iniciada.
PUBLIC_ENDPOINTS = {"auth.login_page", "auth.login_submit", "static", "health"}


def hash_password(raw_password):
    return generate_password_hash(raw_password)


def verify_password(raw_password, password_hash):
    try:
        return check_password_hash(password_hash, raw_password)
    except (TypeError, ValueError):
        return False


def current_user():
    if "user_id" not in session:
        return None
    return {
        "id": session["user_id"],
        "username": session.get("username"),
        "role": session.get("role"),
        "timezone": session.get("timezone"),
    }


def login_user(user_row):
    session.clear()
    session["user_id"] = user_row["id"]
    session["username"] = user_row["username"]
    session["role"] = user_row["role"]
    session["timezone"] = user_row.get("timezone")
    session.permanent = True


def update_session_timezone(tz_name):
    """Refleja de inmediato un cambio de zona horaria personal sin
    necesidad de volver a iniciar sesión."""
    if "user_id" in session:
        session["timezone"] = tz_name


def logout_user():
    session.clear()


def has_role(min_role):
    role = session.get("role")
    if role not in ROLE_LEVELS:
        return False
    return ROLE_LEVELS[role] >= ROLE_LEVELS.get(min_role, 99)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "No autenticado. Inicia sesión de nuevo."}), 401
            return redirect(url_for("auth.login_page", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(min_role):
    """Exige un rol mínimo (viewer < moderator < admin)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "No autenticado."}), 401
                return redirect(url_for("auth.login_page", next=request.path))
            if not has_role(min_role):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "No tienes permisos suficientes para esta acción."}), 403
                return render_template("errors/403.html"), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
