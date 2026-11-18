"""Lectura y validación de las plantillas Excel de Northwind Manager.

La aplicación valida todas las filas antes de ejecutar cambios en SQL Server.
Así, un archivo con un dato incorrecto no deja una importación a medias.
"""

from decimal import Decimal, InvalidOperation
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


# Los encabezados deben coincidir con los archivos que descarga la aplicación.
COLUMNAS_PRODUCTOS = [
    ("ProductID", "Identificador"), ("ProductName", "Producto"),
    ("CategoryID", "Id categoría"), ("CategoryName", "Categoría"),
    ("SupplierID", "Id proveedor"), ("SupplierName", "Proveedor"),
    ("QuantityPerUnit", "Presentación"), ("UnitPrice", "Precio unitario"),
    ("UnitsInStock", "Existencias"), ("UnitsOnOrder", "Unidades pedidas"),
    ("ReorderLevel", "Nivel de reorden"), ("Discontinued", "Descontinuado"),
]

COLUMNAS_CLIENTES = [
    ("CustomerID", "Identificador"), ("CompanyName", "Empresa"),
    ("ContactName", "Contacto"), ("ContactTitle", "Cargo"),
    ("Address", "Dirección"), ("City", "Ciudad"), ("Region", "Región"),
    ("PostalCode", "Código postal"), ("Country", "País"),
    ("Phone", "Teléfono"), ("Fax", "Fax"),
]

COLUMNAS_PROVEEDORES = [
    ("SupplierID", "Identificador"), ("CompanyName", "Empresa"),
    ("ContactName", "Contacto"), ("ContactTitle", "Cargo"),
    ("Address", "Dirección"), ("City", "Ciudad"), ("Region", "Región"),
    ("PostalCode", "Código postal"), ("Country", "País"),
    ("Phone", "Teléfono"), ("Fax", "Fax"), ("HomePage", "Página web"),
]

COLUMNAS_POR_TIPO = {
    "productos": COLUMNAS_PRODUCTOS,
    "clientes": COLUMNAS_CLIENTES,
    "proveedores": COLUMNAS_PROVEEDORES,
}


def _texto(valor, maximo: int, campo: str, fila: int, obligatorio: bool = False):
    """Limpia un texto de Excel y comprueba su longitud."""
    texto = "" if valor is None else str(valor).strip()
    if obligatorio and not texto:
        raise ValueError(f"Fila {fila}: el campo {campo} es obligatorio.")
    if len(texto) > maximo:
        raise ValueError(f"Fila {fila}: {campo} acepta máximo {maximo} caracteres.")
    return texto or None


