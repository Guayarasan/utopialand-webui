from flask import Flask, render_template
from database import get_connection

app = Flask(__name__)


@app.route("/")
def index():
    try:
        conn = get_connection()
        conn.close()
        status = "🟢 Base de datos conectada"
    except Exception as e:
        status = f"🔴 Error de conexión: {e}"

    return render_template("index.html", status=status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
