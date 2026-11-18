"""Inicio y cierre de sesión administrativa."""

import math
import secrets
import time

import pyodbc
from flask import flash, redirect, render_template, request, session, url_for

from conexion import consultar_uno
from ..validaciones import mensaje_error_conexion


def iniciar_sesion():
    """Valida una cuenta existente de la tabla Usuario de Northwind."""
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        bloqueo_hasta = float(session.get("bloqueo_hasta", 0))
        segundos_restantes = math.ceil(bloqueo_hasta - time.time())
        if segundos_restantes > 0:
            flash(
                f"Demasiados intentos fallidos. Espera {segundos_restantes} segundos.",
                "warning",
            )
            return render_template("login.html", titulo="Iniciar sesión"), 429

        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "")
        if not usuario or not contrasena:
            flash("Escribe el usuario y la contraseña.", "warning")
            return render_template("login.html", titulo="Iniciar sesión"), 400

        try:
            cuenta = consultar_uno(
                """
                SELECT TOP 1 IdUsuario, Nombre, Apellido, Login
                FROM Usuario
                WHERE Login = ? AND Password = ?
                """,
                (usuario, contrasena),
            )
        except (pyodbc.Error, ValueError) as error:
            flash(mensaje_error_conexion(error), "danger")
            return render_template("login.html", titulo="Iniciar sesión"), 503

        if cuenta is None:
            intentos = int(session.get("intentos_login", 0)) + 1
            session["intentos_login"] = intentos
            if intentos >= 5:
                session["bloqueo_hasta"] = time.time() + 60
                session["intentos_login"] = 0
                flash(
                    "Se alcanzó el límite de intentos. El acceso se bloqueó por un minuto.",
                    "warning",
                )
            else:
                restantes = 5 - intentos
                flash(
                    f"Usuario o contraseña incorrectos. Quedan {restantes} intentos.",
                    "danger",
                )
            return render_template("login.html", titulo="Iniciar sesión"), 401

        session.clear()
        session.permanent = True
        session["usuario_id"] = cuenta["IdUsuario"]
        session["usuario_login"] = cuenta["Login"]
        session["usuario_nombre"] = f"{cuenta['Nombre']} {cuenta['Apellido']}".strip()
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash(f"Bienvenido, {session['usuario_nombre']}.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", titulo="Iniciar sesión")


def cerrar_sesion():
    """Elimina la sesión del navegador y regresa a la pantalla de acceso."""
    session.clear()
    flash("La sesión se cerró correctamente.", "success")
    return redirect(url_for("iniciar_sesion"))


def registrar_rutas(app):
    app.add_url_rule(
        "/iniciar-sesion",
        endpoint="iniciar_sesion",
        view_func=iniciar_sesion,
        methods=["GET", "POST"],
    )
    app.add_url_rule(
        "/cerrar-sesion",
        endpoint="cerrar_sesion",
        view_func=cerrar_sesion,
        methods=["POST"],
    )
