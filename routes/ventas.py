"""
routes/ventas.py
----------------
Modulo Ventas (GA7-220501096-AA5-EV03).

Endpoints:
  GET  /ventas/                    Listar (con total pagado, saldo y estado)
  GET  /ventas/nueva               Formulario de creacion
  POST /ventas/crear               Crear
  GET  /ventas/<id>/editar         Formulario de edicion
  POST /ventas/<id>/actualizar     Actualizar
  POST /ventas/<id>/eliminar       Eliminar

Reglas de negocio:
  - Solo se pueden vender apartamentos 'disponible' o 'reservado' (un
    apartamento se vende una sola vez: id_apartamento es UNIQUE).
  - Al crear la venta, el apartamento pasa a 'vendido'. Al eliminarla
    (o al cambiarla de apartamento), el anterior vuelve a 'disponible'.
  - Una venta con pagos registrados no se puede eliminar.
  - Al editar, el valor no puede quedar por debajo de lo ya pagado.

Validaciones en el backend:
  - Cliente y apartamento obligatorios y existentes.
  - Fecha valida (AAAA-MM-DD) y no futura.
  - Valor mayor que 0, maximo 13 digitos enteros (DECIMAL(15,2)).
"""

from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import db
from models.apartamento import Apartamento
from models.cliente import Cliente
from models.venta import Venta
from utils.validaciones import a_decimal, a_entero, a_fecha, es_fecha_futura, MAXIMO_DECIMAL_15_2

ventas_bp = Blueprint("ventas", __name__)


def validar_datos_venta(form, venta=None):
    errores = []

    id_cliente = a_entero(form.get("id_cliente"))
    if id_cliente is None or not db.session.get(Cliente, id_cliente):
        errores.append("Debe seleccionar un cliente existente.")

    id_apartamento = a_entero(form.get("id_apartamento"))
    apartamento = db.session.get(Apartamento, id_apartamento) if id_apartamento else None
    if apartamento is None:
        errores.append("Debe seleccionar un apartamento existente.")
    elif venta is None or venta.id_apartamento != apartamento.id_apartamento:
        # Es una venta nueva o se cambio de apartamento: debe estar libre.
        if not apartamento.puede_venderse:
            errores.append(f"El apartamento '{apartamento.numero_apartamento}' no esta disponible para la venta.")

    fecha = a_fecha(form.get("fecha_venta"))
    if fecha is None:
        errores.append("La fecha de venta es obligatoria y debe ser valida.")
    elif es_fecha_futura(fecha):
        errores.append("La fecha de venta no puede ser futura.")
    elif venta is not None and venta.pagos and fecha > min(p.fecha_pago for p in venta.pagos):
        errores.append("La fecha de venta no puede ser posterior al primer pago registrado.")

    valor = a_decimal(form.get("valor_venta"))
    if valor is None or valor <= 0 or valor > MAXIMO_DECIMAL_15_2:
        errores.append("El valor de venta debe ser un numero mayor que 0 (sin puntos de miles).")
    elif venta is not None and valor < venta.total_pagado:
        errores.append("El valor de venta no puede ser menor que lo ya pagado por el cliente.")

    datos = dict(
        id_cliente=id_cliente,
        id_apartamento=id_apartamento,
        fecha_venta=fecha,
        valor_venta=valor,
    )
    return errores, datos, apartamento


def _formulario(datos, accion, venta=None):
    # Apartamentos que se pueden elegir: disponibles o reservados y, al editar,
    # el que ya tiene esta venta.
    consulta = Apartamento.query.filter(Apartamento.estado.in_(("disponible", "reservado")))
    apartamentos = consulta.order_by(Apartamento.id_proyecto, Apartamento.numero_apartamento).all()
    if venta is not None and venta.apartamento not in apartamentos:
        apartamentos.insert(0, venta.apartamento)
    return render_template(
        "ventas/formulario.html",
        datos=datos,
        accion=accion,
        venta=venta,
        clientes=Cliente.query.order_by(Cliente.nombre, Cliente.apellido).all(),
        apartamentos=apartamentos,
    )


@ventas_bp.route("/", methods=["GET"])
def listar_ventas():
    ventas = Venta.query.order_by(Venta.fecha_venta.desc(), Venta.id_venta.desc()).all()
    return render_template("ventas/lista.html", ventas=ventas)


@ventas_bp.route("/nueva", methods=["GET"])
def formulario_nuevo():
    return _formulario({"fecha_venta": date.today().isoformat()}, "crear")


@ventas_bp.route("/crear", methods=["POST"])
def crear_venta():
    errores, datos, apartamento = validar_datos_venta(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "crear")

    try:
        venta = Venta(**datos)
        apartamento.estado = "vendido"
        db.session.add(venta)
        db.session.commit()  # venta + cambio de estado en una sola transaccion
        flash(f"Venta del apartamento '{apartamento.numero_apartamento}' registrada correctamente.", "exito")
        return redirect(url_for("ventas.listar_ventas"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al registrar la venta: {e}", "error")
        return _formulario(request.form, "crear")


@ventas_bp.route("/<int:id>/editar", methods=["GET"])
def formulario_editar(id):
    venta = db.session.get(Venta, id)
    if not venta:
        flash("La venta no existe.", "error")
        return redirect(url_for("ventas.listar_ventas"))
    datos = {
        "id_cliente": venta.id_cliente,
        "id_apartamento": venta.id_apartamento,
        "fecha_venta": venta.fecha_venta.isoformat(),
        "valor_venta": venta.valor_venta,
    }
    return _formulario(datos, "editar", venta)


@ventas_bp.route("/<int:id>/actualizar", methods=["POST"])
def actualizar_venta(id):
    venta = db.session.get(Venta, id)
    if not venta:
        flash("La venta no existe.", "error")
        return redirect(url_for("ventas.listar_ventas"))

    errores, datos, apartamento_nuevo = validar_datos_venta(request.form, venta)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "editar", venta)

    try:
        apartamento_anterior = venta.apartamento
        if apartamento_anterior.id_apartamento != apartamento_nuevo.id_apartamento:
            apartamento_anterior.estado = "disponible"
            apartamento_nuevo.estado = "vendido"
        for campo, valor in datos.items():
            setattr(venta, campo, valor)
        db.session.commit()
        flash(f"Venta #{venta.id_venta} actualizada correctamente.", "exito")
        return redirect(url_for("ventas.listar_ventas"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar la venta: {e}", "error")
        return _formulario(request.form, "editar", venta)


@ventas_bp.route("/<int:id>/eliminar", methods=["POST"])
def eliminar_venta(id):
    venta = db.session.get(Venta, id)
    if not venta:
        flash("La venta no existe.", "error")
    elif venta.pagos:
        flash("No se puede eliminar: la venta tiene pagos registrados. Elimine primero sus pagos.", "error")
    else:
        try:
            venta.apartamento.estado = "disponible"
            db.session.delete(venta)
            db.session.commit()
            flash(f"Venta #{id} eliminada. El apartamento volvio a estar disponible.", "exito")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al eliminar la venta: {e}", "error")
    return redirect(url_for("ventas.listar_ventas"))
