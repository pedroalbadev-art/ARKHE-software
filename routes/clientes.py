"""
routes/clientes.py
-------------------
Rutas (endpoints) del modulo de Clientes: listar, crear, editar y
eliminar. Blueprint de Flask, registrado en app.py bajo el prefijo
/clientes.

Actualizado en la evidencia GA7-220501096-AA3-EV02 (2026-09-09) para
agregar validacion real de contenido, usando utils/validaciones.py
(las mismas funciones que usa routes/usuarios.py). Hasta esta
evidencia, este archivo solo dependia de "required" en el HTML y de
las restricciones NOT NULL/UNIQUE de la base de datos: eso evitaba
campos vacios, pero no un documento con letras o un correo sin
formato valido. El error de documento/correo duplicado (ya exigido
por la base de datos con UNIQUE) tambien se captura aqui para mostrar
un mensaje claro en vez de un error 500 sin control.

Estandar de codificacion seguido en este archivo:
- Nombres de funcion en snake_case describiendo la accion (verbo +
  sustantivo): listar_clientes, crear_cliente, editar_cliente, etc.
- Cada funcion tiene un docstring explicando que hace y por que.
- Las eliminaciones y modificaciones se hacen por POST, nunca por GET,
  para que un simple enlace (o un rastreador de buscador) no pueda
  borrar o cambiar datos por accidente.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from models import db
from models.cliente import Cliente
from utils.seguridad import rol_requerido
from utils.validaciones import (
    es_correo_valido,
    es_documento_valido,
    es_telefono_valido,
    es_texto_valido,
    validar_lengitud,
)

# No se personaliza template_folder: se usa la carpeta de plantillas
# por defecto de la app (templates/), que ya tiene una subcarpeta por
# modulo (templates/clientes/, templates/usuarios/, etc.). Por eso
# cada render_template() de este archivo pide la plantilla con el
# prefijo "clientes/" (ver nota mas abajo, corregida en GA7-AA3-EV02:
# usar un template_folder propio por blueprint mezclaba los nombres de
# plantilla entre modulos y causaba que /usuarios/ mostrara por error
# la plantilla de Clientes).
clientes_bp = Blueprint("clientes", __name__)


def _validar_datos_cliente(form):
    """Revisa los datos de un formulario de cliente y devuelve una
    lista de mensajes de error (vacia si todo es valido)."""
    errores = []

    # Las longitudes maximas son las de las columnas de la tabla
    # (nombre y apellido VARCHAR(100), correo VARCHAR(150)). Se validan
    # aqui para responder con un mensaje claro en vez de un error de
    # base de datos.
    if not es_texto_valido(form.get("nombre", "")):
        errores.append("El nombre solo puede contener letras y espacios.")
    elif not validar_lengitud(form.get("nombre", ""), max_len=100):
        errores.append("El nombre no puede exceder 100 caracteres.")
    if not es_texto_valido(form.get("apellido", "")):
        errores.append("El apellido solo puede contener letras y espacios.")
    elif not validar_lengitud(form.get("apellido", ""), max_len=100):
        errores.append("El apellido no puede exceder 100 caracteres.")
    if not es_documento_valido(form.get("documento", "")):
        errores.append("El documento debe contener solo numeros (6 a 15 digitos).")
    if not es_correo_valido(form.get("correo", "")):
        errores.append("El correo electronico no tiene un formato valido.")
    elif not validar_lengitud(form.get("correo", ""), max_len=150):
        errores.append("El correo electronico no puede exceder 150 caracteres.")
    if not es_telefono_valido(form.get("telefono", "")):
        errores.append("El telefono debe contener solo numeros (7 a 15 digitos).")

    return errores


@clientes_bp.route("/")
@rol_requerido("clientes", "ver")
def listar_clientes():
    """Muestra la tabla con todos los clientes registrados, ordenados
    alfabeticamente por nombre."""
    return _lista()


def _lista(valores=None):
    """Dibuja el listado. `valores` son los datos que la persona escribio
    en el modal "Nuevo Cliente" cuando hubo un error: si llegan, la
    pagina se muestra con el modal abierto y esos datos puestos, para
    que solo corrija lo que fallo en vez de escribir todo de nuevo."""
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template(
        "clientes/lista.html",
        clientes=clientes,
        valores=valores or {},
        abrir_modal=valores is not None,
    )


@clientes_bp.route("/nuevo", methods=["POST"])
@rol_requerido("clientes", "editar")
def crear_cliente():
    """Valida y crea un nuevo cliente a partir del formulario modal
    'Nuevo Cliente' (definido en lista.html). Si hay errores de
    validacion, no se toca la base de datos y se muestran los
    mensajes con flash()."""
    errores = _validar_datos_cliente(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        # Se vuelve a mostrar la lista con el modal abierto y lo escrito.
        return _lista(valores=request.form)

    nuevo_cliente = Cliente(
        nombre=request.form["nombre"].strip(),
        apellido=request.form["apellido"].strip(),
        documento=request.form["documento"].strip(),
        correo=request.form["correo"].strip(),
        telefono=request.form["telefono"].strip(),
    )

    try:
        db.session.add(nuevo_cliente)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un cliente registrado con ese documento o correo.", "error")
        return _lista(valores=request.form)

    flash(f"Cliente '{nuevo_cliente.nombre_completo}' creado correctamente.", "exito")
    return redirect(url_for("clientes.listar_clientes"))


@clientes_bp.route("/<int:id_cliente>/editar", methods=["GET"])
@rol_requerido("clientes", "editar")
def editar_cliente(id_cliente):
    """Muestra el formulario de edicion precargado con los datos
    actuales del cliente indicado.

    get_or_404 busca el cliente por su llave primaria y, si no existe,
    responde automaticamente con un error 404 en vez de que el
    programa falle con una excepcion sin control.
    """
    cliente = Cliente.query.get_or_404(id_cliente)
    return render_template("clientes/formulario.html", cliente=cliente)


@clientes_bp.route("/<int:id_cliente>/editar", methods=["POST"])
@rol_requerido("clientes", "editar")
def actualizar_cliente(id_cliente):
    """Valida y guarda los cambios enviados desde el formulario de
    edicion."""
    cliente = Cliente.query.get_or_404(id_cliente)

    errores = _validar_datos_cliente(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("clientes.editar_cliente", id_cliente=id_cliente))

    cliente.nombre = request.form["nombre"].strip()
    cliente.apellido = request.form["apellido"].strip()
    cliente.documento = request.form["documento"].strip()
    cliente.correo = request.form["correo"].strip()
    cliente.telefono = request.form["telefono"].strip()

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un cliente registrado con ese documento o correo.", "error")
        return redirect(url_for("clientes.editar_cliente", id_cliente=id_cliente))

    flash(f"Cliente '{cliente.nombre_completo}' actualizado.", "exito")
    return redirect(url_for("clientes.listar_clientes"))


@clientes_bp.route("/<int:id_cliente>/eliminar", methods=["POST"])
@rol_requerido("clientes", "eliminar")
def eliminar_cliente(id_cliente):
    """Elimina un cliente de la base de datos.

    Se implementa como POST (disparado desde un formulario con
    confirmacion en el navegador, ver lista.html) y no como GET,
    siguiendo el estandar de codificacion de no realizar operaciones
    que cambian datos a traves de enlaces simples.
    """
    cliente = Cliente.query.get_or_404(id_cliente)
    # Misma regla que la API: un cliente con proyectos o ventas no se
    # elimina. Sin esta comprobacion, la llave foranea de MySQL
    # rechazaria el borrado y la pagina terminaria en un error 500.
    if cliente.proyectos or cliente.ventas:
        flash("No se puede eliminar: el cliente tiene proyectos o ventas asociados.", "error")
        return redirect(url_for("clientes.listar_clientes"))
    nombre_eliminado = cliente.nombre_completo
    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente '{nombre_eliminado}' eliminado.", "info")
    return redirect(url_for("clientes.listar_clientes"))
