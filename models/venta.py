"""
models/venta.py
---------------
Modelo SQLAlchemy para la tabla ARKHE_V1.ventas.

Esquema REAL verificado el 2026-09-30 con information_schema.COLUMNS
(GA7-220501096-AA5-EV03):

    id_venta        INT            PK, AUTO_INCREMENT
    id_cliente      INT            FK -> clientes.id_cliente
    id_apartamento  INT            FK -> apartamentos.id_apartamento, UNIQUE
    fecha_venta     DATE           NOT NULL
    valor_venta     DECIMAL(15,2)  NOT NULL

La tabla NO tiene columna de estado. El estado de la venta (pendiente,
en pago, pagada) se CALCULA a partir de los pagos registrados, con las
propiedades de abajo. Asi no se duplica informacion (3FN) y el estado
nunca queda desactualizado frente a los pagos reales.
"""

from decimal import Decimal

from models import db


class Venta(db.Model):
    """Venta de un apartamento a un cliente (un apartamento solo se
    vende una vez: id_apartamento es UNIQUE en la base de datos)."""

    __tablename__ = "ventas"

    id_venta = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(
        db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=False
    )
    id_apartamento = db.Column(
        db.Integer,
        db.ForeignKey("apartamentos.id_apartamento"),
        nullable=False,
        unique=True,
    )
    fecha_venta = db.Column(db.Date, nullable=False)
    valor_venta = db.Column(db.Numeric(15, 2), nullable=False)

    cliente = db.relationship("Cliente", backref=db.backref("ventas", lazy=True))
    # uselist=False: apartamento.venta es UNA venta (o None), no una lista.
    apartamento = db.relationship(
        "Apartamento", backref=db.backref("venta", uselist=False)
    )

    # ---- Valores calculados (no son columnas) ----

    @property
    def total_pagado(self):
        return sum((p.monto for p in self.pagos), Decimal("0"))

    @property
    def saldo(self):
        return Decimal(self.valor_venta or 0) - self.total_pagado

    @property
    def estado(self):
        """'pendiente' (sin pagos), 'en-pago' (pagos parciales) o
        'pagada' (saldo en cero)."""
        if self.total_pagado <= 0:
            return "pendiente"
        if self.saldo > 0:
            return "en-pago"
        return "pagada"

    def __repr__(self):
        return f"<Venta {self.id_venta}>"
