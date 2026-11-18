"""Conexión y utilidades de acceso a Microsoft SQL Server.

Toda la aplicación usa este módulo para evitar repetir la cadena de conexión y
para garantizar que las transacciones se confirmen o reviertan correctamente.
"""

import os
from contextlib import contextmanager

import pyodbc
from dotenv import load_dotenv


load_dotenv()


def _valor_odbc(valor: str) -> str:
    """Protege valores con espacios o punto y coma dentro de la cadena ODBC.

    Las llaves son la forma estándar de ODBC para delimitar valores como el
    nombre del controlador o una contraseña que pueda contener caracteres raros.
    """
    return "{" + valor.replace("}", "}}") + "}"


def crear_cadena_conexion() -> str:
    """Construye la cadena de conexión a partir del archivo .env.

    Mantener estos datos fuera del código permite cambiar de computadora,
    instancia o autenticación sin modificar las consultas de la aplicación.
    """
    driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server").strip()
    servidor = os.getenv("DB_SERVER", "localhost").strip()
    base_datos = os.getenv("DB_NAME", "Northwind").strip()
    autenticacion = os.getenv("DB_AUTH", "windows").strip().lower()
    cifrar = os.getenv("DB_ENCRYPT", "no").strip()
    confiar_certificado = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes").strip()
    timeout = os.getenv("DB_TIMEOUT", "5").strip()

    # Estas opciones son comunes para autenticación de Windows y de SQL Server.
    partes = [
        f"DRIVER={_valor_odbc(driver)}",
        f"SERVER={_valor_odbc(servidor)}",
        f"DATABASE={_valor_odbc(base_datos)}",
        f"Encrypt={cifrar}",
        f"TrustServerCertificate={confiar_certificado}",
        f"Connection Timeout={timeout}",
    ]

    if autenticacion == "windows":
        # SQL Server utiliza la cuenta con la que se inició sesión en Windows.
        partes.append("Trusted_Connection=yes")
    elif autenticacion == "sql":
        # En este modo sí son obligatorios un usuario y una contraseña propios
        # de SQL Server. Nunca se escriben directamente en el código fuente.
        usuario = os.getenv("DB_USER", "").strip()
        contrasena = os.getenv("DB_PASSWORD", "")
        if not usuario or not contrasena:
            raise ValueError("DB_USER y DB_PASSWORD son obligatorios cuando DB_AUTH=sql.")
        partes.extend([f"UID={_valor_odbc(usuario)}", f"PWD={_valor_odbc(contrasena)}"])
    else:
        raise ValueError("DB_AUTH debe ser 'windows' o 'sql'.")

    return ";".join(partes) + ";"


def obtener_conexion() -> pyodbc.Connection:
    """Abre una conexión nueva. pyodbc administra su propio pool de conexiones.

    ``autocommit=False`` permite confirmar o revertir toda operación de forma
    explícita dentro del administrador de contexto definido abajo.
    """
    return pyodbc.connect(crear_cadena_conexion(), autocommit=False)


@contextmanager
def conexion():
    """Contexto transaccional: confirma al terminar y revierte ante un error.

    El bloque ``with conexion()`` garantiza tres cosas: confirmación (COMMIT) si
    todo salió bien, reversión (ROLLBACK) si algo falló y cierre de la conexión.
    """
    cn = obtener_conexion()
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def _filas_como_diccionarios(cursor) -> list[dict]:
    """Convierte filas de pyodbc en diccionarios fáciles de usar en Jinja."""
    columnas = [columna[0] for columna in cursor.description]
    return [dict(zip(columnas, fila)) for fila in cursor.fetchall()]


def consultar(sql: str, parametros=()) -> list[dict]:
    """Ejecuta un SELECT parametrizado y devuelve todas sus filas.

    ``cursor.execute(sql, parametros)`` asigna los valores a cada signo ?; así
    los textos escritos por el usuario nunca se interpretan como código SQL.
    """
    with conexion() as cn:
        cursor = cn.cursor()
        cursor.execute(sql, parametros)
        return _filas_como_diccionarios(cursor)


def consultar_uno(sql: str, parametros=()) -> dict | None:
    """Ejecuta un SELECT y devuelve la primera fila o None si no hubo resultado."""
    with conexion() as cn:
        cursor = cn.cursor()
        cursor.execute(sql, parametros)
        fila = cursor.fetchone()
        if fila is None:
            return None
        columnas = [columna[0] for columna in cursor.description]
        return dict(zip(columnas, fila))


def ejecutar(sql: str, parametros=()) -> int:
    """Ejecuta INSERT, UPDATE o DELETE y devuelve el número de filas afectadas.

    El administrador de contexto realiza la confirmación. Si SQL Server rechaza
    la operación, la excepción provoca automáticamente una reversión.
    """
    with conexion() as cn:
        cursor = cn.cursor()
        cursor.execute(sql, parametros)
        return cursor.rowcount


def probar_conexion() -> dict:
    """Obtiene servidor, base y usuario para diagnosticar la configuración."""
    return consultar_uno(
        "SELECT @@SERVERNAME AS servidor, DB_NAME() AS base_datos, "
        "SUSER_SNAME() AS usuario_actual"
    )


def verificar_esquema() -> dict:
    """Comprueba las tablas clásicas que esta versión de Northwind necesita.

    INFORMATION_SCHEMA es una vista del sistema: permite revisar los nombres sin
    modificar la estructura ni los registros de la base de datos.
    """
    requeridas = {"Products", "Customers", "Suppliers", "Categories", "Orders", "Order Details"}
    filas = consultar(
        """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        """
    )
    encontradas = {fila["TABLE_NAME"] for fila in filas}
    faltantes = sorted(requeridas - encontradas)
    return {
        "correcto": not faltantes,
        "encontradas": sorted(requeridas & encontradas),
        "faltantes": faltantes,
    }
