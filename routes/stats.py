from flask import Blueprint, jsonify, render_template

from services import stats as stats_service

bp = Blueprint("stats", __name__)


@bp.route("/estadisticas")
def estadisticas_page():
    return render_template("estadisticas.html")


@bp.route("/api/estadisticas/overview")
def api_overview():
    return jsonify(stats_service.get_overview())


@bp.route("/api/estadisticas/tipos")
def api_tipos():
    return jsonify(stats_service.get_type_breakdown())


@bp.route("/api/estadisticas/mundos")
def api_mundos():
    return jsonify(stats_service.get_world_breakdown())


@bp.route("/api/estadisticas/top-jugadores")
def api_top_jugadores():
    return jsonify(stats_service.get_top_players())


@bp.route("/api/estadisticas/actividad")
def api_actividad():
    return jsonify(stats_service.get_activity_timeseries())
