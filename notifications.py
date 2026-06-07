import os
import smtplib
from email.message import EmailMessage
from twilio.rest import Client

# Las siguientes variables DEBEN estar definidas en el entorno (Render)
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

def enviar_notificacion_whatsapp(telefono_destino, mensaje):
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=f'whatsapp:{TWILIO_PHONE}',
            body=mensaje,
            to=f'whatsapp:{telefono_destino}'
        )
        print(f"✅ WhatsApp enviado. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error Twilio: {e}")
        return False

SMTP_SERVER = os.getenv("SMTP_SERVER", "sandbox.smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", "2525"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def enviar_email_factura(correo_destino, contenido_xml):
    msg = EmailMessage()
    msg.set_content(f"Hola,\n\nSe ha generado una nueva factura electrónica.\n\n{contenido_xml}")
    msg['Subject'] = 'Nueva Factura Electrónica - TechStore 360'
    msg['From'] = 'facturacion@techstore360.com'
    msg['To'] = correo_destino
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASS)
            smtp.send_message(msg)
        print(f"✅ Correo enviado a {correo_destino} vía Mailtrap")
        return True
    except Exception as e:
        print(f"❌ Error Mailtrap: {e}")
        return False
