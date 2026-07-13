import logging

from flask import Flask, jsonify

from config import Config
from database import DatabaseNotConfigured, check_connection
from utils.formatting import format_number, unix_to_readable


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Filtros Jinja reutilizables en todas las plantillas.
    app.jinja_env.filters["fecha"] = unix_to_readable
    app.jinja_env.filters["miles"] = format_number

    register_blueprints(app)
    register_error_handlers(app)

    @app.route("/api/health")
    def health():
        ok, message, latency_ms = check_connection()
        return jsonify({
            "status": "ok" if ok else "error",
            "database": message,
            "latency_ms": latency_ms,
            "version": Config.APP_VERSION,
        }), (200 if ok else 503)

    return app


def register_blueprints(app):
    from routes.dashboard import bp as dashboard_bp
    from routes.records import bp as records_bp
    from routes.players import bp as players_bp
    from routes.blocks import bp as blocks_bp
    from routes.coordinates import bp as coordinates_bp
    from routes.stats import bp as stats_bp
    from routes.config import bp as config_bp

    for bp in (dashboard_bp, records_bp, players_bp, blocks_bp, coordinates_bp, stats_bp, config_bp):
        app.register_blueprint(bp)


def register_error_handlers(app):
    @app.errorhandler(DatabaseNotConfigured)
    def handle_db_not_configured(exc):
        return jsonify({"error": str(exc)}), 503

    @app.errorhandler(404)
    def handle_404(exc):
        if _wants_json():
            return jsonify({"error": "No encontrado"}), 404
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def handle_500(exc):
        app.logger.exception("Error interno")
        if _wants_json():
            return jsonify({"error": "Error interno del servidor"}), 500
        from flask import render_template
        return render_template("errors/500.html"), 500


def _wants_json():
    from flask import request
    return request.path.startswith("/api/")


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
