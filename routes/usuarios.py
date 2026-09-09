"""
routes/usuarios.py
-------------------
Rutas (endpoints) del modulo de Usuarios: listar, crear, editar y
eliminar. Blueprint de Flask, registrado en app.py bajo el prefijo
/usuarios. Construido en la evidencia GA7-220501096-AA3-EV02.

Dos diferencias clave frente al primer modulo (Clientes, EV01):

1. Aqui SI se valida el contenido de cada campo antes de guardar (no
   solo que no venga vacio), usando utils/validaciones.py. Es la
   pieza que pide el indicador 2 del instrumento de esta evidencia:
   "Realiza pruebas de validaciones y las documenta". Si hay errores,
   se guardan como mensajes flash de categoria "error" y se redirige
   de vuelta sin tocar la base de datos.
2. La contraseña nunca se guarda en texto plano: se hashea con
   Usuario.establecer_contrasena() (ver models/usuario.py) antes de
   guardar. Al editar, si el campo de contraseña se deja en blanco,
   se conserva la contraseña actual (no se sobreescribe con un hash
   de texto vacio).

El error de correo duplicado (la tabla ya lo exige con UNIQUE) se
captura explicitamente para mostrar un mensaje claro en vez de dejar
que Flask muestre un error 500 sin control.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from models import db
from models.usuario import Usuario
from utils.validaciones import (
    ESTADOS_VALIDOS,
    ROLES_VALIDOS,
    es_contrasena_valida,
    es_correo_valido,
    es_estado_valido,
    es_rol_valido,
    es_texto_valido,
)

# No se personaliza template_folder (ver nota en routes/clientes.py):
# se usa la carpeta de plantillas por defecto de la app, y cada
# render_template() de este archivo pide la plantilla con el prefijo
# "usuarios/" para que su nombre no choque con el de otro modulo.
usuarios_bp = Blueprint("usuarios", __name__)


def _validar_datos_usuario(form, requiere_contrasena):
    """Revisa los datos de un formulario de usuario y devuelve una
    lista de mensajes de error (vacia si todo es valido).

    requiere_contrasena es False al editar cuando el campo de
    contraseña se deja en blanco (significa "no cambiarla"); en ese
    caso no se valida su longitud porque no se va a usar.
    """
    errores = []

    if not es_texto_valido(form.get("nombre", "")):
        errores.append("El nombre solo puede contener letras y espacios.")
    if not es_texto_valido(form.get("apellido", "")):
        errores.append("El apellido solo puede contener letras y espacios.")
    if not es_correo_valido(form.get("correo", "")):
        errores.append("El correo electronico no tiene un formato valido.")

    contrasena = form.get("contrasena", "")
    if requiere_contrasena or contrasena:
        if not es_contrasena_valida(contrasena):
            errores.append("La contraseña debe tener minimo 8 caracteres.")

    if not es_rol_valido(form.get("rol", "")):
        errores.append(f"El rol debe ser uno de: {', '.join(sorted(ROLES_VALIDOS))}.")

    estado = form.get("estado", "activo")
    if not es_estado_valido(estado):
        errores.append(f"El estado debe ser uno de: {', '.join(sorted(ESTADOS_VALIDOS))}.")

    return errores


@usuarios_bp.route("/")
def listar_usuarios():
    """Muestra la tabla con todos los usuarios registrados, ordenados
    alfabeticamente por nombre."""
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template(
        "usuarios/lista.html", usuarios=usuarios, roles=sorted(ROLES_VALIDOS)
    )


@usuarios_bp.route("/nuevo", methods=["POST"])
def crear_usuario():
    """Valida y crea un nuevo usuario a partir del formulario modal
    'Nuevo Usuario' (definido en lista.html). Los usuarios nuevos
    siempre inician con estado 'activo'."""
    errores = _validar_datos_usuario(request.form, requiere_contrasena=True)
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("usuarios.listar_usuarios"))

    nuevo_usuario = Usuario(
        nombre=request.form["nombre"].strip(),
        apellido=request.form["apellido"].strip(),
        correo=request.form["correo"].strip(),
        rol=request.form["rol"],
        estado="activo",
    )
    nuevo_usuario.establecer_contrasena(request.form["contrasena"])

    try:
        db.session.add(nuevo_usuario)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un usuario registrado con ese correo.", "error")
        return redirect(url_for("usuarios.listar_usuarios"))

    flash(f"Usuario '{nuevo_usuario.nombre_completo}' creado correctamente.", "exito")
    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/<int:id_usuario>/editar", methods=["GET"])
def editar_usuario(id_usuario):
    """Muestra el formulario de edicion precargado con los datos
    actuales del usuario indicado."""
    usuario = Usuario.query.get_or_404(id_usuario)
    return render_template(
        "usuarios/formulario.html", usuario=usuario, roles=sorted(ROLES_VALIDOS)
    )


@usuarios_bp.route("/<int:id_usuario>/editar", methods=["POST"])
def actualizar_usuario(id_usuario):
    """Valida y guarda los cambios enviados desde el formulario de
    edicion, incluyendo rol y estado."""
    usuario = Usuario.query.get_or_404(id_usuario)
    contrasena_nueva = request.form.get("contrasena", "").strip()

    errores = _validar_datos_usuario(request.form, requiere_contrasena=False)
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("usuarios.editar_usuario", id_usuario=id_usuario))

    usuario.nombre = request.form["nombre"].strip()
    usuario.apellido = request.form["apellido"].strip()
    usuario.correo = request.form["correo"].strip()
    usuario.rol = request.form["rol"]
    usuario.estado = request.form.get("estado", "activo")
    if contrasena_nueva:
        usuario.establecer_contrasena(contrasena_nueva)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un usuario registrado con ese correo.", "error")
        return redirect(url_for("usuarios.editar_usuario", id_usuario=id_usuario))

    flash(f"Usuario '{usuario.nombre_completo}' actualizado.", "exito")
    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/<int:id_usuario>/eliminar", methods=["POST"])
def eliminar_usuario(id_usuario):
    """Elimina un usuario de la base de datos.

    Se implementa como POST (disparado desde un formulario con
    confirmacion en el navegador, ver lista.html) y no como GET,
    siguiendo el mismo estandar de codificacion que routes/clientes.py.
    """
    usuario = Usuario.query.get_or_404(id_usuario)
    nombre_eliminado = usuario.nombre_completo
    db.session.delete(usuario)
    db.session.commit()
    flash(f"Usuario '{nombre_eliminado}' eliminado.", "info")
    return redirect(url_for("usuarios.listar_usuarios"))
