# -*- coding: utf-8 -*-
"""Endpoint SOAP de Facturación + ruta principal – Blueprint Flask."""
from flask import Blueprint, jsonify, request, Response
from db.connection import get_connection, return_connection
from services.soap.logic import procesar_soap_facturacion

bp = Blueprint("facturation", __name__)

# ==========================================
# WSDL completo (idéntico al original)
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


# ==========================================
# 🏠 Ruta principal
# ==========================================
@bp.route("/")
def home():
    return jsonify({"success": True, "message": "API REST + SOAP funcionando correctamente."})


# ==========================================
# 🧾 Endpoint SOAP
# ==========================================
@bp.route("/facturacion", methods=["POST", "GET"])
def soap_endpoint():
    """GET ?wsdl devuelve el WSDL; POST procesa la petición SOAP."""
    if request.method == "GET" and "wsdl" in request.args:
        return Response(WSDL_CONTENT, mimetype="text/xml")
    elif request.method == "POST":
        conn = None
        try:
            conn = get_connection()
            xml_respuesta = procesar_soap_facturacion(request.data, conn)
            return Response(xml_respuesta, mimetype="text/xml")
        except Exception as e:
            return Response(
                f"<Error>Error interno: {str(e)}</Error>",
                status=500,
                mimetype="text/xml",
            )
        finally:
            if conn:
                return_connection(conn)
    else:
        return Response("Bad Request: use GET ?wsdl or POST SOAP envelope", status=400)


# ==========================================
# 📄 Endpoints para descargar facturas (XML y PDF)
# ==========================================
@bp.route("/factura/<int:id>/xml", methods=["GET"])
def descargar_factura_xml(id):
    try:
        from services.facturacion import generar_xml_factura
        xml_content = generar_xml_factura(id)
        if not xml_content:
            return jsonify({"success": False, "message": f"Factura {id} no encontrada"}), 404
            
        return Response(
            xml_content,
            mimetype="application/xml",
            headers={"Content-Disposition": f"attachment; filename=FAC-2026-{str(id).zfill(5)}.xml"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/factura/<int:id>/pdf", methods=["GET"])
def descargar_factura_pdf(id):
    try:
        from services.facturacion import generar_pdf_factura
        pdf_data = generar_pdf_factura(id)
        if not pdf_data:
            return jsonify({"success": False, "message": f"Factura {id} no encontrada"}), 404
            
        return Response(
            pdf_data,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=FAC-2026-{str(id).zfill(5)}.pdf"}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

