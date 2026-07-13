from flask import Flask, render_template
from database import get_connection,get_total_records

app=Flask(__name__)

@app.route("/")
def index():
    try:
        conn=get_connection()
        conn.close()
        status="🟢 Base de datos conectada"
        total=get_total_records()
    except Exception as e:
        status=f"🔴 Error de conexión: {e}"
        total=None
    return render_template("index.html",status=status,total=total)

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
