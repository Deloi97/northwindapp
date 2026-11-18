# Guía de exposición y explicación del código de Northwind Manager

Esta guía explica tanto el funcionamiento del sistema como el código que lo
hace posible. El recorrido general de una petición es:

```text
Navegador → ruta Flask → validación → consulta SQL → plantilla HTML → navegador
```

## 1. Organización general del proyecto

La aplicación está separada por responsabilidades:

```text
Northwind Manager/
├── app.py                         Inicio del programa
├── conexion.py                    Conexión y transacciones con SQL Server
├── importacion_excel.py           Lectura y validación de Excel
├── exportacion_excel.py           Creación de archivos Excel
├── northwind_manager/
│   ├── __init__.py                Creación y configuración de Flask
│   ├── seguridad.py               Sesión, CSRF y filtros de Jinja
│   ├── validaciones.py            Validación de formularios
│   ├── errores.py                 Páginas de error
│   └── modulos/
│       ├── autenticacion.py       Login y cierre de sesión
│       ├── panel.py               Panel y diagnóstico
│       ├── productos.py           CRUD de productos
│       ├── clientes.py            CRUD de clientes
│       ├── proveedores.py         CRUD de proveedores
│       ├── categorias.py          Consulta de categorías
│       ├── pedidos.py             Pedidos y detalle JSON
│       └── excel.py               Rutas de importación y exportación
├── templates/                     Pantallas HTML
└── static/                        CSS y JavaScript
```

La ventaja de esta separación es que cada archivo tiene una responsabilidad.
Si se necesita modificar el login, se abre `autenticacion.py`; si se necesita
modificar clientes, se abre `clientes.py`.

**Cómo explicarlo:** “Dividimos la aplicación por módulos para evitar un solo
archivo demasiado grande y para localizar rápidamente cada funcionalidad”.

## 2. Punto de entrada: `app.py`

El archivo comienza así:

```python
from northwind_manager import crear_app

app = crear_app()
```

`crear_app()` construye la aplicación Flask y devuelve el objeto `app`. Este
objeto contiene la configuración, las rutas, los filtros y los manejadores de
errores.

Al final se encuentra:

```python
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
```

La condición evita iniciar el servidor cuando `app.py` se importa desde una
prueba o desde otro programa. El servidor se inicia únicamente al ejecutar:

```powershell
python app.py
```

**Cómo explicarlo:** “`app.py` solamente es el punto de arranque; la lógica real
está separada dentro del paquete `northwind_manager`”.

## 3. Creación y configuración de Flask: `northwind_manager/__init__.py`

La función principal es:

```python
def crear_app(configuracion=None):
    load_dotenv()
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
```

`load_dotenv()` carga las variables del archivo `.env`. Después se crea Flask y
se indican las carpetas que contienen las plantillas y los archivos estáticos.

La configuración de seguridad incluye:

```python
app.config.from_mapping(
    SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
```

- `SECRET_KEY` firma la sesión y evita que sea modificada por el navegador.
- `MAX_CONTENT_LENGTH` limita los Excel a 5 MB.
- `PERMANENT_SESSION_LIFETIME` establece una duración de dos horas.
- `HTTPONLY` impide leer la cookie desde JavaScript.
- `SAMESITE` reduce el envío de la cookie desde páginas externas.

Finalmente se conectan las partes del sistema:

```python
registrar_seguridad(app)
registrar_modulos(app)
registrar_errores(app)
```

## 4. Registro de módulos y rutas

`northwind_manager/modulos/__init__.py` llama a la función `registrar_rutas()`
de cada apartado:

```python
def registrar_modulos(app):
    autenticacion.registrar_rutas(app)
    panel.registrar_rutas(app)
    excel.registrar_rutas(app)
    productos.registrar_rutas(app)
    clientes.registrar_rutas(app)
    proveedores.registrar_rutas(app)
    categorias.registrar_rutas(app)
    pedidos.registrar_rutas(app)
```

Cada módulo relaciona una dirección web con una función. Por ejemplo:

```python
app.add_url_rule("/productos", endpoint="productos", view_func=productos)
```

- `"/productos"` es la dirección que escribe el usuario.
- `endpoint="productos"` es el nombre usado por `url_for()`.
- `view_func=productos` es la función de Python que atiende la petición.

Una ruta que modifica información acepta únicamente `POST`:

```python
app.add_url_rule(
    "/productos/nuevo",
    endpoint="producto_nuevo",
    view_func=producto_nuevo,
    methods=["POST"],
)
```

**Cómo explicarlo:** “Las rutas `GET` consultan y muestran información; las
rutas `POST` reciben formularios y pueden modificar la base de datos”.

## 5. Login: `modulos/autenticacion.py`

