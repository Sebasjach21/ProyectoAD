# -*- coding: utf-8 -*-
"""
app.py – Bootstrap principal de Flask.

Toda la lógica de rutas, CRUD y SOAP ahora vive en los paquetes:
  routes/       → blueprints de productos, usuarios, compras, facturación
  services/     → notificaciones (Twilio + Mailtrap), lógica SOAP
  db/           → pool de conexiones Supabase
  config/       → variables de entorno
"""
from flask import Flask
from flask_cors import CORS
from routes import register_routes

app = Flask(__name__)

# CORS global – permite cualquier origen (ajustar en producción si se desea restringir)
CORS(
    app,
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

# Registrar todos los blueprints
register_routes(app)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001)