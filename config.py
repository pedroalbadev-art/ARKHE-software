"""
config.py
---------
Configuracion central del proyecto ARKHE.

Lee las credenciales de la base de datos MySQL (ARKHE_V1) desde el
archivo .env (no versionado, ver .gitignore), reutilizando exactamente
las mismas variables ya definidas en .env.example desde que se
configuro el entorno del proyecto: DB_HOST, DB_PORT, DB_USER,
DB_PASSWORD, DB_NAME.

Estandar de codificacion: PEP 8 (snake_case, docstrings explicando el
"por que" de cada decision).
"""

import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Carga las variables definidas en tu archivo .env hacia el entorno del
# proceso (la misma libreria que ya usaba database/db.py).
load_dotenv()


class Config:
    """Configuracion base de la aplicacion Flask."""

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "ARKHE_V1")

    # Formato que espera SQLAlchemy para conectarse a MySQL a traves
    # del driver PyMySQL:
    #   mysql+pymysql://usuario:contrasena@host:puerto/nombre_basededatos
    # Se arma con URL.create (y no pegando los textos a mano) porque
    # asi SQLAlchemy codifica los caracteres especiales: una contrasena
    # con "@", "/", ":" o "%" romperia una direccion armada a mano.
    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=int(DB_PORT),
        database=DB_NAME,
    ).render_as_string(hide_password=False)

    # Desactiva el sistema de eventos de SQLAlchemy que no se usa en
    # este proyecto y solo consume memoria de mas.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave secreta que usa Flask para firmar la sesion y los mensajes
    # "flash" (los avisos de "Cliente creado correctamente", etc.).
    # Es OBLIGATORIA y solo se lee del .env: no hay un valor por
    # defecto en el codigo, porque una clave publicada en el repositorio
    # permitiria a cualquiera falsificar una sesion. Si falta,
    # create_app() (app.py) detiene el arranque y explica como crearla.
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Modo depuracion (recarga automatica y errores detallados en el
    # navegador). Apagado por defecto: solo se enciende escribiendo
    # FLASK_DEBUG=1 en el .env de un equipo de desarrollo.
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
