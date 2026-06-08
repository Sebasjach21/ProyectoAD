# -*- coding: utf-8 -*-
"""CRUD de Compras – Blueprint Flask."""
from flask import Blueprint, jsonify, request
from db.connection import get_connection, return_connection

bp = Blueprint("purchases", __name__, url_prefix="/compras")


@bp.route("", methods=["GET"])
def listar_compras():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT compra_id, usuario_id, producto_id, cantidad, total, fecha_compra "
            "FROM public.compras ORDER BY fecha_compra DESC"
        )
        rows = cursor.fetchall()
        data = [
            {
                "compra_id": r[0],
                "usuario_id": r[1],
                "producto_id": str(r[2]) if r[2] is not None else "PRODUCTO_ELIMINADO",
                "cantidad": r[3],
                "total": float(r[4]) if r[4] is not None else 0.0,
                "fecha_compra": r[5].isoformat() if r[5] else None,
            }
            for r in rows
        ]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("", methods=["POST"])
def registrar_compra():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario_id = data.get("usuario_id")
        producto_id = data.get("producto_id")
        cantidad = data.get("cantidad")
        total = data.get("total")

        if not usuario_id or not producto_id or not cantidad or total is None:
            return jsonify({"success": False, "message": "Faltan campos obligatorios"}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Verificar stock con bloqueo de fila
        cursor.execute(
            "SELECT stock FROM public.productos WHERE producto_id = %s FOR UPDATE",
            (producto_id,),
        )
        res = cursor.fetchone()
        if not res:
            return jsonify({"success": False, "message": "El producto no existe"}), 404

        stock_actual = res[0]
        if stock_actual < cantidad:
            return jsonify({"success": False, "message": f"Stock insuficiente. Disponible: {stock_actual}"}), 400

        # Reducir stock e insertar compra
        cursor.execute(
            "UPDATE public.productos SET stock = stock - %s WHERE producto_id = %s",
            (cantidad, producto_id),
        )
        cursor.execute(
            "INSERT INTO public.compras (usuario_id, producto_id, cantidad, total, fecha_compra) "
            "VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC') RETURNING compra_id",
            (usuario_id, producto_id, cantidad, total),
        )
        nueva_compra_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"success": True, "message": "Compra registrada con éxito", "compra_id": nueva_compra_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)
