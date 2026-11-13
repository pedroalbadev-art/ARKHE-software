"""
tests/conftest.py
-----------------
Preparacion comun de las pruebas que usan la aplicacion completa
(rutas, API y reglas de negocio). pytest carga este archivo solo y pone
sus "fixtures" a disposicion de todas las pruebas de la carpeta.

Una fixture es una funcion que prepara algo que la prueba necesita (la
app, un cliente HTTP, datos de ejemplo). La prueba la pide escribiendo
su nombre como parametro.

IMPORTANTE: estas pruebas NUNCA tocan la base real ARKHE_V1. Usan
SQLite en memoria: una base temporal que se crea vacia antes de cada
prueba y desaparece al terminar. SQLite viene incluido en Python, no es
una dependencia nueva.

Limite conocido: SQLite no hace cumplir la longitud de VARCHAR(n) como
MySQL. Por eso las longitudes maximas se validan en el codigo Python y
se prueban ahi, sin depender del motor de base de datos.
"""

import sqlite3
from datetime import date, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app import create_app
from config import Config
from models import db
from models.apartamento import Apartamento
from models.cliente import Cliente
from models.proyecto import Proyecto
from models.usuario import Usuario


class ConfigPruebas(Config):
    """Misma configuracion de la app, pero con base temporal."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "clave-solo-para-pruebas"


@event.listens_for(Engine, "connect")
def _activar_llaves_foraneas(conexion, _registro):
    """SQLite ignora las llaves foraneas si no se le pide lo contrario.
    Con este PRAGMA se comporta como MySQL: rechaza, por ejemplo, borrar
    un cliente que todavia tiene ventas."""
    if isinstance(conexion, sqlite3.Connection):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture
def app():
    """Aplicacion nueva con las 6 tablas vacias, para una sola prueba."""
    aplicacion = create_app(ConfigPruebas)
    with aplicacion.app_context():
        db.create_all()
    yield aplicacion
    with aplicacion.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def api(app):
    """Cliente HTTP de pruebas: hace peticiones a la app sin levantar
    el servidor (api.get("/api/clientes"), api.post(..., json={...}))."""
    return app.test_client()


@pytest.fixture
def datos(app):
    """Registros minimos para probar ventas y pagos: un cliente, un
    usuario activo, un proyecto y un apartamento disponible.
    Devuelve los ID (y fechas utiles) en un diccionario."""
    with app.app_context():
        cliente = Cliente(nombre="Ana", apellido="Rojas", documento="10203040",
                          correo="ana@ejemplo.com", telefono="3001234567")
        usuario = Usuario(nombre="Luis", apellido="Mora", correo="luis@ejemplo.com",
                          rol="Administrador", estado="activo")
        usuario.establecer_contrasena("ClaveSegura1")
        db.session.add_all([cliente, usuario])
        db.session.flush()  # asigna los ID sin cerrar la transaccion

        proyecto = Proyecto(id_cliente=cliente.id_cliente, id_usuario=usuario.id_usuario,
                            nombre_proyecto="Torre Prueba", direccion="Calle 1 # 2-3",
                            ciudad="Bogota")
        db.session.add(proyecto)
        db.session.flush()

        apartamento = Apartamento(id_proyecto=proyecto.id_proyecto, numero_apartamento="101",
                                  area_m2=60, habitaciones=3, banos=2,
                                  precio=200000000, estado="disponible")
        db.session.add(apartamento)
        db.session.commit()

        hoy = date.today()
        return {
            "id_cliente": cliente.id_cliente,
            "id_usuario": usuario.id_usuario,
            "id_proyecto": proyecto.id_proyecto,
            "id_apartamento": apartamento.id_apartamento,
            "fecha_venta": (hoy - timedelta(days=10)).isoformat(),
            "fecha_pago": (hoy - timedelta(days=5)).isoformat(),
            "manana": (hoy + timedelta(days=1)).isoformat(),
            "antes_de_la_venta": (hoy - timedelta(days=20)).isoformat(),
        }
