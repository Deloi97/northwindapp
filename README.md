# Northwind Manager

Aplicación web académica para consultar y administrar la base de datos clásica **Northwind** en Microsoft SQL Server. Está construida con Python, Flask, pyodbc, Bootstrap 5 y JavaScript sin frameworks adicionales.

## Funciones incluidas

- Inicio de sesión administrativo usando las cuentas existentes de `Usuario`.
- Protección de todos los módulos, cierre de sesión y límite de intentos fallidos.
- Exportación e importación por apartado para productos, clientes/contactos y proveedores.
- Los Excel descargados funcionan como plantillas para crear o actualizar registros.
- Panel principal con totales reales de productos, clientes, proveedores y pedidos.
- Productos: consulta, búsqueda, filtro por categoría, alta, edición y eliminación.
- Clientes: consulta, búsqueda, alta, edición y eliminación.
- Proveedores: consulta, búsqueda, alta y edición.
- Categorías: conteo y consulta de los productos asociados.
- Pedidos: búsqueda, paginación, detalle de líneas y cálculo de totales con descuentos.
- Diagnóstico de conexión y comprobación de las tablas necesarias.
- Consultas SQL parametrizadas, validación de formularios y protección CSRF.
- Interfaz responsiva con Bootstrap 5 y Bootstrap Icons mediante CDN.

## Requisitos previos

1. Python 3.10 o posterior.
2. Microsoft SQL Server en ejecución.
3. La base de datos clásica `Northwind` ya importada.
4. Microsoft ODBC Driver 17 for SQL Server, que es el controlador detectado en este equipo.

La aplicación espera estas tablas: `Products`, `Customers`, `Suppliers`, `Categories`, `Orders` y `Order Details`. No crea ni modifica la estructura de la base de datos.

## 1. Crear el entorno e instalar dependencias

Abre PowerShell dentro de esta carpeta y ejecuta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación, puedes instalar y ejecutar usando directamente `.\.venv\Scripts\python.exe`.

## 2. Configurar SQL Server

Crea el archivo local de configuración:

```powershell
Copy-Item .env.example .env
```

Edita `.env` según tu instancia. Para autenticación integrada de Windows:

```dotenv
DB_SERVER=.\SQLEXPRESS
DB_NAME=Northwind
DB_AUTH=windows
DB_DRIVER=ODBC Driver 17 for SQL Server
```

Para autenticación propia de SQL Server:

```dotenv
DB_SERVER=localhost
DB_NAME=Northwind
DB_AUTH=sql
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_DRIVER=ODBC Driver 17 for SQL Server
```

El archivo `.env` está ignorado por Git para que la contraseña no se publique. No escribas credenciales reales en `.env.example`.

Para consultar los controladores ODBC instalados en Windows puedes abrir **Orígenes de datos ODBC (64 bits)** o ejecutar:

```powershell
Get-OdbcDriver | Where-Object Name -Like '*SQL Server*'
```

## 3. Ejecutar

Con el entorno virtual activo:

```powershell
python app.py
```

Abre en el navegador:

<http://127.0.0.1:5000>

La página <http://127.0.0.1:5000/diagnostico> prueba la conexión y muestra si falta alguna tabla.

## Organización del proyecto

```text
Northwind Manager/
├── app.py                  Punto de entrada (crea e inicia la aplicación)
├── conexion.py             Configuración y acceso centralizado a SQL Server
├── importacion_excel.py    Lectura y validación de archivos Excel
├── exportacion_excel.py    Creación de libros Excel
├── MAPA_FUNCIONALIDAD.md   Guía rápida para localizar cada función
├── northwind_manager/
│   ├── __init__.py         Configuración y fábrica de la aplicación
│   ├── seguridad.py        Sesión, CSRF y filtros de las plantillas
│   ├── validaciones.py     Validaciones y mensajes compartidos
│   ├── errores.py          Páginas de error 400, 404, 413 y 500
│   └── modulos/
│       ├── autenticacion.py  Login y cierre de sesión
│       ├── panel.py          Panel principal y diagnóstico
│       ├── productos.py      Consulta y CRUD de productos
│       ├── clientes.py       Consulta y CRUD de clientes
│       ├── proveedores.py    Consulta y CRUD de proveedores
│       ├── categorias.py     Categorías y productos asociados
│       ├── pedidos.py        Listado y detalle de pedidos
│       └── excel.py          Importación y exportación
├── requirements.txt        Dependencias de Python
├── .env.example            Plantilla de configuración sin credenciales
├── static/
│   ├── css/styles.css      Diseño visual responsivo
│   └── js/app.js           Modales, confirmaciones y detalle de pedidos
└── templates/
    ├── base.html           Menú, barra superior y estructura común
    └── *.html              Vistas de cada módulo
```

## Puntos importantes para explicar al profesor

- El acceso se valida con una consulta parametrizada sobre `Usuario`; la contraseña nunca se guarda en la sesión.
- Cada importación de Excel valida todas las filas antes de abrir una transacción. Si una fila falla, no se guarda ninguna.
- `conexion.py` genera la cadena ODBC desde variables de entorno y controla `commit`, `rollback` y cierre de cada conexión.
- `app.py` solo inicia el sistema; cada grupo de rutas está en su archivo dentro de `northwind_manager/modulos/`.
- Las búsquedas usan parámetros `?` de pyodbc; los datos escritos por el usuario nunca se concatenan al SQL.
- Los `JOIN` relacionan productos con proveedores/categorías y pedidos con clientes, detalles y productos.
- El total de un pedido se calcula como `UnitPrice * Quantity * (1 - Discount)`.
- `templates/base.html` reutiliza el mismo menú y encabezado en todas las pantallas.
- `static/js/app.js` llena los modales de edición y obtiene el detalle del pedido mediante una ruta JSON.
- Cuando SQL Server rechaza una eliminación por una clave foránea, la interfaz conserva el registro y muestra un mensaje comprensible.

## Notas sobre variantes de Northwind

Esta implementación usa los nombres de la versión clásica de Microsoft, incluida la tabla `[Order Details]` con espacio. Si la copia instalada usa, por ejemplo, `OrderDetails`, primero confirma el esquema en SQL Server y ajusta ese nombre en las consultas de `northwind_manager/modulos/pedidos.py` y `northwind_manager/modulos/excel.py`. La ruta `/diagnostico` ayuda a detectar esta diferencia.
