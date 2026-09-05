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
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    # Desactiva el sistema de eventos de SQLAlchemy que no se usa en
    # este proyecto y solo consume memoria de mas.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Clave secreta que usa Flask para firmar la sesion y los mensajes
    # "flash" (los avisos de "Cliente creado correctamente", etc.).
    # Se puede definir tambien en el .env; si no esta, se usa un valor
    # de desarrollo por defecto.
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-desarrollo-arkhe")