La función `iniciar_sesion()` atiende tanto la pantalla como el formulario:

```python
if request.method == "POST":
    usuario = request.form.get("usuario", "").strip()
    contrasena = request.form.get("contrasena", "")
```

`request.form` contiene los valores enviados por el formulario. Se comprueba
que ambos campos tengan contenido y después se busca la cuenta:

```python
cuenta = consultar_uno(
    """
    SELECT TOP 1 IdUsuario, Nombre, Apellido, Login
    FROM Usuario
    WHERE Login = ? AND Password = ?
    """,
    (usuario, contrasena),
)
```

Los signos `?` son parámetros. El usuario y la contraseña se envían como datos,
no como parte del código SQL.

Cuando la cuenta existe se crea la sesión:

```python
session.clear()
session.permanent = True
session["usuario_id"] = cuenta["IdUsuario"]
session["usuario_login"] = cuenta["Login"]
session["usuario_nombre"] = f"{cuenta['Nombre']} {cuenta['Apellido']}".strip()
```

La contraseña no se guarda en la sesión. También existe un contador de intentos
fallidos: después de cinco errores se bloquea temporalmente el acceso durante un
minuto.

`cerrar_sesion()` ejecuta `session.clear()` y redirige al login.

**Cómo explicarlo:** “SQL Server valida las credenciales y la aplicación guarda
solamente datos públicos de la cuenta; la contraseña nunca queda en la sesión”.

## 6. Seguridad general: `seguridad.py`

### Protección de las páginas

Antes de cada petición se ejecuta:

```python
def exigir_inicio_de_sesion():
    rutas_publicas = {"iniciar_sesion", "static"}
    if request.endpoint not in rutas_publicas and "usuario_id" not in session:
        return redirect(url_for("iniciar_sesion"))
```

Solo el login y los archivos estáticos son públicos. Cualquier otra página
requiere `usuario_id` dentro de la sesión.

### Protección CSRF

La aplicación crea un token aleatorio y lo coloca en los formularios:

```python
session["csrf_token"] = secrets.token_urlsafe(32)
```

Antes de cualquier `POST`, compara el token recibido con el de la sesión:

```python
if request.method == "POST":
    esperado = session.get("csrf_token", "")
    recibido = request.form.get("csrf_token", "")
    if not hmac.compare_digest(esperado, recibido):
        abort(400)
```

Esto evita que otra página envíe formularios en nombre del usuario.

### Filtros de las plantillas

`filtro_moneda()` convierte un valor a `$1,234.00` y `filtro_fecha()` muestra
las fechas como día/mes/año. En una plantilla se utilizan así:

```jinja2
{{ producto.UnitPrice|moneda }}
{{ pedido.OrderDate|fecha }}
```

## 7. Conexión a SQL Server: `conexion.py`

`crear_cadena_conexion()` obtiene del `.env` el servidor, la base, el driver y
el tipo de autenticación. Así las credenciales no quedan escritas en el código.

```python
driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
servidor = os.getenv("DB_SERVER", "localhost")
base_datos = os.getenv("DB_NAME", "Northwind")
```

La función `conexion()` es un administrador de contexto transaccional:

```python
@contextmanager
def conexion():
    cn = obtener_conexion()
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()
```

- `yield` entrega la conexión al bloque que ejecuta la consulta.
- `commit()` confirma los cambios si no hubo errores.
- `rollback()` revierte los cambios si algo falla.
- `close()` cierra siempre la conexión.

Existen tres funciones para no repetir código:

- `consultar()` devuelve varias filas de un `SELECT`.
- `consultar_uno()` devuelve una fila o `None`.
- `ejecutar()` realiza `INSERT`, `UPDATE` o `DELETE` y devuelve las filas afectadas.

Las filas se convierten a diccionarios. Por eso en Python se puede escribir
`producto["ProductName"]` y en Jinja `producto.ProductName`.

## 8. Validaciones: `validaciones.py`

Antes de enviar datos a SQL Server se ejecutan validaciones compartidas:

```python
texto("product_name", 40, True)
entero("units_in_stock")
decimal_positivo("unit_price")
```

- `texto()` elimina espacios, revisa campos obligatorios y longitud máxima.
- `entero()` convierte el valor y verifica un mínimo.
- `decimal_positivo()` usa `Decimal`, rechaza negativos y redondea a dos decimales.

Si un dato no es válido se lanza `ValueError`. La ruta captura ese error y
muestra un mensaje con `flash()` sin ejecutar la consulta.

`mensaje_error_sql()` transforma errores técnicos, como claves foráneas o
identificadores duplicados, en mensajes entendibles para el usuario.

## 9. Código del panel: `modulos/panel.py`

