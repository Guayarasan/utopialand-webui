from flask import Blueprint, render_template

from database import DatabaseNotConfigured, check_connection
from services import stats
from utils.security import login_required

bp = Blueprint("dashboard", __name__)


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
