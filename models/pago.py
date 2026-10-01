"""
models/pago.py
--------------
Modelo SQLAlchemy para la tabla ARKHE_V1.pagos.

Esquema REAL verificado el 2026-09-30 con information_schema.COLUMNS
(GA7-220501096-AA5-EV03):

    id_pago      INT            PK, AUTO_INCREMENT
    id_venta     INT            FK -> ventas.id_venta
    fecha_pago   DATE           NOT NULL
    monto        DECIMAL(15,2)  NOT NULL
    metodo_pago  VARCHAR(50)    NOT NULL

Cada fila es un abono ya realizado a una venta (no una cuota futura).
"""

from models import db

# Lista controlada en el codigo (la columna es VARCHAR libre en MySQL).
METODOS_PAGO = (
    "Efectivo",
    "Transferencia",
    "Tarjeta de credito",
    "Tarjeta debito",
    "Cheque",
    "Credito hipotecario",
)


class Pago(db.Model):
    """Abono realizado por el cliente a una venta."""

    __tablename__ = "pagos"

    id_pago = db.Column(db.Integer, primary_key=True)
    id_venta = db.Column(db.Integer, db.ForeignKey("ventas.id_venta"), nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    monto = db.Column(db.Numeric(15, 2), nullable=False)
    metodo_pago = db.Column(db.String(50), nullable=False)

    # venta.pagos -> lista de pagos de la venta, ordenados por fecha
    venta = db.relationship(
        "Venta",
        backref=db.backref("pagos", lazy=True, order_by="Pago.fecha_pago"),
    )

    def __repr__(self):
        return f"<Pago {self.id_pago} de Venta {self.id_venta}>"
