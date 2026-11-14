"""
utils/resumen.py
----------------
Cifras generales del sistema, calculadas en UN solo lugar.

Las usan el dashboard (routes/dashboard.py) y el servicio
GET /api/resumen (routes/api.py). Antes cada uno hacia sus propias
cuentas; con una sola funcion, la pantalla y la API no pueden mostrar
numeros distintos, y un cambio de regla se hace una sola vez.

Nada de esto se guarda en la base de datos: se calcula al consultarlo.
"""

from decimal import Decimal

from models import db
from models.apartamento import ESTADOS_APARTAMENTO, Apartamento
from models.cliente import Cliente
from models.pago import Pago
from models.proyecto import Proyecto
from models.usuario import Usuario
from models.venta import Venta

ESTADOS_VENTA = ("pendiente", "en-pago", "pagada")


def _suma(columna):
    """Suma de una columna hecha por la base de datos. coalesce evita
    None cuando la tabla esta vacia."""
    total = db.session.query(db.func.coalesce(db.func.sum(columna), 0)).scalar()
    return Decimal(str(total))


def calcular_resumen(ventas=None):
    """Devuelve un diccionario con las cifras del sistema. Los valores
    de dinero son Decimal (exactos); la API los convierte a numero JSON.

    `ventas` permite pasar la lista de ventas si quien llama ya la
    consulto (el dashboard la usa tambien para el grafico mensual), para
    no pedirla dos veces a la base.
    """
    if ventas is None:
        ventas = Venta.query.all()

    valor_vendido = _suma(Venta.valor_venta)
    recaudado = _suma(Pago.monto)

    return {
        "clientes": Cliente.query.count(),
        "usuarios": Usuario.query.count(),
        "proyectos": Proyecto.query.count(),
        "apartamentos": {estado: Apartamento.query.filter_by(estado=estado).count()
                         for estado in ESTADOS_APARTAMENTO},
        # El estado de una venta no es una columna: lo calcula el modelo
        # a partir de sus pagos (models/venta.py).
        "ventas": {estado: sum(1 for venta in ventas if venta.estado == estado)
                   for estado in ESTADOS_VENTA},
        "valor_vendido": valor_vendido,
        "recaudado": recaudado,
        "saldo_por_cobrar": valor_vendido - recaudado,
    }
