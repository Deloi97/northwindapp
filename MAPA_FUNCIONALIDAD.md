# Mapa de funcionalidad

La aplicación está dividida por apartado. Para encontrar una función, abre el
archivo indicado en esta tabla:

| Funcionalidad | Archivo principal | Qué contiene |
|---|---|---|
| Inicio y cierre de sesión | `northwind_manager/modulos/autenticacion.py` | Validación del usuario, intentos fallidos, creación y cierre de la sesión |
| Seguridad general | `northwind_manager/seguridad.py` | Protección CSRF, acceso obligatorio, filtros de fecha y moneda |
| Panel y diagnóstico | `northwind_manager/modulos/panel.py` | Estadísticas, últimos pedidos y prueba de SQL Server |
| Productos | `northwind_manager/modulos/productos.py` | Listar, buscar, filtrar, crear, editar y eliminar |
| Clientes | `northwind_manager/modulos/clientes.py` | Listar, buscar, crear, editar y eliminar |
| Proveedores | `northwind_manager/modulos/proveedores.py` | Listar, buscar, crear y editar |
| Categorías | `northwind_manager/modulos/categorias.py` | Listado y productos asociados a cada categoría |
| Pedidos | `northwind_manager/modulos/pedidos.py` | Búsqueda, paginación y API del detalle de un pedido |
| Excel | `northwind_manager/modulos/excel.py` | Rutas y operaciones de importación/exportación |
| Validación de Excel | `importacion_excel.py` | Encabezados, tipos y validación de las filas cargadas |
| Creación de Excel | `exportacion_excel.py` | Formato y generación del archivo descargable |
| Base de datos | `conexion.py` | Cadena ODBC, consultas, transacciones y diagnóstico |
| Validaciones comunes | `northwind_manager/validaciones.py` | Texto, enteros, decimales y mensajes de error |
| Errores HTTP | `northwind_manager/errores.py` | Pantallas 400, 404, 413 y 500 |
| Configuración Flask | `northwind_manager/__init__.py` | Clave de sesión, límite de archivo y registro de módulos |
| Inicio del programa | `app.py` | Crea la aplicación y abre el servidor local |

## Recorrido de una petición

1. `app.py` crea la aplicación.
2. `northwind_manager/__init__.py` registra seguridad, módulos y errores.
3. `northwind_manager/seguridad.py` valida la sesión y el token CSRF.
4. El archivo del apartado atiende la ruta y usa `conexion.py` para consultar o modificar SQL Server.
5. Flask muestra la plantilla correspondiente desde `templates/`.

Las direcciones web se conservaron. Por ejemplo, `/productos`, `/clientes` y
`/iniciar-sesion` funcionan igual que antes; únicamente cambió la organización
interna del código.