`dashboard()` obtiene los cuatro totales mediante subconsultas:

```sql
SELECT
    (SELECT COUNT(*) FROM Products) AS productos,
    (SELECT COUNT(*) FROM Customers) AS clientes,
    (SELECT COUNT(*) FROM Suppliers) AS proveedores,
    (SELECT COUNT(*) FROM Orders) AS pedidos
```

También consulta los últimos cinco pedidos con `TOP 5`. Los resultados se
envían a la plantilla:

```python
return render_template(
    "dashboard.html",
    estadisticas=estadisticas,
    ultimos_pedidos=ultimos_pedidos,
)
```

`diagnostico()` usa `probar_conexion()` y `verificar_esquema()` para comprobar
el servidor y las tablas necesarias sin modificar información.

## 10. Código de productos: `modulos/productos.py`

### Consulta y filtros

La función `productos()` lee los filtros de la URL:

```python
busqueda = request.args.get("q", "").strip()
categoria = request.args.get("categoria", "").strip()
```

Las condiciones SQL se agregan solo cuando son necesarias. Los valores se
guardan por separado en `parametros`:

```python
if busqueda:
    condiciones.append("p.ProductName LIKE ?")
    parametros.append(f"%{busqueda}%")
```

La consulta usa `LEFT JOIN` para convertir claves en nombres:

```sql
FROM Products p
LEFT JOIN Suppliers s ON s.SupplierID = p.SupplierID
LEFT JOIN Categories c ON c.CategoryID = p.CategoryID
```

Se usa `LEFT JOIN` para conservar un producto aunque su proveedor o categoría
sean nulos.

### Crear

`producto_nuevo()` valida los campos y ejecuta un `INSERT`:

```python
ejecutar(
    """INSERT INTO Products (...)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    datos_producto(),
)
```

### Editar

`producto_editar(producto_id)` añade el identificador recibido en la URL al
final de los valores y ejecuta un `UPDATE ... WHERE ProductID=?`.

### Eliminar

`producto_eliminar(producto_id)` ejecuta:

```python
ejecutar("DELETE FROM Products WHERE ProductID=?", (producto_id,))
```

Si existen detalles de pedidos relacionados, SQL Server impide la eliminación
por la clave foránea y la aplicación presenta un mensaje claro.

## 11. Clientes y proveedores

`clientes.py` y `proveedores.py` siguen el mismo patrón:

```text
listar → validar formulario → insertar o actualizar → mostrar mensaje → redirigir
```

En clientes, `CustomerID` es una clave alfanumérica de hasta cinco caracteres.
Se convierte a mayúsculas al crear el registro. Durante una edición no se
modifica esta clave; solamente se actualizan los datos descriptivos.

En proveedores, `SupplierID` lo genera automáticamente SQL Server. Por eso el
formulario de alta no solicita ese identificador.

Clientes incluye eliminación. Proveedores incluye alta y edición, pero no
eliminación en la interfaz actual.

## 12. Categorías: `modulos/categorias.py`

La consulta principal devuelve cada categoría y cuenta sus productos mediante
una subconsulta:

```sql
SELECT c.CategoryID, c.CategoryName, c.Description,
       (SELECT COUNT(*) FROM Products p
        WHERE p.CategoryID = c.CategoryID) AS ProductCount
FROM Categories c
```

Cuando la URL incluye un identificador, por ejemplo `/categorias/3`, primero se
comprueba que exista. Después se consultan sus productos. Si no existe se llama
a `abort(404)`.

## 13. Pedidos: `modulos/pedidos.py`

La función `pedidos()` permite buscar por número o nombre del cliente. Para no
cargar todos los registros utiliza paginación:

```sql
ORDER BY o.OrderDate DESC, o.OrderID DESC
OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
```

`OFFSET` indica cuántas filas omitir y `FETCH NEXT` cuántas recuperar.

El total utiliza la fórmula de Northwind:

```text
UnitPrice × Quantity × (1 - Discount)
```

La ruta `/api/pedidos/<order_id>` devuelve JSON para el modal. `_serializar()`
convierte fechas a texto ISO y valores `Decimal` a números compatibles con JSON.
JavaScript consulta esta ruta con `fetch()` sin recargar la página completa.

Las relaciones principales son:

```text
Customers → Orders → Order Details → Products
```

## 14. Importación y exportación de Excel

### Lectura y validación

`importacion_excel.py` define las columnas permitidas para productos, clientes
y proveedores. `leer_excel()` comprueba:

- Que el archivo contenga una hoja válida.
- Que los encabezados coincidan con la plantilla.
- Ignora las filas completamente vacías.
- Tipos, campos obligatorios, longitudes y valores numéricos.
- Un límite máximo de 2,000 registros por importación.

