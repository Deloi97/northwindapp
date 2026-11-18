"""Exportación e importación de archivos Excel."""

from datetime import date

import pyodbc
from flask import abort, current_app, flash, redirect, request, send_file, url_for

from conexion import conexion, consultar
from exportacion_excel import crear_excel
from importacion_excel import COLUMNAS_POR_TIPO, leer_excel
from ..validaciones import mensaje_error_sql


def exportar_excel():
    """Genera un libro con toda la información administrada."""
    try:
        productos_excel = consultar(
            """SELECT p.ProductID, p.ProductName, c.CategoryName,
                      s.CompanyName AS SupplierName, p.QuantityPerUnit, p.UnitPrice,
                      p.UnitsInStock, p.UnitsOnOrder, p.ReorderLevel, p.Discontinued
               FROM Products p
               LEFT JOIN Categories c ON c.CategoryID = p.CategoryID
               LEFT JOIN Suppliers s ON s.SupplierID = p.SupplierID
               ORDER BY p.ProductName"""
        )
        clientes_excel = consultar(
            """SELECT CustomerID, CompanyName, ContactName, ContactTitle, Address,
                      City, Region, PostalCode, Country, Phone, Fax
               FROM Customers ORDER BY CompanyName"""
        )
        proveedores_excel = consultar(
            """SELECT SupplierID, CompanyName, ContactName, ContactTitle, Address,
                      City, Region, PostalCode, Country, Phone, Fax, HomePage
               FROM Suppliers ORDER BY CompanyName"""
        )
        categorias_excel = consultar(
            """SELECT c.CategoryID, c.CategoryName, c.Description,
                      (SELECT COUNT(*) FROM Products p
                       WHERE p.CategoryID=c.CategoryID) AS ProductCount
               FROM Categories c ORDER BY c.CategoryName"""
        )
        pedidos_excel = consultar(
            """SELECT o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate,
                      c.CompanyName, o.ShipName, o.ShipCity, o.ShipCountry,
                      COALESCE(SUM(od.UnitPrice * od.Quantity *
                      (1 - od.Discount)), 0) AS OrderTotal
               FROM Orders o
               LEFT JOIN Customers c ON c.CustomerID = o.CustomerID
               LEFT JOIN [Order Details] od ON od.OrderID = o.OrderID
               GROUP BY o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate,
                        c.CompanyName, o.ShipName, o.ShipCity, o.ShipCountry
               ORDER BY o.OrderDate DESC, o.OrderID DESC"""
        )
        detalles_excel = consultar(
            """SELECT od.OrderID, o.OrderDate, c.CompanyName, p.ProductName,
                      od.UnitPrice, od.Quantity, od.Discount,
                      od.UnitPrice * od.Quantity * (1 - od.Discount) AS LineTotal
               FROM [Order Details] od
               INNER JOIN Orders o ON o.OrderID = od.OrderID
               LEFT JOIN Customers c ON c.CustomerID = o.CustomerID
               INNER JOIN Products p ON p.ProductID = od.ProductID
               ORDER BY od.OrderID DESC, p.ProductName"""
        )
        hojas = [
            {
                "nombre": "Productos",
                "columnas": [
                    ("ProductID", "Identificador"), ("ProductName", "Producto"),
                    ("CategoryName", "Categoría"), ("SupplierName", "Proveedor"),
                    ("QuantityPerUnit", "Presentación"),
                    ("UnitPrice", "Precio unitario"),
                    ("UnitsInStock", "Existencias"),
                    ("UnitsOnOrder", "Unidades pedidas"),
                    ("ReorderLevel", "Nivel de reorden"),
                    ("Discontinued", "Descontinuado"),
                ],
                "filas": productos_excel,
            },
            {
                "nombre": "Clientes",
                "columnas": [
                    ("CustomerID", "Identificador"), ("CompanyName", "Empresa"),
                    ("ContactName", "Contacto"), ("ContactTitle", "Cargo"),
                    ("Address", "Dirección"), ("City", "Ciudad"),
                    ("Region", "Región"), ("PostalCode", "Código postal"),
                    ("Country", "País"), ("Phone", "Teléfono"), ("Fax", "Fax"),
                ],
                "filas": clientes_excel,
            },
            {
                "nombre": "Proveedores",
                "columnas": [
                    ("SupplierID", "Identificador"), ("CompanyName", "Empresa"),
                    ("ContactName", "Contacto"), ("ContactTitle", "Cargo"),
                    ("Address", "Dirección"), ("City", "Ciudad"),
                    ("Region", "Región"), ("PostalCode", "Código postal"),
                    ("Country", "País"), ("Phone", "Teléfono"), ("Fax", "Fax"),
                    ("HomePage", "Página web"),
                ],
                "filas": proveedores_excel,
            },
            {
                "nombre": "Categorías",
                "columnas": [
                    ("CategoryID", "Identificador"), ("CategoryName", "Categoría"),
                    ("Description", "Descripción"),
                    ("ProductCount", "Cantidad de productos"),
                ],
                "filas": categorias_excel,
            },
            {
                "nombre": "Pedidos",
                "columnas": [
                    ("OrderID", "Número de pedido"),
                    ("OrderDate", "Fecha del pedido"),
                    ("RequiredDate", "Fecha requerida"),
                    ("ShippedDate", "Fecha de envío"),
                    ("CompanyName", "Cliente"), ("ShipName", "Destinatario"),
                    ("ShipCity", "Ciudad de envío"),
                    ("ShipCountry", "País de envío"),
                    ("OrderTotal", "Total del pedido"),
                ],
                "filas": pedidos_excel,
            },
            {
                "nombre": "Detalle de pedidos",
                "columnas": [
                    ("OrderID", "Número de pedido"),
                    ("OrderDate", "Fecha del pedido"),
                    ("CompanyName", "Cliente"), ("ProductName", "Producto"),
                    ("UnitPrice", "Precio unitario"), ("Quantity", "Cantidad"),
                    ("Discount", "Descuento"), ("LineTotal", "Total de la línea"),
                ],
                "filas": detalles_excel,
            },
        ]
        return send_file(
            crear_excel(hojas),
            as_attachment=True,
            download_name=f"Northwind_{date.today().isoformat()}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except (pyodbc.Error, ValueError) as error:
        current_app.logger.exception("No fue posible generar el archivo de Excel")
        flash(mensaje_error_sql(error, "crear el archivo de Excel"), "danger")
        return redirect(url_for("dashboard"))


def _datos_excel_apartado(tipo: str):
    """Obtiene las filas del apartado respetando los filtros visibles."""
    busqueda = request.args.get("q", "").strip()
    if tipo == "productos":
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
            f"""SELECT p.ProductID, p.ProductName, p.CategoryID, c.CategoryName,
                       p.SupplierID, s.CompanyName AS SupplierName, p.QuantityPerUnit,
                       p.UnitPrice, p.UnitsInStock, p.UnitsOnOrder,
                       p.ReorderLevel, p.Discontinued
                FROM Products p
                LEFT JOIN Categories c ON c.CategoryID=p.CategoryID
                LEFT JOIN Suppliers s ON s.SupplierID=p.SupplierID
                {where} ORDER BY p.ProductName""",
            parametros,
        )
        return "Productos", filas
    if tipo == "clientes":
        where, parametros = "", []
        if busqueda:
            where = "WHERE CompanyName LIKE ? OR ContactName LIKE ?"
            parametros = [f"%{busqueda}%", f"%{busqueda}%"]
        filas = consultar(
            f"""SELECT CustomerID, CompanyName, ContactName, ContactTitle, Address,
                       City, Region, PostalCode, Country, Phone, Fax
                FROM Customers {where} ORDER BY CompanyName""",
            parametros,
        )
        return "Clientes", filas
    if tipo == "proveedores":
        where, parametros = "", []
        if busqueda:
            where = "WHERE CompanyName LIKE ? OR ContactName LIKE ?"
            parametros = [f"%{busqueda}%", f"%{busqueda}%"]
        filas = consultar(
            f"""SELECT SupplierID, CompanyName, ContactName, ContactTitle, Address,
                       City, Region, PostalCode, Country, Phone, Fax, HomePage
                FROM Suppliers {where} ORDER BY CompanyName""",
            parametros,
        )
        return "Proveedores", filas
    abort(404)


