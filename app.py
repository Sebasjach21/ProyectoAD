import os
import psycopg2
from psycopg2 import pool
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from datetime import datetime

# Importamos la lógica SOAP
from soap_logic import procesar_soap_facturacion

app = Flask(__name__)

# Configuración global de CORS
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

# ==========================================
# 📦 CONEXIÓN A SUPABASE (POOL)
# ==========================================
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise ValueError("Falta la variable de entorno DATABASE_URL")

db_pool = pool.SimpleConnectionPool(1, 20, db_url)

def get_connection():
    try:
        return db_pool.getconn()
    except pool.PoolError:
        raise RuntimeError("Pool de conexiones agotado.")

def return_connection(conn):
    if conn:
        db_pool.putconn(conn)

# Datos mock para productos (en caso de error de BD)
PRODUCTOS_MOCK = [
    {"id": "00000000-0000-0000-0000-000000000001", "nombre": "Laptop Gaming ASUS ROG", "precio": 1299.99, "imagen_url": "https://via.placeholder.com/300?text=Laptop+Gaming", "stock": 10},
    {"id": "00000000-0000-0000-0000-000000000002", "nombre": "Monitor UltraWide 34\" LG", "precio": 549.99, "imagen_url": "https://via.placeholder.com/300?text=Monitor", "stock": 25}
]

# ==========================================
# 🧾 SERVICIO SOAP DE FACTURACIÓN
# ==========================================

WSDL_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<definitions name="FacturacionService"
    targetNamespace="uta.edu.ec.facturacion"
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="uta.edu.ec.facturacion"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema">

    <types>
        <xsd:schema targetNamespace="uta.edu.ec.facturacion">
            <xsd:element name="ValidarFactura">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="xmlFactura" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="ValidarFacturaResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="estado" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="GenerarFacturaXML">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="idCompra" type="xsd:string"/>
                        <xsd:element name="cliente" type="xsd:string"/>
                        <xsd:element name="correo" type="xsd:string"/>
                        <xsd:element name="telefono" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="GenerarFacturaXMLResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="xmlGenerado" type="xsd:anyType"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="ConsultarComprobante">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="idCompra" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
            <xsd:element name="ConsultarComprobanteResponse">
                <xsd:complexType>
                    <xsd:sequence>
                        <xsd:element name="estado" type="xsd:string"/>
                    </xsd:sequence>
                </xsd:complexType>
            </xsd:element>
        </xsd:schema>
    </types>

    <message name="ValidarFacturaRequest">
        <part name="parameters" element="tns:ValidarFactura"/>
    </message>
    <message name="ValidarFacturaResponseMsg">
        <part name="parameters" element="tns:ValidarFacturaResponse"/>
    </message>
    <message name="GenerarFacturaXMLRequest">
        <part name="parameters" element="tns:GenerarFacturaXML"/>
    </message>
    <message name="GenerarFacturaXMLResponseMsg">
        <part name="parameters" element="tns:GenerarFacturaXMLResponse"/>
    </message>
    <message name="ConsultarComprobanteRequest">
        <part name="parameters" element="tns:ConsultarComprobante"/>
    </message>
    <message name="ConsultarComprobanteResponseMsg">
        <part name="parameters" element="tns:ConsultarComprobanteResponse"/>
    </message>

    <portType name="FacturacionPortType">
        <operation name="ValidarFactura">
            <input message="tns:ValidarFacturaRequest"/>
            <output message="tns:ValidarFacturaResponseMsg"/>
        </operation>
        <operation name="GenerarFacturaXML">
            <input message="tns:GenerarFacturaXMLRequest"/>
            <output message="tns:GenerarFacturaXMLResponseMsg"/>
        </operation>
        <operation name="ConsultarComprobante">
            <input message="tns:ConsultarComprobanteRequest"/>
            <output message="tns:ConsultarComprobanteResponseMsg"/>
        </operation>
    </portType>

    <binding name="FacturacionBinding" type="tns:FacturacionPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <operation name="ValidarFactura">
            <soap:operation soapAction="uta.edu.ec.facturacion/ValidarFactura"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
        <operation name="GenerarFacturaXML">
            <soap:operation soapAction="uta.edu.ec.facturacion/GenerarFacturaXML"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
        <operation name="ConsultarComprobante">
            <soap:operation soapAction="uta.edu.ec.facturacion/ConsultarComprobante"/>
            <input><soap:body use="literal"/></input>
            <output><soap:body use="literal"/></output>
        </operation>
    </binding>

    <service name="FacturacionService">
        <port name="FacturacionPort" binding="tns:FacturacionBinding">
            <soap:address location="https://tu-api.onrender.com/facturacion"/>
        </port>
    </service>
