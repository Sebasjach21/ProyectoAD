# -*- coding: utf-8 -*-
"""Servicio de generación y envío de facturas."""
import os
import smtplib
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email import encoders

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from db.connection import get_connection, return_connection

# Reusamos configuración de correo si existe, o defaults
SMTP_SERVER = os.getenv("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525").strip())
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def generar_y_enviar_factura(factura_id):
    """
    Genera el XML y PDF de la factura y la envía por correo electrónico.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Obtenemos datos de la factura, usuario y detalles
        cursor.execute("""
            SELECT u.email, u.nombre_completo, f.total_general, 
                   json_agg(
                       json_build_object(
                           'producto_id', d.producto_id, 
                           'cantidad', d.cantidad, 
                           'precio', d.precio_unitario, 
                           'subtotal', d.subtotal
                       )
                   )
            FROM public.facturas f
            JOIN public.usuarios u ON f.usuario_id = u.id
            JOIN public.detalle_facturas d ON f.factura_id = d.factura_id
            WHERE f.factura_id = %s
            GROUP BY u.email, u.nombre_completo, f.total_general
        """, (factura_id,))
        row = cursor.fetchone()
        
        if not row:
            print(f"No se encontró la factura {factura_id} para generar comprobantes.")
            return

        email_cliente, nombre_cliente, total, productos = row
        clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"

        # 1. Generar XML
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<RespuestaFactura>
    <Estado>VALIDADA</Estado>
    <ClaveAcceso>{clave_acceso}</ClaveAcceso>
    <Cliente>{nombre_cliente}</Cliente>
    <Total>{total}</Total>
    <Productos>
"""
        for p in productos:
            xml_content += f"""        <Producto>
            <Id>{p['producto_id']}</Id>
            <Cantidad>{p['cantidad']}</Cantidad>
            <Precio>{p['precio']}</Precio>
            <Subtotal>{p['subtotal']}</Subtotal>
        </Producto>
"""
        xml_content += "    </Productos>\n</RespuestaFactura>"

        # Guardar XML temporalmente para uso de la API (opcional, aunque la API puede generarlo al vuelo,
        # pero es buena práctica guardar un registro si se requiere, aquí solo lo enviaremos por correo).
        # Los endpoints GET /xml y /pdf lo generarán al vuelo.

        # 2. Generar PDF temporal
        pdf_file_path = f"/tmp/factura_{factura_id}.pdf"
        # Crear directorio temporal si no existe (por si acaso en Windows o entornos locales)
        temp_dir = os.path.dirname(pdf_file_path)
        if temp_dir and not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        c = canvas.Canvas(pdf_file_path, pagesize=letter)
        c.drawString(100, 750, f"Factura Electrónica - {clave_acceso}")
        c.drawString(100, 730, f"Cliente: {nombre_cliente}")
        c.drawString(100, 710, f"Total: ${total}")
        y = 690
        for p in productos:
            c.drawString(100, y, f"Producto: {p['producto_id']} - Cant: {p['cantidad']} - Subtotal: ${p['subtotal']}")
            y -= 20
        c.save()

        # 3. Enviar correo
        msg = EmailMessage()
        msg['Subject'] = f'Factura Electrónica - TechStore 360 - {clave_acceso}'
        msg['From'] = SMTP_USER or "facturacion@techstore360.com"
        msg['To'] = email_cliente
        msg.set_content(
            f"Hola {nombre_cliente},\n\n"
            f"Gracias por tu compra. Adjuntamos tu factura en XML y PDF.\n\n"
            f"Total: ${total}\n"
            f"Clave de acceso: {clave_acceso}"
        )

        # Adjuntar XML
        xml_part = MIMEBase('application', 'xml')
        xml_part.set_payload(xml_content.encode('utf-8'))
        encoders.encode_base64(xml_part)
        xml_part.add_header('Content-Disposition', 'attachment', filename=f'{clave_acceso}.xml')
        msg.add_attachment(xml_part.get_payload(), maintype='application', subtype='xml', filename=f'{clave_acceso}.xml')

        # Adjuntar PDF
        with open(pdf_file_path, 'rb') as f:
            pdf_data = f.read()
            msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=f'{clave_acceso}.pdf')

        # Enviar usando SMTP
        if SMTP_USER and SMTP_PASS:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASS)
                smtp.send_message(msg)
            print(f"Factura enviada por correo a {email_cliente}")
        else:
            print("Credenciales SMTP no configuradas. Correo no enviado.")

        # Limpieza
        if os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)

    except Exception as e:
        print(f"Error al generar y enviar factura: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            return_connection(conn)

def generar_xml_factura(factura_id):
    """Genera y retorna el contenido XML de una factura (usado por el endpoint GET)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.nombre_completo, f.total_general, 
                   json_agg(
                       json_build_object(
                           'producto_id', d.producto_id, 
                           'cantidad', d.cantidad, 
                           'precio', d.precio_unitario, 
                           'subtotal', d.subtotal
                       )
                   )
            FROM public.facturas f
            JOIN public.usuarios u ON f.usuario_id = u.id
            JOIN public.detalle_facturas d ON f.factura_id = d.factura_id
            WHERE f.factura_id = %s
            GROUP BY u.nombre_completo, f.total_general
        """, (factura_id,))
        row = cursor.fetchone()
        
        if not row:
            return None

        nombre_cliente, total, productos = row
        clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<RespuestaFactura>
    <Estado>VALIDADA</Estado>
    <ClaveAcceso>{clave_acceso}</ClaveAcceso>
    <Cliente>{nombre_cliente}</Cliente>
    <Total>{total}</Total>
    <Productos>
