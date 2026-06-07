import os
import psycopg2
from notifications import enviar_email_factura, enviar_notificacion_whatsapp

def procesar_soap_facturacion(xml_data, get_db_connection=None):
    if isinstance(xml_data, bytes):
        xml_str = xml_data.decode('utf-8')
    else:
        xml_str = xml_data

    if "ValidarFactura" in xml_str:
        return _validar_factura()
    elif "GenerarFacturaXML" in xml_str or "<factura>" in xml_str:
        return _generar_factura_xml(xml_str, get_db_connection)
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

def _generar_factura_xml(xml_str, get_db_connection):
    # Extraer solo el idCompra del XML
    id_compra = None
    try:
        if "<idCompra>" in xml_str:
            id_compra = xml_str.split("<idCompra>")[1].split("</idCompra>")[0]
        elif "<id>" in xml_str:
            id_compra = xml_str.split("<id>")[1].split("</id>")[0]
    except:
        pass

    if not id_compra:
        return "<Error>Falta el idCompra</Error>"

    # Si no se proporcionó función de conexión, intentar conectar directamente (solo para pruebas)
    if get_db_connection is None:
        # Fallback: usar DATABASE_URL directamente (no recomendado, pero funciona)
        import psycopg2
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return "<Error>No se pudo conectar a la base de datos</Error>"
        conn = psycopg2.connect(db_url)
    else:
        conn = get_db_connection()

    cursor = None
    try:
        cursor = conn.cursor()
        # Obtener datos de la compra y del usuario
        query = """
            SELECT c.compra_id, c.total, u.nombre_completo, u.email, u.telefono
            FROM public.compras c
            JOIN public.usuarios u ON c.usuario_id = u.id
            WHERE c.compra_id = %s
        """
        cursor.execute(query, (id_compra,))
        row = cursor.fetchone()
        if not row:
            return f"<Error>No se encontró la compra con ID {id_compra}</Error>"

        _, total, cliente, correo_destino, telefono_destino = row
        if not correo_destino or not telefono_destino:
            return "<Error>El usuario no tiene email o teléfono registrado</Error>"

        # Generar clave de acceso
        clean_id = str(id_compra).replace("FAC-2026-", "")
        clave_acceso = f"FAC-2026-{clean_id.zfill(5)}"

        xml_respuesta_interna = f"""<RespuestaFactura>
 <Estado>VALIDADA</Estado>
 <Mensaje>Factura generada correctamente para {cliente}</Mensaje>
 <ClaveAcceso>{clave_acceso}</ClaveAcceso>
 <Total>{total}</Total>
</RespuestaFactura>"""

        # Enviar notificaciones
        enviar_email_factura(correo_destino, xml_respuesta_interna)
        mensaje_whatsapp = f"Hola {cliente}, tu factura {clave_acceso} por ${total} ha sido generada."
        enviar_notificacion_whatsapp(telefono_destino, mensaje_whatsapp)

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
        return f"<Error>Error al consultar BD: {str(e)}</Error>"
    finally:
        if cursor:
            cursor.close()
        if get_db_connection is None:
            conn.close()  # cerrar conexión temporal
        else:
            # Si la conexión viene del pool, no la cerramos aquí; se devuelve al pool después
            pass

def _consultar_comprobante():
    return """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <ConsultarComprobanteResponse>
         <estado>AUTORIZADO</estado>
      </ConsultarComprobanteResponse>
   </soapenv:Body>
</soapenv:Envelope>"""