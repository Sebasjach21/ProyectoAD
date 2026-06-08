# -*- coding: utf-8 -*-
"""Servicio de notificaciones: WhatsApp (Twilio) y Email (Mailtrap)."""
import os
import smtplib
from email.message import EmailMessage

try:
    from twilio.rest import Client
except ImportError:
    raise ImportError(
        "Twilio no está instalado. Ejecuta: pip install twilio==9.0.4"
    )

# ==========================================
# 1. CONFIGURACIÓN DE TWILIO
# ==========================================
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")


def enviar_notificacion_whatsapp(telefono_destino: str, mensaje: str) -> bool:
    """Envía una alerta de facturación por WhatsApp usando Twilio Sandbox."""
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=f"whatsapp:{TWILIO_PHONE}",
            body=mensaje,
            to=f"whatsapp:{telefono_destino}",
        )
        print(f"✅ WhatsApp enviado con éxito. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar por Twilio: {e}")
        return False


# ==========================================
# 2. CONFIGURACIÓN DE MAILTRAP (SMTP)
# ==========================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525").strip())
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def enviar_email_factura(correo_destino: str, contenido_xml: str) -> bool:
    """Envía el XML de la factura por correo usando Mailtrap."""
    msg = EmailMessage()
    msg.set_content(
        f"Hola,\n\nSe ha generado una nueva factura electrónica en el sistema distribuido.\n\n"
        f"Contenido del XML adjunto:\n\n{contenido_xml}"
    )
    msg["Subject"] = "Nueva Factura Electrónica Validada - TechStore 360"
    msg["From"] = "facturacion@techstore360.com"
    msg["To"] = correo_destino

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"✅ Correo enviado con éxito (Mailtrap) para {correo_destino}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo por SMTP: {e}")
        return False
