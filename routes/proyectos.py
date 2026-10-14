"""
routes/proyectos.py
-------------------
Modulo Proyectos (GA7-220501096-AA5-EV03).

Endpoints (pantallas HTML):
  GET  /proyectos/                    Listar
  GET  /proyectos/nuevo               Formulario de creacion
  POST /proyectos/crear               Crear
  GET  /proyectos/<id>/editar         Formulario de edicion
  POST /proyectos/<id>/actualizar     Actualizar
  POST /proyectos/<id>/eliminar       Eliminar

Validaciones (en validar_datos_proyecto, reutilizada tambien por la
API REST de routes/api.py):
  - Nombre: obligatorio, unico, maximo 150 caracteres.
  - Direccion: obligatoria, maximo 200 caracteres.
  - Ciudad: obligatoria, solo letras y espacios, maximo 100 caracteres.
  - Cliente: debe existir. Usuario gestor: debe existir y estar activo.

No se permite eliminar un proyecto que tenga apartamentos.
Las plantillas se piden con el prefijo "proyectos/" (sin template_folder
propio) para que no se confundan con las de otros modulos.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import db
from models.apartamento import Apartamento  # noqa: F401 (registra proyecto.apartamentos)
from models.cliente import Cliente
from models.proyecto import Proyecto
from models.usuario import Usuario
from utils.validaciones import a_entero, validar_lengitud, validar_no_vacio, validar_solo_letras

proyectos_bp = Blueprint("proyectos", __name__)


def validar_datos_proyecto(form, proyecto=None):
    """Revisa los datos de un proyecto. `form` es cualquier objeto con
    .get() (el formulario HTML o el JSON de la API). `proyecto` es el
    registro que se edita (None al crear).
    Devuelve (errores, datos_limpios)."""
    errores = []

    nombre = (form.get("nombre_proyecto") or "").strip()
    direccion = (form.get("direccion") or "").strip()
    ciudad = (form.get("ciudad") or "").strip()
    descripcion = (form.get("descripcion") or "").strip()
    id_cliente = a_entero(form.get("id_cliente"))
    id_usuario = a_entero(form.get("id_usuario"))

    if not validar_no_vacio(nombre):
        errores.append("El nombre del proyecto es requerido.")
    elif not validar_lengitud(nombre, max_len=150):
        errores.append("El nombre no puede exceder 150 caracteres.")
    else:
        consulta = Proyecto.query.filter(Proyecto.nombre_proyecto == nombre)
        if proyecto is not None:
            consulta = consulta.filter(Proyecto.id_proyecto != proyecto.id_proyecto)
        if consulta.first():
            errores.append("Ya existe un proyecto con este nombre.")

    if not validar_no_vacio(direccion):
        errores.append("La dirección es requerida.")
    elif not validar_lengitud(direccion, max_len=200):
        errores.append("La dirección no puede exceder 200 caracteres.")

    if not validar_no_vacio(ciudad):
        errores.append("La ciudad es requerida.")
    elif not validar_solo_letras(ciudad):
        errores.append("La ciudad solo puede contener letras y espacios (sin números).")
    elif not validar_lengitud(ciudad, max_len=100):
        errores.append("La ciudad no puede exceder 100 caracteres.")

    if id_cliente is None:
        errores.append("Debe seleccionar un cliente.")
    elif not db.session.get(Cliente, id_cliente):
        errores.append("El cliente seleccionado no existe.")

    if id_usuario is None:
        errores.append("Debe seleccionar un usuario gestor.")
    else:
        usuario = db.session.get(Usuario, id_usuario)
        if not usuario:
            errores.append("El usuario seleccionado no existe.")
        elif usuario.estado != "activo":
            errores.append("El usuario debe estar activo para gestionar un proyecto.")

    datos = dict(
        nombre_proyecto=nombre,
        direccion=direccion,
        ciudad=ciudad,
        descripcion=descripcion or None,
        id_cliente=id_cliente,
        id_usuario=id_usuario,
    )
    return errores, datos


def _formulario(accion, proyecto=None, **valores):
    return render_template(
        "proyectos/formulario.html",
        clientes=Cliente.query.order_by(Cliente.nombre, Cliente.apellido).all(),
        usuarios=Usuario.query.filter_by(estado="activo").order_by(Usuario.nombre).all(),
        proyecto=proyecto,
        accion=accion,
        **valores,
    )


@proyectos_bp.route("/", methods=["GET"])
def listar_proyectos():
    proyectos = Proyecto.query.order_by(Proyecto.nombre_proyecto).all()
    return render_template("proyectos/lista.html", proyectos=proyectos)


@proyectos_bp.route("/nuevo", methods=["GET"])
def formulario_nuevo():
    return _formulario("crear")


@proyectos_bp.route("/crear", methods=["POST"])
def crear_proyecto():
    errores, datos = validar_datos_proyecto(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        # Se devuelven los valores escritos para no obligar a reescribirlos.
        return _formulario(
            "crear",
            nombre=datos["nombre_proyecto"],
            direccion=datos["direccion"],
            ciudad=datos["ciudad"],
            descripcion=datos["descripcion"],
            id_cliente=request.form.get("id_cliente"),
            id_usuario=request.form.get("id_usuario"),
        )

    try:
        db.session.add(Proyecto(**datos))
        db.session.commit()
        flash(f"Proyecto '{datos['nombre_proyecto']}' creado correctamente.", "exito")
        return redirect(url_for("proyectos.listar_proyectos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear proyecto: {e}", "error")
        return _formulario("crear")


@proyectos_bp.route("/<int:id>/editar", methods=["GET"])
def formulario_editar(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))
    return _formulario("editar", proyecto)


@proyectos_bp.route("/<int:id>/actualizar", methods=["POST"])
def actualizar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))

    errores, datos = validar_datos_proyecto(request.form, proyecto)
    if errores:
        for error in errores:
            flash(error, "error")
        return _formulario("editar", proyecto)

    try:
        for campo, valor in datos.items():
            setattr(proyecto, campo, valor)
        db.session.commit()
        flash(f"Proyecto '{proyecto.nombre_proyecto}' actualizado correctamente.", "exito")
        return redirect(url_for("proyectos.listar_proyectos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar proyecto: {e}", "error")
        return _formulario("editar", proyecto)


@proyectos_bp.route("/<int:id>/eliminar", methods=["POST"])
def eliminar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
    elif proyecto.apartamentos:
        flash("No se puede eliminar: el proyecto tiene apartamentos registrados. Elimine primero sus apartamentos.", "error")
    else:
        try:
            nombre = proyecto.nombre_proyecto
            db.session.delete(proyecto)
            db.session.commit()
            flash(f"Proyecto '{nombre}' eliminado correctamente.", "exito")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al eliminar proyecto: {e}", "error")
    return redirect(url_for("proyectos.listar_proyectos"))
