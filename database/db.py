# database/db.py
#
# AVISO (2026-09-05, evidencia GA7-220501096-AA3-EV01): este archivo
# era la conexion manual inicial a MySQL (con mysql-connector-python y
# python-dotenv), creada al configurar el entorno del proyecto.
#
# Desde la codificacion del modulo de Clientes se adopto en su lugar
# Flask-SQLAlchemy como ORM (ver config.py y models/__init__.py en la
# raiz del proyecto), que se conecta a la MISMA base de datos ARKHE_V1
# usando las MISMAS variables de entorno definidas en .env
# (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).
#
# La funcion get_connection() de aqui abajo ya no se usa en ninguna
# ruta actual. Se deja el archivo como referencia historica en vez de
# borrarlo -- si en el futuro se necesita ejecutar una consulta SQL muy
# puntual por fuera del ORM, se puede seguir usando.

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """
    Abre y devuelve una conexión directa a MySQL (sin pasar por el
    ORM). Ya no se usa en las rutas actuales; ver el aviso arriba.
    """
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "3306"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "ARKHE_V1"),
    )
