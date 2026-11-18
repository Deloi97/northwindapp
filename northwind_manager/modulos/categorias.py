"""Consulta de categorías y sus productos asociados."""

from flask import abort, render_template

from conexion import consultar, consultar_uno


def categorias(category_id=None):
    """Muestra categorías y, si se selecciona una, sus productos."""
    filas = consultar(
        """
        SELECT c.CategoryID, c.CategoryName, c.Description,
               (SELECT COUNT(*) FROM Products p WHERE p.CategoryID = c.CategoryID) AS ProductCount
        FROM Categories c
        ORDER BY c.CategoryName
        """
    )
    seleccionada, productos_asociados = None, []
    if category_id is not None:
        seleccionada = consultar_uno(
            "SELECT CategoryID, CategoryName, Description FROM Categories WHERE CategoryID=?",
            (category_id,),
        )
        if seleccionada is None:
            abort(404)
        productos_asociados = consultar(
            """
            SELECT ProductID, ProductName, UnitPrice, UnitsInStock, Discontinued
            FROM Products WHERE CategoryID=? ORDER BY ProductName
            """,
            (category_id,),
        )
    return render_template(
        "categorias.html",
        titulo="Categorías",
        categorias=filas,
        seleccionada=seleccionada,
        productos=productos_asociados,
    )


def registrar_rutas(app):
    app.add_url_rule("/categorias", endpoint="categorias", view_func=categorias)
    app.add_url_rule(
        "/categorias/<int:category_id>",
        endpoint="categorias",
        view_func=categorias,
    )
