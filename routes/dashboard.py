from flask import Blueprint, jsonify, render_template

from database import DatabaseNotConfigured, check_connection
from services import dashboard as dashboard_service
from services import stats
from utils.formatting import unix_to_readable
from utils.security import login_required

bp = Blueprint("dashboard", __name__)


def _fmt_rows(rows):
    for row in rows:
        row["fecha"] = unix_to_readable(row.get("time"))
    return rows


@bp.route("/")
@login_required
def dashboard():
    ok, message, latency_ms = check_connection()
    status_label = f"🟢 {message}" if ok else f"🔴 {message}"

    overview = None
    type_breakdown = []
    if ok:
        try:
            overview = stats.get_overview()
            type_breakdown = stats.get_type_breakdown(limit=6)
        except DatabaseNotConfigured:
            pass

    return render_template(
        "dashboard.html",
        status=status_label,
        connected=ok,
        latency_ms=latency_ms,
        overview=overview,
        type_breakdown=type_breakdown,
    )


@bp.route("/api/dashboard/actividad-reciente")
@login_required
def api_actividad_reciente():
    rows = dashboard_service.get_recent_activity(limit=15)
    return jsonify({"results": _fmt_rows(rows)})


@bp.route("/api/dashboard/jugadores-activos")
@login_required
def api_jugadores_activos():
    rows = dashboard_service.get_active_players_today(limit=8)
    return jsonify({"results": rows})


@bp.route("/api/dashboard/bloques-modificados")
@login_required
def api_bloques_modificados():
    rows = dashboard_service.get_most_modified_blocks_today(limit=8)
    return jsonify({"results": rows})


@bp.route("/api/dashboard/explosiones")
@login_required
def api_explosiones():
    rows = dashboard_service.get_latest_explosions(limit=8)
    return jsonify({"results": _fmt_rows(rows)})


@bp.route("/api/dashboard/muertes")
@login_required
def api_muertes():
    rows = dashboard_service.get_latest_deaths(limit=8)
    return jsonify({"results": _fmt_rows(rows)})


@bp.route("/api/dashboard/eventos-importantes")
@login_required
def api_eventos_importantes():
    rows = dashboard_service.get_important_events(limit=10)
    return jsonify({"results": _fmt_rows(rows)})


@bp.route("/api/dashboard/resumen")
@login_required
def api_resumen():
    overview = stats.get_overview()
    overview["today_calendar"] = dashboard_service.get_today_calendar_count()
    overview["last_event_time_fmt"] = unix_to_readable(overview.get("last_event_time"))
    return jsonify(overview)
