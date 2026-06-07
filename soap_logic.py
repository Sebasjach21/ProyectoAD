import os
from notifications import enviar_email_factura, enviar_notificacion_whatsapp

def procesar_soap_facturacion(xml_data):
    if isinstance(xml_data, bytes):
        xml_str = xml_data.decode('utf-8')
    else:
        xml_str = xml_data

    if "ValidarFactura" in xml_str:
        return _validar_factura()
    elif "GenerarFacturaXML" in xml_str or "<factura>" in xml_str:
        return _generar_factura_xml(xml_str)
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

def _generar_factura_xml(xml_str):
    id_factura = "00001"
    cliente = "Cliente"
    correo_destino = os.getenv("TEST_EMAIL", "cliente@ejemplo.com")
    telefono_destino = os.getenv("TEST_PHONE", "+593999999999")

    try:
        if "<idCompra>" in xml_str:
            id_factura = xml_str.split("<idCompra>")[1].split("</idCompra>")[0]
        elif "<id>" in xml_str:
            id_factura = xml_str.split("<id>")[1].split("</id>")[0]

        if "<cliente>" in xml_str:
            cliente = xml_str.split("<cliente>")[1].split("</cliente>")[0]
        if "<correo>" in xml_str:
            correo_destino = xml_str.split("<correo>")[1].split("</correo>")[0]
        if "<telefono>" in xml_str:
            telefono_destino = xml_str.split("<telefono>")[1].split("</telefono>")[0]
    except:
        pass

    clean_id = id_factura.replace("FAC-2026-", "")
    clave_acceso = f"FAC-2026-{clean_id.zfill(5)}"

    xml_respuesta_interna = f"""<RespuestaFactura>
 <Estado>VALIDADA</Estado>
 <Mensaje>Factura generada correctamente para {cliente}</Mensaje>
 <ClaveAcceso>{clave_acceso}</ClaveAcceso>
</RespuestaFactura>"""

    # Notificaciones
    enviar_email_factura(correo_destino, xml_respuesta_interna)
    mensaje_whatsapp = f"Hola {cliente}, tu factura {clave_acceso} ha sido generada exitosamente."
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

def _consultar_comprobante():
    return """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <ConsultarComprobanteResponse>
         <estado>AUTORIZADO</estado>
      </ConsultarComprobanteResponse>
   </soapenv:Body>
</soapenv:Envelope>"""