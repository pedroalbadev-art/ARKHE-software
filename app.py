"""
app.py
------
Punto de entrada de la aplicacion ARKHE (ERP inmobiliario).

Registra TODOS los modulos construidos como blueprints de Flask:
  - Dashboard (página de inicio)
  - Clientes (GA7-220501096-AA3-EV01)
  - Usuarios (GA7-220501096-AA3-EV02)
  - Proyectos (GA7-220501096-AA5-EV03)
  - Apartamentos (GA7-220501096-AA5-EV03)
  - Ventas (GA7-220501096-AA5-EV03)
  - Pagos (GA7-220501096-AA5-EV03)

Este archivo cierra la evidencia GA7-220501096-AA5-EV03 "Diseño y desarrollo de
servicios web - proyecto" con los 4 módulos finales construidos + Dashboard.

Para ejecutar el proyecto (con el entorno virtual activo y las
dependencias de requirements.txt instaladas):
    python app.py

Los módulos están organizados por carpetas:
  - models/        : Definición de modelos SQLAlchemy (ORM)
  - routes/        : Blueprints con CRUD y lógica de negocio
  - templates/     : Templates HTML por módulo
  - static/        : CSS y assets estáticos
  - utils/         : Funciones utilitarias compartidas
"""

from flask import Flask

from config import Config
from models import db
from routes.dashboard import dashboard_bp
from routes.clientes import clientes_bp
from routes.usuarios import usuarios_bp
from routes.proyectos import proyectos_bp
from routes.apartamentos import apartamentos_bp
from routes.ventas import ventas_bp
from routes.pagos import pagos_bp


def create_app():
    """Crea y configura la aplicacion Flask (patron "application
    factory").

    Se usa una funcion en vez de crear la app directamente a nivel de
    modulo porque asi es mas facil crear varias instancias de la
    aplicacion sin que se interfieran entre si (por ejemplo, una
    instancia para desarrollo y otra para pruebas automatizadas).
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Conecta la extension Flask-SQLAlchemy con esta instancia de la app.
    db.init_app(app)

    # Registra los blueprints (grupos de rutas) de cada modulo.
    # El dashboard está registrado sin url_prefix porque es la raíz (/).
    app.register_blueprint(dashboard_bp)

    # El resto de módulos tienen su prefijo
    app.register_blueprint(clientes_bp, url_prefix="/clientes")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(proyectos_bp, url_prefix="/proyectos")
    app.register_blueprint(apartamentos_bp, url_prefix="/apartamentos")
    app.register_blueprint(ventas_bp, url_prefix="/ventas")
    app.register_blueprint(pagos_bp, url_prefix="/pagos")

    return app


# Instancia global usada por "python app.py" y por el servidor de
# desarrollo de Flask.
app = create_app()

if __name__ == "__main__":
    # debug=True recarga el servidor automaticamente al guardar
    # cambios y muestra errores detallados en el navegador; debe
    # desactivarse en un entorno de produccion real.
    app.run(debug=True)
