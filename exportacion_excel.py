"""Herramientas para convertir consultas de Northwind en un archivo de Excel.

Este módulo no consulta la base de datos. Recibe las filas que ``app.py`` ya
obtuvo de SQL Server y se encarga únicamente de presentarlas en hojas ordenadas.
"""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# Colores compartidos por todas las hojas para conservar el diseño de la web.
COLOR_ENCABEZADO = "17365D"
COLOR_FILA_PAR = "EDF3FA"
COLOR_BORDE = "D9E2F0"


def _valor_excel(valor):
    """Convierte tipos de SQL/Python a valores compatibles con openpyxl."""
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _formato_segun_encabezado(encabezado: str) -> str | None:
    """Selecciona un formato de celda usando el nombre visible de la columna."""
    texto = encabezado.lower()
    if "fecha" in texto:
        return "dd/mm/yyyy"
    if "precio" in texto or "total" in texto or "importe" in texto:
        return '$#,##0.00'
    if "descuento" in texto:
        return "0%"
    return None


def _agregar_hoja(libro: Workbook, nombre: str, columnas: list[tuple], filas: list[dict]):
    """Crea una hoja con encabezado, filas, filtros y anchos automáticos.

    Cada elemento de ``columnas`` contiene la clave devuelta por SQL y el texto
    en español que verá el usuario, por ejemplo ``("ProductName", "Producto")``.
    """
    hoja = libro.create_sheet(title=nombre[:31])
    borde_fino = Side(style="thin", color=COLOR_BORDE)

    # Primera fila: títulos visibles de las columnas.
    for numero, (_clave, encabezado) in enumerate(columnas, start=1):
        celda = hoja.cell(row=1, column=numero, value=encabezado)
        celda.fill = PatternFill("solid", fgColor=COLOR_ENCABEZADO)
        celda.font = Font(color="FFFFFF", bold=True)
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = Border(bottom=borde_fino)

    # Resto de las filas: se respeta el mismo orden definido en ``columnas``.
    for numero_fila, fila in enumerate(filas, start=2):
        for numero_columna, (clave, encabezado) in enumerate(columnas, start=1):
            valor = _valor_excel(fila.get(clave))
            celda = hoja.cell(row=numero_fila, column=numero_columna, value=valor)
            celda.alignment = Alignment(vertical="top")
            celda.border = Border(bottom=borde_fino)
            if numero_fila % 2 == 0:
                celda.fill = PatternFill("solid", fgColor=COLOR_FILA_PAR)

            formato = _formato_segun_encabezado(encabezado)
            if formato and isinstance(valor, (int, float, Decimal, date, datetime)):
                celda.number_format = formato

    # Mantiene el encabezado visible al desplazarse y permite filtrar en Excel.
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    hoja.row_dimensions[1].height = 24

    # Calcula un ancho legible sin permitir columnas excesivamente grandes.
    for numero_columna, (_clave, encabezado) in enumerate(columnas, start=1):
        longitud = len(encabezado)
        for celda in hoja[get_column_letter(numero_columna)]:
            if celda.value is not None:
                longitud = max(longitud, len(str(celda.value)))
        hoja.column_dimensions[get_column_letter(numero_columna)].width = min(longitud + 3, 45)


def crear_excel(hojas: list[dict]) -> BytesIO:
    """Construye el libro completo y lo devuelve listo para descargar."""
    libro = Workbook()
    # openpyxl crea una hoja vacía por defecto; se elimina antes de agregar las reales.
    libro.remove(libro.active)

    for configuracion in hojas:
        _agregar_hoja(
            libro,
            configuracion["nombre"],
            configuracion["columnas"],
            configuracion["filas"],
        )

    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)
    return archivo