def _entero(valor, campo: str, fila: int, minimo: int = 0):
    """Convierte números de Excel, incluso si llegan como 1.0, a enteros."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        numero_decimal = Decimal(str(valor))
        if numero_decimal != numero_decimal.to_integral_value():
            raise ValueError
        numero = int(numero_decimal)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Fila {fila}: {campo} debe ser un número entero.") from None
    if numero < minimo:
        raise ValueError(f"Fila {fila}: {campo} debe ser mayor o igual a {minimo}.")
    return numero


def _decimal(valor, campo: str, fila: int):
    """Convierte precios de Excel a Decimal sin aceptar valores negativos."""
    if valor is None or str(valor).strip() == "":
        return None
    try:
        numero = Decimal(str(valor))
    except InvalidOperation:
        raise ValueError(f"Fila {fila}: {campo} debe ser numérico.") from None
    if numero < 0:
        raise ValueError(f"Fila {fila}: {campo} no puede ser negativo.")
    return numero.quantize(Decimal("0.01"))


def _booleano(valor, campo: str, fila: int) -> int:
    """Acepta valores comunes de Excel para representar Sí/No."""
    if valor is None or str(valor).strip() == "":
        return 0
    normalizado = str(valor).strip().lower()
    if normalizado in {"1", "true", "sí", "si", "yes", "descontinuado"}:
        return 1
    if normalizado in {"0", "false", "no", "activo"}:
        return 0
    raise ValueError(f"Fila {fila}: {campo} debe contener Sí o No.")


def _validar_producto(datos: dict, fila: int) -> dict:
    return {
        "ProductID": _entero(datos["ProductID"], "Identificador", fila, 1),
        "ProductName": _texto(datos["ProductName"], 40, "Producto", fila, True),
        "CategoryID": _entero(datos["CategoryID"], "Id categoría", fila, 1),
        "SupplierID": _entero(datos["SupplierID"], "Id proveedor", fila, 1),
        "QuantityPerUnit": _texto(datos["QuantityPerUnit"], 20, "Presentación", fila),
        "UnitPrice": _decimal(datos["UnitPrice"], "Precio unitario", fila),
        "UnitsInStock": _entero(datos["UnitsInStock"], "Existencias", fila),
        "UnitsOnOrder": _entero(datos["UnitsOnOrder"], "Unidades pedidas", fila),
        "ReorderLevel": _entero(datos["ReorderLevel"], "Nivel de reorden", fila),
        "Discontinued": _booleano(datos["Discontinued"], "Descontinuado", fila),
        "fila_excel": fila,
    }


def _validar_cliente(datos: dict, fila: int) -> dict:
    identificador = (_texto(datos["CustomerID"], 5, "Identificador", fila, True) or "").upper()
    # La columna real es nchar(5), pero esta base contiene EDTC con cuatro letras
    # y SQL Server completa internamente el espacio restante. Se aceptan de 1 a 5.
    return {
        "CustomerID": identificador,
        "CompanyName": _texto(datos["CompanyName"], 40, "Empresa", fila, True),
        "ContactName": _texto(datos["ContactName"], 30, "Contacto", fila),
        "ContactTitle": _texto(datos["ContactTitle"], 30, "Cargo", fila),
        "Address": _texto(datos["Address"], 60, "Dirección", fila),
        "City": _texto(datos["City"], 15, "Ciudad", fila),
        "Region": _texto(datos["Region"], 15, "Región", fila),
        "PostalCode": _texto(datos["PostalCode"], 10, "Código postal", fila),
        "Country": _texto(datos["Country"], 15, "País", fila),
        "Phone": _texto(datos["Phone"], 24, "Teléfono", fila),
        "Fax": _texto(datos["Fax"], 24, "Fax", fila),
        "fila_excel": fila,
    }


def _validar_proveedor(datos: dict, fila: int) -> dict:
    return {
        "SupplierID": _entero(datos["SupplierID"], "Identificador", fila, 1),
        "CompanyName": _texto(datos["CompanyName"], 40, "Empresa", fila, True),
        "ContactName": _texto(datos["ContactName"], 30, "Contacto", fila),
        "ContactTitle": _texto(datos["ContactTitle"], 30, "Cargo", fila),
        "Address": _texto(datos["Address"], 60, "Dirección", fila),
        "City": _texto(datos["City"], 15, "Ciudad", fila),
        "Region": _texto(datos["Region"], 15, "Región", fila),
        "PostalCode": _texto(datos["PostalCode"], 10, "Código postal", fila),
        "Country": _texto(datos["Country"], 15, "País", fila),
        "Phone": _texto(datos["Phone"], 24, "Teléfono", fila),
        "Fax": _texto(datos["Fax"], 24, "Fax", fila),
        "HomePage": _texto(datos["HomePage"], 255, "Página web", fila),
        "fila_excel": fila,
    }


VALIDADORES = {
    "productos": _validar_producto,
    "clientes": _validar_cliente,
    "proveedores": _validar_proveedor,
}


def leer_excel(archivo, tipo: str) -> list[dict]:
    """Lee la primera hoja, valida encabezados y devuelve filas preparadas."""
    if tipo not in COLUMNAS_POR_TIPO:
        raise ValueError("El apartado solicitado no admite importación.")
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except (BadZipFile, InvalidFileException, OSError, ValueError):
        raise ValueError("El archivo no es un libro de Excel .xlsx válido.") from None

    hoja = libro.active
    columnas = COLUMNAS_POR_TIPO[tipo]
    esperados = [encabezado for _clave, encabezado in columnas]
    recibidos = [str(celda.value).strip() if celda.value is not None else "" for celda in hoja[1]]
    if recibidos[:len(esperados)] != esperados:
        raise ValueError("Los encabezados fueron modificados. Descarga nuevamente la plantilla del apartado.")

    registros = []
    for numero_fila, valores in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
        valores_utiles = valores[:len(columnas)]
        if not any(valor is not None and str(valor).strip() != "" for valor in valores_utiles):
            continue
        datos = {clave: valores_utiles[indice] for indice, (clave, _titulo) in enumerate(columnas)}
        registros.append(VALIDADORES[tipo](datos, numero_fila))
        if len(registros) > 2000:
            raise ValueError("El archivo supera el límite de 2,000 filas por importación.")

    if not registros:
        raise ValueError("El archivo no contiene filas para importar.")
    return registros