</definitions>
"""

@app.route('/facturacion', methods=['POST', 'GET'])
def soap_endpoint():
    """Endpoint SOAP que sirve el WSDL y procesa las operaciones."""
    if request.method == 'GET' and 'wsdl' in request.args:
        return Response(WSDL_CONTENT, mimetype='text/xml')
    elif request.method == 'POST':
        conn = None
        try:
            conn = get_connection()                     # obtener conexión del pool
            xml_respuesta = procesar_soap_facturacion(request.data, conn)
            return Response(xml_respuesta, mimetype='text/xml')
        except Exception as e:
            return Response(f"<Error>Error interno: {str(e)}</Error>", status=500, mimetype='text/xml')
        finally:
            if conn:
                return_connection(conn)                 # devolver la conexión al pool
    else:
        return Response("Bad Request: use GET ?wsdl or POST SOAP envelope", status=400)

# ==========================================
# 🏠 RUTA PRINCIPAL
# ==========================================
@app.route("/")
def home():
    return jsonify({"success": True, "message": "API REST + SOAP funcionando correctamente."})

# ==========================================
# 📦 CRUD: PRODUCTOS
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
        data = [{"id": str(row[0]), "nombre": row[1], "precio": float(row[2]) if row[2] is not None else 0.0, "imagen_url": row[3], "stock": row[4]} for row in rows]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": True, "data": PRODUCTOS_MOCK, "warning": "Usando datos Mock."})
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

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
        cursor.execute("INSERT INTO public.productos (nombre_producto, precio, imagen_url, stock, version) VALUES (%s, %s, %s, %s, 1) RETURNING producto_id", (nombre, precio, imagen_url, stock))
        nuevo_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"success": True, "message": "Producto creado exitosamente", "id": str(nuevo_id)}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

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
        cursor.execute("UPDATE public.productos SET nombre_producto = COALESCE(%s, nombre_producto), precio = COALESCE(%s, precio), imagen_url = COALESCE(%s, imagen_url), stock = COALESCE(%s, stock), version = version + 1 WHERE producto_id = %s", (nombre, precio, imagen_url, stock, id))
        conn.commit()
        return jsonify({"success": True, "message": f"Producto {id} actualizado"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@app.route("/productos/<string:id>", methods=["DELETE"])
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
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

# ==========================================
# 👥 CRUD: USUARIOS (con cédula, email, teléfono)
# ==========================================
@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, usuario, nombre_completo, rol, cedula, email, telefono FROM public.usuarios ORDER BY id ASC")
        rows = cursor.fetchall()
        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "usuario": row[1],
                "nombre_completo": row[2],
                "rol": row[3],
                "cedula": row[4] if row[4] is not None else "",
                "email": row[5] if row[5] is not None else "",
                "telefono": row[6] if row[6] is not None else ""
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@app.route("/usuarios", methods=["POST"])
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
        cursor.execute("""
            INSERT INTO public.usuarios (usuario, nombre_completo, rol, cedula, email, telefono)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (usuario, nombre_completo, rol, str(cedula), email, telefono))
        nuevo_id = cursor.fetchone()[0]
        conn.commit()

        return jsonify({"success": True, "message": "Usuario registrado exitosamente", "id": nuevo_id}), 201
    except psycopg2.errors.UniqueViolation:
        if conn: conn.rollback()
        return jsonify({"success": False, "message": "La cédula o el usuario ya se encuentran registrados"}), 400
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@app.route("/usuarios/<int:id>", methods=["PUT"])
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
        cursor.execute("""
            UPDATE public.usuarios 
            SET usuario = COALESCE(%s, usuario),
                nombre_completo = COALESCE(%s, nombre_completo),
                rol = COALESCE(%s, rol),
                cedula = COALESCE(%s, cedula),
                email = COALESCE(%s, email),
                telefono = COALESCE(%s, telefono)
            WHERE id = %s
        """, (usuario, nombre_completo, rol, cedula, email, telefono, id))
        conn.commit()

        return jsonify({"success": True, "message": f"Usuario {id} actualizado correctamente"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@app.route("/usuarios/<int:id>", methods=["DELETE"])
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
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

# ==========================================
# 🛍️ CRUD: COMPRAS
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
        data = [{
            "compra_id": row[0],
            "usuario_id": row[1],
            "producto_id": str(row[2]) if row[2] is not None else "PRODUCTO_ELIMINADO",
            "cantidad": row[3],
            "total": float(row[4]) if row[4] is not None else 0.0,
            "fecha_compra": row[5].isoformat() if row[5] else None
        } for row in rows]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

@app.route("/compras", methods=["POST"])
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
        cursor.execute("SELECT stock FROM public.productos WHERE producto_id = %s FOR UPDATE", (producto_id,))
        res = cursor.fetchone()
        if not res:
            return jsonify({"success": False, "message": "El producto no existe"}), 404

        stock_actual = res[0]
        if stock_actual < cantidad:
            return jsonify({"success": False, "message": f"Stock insuficiente. Disponible: {stock_actual}"}), 400

        cursor.execute("UPDATE public.productos SET stock = stock - %s WHERE producto_id = %s", (cantidad, producto_id))
        cursor.execute("INSERT INTO public.compras (usuario_id, producto_id, cantidad, total, fecha_compra) VALUES (%s, %s, %s, %s, NOW() AT TIME ZONE 'UTC') RETURNING compra_id", (usuario_id, producto_id, cantidad, total))
        nueva_compra_id = cursor.fetchone()[0]

        conn.commit()
        return jsonify({"success": True, "message": "Compra registrada con éxito", "compra_id": nueva_compra_id}), 201
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)