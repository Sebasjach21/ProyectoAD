import os
import smtplib
from email.message import EmailMessage
from twilio.rest import Client

# ==========================================
# 1. CONFIGURACIÓN DE TWILIO (COMPROBADA)
# ==========================================
# Las siguientes variables DEBEN estar definidas en el entorno (Render)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

def enviar_notificacion_whatsapp(telefono_destino, mensaje):
    """
    Envía una alerta de facturación por WhatsApp usando Twilio.
    """
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        
        # El Sandbox de Twilio exige el prefijo 'whatsapp:' tanto en el emisor como en el destino
        message = client.messages.create(
            from_=f'whatsapp:{TWILIO_PHONE}',
            body=mensaje,
            to=f'whatsapp:{telefono_destino}'
        )
        print(f"✅ WhatsApp enviado con éxito. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar por Twilio: {e}")
        return False


# ==========================================
# 2. CONFIGURACIÓN DE MAILTRAP (SMTP REAL)
# ==========================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "sandbox.smtp.mailtrap.io").strip()
smtp_port_env = os.getenv("SMTP_PORT", "2525").strip()
SMTP_PORT = int(smtp_port_env) if smtp_port_env else 2525
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def enviar_email_factura(correo_destino, contenido_xml):
    """
    Envía el XML de la factura por correo usando el servidor SMTP de Mailtrap.
    """
    # Construimos la estructura estándar del correo electrónico
    msg = EmailMessage()
    msg.set_content(f"Hola,\n\nSe ha generado una nueva factura electrónica en el sistema distribuido.\n\nContenido del XML adjunto:\n\n{contenido_xml}")
    msg['Subject'] = 'Nueva Factura Electrónica Validada - TechStore 360'
    msg['From'] = 'facturacion@techstore360.com'
    msg['To'] = correo_destino

    try:
        # Mailtrap requiere conexión SMTP estándar con elevación TLS en puerto 2525
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()  # Activamos el cifrado seguro obligatorio
            smtp.login(SMTP_USER, SMTP_PASS)  # Autenticación con tus credenciales
            smtp.send_message(msg)           # Despacho del correo
            
        print(f"✅ Correo enviado con éxito (capturado en Mailtrap) para {correo_destino}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar correo por SMTP: {e}")
        return False
