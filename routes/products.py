# -*- coding: utf-8 -*-
"""CRUD de Productos – Blueprint Flask."""
from flask import Blueprint, jsonify, request
from db.connection import get_connection, return_connection

bp = Blueprint("products", __name__, url_prefix="/productos")

# Datos mock en caso de error de BD
PRODUCTOS_MOCK = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "nombre": "Laptop Gaming ASUS ROG",
        "precio": 1299.99,
        "imagen_url": "https://via.placeholder.com/300?text=Laptop+Gaming",
        "stock": 10,
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "nombre": 'Monitor UltraWide 34" LG',
        "precio": 549.99,
        "imagen_url": "https://via.placeholder.com/300?text=Monitor",
        "stock": 25,
    },
]


@bp.route("", methods=["GET"])
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT producto_id, nombre_producto, precio, imagen_url, stock "
            "FROM public.productos ORDER BY nombre_producto ASC"
        )
        rows = cursor.fetchall()
        data = [
            {
                "id": str(r[0]),
                "nombre": r[1],
                "precio": float(r[2]) if r[2] is not None else 0.0,
                "imagen_url": r[3],
                "stock": r[4],
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})
    except Exception:
        return jsonify({"success": True, "data": PRODUCTOS_MOCK, "warning": "Usando datos Mock."})
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("", methods=["POST"])
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
        cursor.execute(
            "INSERT INTO public.productos (nombre_producto, precio, imagen_url, stock, version) "
            "VALUES (%s, %s, %s, %s, 1) RETURNING producto_id",
            (nombre, precio, imagen_url, stock),
        )
        nuevo_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"success": True, "message": "Producto creado exitosamente", "id": str(nuevo_id)}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("/<string:id>", methods=["PUT"])
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
        cursor.execute(
            "UPDATE public.productos SET nombre_producto = COALESCE(%s, nombre_producto), "
            "precio = COALESCE(%s, precio), imagen_url = COALESCE(%s, imagen_url), "
            "stock = COALESCE(%s, stock), version = version + 1 WHERE producto_id = %s",
            (nombre, precio, imagen_url, stock, id),
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Producto {id} actualizado"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("/<string:id>", methods=["DELETE"])
def eliminar_producto(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM public.productos WHERE producto_id = %s", (id,))
        conn.commit()
        return jsonify({"success": True, "message": "Producto eliminado. Las compras mantienen su ID original."})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)
