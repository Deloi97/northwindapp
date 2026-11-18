"""Punto de entrada de Northwind Manager.

La configuración y los módulos funcionales se encuentran en el paquete
``northwind_manager``. Se conserva este archivo para iniciar igual que antes:
``python app.py``.
"""

import os

from northwind_manager import crear_app


app = crear_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
