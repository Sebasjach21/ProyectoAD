import os
import threading
import requests
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def enviar_correo_resend(destino, asunto, mensaje):
    """Envía correo usando Resend REST API (Punto 12 - Notificaciones)."""
    resend_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("MAIL_RESEND", "onboarding@resend.dev")
    
    if not resend_key:
        raise ValueError("Falta RESEND_API_KEY")
    
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": from_email,
        "to": destino,
        "subject": asunto,
        "html": f"<p>{mensaje}</p>"
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    if resp.status_code not in (200, 201):
        raise ValueError(f"Error Resend {resp.status_code}: {resp.text}")
    return resp.json()

def get_connection():
    """Conexión limpia a Supabase usando la URI del Shared Pooler."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("Falta la variable de entorno DATABASE_URL")
    return psycopg2.connect(db_url)

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API de Notificaciones y Productos (Supabase) corriendo en Render"
    })

@app.route("/enviar-alerta", methods=["POST"])
def enviar_alerta():
    try:
        data = request.get_json(silent=True) or {}
        destino = data.get("to") or data.get("email")
        asunto = data.get("subject")
        mensaje = data.get("message")

        if not destino or not asunto or not mensaje:
            return jsonify({"success": False, "message": "Faltan datos"}), 400

        result = enviar_correo_resend(destino, asunto, mensaje)
        return jsonify({"success": True, "message": "Correo enviado", "id": result.get("id")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/productos", methods=["GET"])
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Consulta adaptada a la estructura de Postgres que creamos
        cursor.execute("""
            SELECT producto_id, nombre_producto, precio, imagen_url, stock
            FROM public.productos
            ORDER BY nombre_producto ASC
            LIMIT 20
        """)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": str(row[0]),
                "nombre": row[1],
                "precio": float(row[2]) if row[2] is not None else None,
                "imagen_url": row[3],
                "stock": row[4]
            })

        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": "Error al consultar productos", "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()