"""
models/proyecto.py
------------------
Modelo SQLAlchemy para la tabla ARKHE_V1.proyectos

Relaciona proyectos con clientes (responsable) y usuarios (gestor).
"""

from models import db


class Proyecto(db.Model):
    """
    Representa un proyecto inmobiliario.

    Relaciones:
      - Pertenece a un Cliente (id_cliente FK, responsable del proyecto)
      - Tiene un Usuario gestor (id_usuario FK, usuario que lo administra)
      - Tiene muchos Apartamentos (relación inversa: apartamentos)
    """

    __tablename__ = "proyectos"

    id_proyecto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre_proyecto = db.Column(db.String(150), nullable=False, unique=True)
    direccion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Relaciones hacia otras tablas
    cliente = db.relationship(
        "Cliente",
        backref="proyectos"
    )
    usuario = db.relationship(
        "Usuario",
        backref="proyectos"
    )

    def __repr__(self):
        return f"<Proyecto {self.nombre_proyecto}>"
