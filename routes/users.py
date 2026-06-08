# -*- coding: utf-8 -*-
"""CRUD de Usuarios – Blueprint Flask."""
import psycopg2
from flask import Blueprint, jsonify, request
from db.connection import get_connection, return_connection

bp = Blueprint("users", __name__, url_prefix="/usuarios")


@bp.route("", methods=["GET"])
def listar_usuarios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, usuario, nombre_completo, rol, cedula, email, telefono "
            "FROM public.usuarios ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        data = [
            {
                "id": r[0],
                "usuario": r[1],
                "nombre_completo": r[2],
                "rol": r[3],
                "cedula": r[4] if r[4] is not None else "",
                "email": r[5] if r[5] is not None else "",
                "telefono": r[6] if r[6] is not None else "",
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
def crear_usuario():
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario = data.get("usuario")
        nombre_completo = data.get("nombre_completo")
        rol = data.get("rol", "Cliente")
        cedula = data.get("cedula")
        email = data.get("email")
        telefono = data.get("telefono")

        if not usuario or not nombre_completo or not cedula:
            return jsonify({"success": False, "message": "Usuario, nombre_completo y cédula son requeridos"}), 400

        if len(str(cedula)) != 10:
            return jsonify({"success": False, "message": "La cédula debe tener exactamente 10 dígitos"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO public.usuarios (usuario, nombre_completo, rol, cedula, email, telefono)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (usuario, nombre_completo, rol, str(cedula), email, telefono),
        )
        nuevo_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"success": True, "message": "Usuario registrado exitosamente", "id": nuevo_id}), 201
    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "message": "La cédula o el usuario ya se encuentran registrados"}), 400
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("/<int:id>", methods=["PUT"])
def actualizar_usuario(id):
    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        usuario = data.get("usuario")
        nombre_completo = data.get("nombre_completo")
        rol = data.get("rol")
        cedula = data.get("cedula")
        email = data.get("email")
        telefono = data.get("telefono")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE public.usuarios
            SET usuario = COALESCE(%s, usuario),
                nombre_completo = COALESCE(%s, nombre_completo),
                rol = COALESCE(%s, rol),
                cedula = COALESCE(%s, cedula),
                email = COALESCE(%s, email),
                telefono = COALESCE(%s, telefono)
            WHERE id = %s
            """,
            (usuario, nombre_completo, rol, cedula, email, telefono, id),
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Usuario {id} actualizado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)


@bp.route("/<int:id>", methods=["DELETE"])
def eliminar_usuario(id):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM public.usuarios WHERE id = %s", (id,))
        conn.commit()
        return jsonify({"success": True, "message": f"Usuario {id} eliminado"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)
