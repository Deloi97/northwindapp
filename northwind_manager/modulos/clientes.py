"""Consulta y operaciones CRUD de clientes."""

import pyodbc
from flask import flash, redirect, render_template, request, url_for

from conexion import consultar, ejecutar
from ..validaciones import mensaje_error_sql, texto


def clientes():
    """Busca clientes por empresa o persona de contacto."""
    busqueda = request.args.get("q", "").strip()
    where, parametros = "", []
    if busqueda:
        where = "WHERE CompanyName LIKE ? OR ContactName LIKE ?"
        parametros = [f"%{busqueda}%", f"%{busqueda}%"]
    filas = consultar(
        f"""
        SELECT CustomerID, CompanyName, ContactName, ContactTitle, Address, City,
               Region, PostalCode, Country, Phone, Fax
        FROM Customers {where}
        ORDER BY CompanyName
        """,
        parametros,
    )
    return render_template("clientes.html", titulo="Clientes", clientes=filas, q=busqueda)


def datos_cliente(incluir_id: bool = False) -> tuple:
    """Valida los datos del cliente y, durante el alta, también CustomerID."""
    valores = (
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
    )
    if incluir_id:
        customer_id = (texto("customer_id", 5, True) or "").upper()
        if not 1 <= len(customer_id) <= 5:
            raise ValueError("El identificador del cliente acepta entre 1 y 5 caracteres.")
        return (customer_id,) + valores
    return valores


def cliente_nuevo():
    try:
        ejecutar(
            """
            INSERT INTO Customers
                (CustomerID, CompanyName, ContactName, ContactTitle, Address, City,
                 Region, PostalCode, Country, Phone, Fax)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            datos_cliente(True),
        )
        flash("Cliente agregado correctamente.", "success")
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "agregar el cliente"), "danger")
    return redirect(url_for("clientes"))


def cliente_editar(customer_id):
    try:
        afectadas = ejecutar(
            """
            UPDATE Customers SET CompanyName=?, ContactName=?, ContactTitle=?,
                Address=?, City=?, Region=?, PostalCode=?, Country=?, Phone=?, Fax=?
            WHERE CustomerID=?
            """,
            datos_cliente() + (customer_id,),
        )
        flash(
            "Cliente actualizado correctamente." if afectadas else "El cliente ya no existe.",
            "success" if afectadas else "warning",
        )
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "editar el cliente"), "danger")
    return redirect(url_for("clientes"))


def cliente_eliminar(customer_id):
    try:
        afectadas = ejecutar("DELETE FROM Customers WHERE CustomerID=?", (customer_id,))
        flash(
            "Cliente eliminado correctamente." if afectadas else "El cliente ya no existe.",
            "success" if afectadas else "warning",
        )
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "eliminar el cliente"), "danger")
    return redirect(url_for("clientes"))


def registrar_rutas(app):
    app.add_url_rule("/clientes", endpoint="clientes", view_func=clientes)
    app.add_url_rule(
        "/clientes/nuevo",
        endpoint="cliente_nuevo",
        view_func=cliente_nuevo,
        methods=["POST"],
    )
    app.add_url_rule(
        "/clientes/<string:customer_id>/editar",
        endpoint="cliente_editar",
        view_func=cliente_editar,
        methods=["POST"],
    )
    app.add_url_rule(
        "/clientes/<string:customer_id>/eliminar",
        endpoint="cliente_eliminar",
        view_func=cliente_eliminar,
        methods=["POST"],
    )