def exportar_apartado_excel(tipo):
    """Descarga un Excel del apartado actual que sirve como plantilla."""
    if tipo not in COLUMNAS_POR_TIPO:
        abort(404)
    try:
        nombre_hoja, filas = _datos_excel_apartado(tipo)
        archivo = crear_excel([{
            "nombre": nombre_hoja,
            "columnas": COLUMNAS_POR_TIPO[tipo],
            "filas": filas,
        }])
        return send_file(
            archivo,
            as_attachment=True,
            download_name=f"Plantilla_{nombre_hoja}_{date.today().isoformat()}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except (pyodbc.Error, ValueError) as error:
        current_app.logger.exception("No fue posible exportar el apartado %s", tipo)
        flash(mensaje_error_sql(error, "crear el archivo de Excel"), "danger")
        return redirect(url_for(tipo))


def _importar_productos(cursor, registros):
    creados = actualizados = 0
    for registro in registros:
        valores = (
            registro["ProductName"], registro["SupplierID"], registro["CategoryID"],
            registro["QuantityPerUnit"], registro["UnitPrice"],
            registro["UnitsInStock"], registro["UnitsOnOrder"],
            registro["ReorderLevel"], registro["Discontinued"],
        )
        if registro["ProductID"] is None:
            cursor.execute(
                """INSERT INTO Products
                   (ProductName, SupplierID, CategoryID, QuantityPerUnit, UnitPrice,
                    UnitsInStock, UnitsOnOrder, ReorderLevel, Discontinued)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                valores,
            )
            creados += 1
        else:
            existe = cursor.execute(
                "SELECT 1 FROM Products WHERE ProductID=?", registro["ProductID"]
            ).fetchone()
            if not existe:
                raise ValueError(
                    f"Fila {registro['fila_excel']}: no existe el producto con identificador "
                    f"{registro['ProductID']}. Déjalo vacío para crear uno nuevo."
                )
            cursor.execute(
                """UPDATE Products SET ProductName=?, SupplierID=?, CategoryID=?,
                   QuantityPerUnit=?, UnitPrice=?, UnitsInStock=?, UnitsOnOrder=?,
                   ReorderLevel=?, Discontinued=? WHERE ProductID=?""",
                valores + (registro["ProductID"],),
            )
            actualizados += 1
    return creados, actualizados


def _importar_clientes(cursor, registros):
    creados = actualizados = 0
    for registro in registros:
        valores = (
            registro["CompanyName"], registro["ContactName"],
            registro["ContactTitle"], registro["Address"], registro["City"],
            registro["Region"], registro["PostalCode"], registro["Country"],
            registro["Phone"], registro["Fax"],
        )
        existe = cursor.execute(
            "SELECT 1 FROM Customers WHERE CustomerID=?", registro["CustomerID"]
        ).fetchone()
        if existe:
            cursor.execute(
                """UPDATE Customers SET CompanyName=?, ContactName=?, ContactTitle=?,
                   Address=?, City=?, Region=?, PostalCode=?, Country=?, Phone=?, Fax=?
                   WHERE CustomerID=?""",
                valores + (registro["CustomerID"],),
            )
            actualizados += 1
        else:
            cursor.execute(
                """INSERT INTO Customers
                   (CustomerID, CompanyName, ContactName, ContactTitle, Address,
                    City, Region, PostalCode, Country, Phone, Fax)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (registro["CustomerID"],) + valores,
            )
            creados += 1
    return creados, actualizados


def _importar_proveedores(cursor, registros):
    creados = actualizados = 0
    for registro in registros:
        valores = (
            registro["CompanyName"], registro["ContactName"],
            registro["ContactTitle"], registro["Address"], registro["City"],
            registro["Region"], registro["PostalCode"], registro["Country"],
            registro["Phone"], registro["Fax"], registro["HomePage"],
        )
        if registro["SupplierID"] is None:
            cursor.execute(
                """INSERT INTO Suppliers
                   (CompanyName, ContactName, ContactTitle, Address, City, Region,
                    PostalCode, Country, Phone, Fax, HomePage)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                valores,
            )
            creados += 1
        else:
            existe = cursor.execute(
                "SELECT 1 FROM Suppliers WHERE SupplierID=?", registro["SupplierID"]
            ).fetchone()
            if not existe:
                raise ValueError(
                    f"Fila {registro['fila_excel']}: no existe el proveedor con identificador "
                    f"{registro['SupplierID']}. Déjalo vacío para crear uno nuevo."
                )
            cursor.execute(
                """UPDATE Suppliers SET CompanyName=?, ContactName=?, ContactTitle=?,
                   Address=?, City=?, Region=?, PostalCode=?, Country=?, Phone=?,
                   Fax=?, HomePage=? WHERE SupplierID=?""",
                valores + (registro["SupplierID"],),
            )
            actualizados += 1
    return creados, actualizados


IMPORTADORES = {
    "productos": _importar_productos,
    "clientes": _importar_clientes,
    "proveedores": _importar_proveedores,
}


def importar_apartado_excel(tipo):
    """Valida el Excel y aplica todos sus cambios en una transacción."""
    if tipo not in IMPORTADORES:
        abort(404)
    archivo = request.files.get("archivo_excel")
    if archivo is None or not archivo.filename:
        flash("Selecciona un archivo de Excel para importar.", "warning")
        return redirect(url_for(tipo))
    if not archivo.filename.lower().endswith(".xlsx"):
        flash("El archivo debe tener la extensión .xlsx.", "warning")
        return redirect(url_for(tipo))
    try:
        registros = leer_excel(archivo, tipo)
        with conexion() as cn:
            creados, actualizados = IMPORTADORES[tipo](cn.cursor(), registros)
        flash(
            f"Importación terminada: {creados} registros creados y "
            f"{actualizados} actualizados.",
            "success",
        )
    except ValueError as error:
        flash(str(error), "warning")
    except pyodbc.Error as error:
        current_app.logger.exception("No fue posible importar el archivo de %s", tipo)
        flash(mensaje_error_sql(error, "importar el archivo de Excel"), "danger")
    return redirect(url_for(tipo))


def registrar_rutas(app):
    app.add_url_rule("/exportar/excel", endpoint="exportar_excel", view_func=exportar_excel)
    app.add_url_rule(
        "/exportar/<string:tipo>/excel",
        endpoint="exportar_apartado_excel",
        view_func=exportar_apartado_excel,
    )
    app.add_url_rule(
        "/importar/<string:tipo>/excel",
        endpoint="importar_apartado_excel",
        view_func=importar_apartado_excel,
        methods=["POST"],
    )
