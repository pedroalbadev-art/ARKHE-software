"""
app.py
------
Punto de entrada de la aplicacion ARKHE (ERP inmobiliario).

Reemplaza la version de prueba inicial (que solo confirmaba que el
entorno -- venv + Flask -- quedo bien configurado) por la aplicacion
real: conecta Flask-SQLAlchemy con la base de datos ARKHE_V1 y
registra el primer modulo construido, Clientes (evidencia
GA7-220501096-AA3-EV01). Los proximos modulos (Usuarios, Proyectos,
Apartamentos, Ventas, Pagos) se iran agregando aqui de la misma forma,
como nuevos blueprints en routes/.

Para ejecutar el proyecto (con el entorno virtual activo y las
dependencias de requirements.txt instaladas):
    python app.py
"""

from flask import Flask, redirect, url_for

from config import Config
from models import db
from routes.clientes import clientes_bp


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

    # Registra el blueprint (grupo de rutas) del modulo de Clientes.
    # url_prefix hace que todas sus rutas empiecen por /clientes
    # (ej: /clientes/, /clientes/nuevo, /clientes/3/editar).
    app.register_blueprint(clientes_bp, url_prefix="/clientes")

    @app.route("/")
    def inicio():
        """Redirige la raiz del sitio al modulo de clientes, que por
        ahora es el unico modulo construido."""
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
