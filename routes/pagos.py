"""
routes/pagos.py
---------------
Modulo Pagos (GA7-220501096-AA5-EV03).

Endpoints:
  GET  /pagos/                     Listar (filtro opcional ?venta=<id>)
  GET  /pagos/nuevo                Formulario de creacion (?venta=<id> la preselecciona)
  POST /pagos/crear                Crear
  GET  /pagos/<id>/editar          Formulario de edicion
  POST /pagos/<id>/actualizar      Actualizar
  POST /pagos/<id>/eliminar        Eliminar

Validaciones en el backend:
  - Venta obligatoria y existente.
  - Fecha valida, no futura y no anterior a la fecha de la venta.
  - Monto mayor que 0 y que no supere el saldo pendiente de la venta
    (al editar, el saldo se calcula sin contar el propio pago). Antes de
    calcular el saldo se bloquea la fila de la venta (ver
    venta_con_bloqueo), para que dos pagos simultaneos no la sobrepasen.
  - Metodo de pago dentro de la lista permitida (models/pago.py).
"""

from datetime import date
from decimal import Decimal

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from models import db
from models.pago import METODOS_PAGO, Pago
from models.venta import Venta
from utils.formato import formato_pesos
from utils.seguridad import rol_requerido
from utils.validaciones import a_decimal, a_entero, a_fecha, es_fecha_futura

pagos_bp = Blueprint("pagos", __name__)


def venta_con_bloqueo(id_venta):
    """Devuelve (venta, pagos) BLOQUEANDO la fila de la venta, o
    (None, []) si la venta no existe.

    El problema que resuelve: dos personas registran al mismo tiempo un
    pago sobre la misma venta. Sin bloqueo, las dos peticiones leen el
    mismo saldo, las dos pasan la validacion y entre las dos lo superan.

    Como funciona: with_for_update hace que la consulta sea
    SELECT ... FOR UPDATE. MySQL deja la fila de la venta bloqueada para
    esta transaccion hasta su commit o rollback. Si otra peticion pide
    el mismo bloqueo, ESPERA en esta linea; cuando la primera termina,
    la segunda continua y ya encuentra el pago de la primera, asi que
    valida contra el saldo real.

    Los pagos tambien se leen con FOR UPDATE por una razon propia de
    MySQL: una consulta normal ve la base como estaba al empezar la
    transaccion (lectura consistente), y no veria el pago que la otra
    peticion acaba de guardar. Una lectura con bloqueo siempre ve lo
    ultimo confirmado. populate_existing refresca los objetos que ya
    estuvieran cargados en la sesion.

    El bloqueo se libera solo: con el commit al guardar, o con el
    rollback que Flask-SQLAlchemy hace al terminar la peticion si la
    validacion falla. SQLite (la base de las pruebas) ignora FOR UPDATE.
    """
    venta = db.session.get(Venta, id_venta, with_for_update=True, populate_existing=True)
    if venta is None:
        return None, []
    pagos = (Pago.query.filter_by(id_venta=id_venta)
             .with_for_update().populate_existing().all())
    return venta, pagos


def validar_datos_pago(form, pago=None):
    errores = []

    id_venta = a_entero(form.get("id_venta"))
    venta, pagos_de_la_venta = venta_con_bloqueo(id_venta) if id_venta else (None, [])
    if venta is None:
        errores.append("Debe seleccionar una venta existente.")

    fecha = a_fecha(form.get("fecha_pago"))
    if fecha is None:
        errores.append("La fecha de pago es obligatoria y debe ser válida.")
    elif es_fecha_futura(fecha):
        errores.append("La fecha de pago no puede ser futura.")
    elif venta is not None and fecha < venta.fecha_venta:
        errores.append("La fecha de pago no puede ser anterior a la fecha de la venta.")

    monto = a_decimal(form.get("monto"))
    if monto is None or monto <= 0:
        errores.append("El monto debe ser un número mayor que 0 (sin puntos de miles).")
    elif venta is not None:
        # El saldo se calcula con los pagos leidos bajo el bloqueo. Al
        # editar, el propio pago no cuenta contra el saldo.
        ya_pagado = sum((p.monto for p in pagos_de_la_venta
                         if pago is None or p.id_pago != pago.id_pago), Decimal("0"))
        saldo_disponible = Decimal(venta.valor_venta) - ya_pagado
        if monto > saldo_disponible:
            errores.append(f"El monto supera el saldo pendiente de la venta ({formato_pesos(saldo_disponible)}).")

    metodo = (form.get("metodo_pago") or "").strip()
    if metodo not in METODOS_PAGO:
        errores.append("Seleccione un método de pago válido.")

    datos = dict(id_venta=id_venta, fecha_pago=fecha, monto=monto, metodo_pago=metodo)
    return errores, datos


