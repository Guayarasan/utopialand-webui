import os


def _env_bool(name, default=False):
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Base de datos (Aiven MySQL) ---
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_TABLE = os.getenv("DB_TABLE", "LOGDATA")

    # SSL: Aiven exige TLS. Si se provee un certificado vía variable de
    # entorno o archivo montado, se usa; si no, se habilita TLS "laxo".
    DB_SSL_CA = os.getenv("DB_SSL_CA")  # ruta a ca.pem, opcional

    # --- Pool de conexiones ---
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_POOL_MIN_CACHED = int(os.getenv("DB_POOL_MIN_CACHED", "2"))
    DB_POOL_MAX_CACHED = int(os.getenv("DB_POOL_MAX_CACHED", "5"))
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

    # --- Paginación ---
    DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "200"))

    # --- Caché en memoria (para agregados costosos) ---
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
    CACHE_TTL_LONG_SECONDS = int(os.getenv("CACHE_TTL_LONG_SECONDS", "300"))

    # --- Exportación ---
    EXPORT_MAX_ROWS = int(os.getenv("EXPORT_MAX_ROWS", "100000"))

    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "utopialand-dev-secret-change-me")
    DEBUG = _env_bool("FLASK_DEBUG", False)
    ENV = os.getenv("FLASK_ENV", "production")

    # --- Autenticación ---
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # si no se define, se genera al azar (ver logs)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_SECONDS", str(60 * 60 * 12)))

    # --- Consola SQL ---
    SQL_CONSOLE_MAX_ROWS = int(os.getenv("SQL_CONSOLE_MAX_ROWS", "1000"))
    SQL_CONSOLE_TIMEOUT_SECONDS = int(os.getenv("SQL_CONSOLE_TIMEOUT_SECONDS", "10"))

    # --- App info ---
    APP_NAME = "Utopialand WebUI"
    APP_VERSION = "2.0.0"

    @classmethod
    def is_db_configured(cls):
        return all([cls.DB_HOST, cls.DB_NAME, cls.DB_USER, cls.DB_PASSWORD])