"""
        for p in productos:
            xml_content += f"""        <Producto>
            <Id>{p['producto_id']}</Id>
            <Cantidad>{p['cantidad']}</Cantidad>
            <Precio>{p['precio']}</Precio>
            <Subtotal>{p['subtotal']}</Subtotal>
        </Producto>
"""
        xml_content += "    </Productos>\n</RespuestaFactura>"
        return xml_content
    finally:
        if cursor: cursor.close()
        if conn: return_connection(conn)

def generar_pdf_factura(factura_id):
    """Genera y retorna el contenido PDF binario de una factura (usado por el endpoint GET)."""
    conn = get_connection()
    cursor = conn.cursor()
    pdf_file_path = f"/tmp/factura_endpoint_{factura_id}.pdf"
    try:
        cursor.execute("""
            SELECT u.nombre_completo, f.total_general, 
                   json_agg(
                       json_build_object(
                           'producto_id', d.producto_id, 
                           'cantidad', d.cantidad, 
                           'precio', d.precio_unitario, 
                           'subtotal', d.subtotal
                       )
                   )
            FROM public.facturas f
            JOIN public.usuarios u ON f.usuario_id = u.id
            JOIN public.detalle_facturas d ON f.factura_id = d.factura_id
            WHERE f.factura_id = %s
            GROUP BY u.nombre_completo, f.total_general
        """, (factura_id,))
        row = cursor.fetchone()
        
        if not row:
            return None

        nombre_cliente, total, productos = row
        clave_acceso = f"FAC-2026-{str(factura_id).zfill(5)}"

        temp_dir = os.path.dirname(pdf_file_path)
        if temp_dir and not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        c = canvas.Canvas(pdf_file_path, pagesize=letter)
        c.drawString(100, 750, f"Factura Electrónica - {clave_acceso}")
        c.drawString(100, 730, f"Cliente: {nombre_cliente}")
        c.drawString(100, 710, f"Total: ${total}")
        y = 690
        for p in productos:
            c.drawString(100, y, f"Producto: {p['producto_id']} - Cant: {p['cantidad']} - Subtotal: ${p['subtotal']}")
            y -= 20
        c.save()

        with open(pdf_file_path, 'rb') as f:
            pdf_data = f.read()
            
        return pdf_data
    finally:
        if os.path.exists(pdf_file_path):
            os.remove(pdf_file_path)
        if cursor: cursor.close()
        if conn: return_connection(conn)
