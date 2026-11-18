"""Páginas de error comunes de la aplicación."""

from flask import render_template


def error_400(error):
    return render_template(
        "error.html",
        titulo="Solicitud inválida",
        codigo=400,
        mensaje=error.description,
    ), 400


def error_404(_error):
    return render_template(
        "error.html",
        titulo="No encontrado",
        codigo=404,
        mensaje="La página o el registro solicitado no existe.",
    ), 404


def error_413(_error):
    return render_template(
        "error.html",
        titulo="Archivo demasiado grande",
        codigo=413,
        mensaje="El archivo supera el límite permitido de 5 MB.",
    ), 413


def error_500(_error):
    return render_template(
        "error.html",
        titulo="Error interno",
        codigo=500,
        mensaje="Ocurrió un error inesperado al procesar la solicitud.",
    ), 500


def registrar_errores(app):
    app.register_error_handler(400, error_400)
    app.register_error_handler(404, error_404)
    app.register_error_handler(413, error_413)
    app.register_error_handler(500, error_500)
