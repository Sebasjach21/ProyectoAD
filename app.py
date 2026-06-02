import os
import requests
import psycopg2
from psycopg2 import pool
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)

# Configuración global y abierta de CORS
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# ✅ MEJORA 1: Connection Pool para producción
# Evita agotamiento de conexiones en Render
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("Falta la variable de entorno DATABASE_URL")

db_pool = pool.SimpleConnectionPool(1, 20, db_url)  # Min 1, Max 20 conexiones

def get_connection():
    """Obtiene conexión del pool. Más eficiente que crear cada vez."""
    try:
        return db_pool.getconn()
    except pool.PoolError:
        raise RuntimeError("Pool de conexiones agotado. Demasiadas solicitudes concurrentes.")

def return_connection(conn):
    """Devuelve la conexión al pool."""
    if conn:
        db_pool.putconn(conn)

# ✅ DATOS MOCK (Fallback si Supabase falla)
PRODUCTOS_MOCK = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "nombre": "Laptop Gaming ASUS ROG",
        "precio": 1299.99,
        "imagen_url": "https://via.placeholder.com/300?text=Laptop+Gaming",
        "stock": 10
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "nombre": "Monitor UltraWide 34\" LG",
        "precio": 549.99,
        "imagen_url": "https://via.placeholder.com/300?text=Monitor",
        "stock": 25
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "nombre": "Teclado Mecánico RGB",
        "precio": 129.99,
        "imagen_url": "https://via.placeholder.com/300?text=Teclado",
        "stock": 50
    }
]

def enviar_correo_resend(destino, asunto, mensaje):
    """Envía correo usando Resend REST API."""
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

@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API REST Unificada (CRUD Completo + Auditoría) corriendo exitosamente en Render"
    })

