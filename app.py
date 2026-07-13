from flask import Flask, render_template
from database import get_connection, get_total_records

app = Flask(__name__)

def get_status():
    try:
        conn = get_connection()
        conn.close()
        return "🟢 Base de datos conectada"
    except Exception as e:
        return f"🔴 Error de conexión: {e}"

@app.route("/")
def dashboard():
    status=get_status()
    total=None
    if status.startswith("🟢"):
        total=get_total_records()
    return render_template("dashboard.html", status=status, total=total)

@app.route("/registros")
def registros():
    return render_template("registros.html")

@app.route("/jugadores")
def jugadores():
    return render_template("jugadores.html")

@app.route("/bloques")
def bloques():
    return render_template("bloques.html")

@app.route("/coordenadas")
def coordenadas():
    return render_template("coordenadas.html")

@app.route("/estadisticas")
def estadisticas():
    return render_template("estadisticas.html")

@app.route("/configuracion")
def configuracion():
    return render_template("configuracion.html")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
