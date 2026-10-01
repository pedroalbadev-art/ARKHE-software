"""
routes/proyectos.py (v2)
------------------------
Rutas (endpoints) del módulo Proyectos.

Actualizado 2026-09-30:
  - Agregada validación: ciudad solo acepta letras y espacios (sin números)
  - Plantillas con prefijo "proyectos/" (sin template_folder propio)
  - No permite eliminar un proyecto que tenga apartamentos
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db
from models.proyecto import Proyecto
from models.cliente import Cliente
from models.usuario import Usuario
from models.apartamento import Apartamento  # noqa: F401 (registra proyecto.apartamentos)
from utils.validaciones import validar_no_vacio, validar_lengitud, validar_solo_letras

# Sin template_folder propio: las plantillas se piden con el prefijo
# "proyectos/" (igual que Clientes y Usuarios) para que lista.html y
# formulario.html no se confundan con las de otros modulos.
proyectos_bp = Blueprint("proyectos", __name__)


@proyectos_bp.route("/", methods=["GET"])
def listar_proyectos():
    """
    GET /proyectos/
    Muestra una tabla con todos los proyectos registrados.
    Incluye nombre, ciudad, cliente responsable y usuario gestor.
    """
    proyectos = Proyecto.query.all()
    return render_template("proyectos/lista.html", proyectos=proyectos)


@proyectos_bp.route("/nuevo", methods=["GET"])
def formulario_nuevo():
    """
    GET /proyectos/nuevo
    Muestra el formulario para crear un nuevo proyecto.
    Carga la lista de clientes y usuarios disponibles en selectores.
    """
    clientes = Cliente.query.all()
    usuarios = Usuario.query.filter_by(estado="activo").all()
    return render_template(
        "proyectos/formulario.html",
        clientes=clientes,
        usuarios=usuarios,
        proyecto=None,
        accion="crear",
    )


@proyectos_bp.route("/crear", methods=["POST"])
def crear_proyecto():
    """
    POST /proyectos/crear
    Recibe los datos del formulario y crea un nuevo proyecto.

    Validaciones:
      - Campos requeridos: nombre, direccion, ciudad, id_cliente, id_usuario
      - Nombre: no vacío, único, máx 150 chars
      - Dirección: no vacío, máx 200 chars (permite números y caracteres especiales)
      - Ciudad: solo letras y espacios, no vacío, máx 100 chars
      - Cliente: debe existir (id_cliente en tabla clientes)
      - Usuario: debe existir y estar activo (id_usuario en tabla usuarios)
    """
    nombre = request.form.get("nombre_proyecto", "").strip()
    direccion = request.form.get("direccion", "").strip()
    ciudad = request.form.get("ciudad", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    id_cliente = request.form.get("id_cliente")
    id_usuario = request.form.get("id_usuario")

    # Validar campos requeridos
    errores = []

    if not validar_no_vacio(nombre):
        errores.append("El nombre del proyecto es requerido.")
    elif not validar_lengitud(nombre, max_len=150):
        errores.append("El nombre no puede exceder 150 caracteres.")
    else:
        # Verificar unicidad de nombre
        existe = Proyecto.query.filter_by(nombre_proyecto=nombre).first()
        if existe:
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

    if not id_cliente:
        errores.append("Debe seleccionar un cliente.")
    else:
        try:
            cliente = db.session.get(Cliente, int(id_cliente))
            if not cliente:
                errores.append("El cliente seleccionado no existe.")
        except (ValueError, TypeError):
            errores.append("ID de cliente inválido.")

    if not id_usuario:
        errores.append("Debe seleccionar un usuario gestor.")
    else:
        try:
            usuario = db.session.get(Usuario, int(id_usuario))
            if not usuario:
                errores.append("El usuario seleccionado no existe.")
            elif usuario.estado != "activo":
                errores.append("El usuario debe estar activo para gestionar un proyecto.")
        except (ValueError, TypeError):
            errores.append("ID de usuario inválido.")

    if errores:
        for error in errores:
            flash(error, "error")
        clientes = Cliente.query.all()
        usuarios = Usuario.query.filter_by(estado="activo").all()
        return render_template(
            "proyectos/formulario.html",
            clientes=clientes,
            usuarios=usuarios,
            proyecto=None,
            accion="crear",
            nombre=nombre,
            direccion=direccion,
            ciudad=ciudad,
            descripcion=descripcion,
            id_cliente=id_cliente,
            id_usuario=id_usuario,
        )

    # Crear nuevo proyecto
    try:
        nuevo_proyecto = Proyecto(
            nombre_proyecto=nombre,
            direccion=direccion,
            ciudad=ciudad,
            descripcion=descripcion if descripcion else None,
            id_cliente=int(id_cliente),
            id_usuario=int(id_usuario),
        )
        db.session.add(nuevo_proyecto)
        db.session.commit()
        flash(f"Proyecto '{nombre}' creado correctamente.", "exito")
        return redirect(url_for("proyectos.listar_proyectos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear proyecto: {str(e)}", "error")
        clientes = Cliente.query.all()
        usuarios = Usuario.query.filter_by(estado="activo").all()
        return render_template(
            "proyectos/formulario.html",
            clientes=clientes,
            usuarios=usuarios,
            proyecto=None,
            accion="crear",
        )


@proyectos_bp.route("/<int:id>/editar", methods=["GET"])
def formulario_editar(id):
    """
    GET /proyectos/<id>/editar
    Muestra el formulario para editar un proyecto existente.
    """
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))

    clientes = Cliente.query.all()
    usuarios = Usuario.query.filter_by(estado="activo").all()
    return render_template(
        "proyectos/formulario.html",
        clientes=clientes,
        usuarios=usuarios,
        proyecto=proyecto,
        accion="editar",
    )


@proyectos_bp.route("/<int:id>/actualizar", methods=["POST"])
def actualizar_proyecto(id):
    """
    POST /proyectos/<id>/actualizar
    Actualiza los datos de un proyecto existente.
    Aplica las mismas validaciones que crear_proyecto().
    """
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))

    nombre = request.form.get("nombre_proyecto", "").strip()
    direccion = request.form.get("direccion", "").strip()
    ciudad = request.form.get("ciudad", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    id_cliente = request.form.get("id_cliente")
    id_usuario = request.form.get("id_usuario")

    # Validar campos (igual que en crear_proyecto)
    errores = []

    if not validar_no_vacio(nombre):
        errores.append("El nombre del proyecto es requerido.")
    elif not validar_lengitud(nombre, max_len=150):
        errores.append("El nombre no puede exceder 150 caracteres.")
    else:
        # Verificar unicidad (permitir el mismo nombre si es el mismo proyecto)
        existe = Proyecto.query.filter(
            Proyecto.nombre_proyecto == nombre,
            Proyecto.id_proyecto != id,
        ).first()
        if existe:
            errores.append("Ya existe otro proyecto con este nombre.")

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

    if not id_cliente:
        errores.append("Debe seleccionar un cliente.")
    else:
        try:
            cliente = db.session.get(Cliente, int(id_cliente))
            if not cliente:
                errores.append("El cliente seleccionado no existe.")
        except (ValueError, TypeError):
            errores.append("ID de cliente inválido.")

    if not id_usuario:
        errores.append("Debe seleccionar un usuario gestor.")
    else:
        try:
            usuario = db.session.get(Usuario, int(id_usuario))
            if not usuario:
                errores.append("El usuario seleccionado no existe.")
            elif usuario.estado != "activo":
                errores.append("El usuario debe estar activo para gestionar un proyecto.")
        except (ValueError, TypeError):
            errores.append("ID de usuario inválido.")

    if errores:
        for error in errores:
            flash(error, "error")
        clientes = Cliente.query.all()
        usuarios = Usuario.query.filter_by(estado="activo").all()
        return render_template(
            "proyectos/formulario.html",
            clientes=clientes,
            usuarios=usuarios,
            proyecto=proyecto,
            accion="editar",
        )

    # Actualizar proyecto
    try:
        proyecto.nombre_proyecto = nombre
        proyecto.direccion = direccion
        proyecto.ciudad = ciudad
        proyecto.descripcion = descripcion if descripcion else None
        proyecto.id_cliente = int(id_cliente)
        proyecto.id_usuario = int(id_usuario)
        db.session.commit()
        flash(f"Proyecto '{nombre}' actualizado correctamente.", "exito")
        return redirect(url_for("proyectos.listar_proyectos"))
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar proyecto: {str(e)}", "error")
        clientes = Cliente.query.all()
        usuarios = Usuario.query.filter_by(estado="activo").all()
        return render_template(
            "proyectos/formulario.html",
            clientes=clientes,
            usuarios=usuarios,
            proyecto=proyecto,
            accion="editar",
        )


@proyectos_bp.route("/<int:id>/eliminar", methods=["POST"])
def eliminar_proyecto(id):
    """
    POST /proyectos/<id>/eliminar
    Elimina un proyecto de la base de datos.

    Nota de negocio: Verificar si tiene apartamentos asociados antes de
    permitir la eliminación (por ahora, si hay apartamentos, la BD lanzará
    un error de integridad referencial).
    """
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash("El proyecto no existe.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))

    if proyecto.apartamentos:
        flash("No se puede eliminar: el proyecto tiene apartamentos registrados. Elimine primero sus apartamentos.", "error")
        return redirect(url_for("proyectos.listar_proyectos"))

    try:
        nombre = proyecto.nombre_proyecto
        db.session.delete(proyecto)
        db.session.commit()
        flash(f"Proyecto '{nombre}' eliminado correctamente.", "exito")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar proyecto: {str(e)}", "error")

    return redirect(url_for("proyectos.listar_proyectos"))
