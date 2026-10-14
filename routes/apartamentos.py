"""
routes/apartamentos.py
----------------------
Modulo Apartamentos (GA7-220501096-AA5-EV03).

Endpoints:
  GET  /apartamentos/                    Listar
  GET  /apartamentos/nuevo               Formulario de creacion
  POST /apartamentos/crear               Crear
  GET  /apartamentos/<id>/editar         Formulario de edicion
  POST /apartamentos/<id>/actualizar     Actualizar
  POST /apartamentos/<id>/eliminar       Eliminar

Validaciones en el backend (no se depende solo del HTML):
  - Proyecto: obligatorio y debe existir.
  - Numero: obligatorio, max 20 caracteres (VARCHAR(20)), solo letras,
    numeros, guion y espacios; unico dentro del mismo proyecto.
  - Area m2: numero mayor que 0 y hasta 9999.99.
  - Habitaciones: entero entre 1 y 10. Banos: entero entre 1 y 10.
  - Precio: numero mayor que 0, maximo 13 digitos enteros (DECIMAL(15,2)).
  - Estado: 'disponible' o 'reservado'. 'vendido' lo asigna solo
    el modulo de Ventas; un apartamento con venta no puede cambiar de
    estado ni eliminarse.

Las plantillas se piden con el prefijo "apartamentos/" (sin
template_folder propio), igual que Clientes y Usuarios, para que los
nombres lista.html/formulario.html no se mezclen entre modulos.
"""

from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import db
from models.apartamento import ESTADOS_EDITABLES, Apartamento
from models.proyecto import Proyecto
from utils.validaciones import a_decimal, a_entero, es_numero_apto_valido, MAXIMO_DECIMAL_15_2

apartamentos_bp = Blueprint("apartamentos", __name__)


def validar_datos_apartamento(form, apartamento=None):
    """Devuelve (errores, datos_limpios). `apartamento` es el registro
    que se esta editando (None al crear)."""
    errores = []

    id_proyecto = a_entero(form.get("id_proyecto"))
    if id_proyecto is None or not db.session.get(Proyecto, id_proyecto):
        errores.append("Debe seleccionar un proyecto existente.")

    numero = (form.get("numero_apartamento") or "").strip()
    if not numero:
        errores.append("El numero de apartamento es obligatorio.")
    elif len(numero) > 20:
        errores.append("El numero de apartamento no puede superar 20 caracteres.")
    elif not es_numero_apto_valido(numero):
        errores.append("El numero de apartamento solo admite letras, numeros, guion y espacios.")
    elif id_proyecto is not None:
        consulta = Apartamento.query.filter_by(id_proyecto=id_proyecto, numero_apartamento=numero)
        if apartamento:
            consulta = consulta.filter(Apartamento.id_apartamento != apartamento.id_apartamento)
        if consulta.first():
            errores.append(f"Ya existe el apartamento '{numero}' en ese proyecto.")

    area = a_decimal(form.get("area_m2"))
    if area is None or area <= 0 or area > Decimal("9999.99"):
        errores.append("El area debe ser un numero mayor que 0 y hasta 9999.99 m2.")

    habitaciones = a_entero(form.get("habitaciones"))
    if habitaciones is None or not 1 <= habitaciones <= 10:
        errores.append("Las habitaciones deben ser un numero entero entre 1 y 10.")

    banos = a_entero(form.get("banos"))
    if banos is None or not 1 <= banos <= 10:
        errores.append("Los banos deben ser un numero entero entre 1 y 10.")

    precio = a_decimal(form.get("precio"))
    if precio is None or precio <= 0 or precio > MAXIMO_DECIMAL_15_2:
        errores.append("El precio debe ser un numero mayor que 0 (sin puntos de miles).")

    estado = (form.get("estado") or "").strip()
    if apartamento is not None and apartamento.venta is not None:
        # Ya vendido: el estado no se toca desde este modulo.
        estado = "vendido"
    elif estado not in ESTADOS_EDITABLES:
        errores.append("El estado debe ser 'disponible' o 'reservado'.")

    datos = dict(
        id_proyecto=id_proyecto,
        numero_apartamento=numero,
        area_m2=area,
        habitaciones=habitaciones,
        banos=banos,
        precio=precio,
        estado=estado,
    )
    return errores, datos


def _formulario(datos, accion, apartamento=None):
    return render_template(
        "apartamentos/formulario.html",
        datos=datos,
        accion=accion,
        apartamento=apartamento,
        proyectos=Proyecto.query.order_by(Proyecto.nombre_proyecto).all(),
        estados=ESTADOS_EDITABLES,
    )


@apartamentos_bp.route("/", methods=["GET"])
def listar_apartamentos():
    apartamentos = Apartamento.query.order_by(
        Apartamento.id_proyecto, Apartamento.numero_apartamento
    ).all()
    return render_template("apartamentos/lista.html", apartamentos=apartamentos)


@apartamentos_bp.route("/nuevo", methods=["GET"])
def formulario_nuevo():
    return _formulario({"estado": "disponible"}, "crear")


@apartamentos_bp.route("/crear", methods=["POST"])
def crear_apartamento():
    errores, datos = validar_datos_apartamento(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "crear")

    try:
        db.session.add(Apartamento(**datos))
        db.session.commit()
        flash(f"Apartamento '{datos['numero_apartamento']}' creado correctamente.", "exito")
        return redirect(url_for("apartamentos.listar_apartamentos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear el apartamento: {e}", "error")
        return _formulario(request.form, "crear")


@apartamentos_bp.route("/<int:id>/editar", methods=["GET"])
def formulario_editar(id):
    apartamento = db.session.get(Apartamento, id)
    if not apartamento:
        flash("El apartamento no existe.", "error")
        return redirect(url_for("apartamentos.listar_apartamentos"))
    datos = {
        "id_proyecto": apartamento.id_proyecto,
        "numero_apartamento": apartamento.numero_apartamento,
        "area_m2": apartamento.area_m2,
        "habitaciones": apartamento.habitaciones,
        "banos": apartamento.banos,
        "precio": apartamento.precio,
        "estado": apartamento.estado,
    }
    return _formulario(datos, "editar", apartamento)


@apartamentos_bp.route("/<int:id>/actualizar", methods=["POST"])
def actualizar_apartamento(id):
    apartamento = db.session.get(Apartamento, id)
    if not apartamento:
        flash("El apartamento no existe.", "error")
        return redirect(url_for("apartamentos.listar_apartamentos"))

    errores, datos = validar_datos_apartamento(request.form, apartamento)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario(request.form, "editar", apartamento)

    try:
        for campo, valor in datos.items():
            setattr(apartamento, campo, valor)
        db.session.commit()
        flash(f"Apartamento '{apartamento.numero_apartamento}' actualizado correctamente.", "exito")
        return redirect(url_for("apartamentos.listar_apartamentos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar el apartamento: {e}", "error")
        return _formulario(request.form, "editar", apartamento)


@apartamentos_bp.route("/<int:id>/eliminar", methods=["POST"])
def eliminar_apartamento(id):
    apartamento = db.session.get(Apartamento, id)
    if not apartamento:
        flash("El apartamento no existe.", "error")
    elif apartamento.venta is not None:
        flash("No se puede eliminar: el apartamento ya tiene una venta registrada.", "error")
    else:
        try:
            numero = apartamento.numero_apartamento
            db.session.delete(apartamento)
            db.session.commit()
            flash(f"Apartamento '{numero}' eliminado correctamente.", "exito")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al eliminar el apartamento: {e}", "error")
    return redirect(url_for("apartamentos.listar_apartamentos"))
