# -*- coding: utf-8 -*-
"""Package initializer for route blueprints.
It imports each module's Blueprint and registers it on the Flask app.
"""

from flask import Flask

# Import blueprints from sub‑modules
from .products import bp as products_bp
from .users import bp as users_bp
from .purchases import bp as purchases_bp
from .facturation import bp as facturation_bp


def register_routes(app: Flask):
    """Register all route blueprints on the given Flask app.
    This function is called from ``app.py``.
    """
    app.register_blueprint(products_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(facturation_bp)
