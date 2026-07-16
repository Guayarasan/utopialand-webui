import logging

from flask import Flask, g, jsonify, redirect, request, session, url_for

from config import Config
from database import DatabaseNotConfigured, check_connection
from services.admin_db import ensure_bootstrapped
from utils.formatting import format_number, unix_to_readable
from utils.security import PUBLIC_ENDPOINTS, current_user


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

    @app.context_processor
    def inject_current_user():
        return {"current_user": current_user()}

    @app.context_processor
    def inject_appearance():
        from services import appearance as appearance_service
        user = current_user()
        try:
            settings = appearance_service.get_settings(user["id"]) if user else dict(appearance_service.DEFAULTS)
        except Exception:  # noqa: BLE001 -- nunca romper el render por esto (DB aún no lista, etc.)
            settings = dict(appearance_service.DEFAULTS)
        return {"appearance": settings, "appearance_css_vars": appearance_service.css_variables(settings)}

    register_blueprints(app)
    register_error_handlers(app)

    @app.before_request
    def bootstrap_and_gate():
        # Crea (si hace falta) las tablas propias de la WebUI y el admin inicial.
        ensure_bootstrapped()

        endpoint = request.endpoint or ""
        if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith("static"):
            return None
        if "user_id" in session:
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "No autenticado. Inicia sesión de nuevo."}), 401
        return redirect(url_for("auth.login_page", next=request.path))

    @app.before_request
    def resolve_timezone():
        # Se resuelve una sola vez por petición y queda disponible para
        # utils.formatting.unix_to_readable (y por tanto para el filtro
        # Jinja `fecha`) sin tener que tocar cada punto de la app que
        # formatea una fecha.
        if request.endpoint == "static":
            return None
        from services import timezone_settings
        g.tz_name = timezone_settings.get_effective_timezone(current_user())

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
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.records import bp as records_bp
    from routes.players import bp as players_bp
    from routes.blocks import bp as blocks_bp
    from routes.coordinates import bp as coordinates_bp
    from routes.stats import bp as stats_bp
    from routes.config import bp as config_bp
    from routes.users import bp as users_bp
    from routes.sql_console import bp as sql_bp
    from routes.alerts import bp as alerts_bp
    from routes.appearance import bp as appearance_bp
    from routes.investigation import bp as investigation_bp

    blueprints = (
        auth_bp, dashboard_bp, records_bp, players_bp, blocks_bp,
        coordinates_bp, stats_bp, config_bp, users_bp, sql_bp, alerts_bp,
        appearance_bp, investigation_bp,
    )
    for bp in blueprints:
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
