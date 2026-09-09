"""
app.py
------
Punto de entrada de la aplicacion ARKHE (ERP inmobiliario).

Registra los modulos construidos hasta ahora como blueprints de
Flask: Clientes (evidencia GA7-220501096-AA3-EV01) y Usuarios
(evidencia GA7-220501096-AA3-EV02). Los proximos modulos (Proyectos,
Apartamentos, Ventas, Pagos) se iran agregando aqui de la misma
forma.

Para ejecutar el proyecto (con el entorno virtual activo y las
dependencias de requirements.txt instaladas):
    python app.py
"""

from flask import Flask, redirect, url_for

from config import Config
from models import db
from routes.clientes import clientes_bp
from routes.usuarios import usuarios_bp


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
    # url_prefix hace que todas las rutas de un modulo empiecen por su
    # propio prefijo (ej: /clientes/, /usuarios/nuevo).
    app.register_blueprint(clientes_bp, url_prefix="/clientes")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")

    @app.route("/")
    def inicio():
        """Redirige la raiz del sitio al modulo de clientes."""
        return redirect(url_for("clientes.listar_clientes"))

    return app


# Instancia global usada por "python app.py" y por el servidor de
# desarrollo de Flask.
app = create_app()

if __name__ == "__main__":
    # debug=True recarga el servidor automaticamente al guardar
    # cambios y muestra errores detallados en el navegador; debe
    # desactivarse en un entorno de produccion real.
    app.run(debug=True)
