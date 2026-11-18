"""Registro central de los módulos funcionales de Northwind Manager."""

from . import autenticacion, categorias, clientes, excel, panel, pedidos, productos, proveedores


def registrar_modulos(app):
    """Registra todas las rutas conservando sus nombres y direcciones originales."""
    autenticacion.registrar_rutas(app)
    panel.registrar_rutas(app)
    excel.registrar_rutas(app)
    productos.registrar_rutas(app)
    clientes.registrar_rutas(app)
    proveedores.registrar_rutas(app)
    categorias.registrar_rutas(app)
    pedidos.registrar_rutas(app)