@app.route("/enviar-alerta", methods=["POST"])
def enviar_alerta():
    try:
        data = request.get_json(silent=True) or {}
        destino = data.get("to") or data.get("email")
        asunto = data.get("subject")
        mensaje = data.get("message")

        if not destino or not asunto or not mensaje:
            return jsonify({"success": False, "message": "Faltan datos obligatorios"}), 400

        result = enviar_correo_resend(destino, asunto, mensaje)
        return jsonify({"success": True, "message": "Correo enviado", "id": result.get("id")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# 📦 CRUD: MÓDULO DE PRODUCTOS (MEJORADO)
# ==========================================

@app.route("/productos", methods=["GET"])
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT producto_id, nombre_producto, precio, imagen_url, stock FROM public.productos ORDER BY nombre_producto ASC")
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": str(row[0]),
                "nombre": row[1],
                "precio": float(row[2]) if row[2] is not None else 0.0,
                "imagen_url": row[3],
                "stock": row[4]
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        # ✅ MEJORA 2: Fallback a datos Mock si falla Supabase
        print(f"[ERROR] GET /productos falló: {str(e)}. Usando datos Mock.")
        return jsonify({
            "success": True,
            "data": PRODUCTOS_MOCK,
            "warning": "Base de datos no disponible. Mostrando catálogo en caché (Mock)."
        })
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/productos", methods=["POST"])
def crear_producto():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        nombre = data.get("nombre") or data.get("nombre_producto")
        precio = data.get("precio")
        imagen_url = data.get("imagen_url")
        stock = data.get("stock", 0)

        if not nombre or precio is None:
            return jsonify({"success": False, "message": "Nombre y precio son requeridos"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO public.productos (nombre_producto, precio, imagen_url, stock, version)
            VALUES (%s, %s, %s, %s, 1) RETURNING producto_id
        """, (nombre, precio, imagen_url, stock))
        nuevo_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"success": True, "message": "Producto creado exitosamente", "id": str(nuevo_id)}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al crear producto", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/productos/<string:id>", methods=["PUT"])
def actualizar_producto(id):
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        nombre = data.get("nombre")
        precio = data.get("precio")
        imagen_url = data.get("imagen_url")
        stock = data.get("stock")

        conn = get_connection()
        cursor = conn.cursor()

        # ✅ MEJORA 3: Validar que el producto existe antes de actualizar
        cursor.execute("SELECT producto_id FROM public.productos WHERE producto_id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": f"Producto {id} no encontrado"}), 404

        cursor.execute("""
            UPDATE public.productos 
            SET nombre_producto = COALESCE(%s, nombre_producto),
                precio = COALESCE(%s, precio),
                imagen_url = COALESCE(%s, imagen_url),
                stock = COALESCE(%s, stock),
                version = version + 1
            WHERE producto_id = %s
        """, (nombre, precio, imagen_url, stock, id))
        conn.commit()

        return jsonify({"success": True, "message": f"Producto {id} actualizado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al actualizar producto", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/productos/<string:id>", methods=["DELETE"])
def eliminar_producto(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM public.productos WHERE producto_id = %s", (id,))
        rows_deleted = cursor.rowcount
        conn.commit()

        if rows_deleted == 0:
            return jsonify({"success": False, "message": f"Producto {id} no encontrado"}), 404

        return jsonify({"success": True, "message": f"Producto {id} eliminado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al eliminar producto", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


# ==========================================
# 👥 CRUD: MÓDULO DE USUARIOS (MEJORADO)
# ==========================================

@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, usuario, nombre_completo, rol FROM public.usuarios ORDER BY id ASC")
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "usuario": row[1],
                "nombre_completo": row[2],
                "rol": row[3]
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": "Error al obtener usuarios", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/usuarios", methods=["POST"])
def crear_usuario():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario = data.get("usuario")  # correo electrónico
        nombre_completo = data.get("nombre_completo")
        rol = data.get("rol", "Cliente")

        if not usuario or not nombre_completo:
            return jsonify({"success": False, "message": "Usuario (email) y nombre_completo requeridos"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO public.usuarios (usuario, nombre_completo, rol)
            VALUES (%s, %s, %s) RETURNING id
        """, (usuario, nombre_completo, rol))
        nuevo_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"success": True, "message": "Usuario registrado localmente", "id": nuevo_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al guardar usuario", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/usuarios/<int:id>", methods=["PUT"])
def actualizar_usuario(id):
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        nombre_completo = data.get("nombre_completo")
        rol = data.get("rol")

        conn = get_connection()
        cursor = conn.cursor()

        # ✅ MEJORA: Validar que el usuario existe
        cursor.execute("SELECT id FROM public.usuarios WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": f"Usuario {id} no encontrado"}), 404

        cursor.execute("""
            UPDATE public.usuarios 
            SET nombre_completo = COALESCE(%s, nombre_completo),
                rol = COALESCE(%s, rol)
            WHERE id = %s
        """, (nombre_completo, rol, id))
        conn.commit()

        return jsonify({"success": True, "message": f"Usuario {id} actualizado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al actualizar usuario", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/usuarios/<int:id>", methods=["DELETE"])
def eliminar_usuario(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM public.usuarios WHERE id = %s", (id,))
        rows_deleted = cursor.rowcount
        conn.commit()

        if rows_deleted == 0:
            return jsonify({"success": False, "message": f"Usuario {id} no encontrado"}), 404

        return jsonify({"success": True, "message": f"Usuario {id} eliminado de la base local"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "Error al eliminar usuario", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


# ==========================================
# 🛍️ CRUD: MÓDULO DE COMPRAS (MEJORADO - CRÍTICO)
# ==========================================

@app.route("/compras", methods=["GET"])
def listar_compras():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT compra_id, usuario_id, producto_id, cantidad, total, fecha_compra FROM public.compras ORDER BY fecha_compra DESC")
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "compra_id": row[0],
                "usuario_id": row[1],
                "producto_id": str(row[2]),
                "cantidad": row[3],
                "total": float(row[4]) if row[4] is not None else 0.0,
                "fecha_compra": row[5].isoformat() if row[5] else None
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "message": "Error al obtener compras", "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/compras", methods=["POST"])
def registrar_compra():
    """
    ✅ MEJORAS CRÍTICAS:
    1. SELECT ... FOR UPDATE (evita race condition)
    2. Valida usuario existe
    3. Valida producto existe
    4. Descuenta stock atómicamente
    5. UTC timezone explícito
    6. Rollback completo si algo falla
    """
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        producto_id = data.get("producto_id")
        cantidad = data.get("cantidad")
        total = data.get("total")

        if not usuario_id or not producto_id or not cantidad or total is None:
            return jsonify({"success": False, "message": "Faltan campos obligatorios para procesar el pedido"}), 400

        if cantidad <= 0:
            return jsonify({"success": False, "message": "La cantidad debe ser mayor a 0"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # ✅ MEJORA 4: Validar que el usuario existe
        cursor.execute("SELECT id FROM public.usuarios WHERE id = %s", (usuario_id,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": f"Usuario {usuario_id} no encontrado"}), 404

        # ✅ MEJORA 5: Lock pesimista con SELECT ... FOR UPDATE
        # Esto evita que dos transacciones simultáneas descuenten el mismo stock
        cursor.execute(
            "SELECT stock FROM public.productos WHERE producto_id = %s FOR UPDATE",
            (producto_id,)
        )
        res = cursor.fetchone()
        if not res:
            return jsonify({"success": False, "message": "El producto seleccionado no existe"}), 404

        stock_actual = res[0]
        if stock_actual < cantidad:
            return jsonify({
                "success": False,
                "message": f"Stock insuficiente. Disponible: {stock_actual}, Solicitado: {cantidad}"
            }), 400

        # ✅ MEJORA 6: Descontar stock (dentro del lock)
        cursor.execute(
            "UPDATE public.productos SET stock = stock - %s WHERE producto_id = %s",
            (cantidad, producto_id)
        )

        # ✅ MEJORA 7: UTC timezone explícito en NOW()
        cursor.execute("""
            INSERT INTO public.compras (usuario_id, producto_id, cantidad, total, fecha_compra)
            VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC') RETURNING compra_id
        """, (usuario_id, producto_id, cantidad, total))
        nueva_compra_id = cursor.fetchone()[0]

        conn.commit()
        return jsonify({
            "success": True,
            "message": "Compra registrada con éxito",
            "compra_id": nueva_compra_id
        }), 201
    except Exception as e:
        # ✅ MEJORA 8: Rollback automático si algo falla
        if conn:
            conn.rollback()
        return jsonify({
            "success": False,
            "message": "Error al procesar la transacción de compra",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

@app.route("/compras/<int:id>", methods=["DELETE"])
def cancelar_compra(id):
    """
    ✅ MEJORA 9: Al cancelar, RESTAURAR el stock del producto
    Mantiene integridad de datos.
    """
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Obtener detalles de la compra
        cursor.execute(
            "SELECT producto_id, cantidad FROM public.compras WHERE compra_id = %s",
            (id,)
        )
        compra = cursor.fetchone()
        if not compra:
            return jsonify({"success": False, "message": f"Compra {id} no encontrada"}), 404

        producto_id, cantidad = compra

        # 2. Restaurar stock
        cursor.execute(
            "UPDATE public.productos SET stock = stock + %s WHERE producto_id = %s",
            (cantidad, producto_id)
        )

        # 3. Eliminar compra
        cursor.execute("DELETE FROM public.compras WHERE compra_id = %s", (id,))

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"Compra {id} cancelada y stock restaurado"
        })
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "success": False,
            "message": "Error al cancelar la compra",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


# ==========================================
# 🔧 ENDPOINT DE SALUD (Health Check)
# ==========================================

@app.route("/health", methods=["GET"])
def health():
    """Verifica que la base de datos está accesible."""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "database": "disconnected", "error": str(e)}), 503
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
