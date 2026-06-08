# -*- coding: utf-8 -*-
"""
notifications.py – conservado por compatibilidad.
Ahora re-exporta desde services.notifications.
"""
from services.notifications import (  # noqa: F401
    enviar_email_factura,
    enviar_notificacion_whatsapp,
)
