"""Consulta y operaciones CRUD de proveedores."""

import pyodbc
from flask import flash, redirect, render_template, request, url_for

from conexion import consultar, ejecutar
from ..validaciones import mensaje_error_sql, texto


def proveedores():
    """Muestra proveedores y permite buscar por empresa o contacto."""
    busqueda = request.args.get("q", "").strip()
    where, parametros = "", []
    if busqueda:
        where = "WHERE CompanyName LIKE ? OR ContactName LIKE ?"
        parametros = [f"%{busqueda}%", f"%{busqueda}%"]
    filas = consultar(
        f"""
        SELECT SupplierID, CompanyName, ContactName, ContactTitle, Address, City,
               Region, PostalCode, Country, Phone, Fax, HomePage
        FROM Suppliers {where}
        ORDER BY CompanyName
        """,
        parametros,
    )
    return render_template(
        "proveedores.html",
        titulo="Proveedores",
        proveedores=filas,
        q=busqueda,
    )


def datos_proveedor() -> tuple:
    """Valida los campos compartidos por alta y edición."""
    return (
        texto("company_name", 40, True),
        texto("contact_name", 30),
        texto("contact_title", 30),
        texto("address", 60),
        texto("city", 15),
        texto("region", 15),
        texto("postal_code", 10),
        texto("country", 15),
        texto("phone", 24),
        texto("fax", 24),
        texto("home_page", 255),
    )


def proveedor_nuevo():
    try:
        ejecutar(
            """
            INSERT INTO Suppliers
                (CompanyName, ContactName, ContactTitle, Address, City, Region,
                 PostalCode, Country, Phone, Fax, HomePage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            datos_proveedor(),
        )
        flash("Proveedor agregado correctamente.", "success")
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "agregar el proveedor"), "danger")
    return redirect(url_for("proveedores"))


def proveedor_editar(supplier_id):
    try:
        afectadas = ejecutar(
            """
            UPDATE Suppliers SET CompanyName=?, ContactName=?, ContactTitle=?,
                Address=?, City=?, Region=?, PostalCode=?, Country=?, Phone=?,
                Fax=?, HomePage=? WHERE SupplierID=?
            """,
            datos_proveedor() + (supplier_id,),
        )
        flash(
            "Proveedor actualizado correctamente."
            if afectadas
            else "El proveedor ya no existe.",
            "success" if afectadas else "warning",
        )
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "editar el proveedor"), "danger")
    return redirect(url_for("proveedores"))


def registrar_rutas(app):
    app.add_url_rule("/proveedores", endpoint="proveedores", view_func=proveedores)
    app.add_url_rule(
        "/proveedores/nuevo",
        endpoint="proveedor_nuevo",
        view_func=proveedor_nuevo,
        methods=["POST"],
    )
    app.add_url_rule(
        "/proveedores/<int:supplier_id>/editar",
        endpoint="proveedor_editar",
        view_func=proveedor_editar,
        methods=["POST"],
    )
