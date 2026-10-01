"""
models/apartamento.py
---------------------
Modelo SQLAlchemy para la tabla ARKHE_V1.apartamentos.

Esquema REAL verificado el 2026-09-30 con information_schema.COLUMNS
(GA7-220501096-AA5-EV03). Cada columna de esta clase existe tal cual en
la base de datos; no se agrega ninguna columna que la tabla no tenga.

    id_apartamento      INT            PK, AUTO_INCREMENT
    id_proyecto         INT            FK -> proyectos.id_proyecto
    numero_apartamento  VARCHAR(20)    NOT NULL
    area_m2             DECIMAL(10,2)  NOT NULL
    habitaciones        INT            NOT NULL
    banos               INT            NOT NULL
    precio              DECIMAL(15,2)  NOT NULL
    estado              VARCHAR(20)    NOT NULL
"""

from models import db

# Estados permitidos (los mismos del mockup de Apartamentos). La columna
# es VARCHAR libre en MySQL (no ENUM), asi que la lista se controla aqui
# en el codigo, igual que rol/estado en usuarios. "vendido" solo lo
# asigna el modulo de Ventas, nunca a mano.
ESTADOS_APARTAMENTO = ("disponible", "reservado", "vendido")
ESTADOS_EDITABLES = ("disponible", "reservado")


class Apartamento(db.Model):
    """Unidad de vivienda que pertenece a un proyecto."""

    __tablename__ = "apartamentos"

    id_apartamento = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(
        db.Integer, db.ForeignKey("proyectos.id_proyecto"), nullable=False
    )
    numero_apartamento = db.Column(db.String(20), nullable=False)
    area_m2 = db.Column(db.Numeric(10, 2), nullable=False)
    habitaciones = db.Column(db.Integer, nullable=False)
    banos = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Numeric(15, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="disponible")

    # proyecto.apartamentos -> lista de apartamentos del proyecto
    proyecto = db.relationship(
        "Proyecto", backref=db.backref("apartamentos", lazy=True)
    )

    @property
    def puede_venderse(self):
        """Un apartamento disponible o reservado (apartado por un cliente)
        se puede vender; uno ya vendido no."""
        return (self.estado or "").lower() in ESTADOS_EDITABLES and self.venta is None

    def __repr__(self):
        return f"<Apartamento {self.numero_apartamento}>"
