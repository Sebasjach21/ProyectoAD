# -*- coding: utf-8 -*-
"""Lógica de negocio SOAP para el servicio de facturación.
Contenido migrado de soap_logic.py – los imports apuntan ahora a services.notifications.
"""
import os
import psycopg2
from services.notifications import enviar_email_factura, enviar_notificacion_whatsapp


def procesar_soap_facturacion(xml_data, db_connection=None):
    """
    Procesa la petición SOAP.
    Si se pasa db_connection la usa; si no, intenta conectar directamente (desarrollo local).
    """
    if isinstance(xml_data, bytes):
        xml_str = xml_data.decode("utf-8")
    else:
        xml_str = xml_data

    if "ValidarFactura" in xml_str:
        return _validar_factura()
    elif "GenerarFacturaXML" in xml_str or "<factura>" in xml_str:
        return _generar_factura_xml(xml_str, db_connection)
    elif "ConsultarComprobante" in xml_str:
        return _consultar_comprobante()
    else:
        return "<Error>Operación no reconocida</Error>"


def _validar_factura():
    return """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <ValidarFacturaResponse>
         <estado>VALIDA</estado>
      </ValidarFacturaResponse>
   </soapenv:Body>
</soapenv:Envelope>"""


def _generar_factura_xml(xml_str, db_connection):
    # Extraer idCompra del XML
    id_compra = None
    try:
        if "<idCompra>" in xml_str:
            id_compra = xml_str.split("<idCompra>")[1].split("</idCompra>")[0]
        elif "<id>" in xml_str:
            id_compra = xml_str.split("<id>")[1].split("</id>")[0]
    except Exception:
        pass

    if not id_compra:
        return "<Error>Falta el idCompra en la petición</Error>"

    # Obtener conexión a la BD
    close_conn = False
    if db_connection is None:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres.aifsfrslffnzfufodqwx:47OLPjn1vxbkbL6k"
            "@aws-1-us-west-2.pooler.supabase.com:5432/postgres",
        )
        if not db_url:
            return "<Error>No se pudo conectar a la base de datos</Error>"
        conn = psycopg2.connect(db_url)
        close_conn = True
    else:
        conn = db_connection

    cursor = None
    try:
        cursor = conn.cursor()
        query = """
            SELECT
                c.compra_id,
                c.total,
                u.nombre_completo,
                u.email,
                u.telefono
            FROM public.compras c
            JOIN public.usuarios u ON c.usuario_id = u.id
            WHERE c.compra_id = %s
        """
        cursor.execute(query, (id_compra,))
        row = cursor.fetchone()
        if not row:
            return f"<Error>No se encontró la compra con ID {id_compra}</Error>"

        _, total, nombre_cliente, email_cliente, telefono_cliente = row

        if not email_cliente:
            return "<Error>El usuario no tiene email registrado</Error>"
        if not telefono_cliente:
            return "<Error>El usuario no tiene teléfono registrado</Error>"

        # Generar clave de acceso (formato FAC-2026-XXXXX)
        clean_id = str(id_compra).replace("FAC-2026-", "")
        clave_acceso = f"FAC-2026-{clean_id.zfill(5)}"

        # XML de respuesta interna
        xml_respuesta_interna = f"""<RespuestaFactura>
 <Estado>VALIDADA</Estado>
 <Mensaje>Factura generada correctamente para {nombre_cliente}</Mensaje>
 <ClaveAcceso>{clave_acceso}</ClaveAcceso>
 <Total>{total}</Total>
</RespuestaFactura>"""

        # Enviar notificaciones
        enviar_email_factura(email_cliente, xml_respuesta_interna)
        mensaje_whatsapp = (
            f"Hola {nombre_cliente}, tu factura {clave_acceso} por ${total} "
            "ha sido generada exitosamente."
        )
        enviar_notificacion_whatsapp(telefono_cliente, mensaje_whatsapp)

        # Respuesta SOAP completa
        return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <GenerarFacturaXMLResponse>
         <xmlGenerado>
            {xml_respuesta_interna}
         </xmlGenerado>
      </GenerarFacturaXMLResponse>
   </soapenv:Body>
</soapenv:Envelope>"""

    except Exception as e:
        return f"<Error>Error al consultar la base de datos: {str(e)}</Error>"
    finally:
        if cursor:
            cursor.close()
        if close_conn and conn:
            conn.close()


def _consultar_comprobante():
    return """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <ConsultarComprobanteResponse>
         <estado>AUTORIZADO</estado>
      </ConsultarComprobanteResponse>
   </soapenv:Body>
</soapenv:Envelope>"""
