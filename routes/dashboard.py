"""
routes/dashboard.py
-------------------
Panel de inicio de ARKHE (ruta "/").

Sigue el mockup de Dashboard de la evidencia de frontend: indicadores
(KPI), ventas por mes, estado de apartamentos y ventas, y tablas de
ultimas ventas y ultimos pagos. Todo sale de la base de datos real
(no hay datos de ejemplo fijos en el codigo).

Tambien registra el filtro de plantilla "pesos" (formato $350.000.000),
disponible en todas las plantillas de la aplicacion.
"""

from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template

from models import db
from models.apartamento import Apartamento
from models.cliente import Cliente
from models.pago import Pago
from models.proyecto import Proyecto
from models.usuario import Usuario
from models.venta import Venta
from utils.formato import formato_pesos

dashboard_bp = Blueprint("dashboard", __name__)


# Filtro {{ valor|pesos }} disponible en TODAS las plantillas de la app.
dashboard_bp.add_app_template_filter(formato_pesos, "pesos")


MESES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def _ventas_ultimos_meses(ventas, cantidad=6):
    """Suma valor_venta por mes para los ultimos `cantidad` meses
    (incluido el actual). Devuelve [(etiqueta, total, numero_ventas)]."""
    hoy = date.today()
    meses = []
    anio, mes = hoy.year, hoy.month
    for _ in range(cantidad):
        meses.append((anio, mes))
        mes -= 1
        if mes == 0:
            anio, mes = anio - 1, 12
    meses.reverse()
    resultado = []
    for anio, mes in meses:
        del_mes = [v for v in ventas if v.fecha_venta.year == anio and v.fecha_venta.month == mes]
        total = sum((Decimal(v.valor_venta) for v in del_mes), Decimal("0"))
        resultado.append((f"{MESES[mes - 1]} {str(anio)[2:]}", total, len(del_mes)))
    return resultado


@dashboard_bp.route("/")
def inicio():
    ventas = Venta.query.all()

    # Suma de una columna; coalesce evita None cuando la tabla esta vacia.
    def suma(columna):
        return db.session.query(db.func.coalesce(db.func.sum(columna), 0)).scalar()

    total_vendido = Decimal(suma(Venta.valor_venta))
    total_recaudado = Decimal(suma(Pago.monto))
    total_apartamentos = Apartamento.query.count()

    # Alto de cada barra en % del mes con mas ventas (85% deja espacio
    # para la etiqueta del valor maximo encima de la barra).
    meses = _ventas_ultimos_meses(ventas)
    maximo_mes = max((total for _, total, _ in meses), default=0)
    ventas_por_mes = [
        (etiqueta, total, cantidad, round(float(total / maximo_mes) * 85, 1) if maximo_mes else 0)
        for etiqueta, total, cantidad in meses
    ]

    contexto = dict(
        total_clientes=Cliente.query.count(),
        total_usuarios=Usuario.query.count(),
        usuarios_activos=Usuario.query.filter_by(estado="activo").count(),
        total_proyectos=Proyecto.query.count(),
        total_apartamentos=total_apartamentos,
        total_ventas=len(ventas),
        total_pagos=Pago.query.count(),
        apartamentos_disponibles=Apartamento.query.filter_by(estado="disponible").count(),
        apartamentos_reservados=Apartamento.query.filter_by(estado="reservado").count(),
        apartamentos_vendidos=Apartamento.query.filter_by(estado="vendido").count(),
        ventas_pendientes=sum(1 for v in ventas if v.estado == "pendiente"),
        ventas_en_pago=sum(1 for v in ventas if v.estado == "en-pago"),
        ventas_pagadas=sum(1 for v in ventas if v.estado == "pagada"),
        total_vendido=total_vendido,
        total_recaudado=total_recaudado,
        saldo_por_cobrar=total_vendido - total_recaudado,
        porcentaje_recaudado=round(total_recaudado * 100 / total_vendido) if total_vendido else 0,
        ventas_por_mes=ventas_por_mes,
        maximo_mes=maximo_mes,
        # Sin columna de fecha de creacion: el ID mas alto es el mas reciente.
        ultimas_ventas=Venta.query.order_by(Venta.fecha_venta.desc(), Venta.id_venta.desc()).limit(5).all(),
        ultimos_pagos=Pago.query.order_by(Pago.fecha_pago.desc(), Pago.id_pago.desc()).limit(5).all(),
    )
    return render_template("dashboard/inicio.html", **contexto)