### Guardado transaccional

`modulos/excel.py` valida todo antes de abrir la transacción:

```python
registros = leer_excel(archivo, tipo)
with conexion() as cn:
    creados, actualizados = IMPORTADORES[tipo](cn.cursor(), registros)
```

Si una fila falla, se ejecuta `rollback` y no queda una importación incompleta.
En productos y proveedores, un ID vacío crea un registro y uno existente lo
actualiza. En clientes, el ID es obligatorio: se actualiza si existe o se crea
si es nuevo.

### Exportación

`exportacion_excel.py` usa `openpyxl`. `crear_excel()` recibe una lista de hojas;
`_agregar_hoja()` escribe encabezados, filas, formatos, anchos y filtros. El
resultado se guarda en memoria con `BytesIO` y Flask lo descarga con
`send_file()`.

## 15. Plantillas HTML y Jinja

`templates/base.html` contiene el menú, la barra superior, los mensajes y las
referencias a CSS y JavaScript. Las demás páginas reutilizan esa estructura:

```jinja2
{% extends "base.html" %}
```

Flask envía variables con `render_template()` y Jinja las muestra:

```jinja2
{% for producto in productos %}
    {{ producto.ProductName }}
{% endfor %}
```

`url_for()` genera las direcciones usando el nombre del endpoint. Esto evita
escribir URLs manualmente en todas las plantillas.

## 16. JavaScript: `static/js/app.js`

JavaScript se encarga de la interacción visual:

1. Lee los atributos `data-record` y llena el modal de edición.
2. Configura la confirmación y la dirección para eliminar.
3. Solicita el detalle JSON de un pedido con `fetch()`.

La validación importante permanece en Python porque el JavaScript del navegador
puede ser desactivado o modificado por el usuario.

## 17. Manejo de errores: `errores.py`

La aplicación registra páginas para los códigos principales:

- `400`: formulario o token CSRF inválido.
- `404`: página o registro inexistente.
- `413`: archivo mayor de 5 MB.
- `500`: error interno inesperado.

Estas páginas evitan mostrar detalles técnicos o información sensible al
usuario final.

## 18. Ejemplo completo: editar un producto

Este es el recorrido que puede explicarse durante la exposición:

1. El usuario abre `/productos`.
2. `seguridad.py` comprueba que exista una sesión.
3. `productos()` consulta SQL Server y muestra `productos.html`.
4. JavaScript llena el modal con el producto seleccionado.
5. El formulario envía un `POST` a `/productos/<id>/editar`.
6. `seguridad.py` valida el token CSRF.
7. `datos_producto()` valida texto, enteros y precio.
8. `producto_editar()` ejecuta un `UPDATE` parametrizado.
9. `conexion()` confirma con `commit()`.
10. `flash()` guarda el mensaje y Flask redirige al listado.

Si ocurre un error SQL, `conexion()` ejecuta `rollback()` y la aplicación muestra
un mensaje sin dejar cambios parciales.

## 19. Demostración sugerida

1. Mostrar la estructura de carpetas y explicar la separación por módulos.
2. Ejecutar `python app.py` y abrir el login.
3. Iniciar sesión y enseñar los datos guardados en `session`.
4. Explicar las estadísticas del panel.
5. Buscar y filtrar productos.
6. Abrir un modal de edición y relacionarlo con la ruta `POST`.
7. Mostrar una categoría y sus productos.
8. Buscar un pedido y abrir el detalle JSON.
9. Descargar una plantilla Excel y explicar la transacción de importación.
10. Abrir `/diagnostico` para mostrar servidor, base y esquema.

## 20. Preguntas que podrían hacer durante la exposición

### ¿Por qué se usan signos `?` en SQL?

Porque son parámetros. Separan los valores escritos por el usuario del código
SQL y reducen el riesgo de inyección.

### ¿Por qué se usa `Decimal` para los precios?

Porque representa valores monetarios con precisión y evita errores habituales
de los números de punto flotante.

### ¿Cuál es la diferencia entre `commit` y `rollback`?

`commit` confirma una transacción; `rollback` deshace sus operaciones cuando
ocurre un error.

### ¿Por qué se utiliza `LEFT JOIN`?

Porque permite conservar el registro principal aunque su relación opcional sea
nula. Por ejemplo, conserva un producto aunque no tenga categoría.

### ¿Por qué el detalle del pedido usa una API JSON?

Para cargar las líneas solo cuando se abre el modal, evitando enviar todos los
detalles en la página inicial.

### ¿Por qué la aplicación está separada en módulos?

Porque cada archivo tiene una responsabilidad concreta. Esto mejora la lectura,
el mantenimiento, las pruebas y el trabajo en equipo.
