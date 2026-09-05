"""
models/cliente.py
------------------
Modelo de datos del Cliente.

Representa la tabla `clientes` de la base de datos ARKHE_V1, tal como
existe REALMENTE en el MySQL de Pedro (verificado con
`DESCRIBE ARKHE_V1.clientes;` el 2026-09-05). En vez de escribir
sentencias SQL a mano (INSERT, SELECT, etc.), Flask-SQLAlchemy permite
describir la tabla como una clase de Python: cada atributo de la clase
es una columna, y cada instancia de la clase es una fila real de la
tabla.

Nota de diseno (2026-09-05, corregida tras verificar la tabla real):
la documentacion original de la evidencia GA6 y el mockup
(arkhe_clientes_module.html) suponian una columna unica
"nombre_completo" y un campo "direccion", pero la tabla real que
existe en MySQL tiene:
  - nombre y apellido en columnas SEPARADAS (no una sola).
  - SIN columna de direccion.
  - correo y telefono como NOT NULL (obligatorios), y correo ademas
    UNIQUE.
Este modelo sigue el esquema REAL de la base de datos (la fuente de
verdad es lo que hay creado en MySQL, no un documento desactualizado).
Se agrega una propiedad "nombre_completo" calculada en Python (no una
columna) para poder mostrar "nombre + apellido" juntos en las
plantillas sin duplicar el dato en la base de datos.
"""

from models import db


class Cliente(db.Model):
    """Representa un cliente de ARKHE (comprador potencial o real de
    un apartamento).

    Corresponde 1 a 1 con la tabla `clientes` de ARKHE_V1.
    """

    # Nombre real de la tabla en MySQL. Si no se indicara, SQLAlchemy
    # usaria por defecto el nombre de la clase en minuscula ("cliente"),
    # que no coincide con la tabla que ya existe ("clientes").
    __tablename__ = "clientes"

    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    documento = db.Column(db.String(20), nullable=False, unique=True)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    telefono = db.Column(db.String(20), nullable=False)

    @property
    def nombre_completo(self):
        """Combina nombre y apellido en un solo texto para mostrarlo
        en las plantillas (lista.html), ya que la tabla real los
        guarda en dos columnas separadas y no como un solo campo."""
        return f"{self.nombre} {self.apellido}"

    def __repr__(self):
        """Representacion legible del objeto, util al depurar (por
        ejemplo al imprimirlo en la consola de Python)."""
        return f"<Cliente {self.id_cliente} - {self.nombre_completo}>"
