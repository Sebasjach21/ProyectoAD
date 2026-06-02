import os
import threading
import requests
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# Habilitamos CORS de forma global y abierta para peticiones OPTIONS preflight de React/Flutter
CORS(app, resources={r"/*": {"origins": "*"}})

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
        "message": "API Unificada de Productos, Usuarios y Compras corriendo en Render"
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

        # Fallback: Si la tabla está vacía en Supabase, mandamos mocks para que React funcione
        if not data:
            data = [
                {"id": "916519d8-4a99-458e-b87e-f9553c4f0a7d", "nombre": "iPhone 15 Pro", "precio": 999.99, "stock": 48, "imagen_url": "https://example.com/iphone15pro.jpg"},
                {"id": "1b36c90c-a5ea-4b5f-ae4a-0d6aa3c27164", "nombre": "iPhone 17 Pro", "precio": 999.99, "stock": 50, "imagen_url": "https://example.com/iphone17pro.jpg"}
            ]

        return jsonify({"success": True, "data": data})
    except Exception as e:
        # En caso de error de red, devolvemos los datos mock de respaldo
        data_mock = [
            {"id": "916519d8-4a99-458e-b87e-f9553c4f0a7d", "nombre": "iPhone 15 Pro (Fallback)", "precio": 999.99, "stock": 48, "imagen_url": "https://example.com/iphone15pro.jpg"}
        ]
        return jsonify({"success": True, "data": data_mock, "note": "Datos mock por error de BD", "error": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 👥 NUEVO ENDPOINT: Listar Usuarios locales
@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Ajusta los nombres de las columnas según tu tabla local de usuarios si es necesario
        cursor.execute("SELECT id, usuario, nombre_completo, rol FROM public.usuarios LIMIT 20")
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "usuario": row[1],
                "nombre_completo": row[2],
                "rol": row[3]
            })
            
        if not data:
            data = [
                {"id": 1, "usuario": "sebas@uta.edu.ec", "nombre_completo": "Sebas Jacho", "rol": "Admin"}
            ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        data_mock = [{"id": 1, "usuario": "admin@test.com", "nombre_completo": "Usuario de Prueba", "rol": "Admin"}]
        return jsonify({"success": True, "data": data_mock, "note": "Datos mock por error de BD", "error": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# 🛍️ NUEVO ENDPOINT: Ver Historial de Compras
@app.route("/compras", methods=["GET"])
def listar_compras():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT compra_id, usuario_id, producto_id, cantidad, total FROM public.compras LIMIT 20")
        rows = cursor.fetchall()
        
        data = []
        for row in rows:
            data.append({
                "compra_id": row[0],
                "usuario_id": row[1],
                "producto_id": str(row[2]),
                "cantidad": row[3],
                "total": float(row[4]) if row[4] is not None else 0.0
            })
            
        if not data:
            data = [
                {"compra_id": 101, "usuario_id": 1, "producto_id": "916519d8-4a99-458e-b87e-f9553c4f0a7d", "cantidad": 1, "total": 999.99}
            ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        data_mock = [{"compra_id": 101, "usuario_id": 1, "producto_id": "916519d8-4a99-458e-b87e-f9553c4f0a7d", "cantidad": 1, "total": 999.99}]
        return jsonify({"success": True, "data": data_mock, "note": "Datos mock por error de BD", "error": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()