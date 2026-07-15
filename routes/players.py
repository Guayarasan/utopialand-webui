from flask import Blueprint, jsonify, render_template, request

from services import players as players_service
from utils.formatting import unix_to_readable

bp = Blueprint("players", __name__)


@bp.route("/jugadores")
def jugadores_page():
    return render_template("jugadores.html")


@bp.route("/api/jugadores")
def api_jugadores():
    rows, total = players_service.get_players(request.args)
    for row in rows:
        row["last_seen_fmt"] = unix_to_readable(row["last_seen"])
        row["first_seen_fmt"] = unix_to_readable(row["first_seen"])
    return jsonify({"results": rows, "total": total})


@bp.route("/api/jugadores/<string:name>")
def api_jugador_detail(name):
    summary = players_service.get_player_summary(name)
    if not summary:
        return jsonify({"error": "Jugador no encontrado"}), 404
    summary["last_seen_fmt"] = unix_to_readable(summary["last_seen"])
    summary["first_seen_fmt"] = unix_to_readable(summary["first_seen"])
    breakdown = players_service.get_player_type_breakdown(name)
    return jsonify({"summary": summary, "breakdown": breakdown})


@bp.route("/api/jugadores/<string:name>/actividad")
def api_jugador_actividad(name):
    rows = players_service.get_player_activity(name, request.args)
    for row in rows:
        row["fecha"] = unix_to_readable(row["time"])
    return jsonify({"results": rows})


@bp.route("/api/jugadores/<string:name>/ficha")
def api_jugador_ficha(name):
    """Datos completos para la ficha enriquecida: series temporales,
    rankings de bloques/entidades, mundos y zonas frecuentes."""
    summary = players_service.get_player_summary(name)
    if not summary:
        return jsonify({"error": "Jugador no encontrado"}), 404
    summary["last_seen_fmt"] = unix_to_readable(summary["last_seen"])
    summary["first_seen_fmt"] = unix_to_readable(summary["first_seen"])

    return jsonify({
        "summary": summary,
        "daily": players_service.get_player_daily_activity(name, days=30),
        "hourly": players_service.get_player_hourly_activity(name),
        "top_broken": players_service.get_player_top_blocks(name, "block_break", limit=8),
        "top_placed": players_service.get_player_top_blocks(name, "block_place", limit=8),
        "entities_attacked": players_service.get_player_entities_attacked(name, limit=8),
        "worlds": players_service.get_player_worlds(name),
        "frequent_coords": players_service.get_player_frequent_coords(name, limit=8),
        "timeline": [
            {**row, "fecha": unix_to_readable(row["time"])}
            for row in players_service.get_player_activity(name, request.args, limit=20)
        ],
    })