def _formulario(datos, accion, pago=None):
    # Ventas que todavia reciben pagos (saldo > 0) y, al editar, la del pago.
    ventas = [v for v in Venta.query.order_by(Venta.id_venta.desc()).all() if v.saldo > 0]
    if pago is not None and pago.venta not in ventas:
        ventas.insert(0, pago.venta)
    return render_template(
        "pagos/formulario.html",
        datos=datos,
        accion=accion,
        pago=pago,
        ventas=ventas,
        metodos=METODOS_PAGO,
    )


@pagos_bp.route("/", methods=["GET"])
@rol_requerido("pagos", "ver")
def listar_pagos():
    consulta = Pago.query
    venta = None
    id_venta = a_entero(request.args.get("venta"))
    if id_venta:
        venta = db.session.get(Venta, id_venta)
        consulta = consulta.filter_by(id_venta=id_venta)
    pagos = consulta.order_by(Pago.fecha_pago.desc(), Pago.id_pago.desc()).all()
    return render_template("pagos/lista.html", pagos=pagos, venta_filtro=venta)


@pagos_bp.route("/nuevo", methods=["GET"])
@rol_requerido("pagos", "editar")
def formulario_nuevo():
    datos = {"id_venta": request.args.get("venta", ""), "fecha_pago": date.today().isoformat()}
    return _formulario(datos, "crear")


@pagos_bp.route("/crear", methods=["POST"])
@rol_requerido("pagos", "editar")
def crear_pago():
    errores, datos = validar_datos_pago(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "crear")

    try:
        db.session.add(Pago(**datos))
        db.session.commit()
        flash(f"Pago de {formato_pesos(datos['monto'])} registrado para la venta #{datos['id_venta']}.", "exito")
        return redirect(url_for("pagos.listar_pagos"))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error al registrar el pago")
        flash("Error al registrar el pago. Intente de nuevo o avise al administrador.", "error")
        return _formulario(request.form, "crear")


@pagos_bp.route("/<int:id>/editar", methods=["GET"])
@rol_requerido("pagos", "editar")
def formulario_editar(id):
    pago = db.session.get(Pago, id)
    if not pago:
        flash("El pago no existe.", "error")
        return redirect(url_for("pagos.listar_pagos"))
    datos = {
        "id_venta": pago.id_venta,
        "fecha_pago": pago.fecha_pago.isoformat(),
        "monto": pago.monto,
        "metodo_pago": pago.metodo_pago,
    }
    return _formulario(datos, "editar", pago)


@pagos_bp.route("/<int:id>/actualizar", methods=["POST"])
@rol_requerido("pagos", "editar")
def actualizar_pago(id):
    pago = db.session.get(Pago, id)
    if not pago:
        flash("El pago no existe.", "error")
        return redirect(url_for("pagos.listar_pagos"))

    errores, datos = validar_datos_pago(request.form, pago)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "editar", pago)

    try:
        for campo, valor in datos.items():
            setattr(pago, campo, valor)
        db.session.commit()
        flash(f"Pago #{pago.id_pago} actualizado correctamente.", "exito")
        return redirect(url_for("pagos.listar_pagos"))
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error al actualizar el pago")
        flash("Error al actualizar el pago. Intente de nuevo o avise al administrador.", "error")
        return _formulario(request.form, "editar", pago)


@pagos_bp.route("/<int:id>/eliminar", methods=["POST"])
@rol_requerido("pagos", "eliminar")
def eliminar_pago(id):
    pago = db.session.get(Pago, id)
    if not pago:
        flash("El pago no existe.", "error")
    else:
        try:
            db.session.delete(pago)
            db.session.commit()
            flash(f"Pago #{id} eliminado correctamente.", "exito")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Error al eliminar el pago")
            flash("Error al eliminar el pago. Intente de nuevo o avise al administrador.", "error")
    return redirect(url_for("pagos.listar_pagos"))
