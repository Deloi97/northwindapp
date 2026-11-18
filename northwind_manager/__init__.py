"""Fábrica de la aplicación Northwind Manager.

Este archivo solo crea y configura Flask. Las funciones de cada apartado viven
en ``modulos`` para que sea fácil localizar y mantener su funcionalidad.
"""

import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask

from .errores import registrar_errores
from .modulos import registrar_modulos
from .seguridad import registrar_seguridad


def crear_app(configuracion: dict | None = None) -> Flask:
    """Crea una instancia configurada de la aplicación Flask."""
    load_dotenv()

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if configuracion:
        app.config.update(configuracion)

    registrar_seguridad(app)
    registrar_modulos(app)
    registrar_errores(app)
    return app
