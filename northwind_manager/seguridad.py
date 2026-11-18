"""Seguridad transversal, filtros de plantillas y control de sesión."""

import hmac
import secrets
from datetime import date, datetime
from decimal import Decimal

from flask import abort, redirect, request, session, url_for


def utilidades_plantillas():
    """Comparte un token CSRF con todas las plantillas HTML."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return {"csrf_token": session["csrf_token"]}


def validar_csrf():
    """Protege todas las operaciones POST contra solicitudes externas."""
    if request.method == "POST":
        esperado = session.get("csrf_token", "")
        recibido = request.form.get("csrf_token", "")
        if not esperado or not hmac.compare_digest(esperado, recibido):
            abort(
                400,
                description="El formulario expiró. Actualiza la página e inténtalo de nuevo.",
            )


def exigir_inicio_de_sesion():
    """Impide consultar módulos sin una sesión administrativa válida."""
    rutas_publicas = {"iniciar_sesion", "static"}
    if request.endpoint not in rutas_publicas and "usuario_id" not in session:
        return redirect(url_for("iniciar_sesion"))


def filtro_moneda(valor):
    """Convierte un número en una cantidad con dos decimales."""
    return f"${Decimal(valor or 0):,.2f}"


def filtro_fecha(valor):
    """Muestra fechas de SQL Server en formato día/mes/año."""
    if not valor:
        return "—"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


def registrar_seguridad(app):
    """Conecta con Flask los controles y filtros compartidos."""
    app.context_processor(utilidades_plantillas)
    app.before_request(validar_csrf)
    app.before_request(exigir_inicio_de_sesion)
    app.add_template_filter(filtro_moneda, "moneda")
    app.add_template_filter(filtro_fecha, "fecha")
