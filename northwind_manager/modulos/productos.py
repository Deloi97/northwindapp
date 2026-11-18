"""Consulta y operaciones CRUD de productos."""

import pyodbc
from flask import flash, redirect, render_template, request, url_for

from conexion import consultar, ejecutar
from ..validaciones import decimal_positivo, entero, mensaje_error_sql, texto


def productos():
    """Lista productos con búsqueda y filtro opcional por categoría."""
    busqueda = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()
    condiciones, parametros = [], []
    if busqueda:
        condiciones.append("p.ProductName LIKE ?")
        parametros.append(f"%{busqueda}%")
    if categoria.isdigit():
        condiciones.append("p.CategoryID = ?")
        parametros.append(int(categoria))
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    filas = consultar(
        f"""
        SELECT p.ProductID, p.ProductName, p.SupplierID, p.CategoryID,
               p.QuantityPerUnit, p.UnitPrice, p.UnitsInStock,
               p.UnitsOnOrder, p.ReorderLevel, p.Discontinued,
               s.CompanyName AS SupplierName, c.CategoryName
        FROM Products p
        LEFT JOIN Suppliers s ON s.SupplierID = p.SupplierID
        LEFT JOIN Categories c ON c.CategoryID = p.CategoryID
        {where}
        ORDER BY p.ProductName
        """,
        parametros,
    )
    return render_template(
        "productos.html",
        titulo="Productos",
        productos=filas,
        categorias=consultar(
            "SELECT CategoryID, CategoryName FROM Categories ORDER BY CategoryName"
        ),
        proveedores=consultar(
            "SELECT SupplierID, CompanyName FROM Suppliers ORDER BY CompanyName"
        ),
        q=busqueda,
        categoria_seleccionada=categoria,
    )


def datos_producto() -> tuple:
    """Valida el formulario en el orden utilizado por INSERT y UPDATE."""
    return (
        texto("product_name", 40, True),
        entero("supplier_id", 1),
        entero("category_id", 1),
        texto("quantity_per_unit", 20),
        decimal_positivo("unit_price"),
        entero("units_in_stock"),
        entero("units_on_order"),
        entero("reorder_level"),
        1 if request.form.get("discontinued") == "1" else 0,
    )


def producto_nuevo():
    try:
        ejecutar(
            """
            INSERT INTO Products
                (ProductName, SupplierID, CategoryID, QuantityPerUnit, UnitPrice,
                 UnitsInStock, UnitsOnOrder, ReorderLevel, Discontinued)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            datos_producto(),
        )
        flash("Producto agregado correctamente.", "success")
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "agregar el producto"), "danger")
    return redirect(url_for("productos"))


def producto_editar(producto_id):
    try:
        afectadas = ejecutar(
            """
            UPDATE Products SET ProductName=?, SupplierID=?, CategoryID=?,
                QuantityPerUnit=?, UnitPrice=?, UnitsInStock=?, UnitsOnOrder=?,
                ReorderLevel=?, Discontinued=?
            WHERE ProductID=?
            """,
            datos_producto() + (producto_id,),
        )
        flash(
            "Producto actualizado correctamente." if afectadas else "El producto ya no existe.",
            "success" if afectadas else "warning",
        )
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "editar el producto"), "danger")
    return redirect(url_for("productos"))


def producto_eliminar(producto_id):
    try:
        afectadas = ejecutar("DELETE FROM Products WHERE ProductID=?", (producto_id,))
        flash(
            "Producto eliminado correctamente." if afectadas else "El producto ya no existe.",
            "success" if afectadas else "warning",
        )
    except pyodbc.Error as error:
        flash(mensaje_error_sql(error, "eliminar el producto"), "danger")
    return redirect(url_for("productos"))


def registrar_rutas(app):
    app.add_url_rule("/productos", endpoint="productos", view_func=productos)
    app.add_url_rule(
        "/productos/nuevo",
        endpoint="producto_nuevo",
        view_func=producto_nuevo,
        methods=["POST"],
    )
    app.add_url_rule(
        "/productos/<int:producto_id>/editar",
        endpoint="producto_editar",
        view_func=producto_editar,
        methods=["POST"],
    )
    app.add_url_rule(
        "/productos/<int:producto_id>/eliminar",
        endpoint="producto_eliminar",
        view_func=producto_eliminar,
        methods=["POST"],
    )
