"""Listado, paginación y detalle de pedidos."""

import math
from datetime import date, datetime
from decimal import Decimal

from flask import jsonify, render_template, request

from conexion import consultar, consultar_uno


def pagina_actual() -> int:
    """Obtiene una página válida desde la URL."""
    try:
        return max(1, int(request.args.get("pagina", 1)))
    except ValueError:
        return 1


def pedidos():
    """Lista pedidos, permite buscarlos y los divide en páginas de 20 filas."""
    busqueda = request.args.get("q", "").strip()
    pagina, por_pagina = pagina_actual(), 20
    condiciones, parametros = [], []
    if busqueda:
        if busqueda.isdigit():
            condiciones.append("(o.OrderID = ? OR c.CompanyName LIKE ?)")
            parametros.extend([int(busqueda), f"%{busqueda}%"])
        else:
            condiciones.append("c.CompanyName LIKE ?")
            parametros.append(f"%{busqueda}%")
    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    total = consultar_uno(
        f"SELECT COUNT(*) AS total FROM Orders o "
        f"LEFT JOIN Customers c ON c.CustomerID=o.CustomerID {where}",
        parametros,
    )["total"]
    total_paginas = max(1, math.ceil(total / por_pagina))
    pagina = min(pagina, total_paginas)
    desplazamiento = (pagina - 1) * por_pagina
    filas = consultar(
        f"""
        SELECT o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate,
               c.CompanyName, o.ShipCity, o.ShipCountry,
               COALESCE(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 0) AS OrderTotal
        FROM Orders o
        LEFT JOIN Customers c ON c.CustomerID = o.CustomerID
        LEFT JOIN [Order Details] od ON od.OrderID = o.OrderID
        {where}
        GROUP BY o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate,
                 c.CompanyName, o.ShipCity, o.ShipCountry
        ORDER BY o.OrderDate DESC, o.OrderID DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """,
        parametros + [desplazamiento, por_pagina],
    )
    return render_template(
        "pedidos.html",
        titulo="Pedidos",
        pedidos=filas,
        q=busqueda,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
    )


def _serializar(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def pedido_detalle(order_id):
    """Devuelve en JSON el encabezado y las líneas de un pedido."""
    pedido = consultar_uno(
        """
        SELECT o.OrderID, o.OrderDate, o.RequiredDate, o.ShippedDate,
               c.CompanyName, c.ContactName, o.ShipName, o.ShipAddress,
               o.ShipCity, o.ShipRegion, o.ShipPostalCode, o.ShipCountry
        FROM Orders o
        LEFT JOIN Customers c ON c.CustomerID = o.CustomerID
        WHERE o.OrderID=?
        """,
        (order_id,),
    )
    if pedido is None:
        return jsonify({"error": "El pedido no existe."}), 404
    detalles = consultar(
        """
        SELECT p.ProductName, od.UnitPrice, od.Quantity, od.Discount,
               od.UnitPrice * od.Quantity * (1 - od.Discount) AS LineTotal
        FROM [Order Details] od
        INNER JOIN Products p ON p.ProductID = od.ProductID
        WHERE od.OrderID=? ORDER BY p.ProductName
        """,
        (order_id,),
    )
    pedido_json = {clave: _serializar(valor) for clave, valor in pedido.items()}
    detalles_json = [
        {clave: _serializar(valor) for clave, valor in detalle.items()}
        for detalle in detalles
    ]
    pedido_json["detalles"] = detalles_json
    pedido_json["total"] = sum(float(detalle["LineTotal"] or 0) for detalle in detalles)
    return jsonify(pedido_json)


def registrar_rutas(app):
    app.add_url_rule("/pedidos", endpoint="pedidos", view_func=pedidos)
    app.add_url_rule(
        "/api/pedidos/<int:order_id>",
        endpoint="pedido_detalle",
        view_func=pedido_detalle,
    )
