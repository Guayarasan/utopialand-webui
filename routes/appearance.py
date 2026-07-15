from flask import Blueprint, jsonify, render_template, request

from services import appearance as appearance_service
from utils.security import current_user, login_required

bp = Blueprint("appearance", __name__)


@bp.route("/apariencia")
@login_required
def apariencia_page():
    settings = appearance_service.get_settings(current_user()["id"])
    return render_template(
        "apariencia.html",
        settings=settings,
        font_options=appearance_service.FONT_OPTIONS,
        radius_options=list(appearance_service.RADIUS_PRESETS.keys()),
        density_options=list(appearance_service.DENSITY_PRESETS.keys()),
        speed_options=list(appearance_service.ANIM_SPEED_MULT.keys()),
    )


@bp.route("/api/apariencia")
@login_required
def api_obtener_apariencia():
    return jsonify(appearance_service.get_settings(current_user()["id"]))


@bp.route("/api/apariencia", methods=["POST"])
@login_required
def api_guardar_apariencia():
    data = request.get_json(silent=True) or {}
    clean = appearance_service.save_settings(current_user()["id"], data)
    return jsonify({"ok": True, "settings": clean})


@bp.route("/api/apariencia/reset", methods=["POST"])
@login_required
def api_reset_apariencia():
    clean = appearance_service.reset_settings(current_user()["id"])
    return jsonify({"ok": True, "settings": clean})
