"""Validación compartida de formularios y mensajes de error."""

from decimal import Decimal, InvalidOperation

from flask import request


def texto(nombre: str, maximo: int, obligatorio: bool = False) -> str | None:
    """Lee, limpia y valida un campo de texto del formulario actual."""
    valor = request.form.get(nombre, "").strip()
    if obligatorio and not valor:
        raise ValueError(f"El campo {nombre.replace('_', ' ')} es obligatorio.")
    if len(valor) > maximo:
        raise ValueError(
            f"El campo {nombre.replace('_', ' ')} acepta máximo {maximo} caracteres."
        )
    return valor or None


def entero(nombre: str, minimo: int = 0, obligatorio: bool = False) -> int | None:
    """Convierte un campo a entero y comprueba su valor mínimo."""
    valor = request.form.get(nombre, "").strip()
    if not valor and not obligatorio:
        return None
    try:
        numero = int(valor)
    except ValueError as exc:
        raise ValueError(
            f"El campo {nombre.replace('_', ' ')} debe ser un número entero."
        ) from exc
    if numero < minimo:
        raise ValueError(
            f"El campo {nombre.replace('_', ' ')} debe ser mayor o igual a {minimo}."
        )
    return numero


def decimal_positivo(nombre: str, obligatorio: bool = False) -> Decimal | None:
    """Valida precios positivos y los redondea a dos decimales."""
    valor = request.form.get(nombre, "").strip()
    if not valor and not obligatorio:
        return None
    try:
        numero = Decimal(valor)
    except InvalidOperation as exc:
        raise ValueError(
            f"El campo {nombre.replace('_', ' ')} debe ser numérico."
        ) from exc
    if numero < 0:
        raise ValueError(f"El campo {nombre.replace('_', ' ')} no puede ser negativo.")
    return numero.quantize(Decimal("0.01"))


def mensaje_error_sql(error: Exception, accion: str) -> str:
    """Traduce errores frecuentes de SQL Server a mensajes comprensibles."""
    mensaje = str(error).lower()
    if "reference constraint" in mensaje or "foreign key" in mensaje or "conflicted" in mensaje:
        return f"No se pudo {accion} porque el registro tiene información relacionada."
    if "duplicate" in mensaje or "primary key" in mensaje or "unique" in mensaje:
        return "Ya existe un registro con ese identificador."
    return (
        f"No se pudo {accion}. SQL Server devolvió un error; "
        "revisa la configuración y los datos."
    )


def mensaje_error_conexion(error: Exception) -> str:
    """Convierte errores habituales de conexión ODBC a mensajes en español."""
    detalle = str(error).lower()
    if "login failed" in detalle or "inicio de sesión" in detalle:
        return "SQL Server rechazó el usuario o la contraseña configurados."
    if "server is not found" in detalle or "servidor no se encontró" in detalle:
        return "No se encontró la instancia de SQL Server. Revisa el nombre del servidor."
    if "data source name not found" in detalle or "driver" in detalle and "not found" in detalle:
        return "No se encontró el controlador ODBC configurado en el archivo .env."
    if "cannot open database" in detalle or "no se puede abrir la base de datos" in detalle:
        return "No se pudo abrir la base Northwind con el usuario configurado."
    if "timeout" in detalle or "tiempo de espera" in detalle:
        return "SQL Server tardó demasiado en responder. Comprueba que el servicio esté iniciado."
    if "single user mode" in detalle or "modo de usuario único" in detalle:
        return "SQL Server está ocupado por otra conexión en modo de usuario único."
    return "No fue posible conectar con SQL Server. Revisa la configuración del archivo .env."
