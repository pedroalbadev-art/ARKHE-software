# Aquí van los modelos de datos: la representación en Python de cada tabla
# de ARKHE_V1 (usuarios, clientes, proyectos, apartamentos, ventas, pagos).
# Un archivo por tabla, reflejando exactamente los campos y llaves foráneas
# ya definidos en la base de datos MySQL.
#
# Decision tomada en la evidencia GA7-220501096-AA3-EV01 (2026-09-05):
# se usa Flask-SQLAlchemy como ORM. En vez de que cada archivo de este
# paquete escriba sentencias SQL a mano, cada tabla se representa como
# una clase Python que hereda de db.Model. La instancia "db" se crea
# aqui, en el __init__ del paquete (y no en app.py), para que todos los
# modelos (cliente.py y los que se agreguen despues) puedan importarla
# sin depender de app.py -- evitando asi "importaciones circulares".

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
