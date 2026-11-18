"""Panel principal y diagnóstico de la conexión."""

import pyodbc
from flask import current_app, render_template

from conexion import consultar, consultar_uno, probar_conexion, verificar_esquema
from ..validaciones import mensaje_error_conexion


def dashboard():
    """Carga el resumen principal usando información de Northwind."""
    try:
        estadisticas = consultar_uno(
            """
            SELECT
                (SELECT COUNT(*) FROM Products) AS productos,
                (SELECT COUNT(*) FROM Customers) AS clientes,
                (SELECT COUNT(*) FROM Suppliers) AS proveedores,
                (SELECT COUNT(*) FROM Orders) AS pedidos
            """
        )
        ultimos_pedidos = consultar(
            """
            SELECT TOP 5 o.OrderID, o.OrderDate, c.CompanyName
            FROM Orders o
            LEFT JOIN Customers c ON c.CustomerID = o.CustomerID
            ORDER BY o.OrderDate DESC, o.OrderID DESC
            """
        )
        return render_template(
            "dashboard.html",
            titulo="Panel principal",
            estadisticas=estadisticas,
            ultimos_pedidos=ultimos_pedidos,
            conexion_correcta=True,
        )
    except (pyodbc.Error, ValueError) as error:
        current_app.logger.exception("No fue posible cargar el panel principal")
        return render_template(
            "dashboard.html",
            titulo="Panel principal",
            estadisticas={"productos": 0, "clientes": 0, "proveedores": 0, "pedidos": 0},
            ultimos_pedidos=[],
            conexion_correcta=False,
            error_conexion=mensaje_error_conexion(error),
        )


def diagnostico():
    """Prueba la conexión y confirma que existan las tablas requeridas."""
    try:
        datos = probar_conexion()
        esquema = verificar_esquema()
        return render_template(
            "diagnostico.html",
            titulo="Diagnóstico",
            datos=datos,
            esquema=esquema,
        )
    except (pyodbc.Error, ValueError) as error:
        return render_template(
            "diagnostico.html",
            titulo="Diagnóstico",
            error=mensaje_error_conexion(error),
        ), 503


def registrar_rutas(app):
    app.add_url_rule("/", endpoint="dashboard", view_func=dashboard)
    app.add_url_rule("/diagnostico", endpoint="diagnostico", view_func=diagnostico)
