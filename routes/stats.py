from flask import Blueprint, jsonify, render_template

from services import stats as stats_service
from utils.formatting import current_utc_offset_sql
from utils.security import login_required

bp = Blueprint("stats", __name__)


@bp.route("/estadisticas")
@login_required
def estadisticas_page():
    return render_template("estadisticas.html")


@bp.route("/api/estadisticas/overview")
@login_required
def api_overview():
    return jsonify(stats_service.get_overview())


@bp.route("/api/estadisticas/tipos")
@login_required
def api_tipos():
    return jsonify(stats_service.get_type_breakdown())


@bp.route("/api/estadisticas/mundos")
@login_required
def api_mundos():
    return jsonify(stats_service.get_world_breakdown())


@bp.route("/api/estadisticas/top-jugadores")
@login_required
def api_top_jugadores():
    return jsonify(stats_service.get_top_players())


@bp.route("/api/estadisticas/top-bloques")
@login_required
def api_top_bloques():
    return jsonify(stats_service.get_top_blocks())


@bp.route("/api/estadisticas/top-entidades")
@login_required
def api_top_entidades():
    return jsonify(stats_service.get_top_entities())


@bp.route("/api/estadisticas/actividad")
@login_required
def api_actividad():
    return jsonify(stats_service.get_activity_timeseries(tz_offset=current_utc_offset_sql()))


@bp.route("/api/estadisticas/actividad-horaria")
@login_required
def api_actividad_horaria():
    return jsonify(stats_service.get_hourly_activity(tz_offset=current_utc_offset_sql()))


@bp.route("/api/estadisticas/heatmap")
@login_required
def api_heatmap():
    return jsonify(stats_service.get_heatmap(tz_offset=current_utc_offset_sql()))
