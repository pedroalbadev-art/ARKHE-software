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

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from models import db
from models.usuario import Usuario
from utils.seguridad import puede_cambiar_estado, rol_requerido, usuario_actual
from utils.validaciones import (
    ESTADOS_VALIDOS,
    ROLES_VALIDOS,
    es_contrasena_valida,
    es_correo_valido,
    es_estado_valido,
    es_rol_valido,
    es_texto_valido,
    validar_lengitud,
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

    # Longitudes maximas de las columnas (nombre y apellido VARCHAR(100),
    # correo VARCHAR(150)), igual que en routes/clientes.py.
    if not es_texto_valido(form.get("nombre", "")):
        errores.append("El nombre solo puede contener letras y espacios.")
    elif not validar_lengitud(form.get("nombre", ""), max_len=100):
        errores.append("El nombre no puede exceder 100 caracteres.")
    if not es_texto_valido(form.get("apellido", "")):
        errores.append("El apellido solo puede contener letras y espacios.")
    elif not validar_lengitud(form.get("apellido", ""), max_len=100):
        errores.append("El apellido no puede exceder 100 caracteres.")
    if not es_correo_valido(form.get("correo", "")):
        errores.append("El correo electrónico no tiene un formato válido.")
    elif not validar_lengitud(form.get("correo", ""), max_len=150):
        errores.append("El correo electrónico no puede exceder 150 caracteres.")

    contrasena = form.get("contrasena", "")
    if requiere_contrasena or contrasena:
        if not es_contrasena_valida(contrasena):
            errores.append("La contraseña debe tener mínimo 8 caracteres, sin espacios al inicio ni al final.")

    if not es_rol_valido(form.get("rol", "")):
        errores.append(f"El rol debe ser uno de: {', '.join(sorted(ROLES_VALIDOS))}.")

    estado = form.get("estado", "activo")
    if not es_estado_valido(estado):
        errores.append(f"El estado debe ser uno de: {', '.join(sorted(ESTADOS_VALIDOS))}.")

    return errores


def motivo_bloqueo_usuario(usuario, actual, rol_nuevo=None, estado_nuevo=None, eliminar=False):
    """Reglas que protegen las cuentas (las usan las pantallas y la API).
    `usuario` es la cuenta que se va a cambiar y `actual` quien tiene la
    sesion. Devuelve el motivo por el que NO se permite el cambio, o
    None si se permite.

      1. Nadie puede eliminar ni desactivar su propia cuenta (se
         quedaria fuera del sistema en ese mismo instante).
      2. El sistema nunca puede quedar sin un Administrador activo: no
         se elimina, desactiva ni cambia de rol al ultimo que queda.
    """
    rol_nuevo = usuario.rol if rol_nuevo is None else rol_nuevo
    estado_nuevo = usuario.estado if estado_nuevo is None else estado_nuevo
    es_propia = actual is not None and usuario.id_usuario == actual.id_usuario

    if es_propia and eliminar:
        return "No puede eliminar su propia cuenta."
    if es_propia and estado_nuevo != "activo":
        return "No puede desactivar su propia cuenta."

    era_admin_activo = usuario.rol == "Administrador" and usuario.estado == "activo"
    sigue_admin_activo = not eliminar and rol_nuevo == "Administrador" and estado_nuevo == "activo"
    if era_admin_activo and not sigue_admin_activo:
        otros = Usuario.query.filter(
            Usuario.rol == "Administrador",
            Usuario.estado == "activo",
            Usuario.id_usuario != usuario.id_usuario,
        ).count()
        if otros == 0:
            return "No se permite: el sistema quedaría sin ningún Administrador activo."
    return None


@usuarios_bp.route("/")
@rol_requerido("usuarios", "ver")
def listar_usuarios():
    """Muestra la tabla con todos los usuarios registrados, ordenados
    alfabeticamente por nombre."""
    return _lista()


def _lista(valores=None):
    """Dibuja el listado. Si llegan `valores` (lo escrito en el modal
    "Nuevo Usuario" cuando hubo un error), la pagina se muestra con el
    modal abierto y esos datos puestos. La contraseña nunca se devuelve
    al formulario: la plantilla no la usa y hay que escribirla de nuevo."""
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template(
        "usuarios/lista.html",
        usuarios=usuarios,
        roles=sorted(ROLES_VALIDOS),
        valores=valores or {},
        abrir_modal=valores is not None,
    )


@usuarios_bp.route("/nuevo", methods=["POST"])
@rol_requerido("usuarios", "editar")
def crear_usuario():
    """Valida y crea un nuevo usuario a partir del formulario modal
    'Nuevo Usuario' (definido en lista.html). Los usuarios nuevos
    siempre inician con estado 'activo'."""
    errores = _validar_datos_usuario(request.form, requiere_contrasena=True)
    if errores:
        for error in errores:
            flash(error, "error")
        # Se vuelve a mostrar la lista con el modal abierto y lo escrito.
        return _lista(valores=request.form)

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
        return _lista(valores=request.form)

    flash(f"Usuario '{nuevo_usuario.nombre_completo}' creado correctamente.", "exito")
    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/<int:id_usuario>/editar", methods=["GET"])
@rol_requerido("usuarios", "editar")
def editar_usuario(id_usuario):
    """Muestra el formulario de edicion precargado con los datos
    actuales del usuario indicado."""
    usuario = Usuario.query.get_or_404(id_usuario)
    return render_template(
        "usuarios/formulario.html", usuario=usuario, roles=sorted(ROLES_VALIDOS)
    )


@usuarios_bp.route("/<int:id_usuario>/editar", methods=["POST"])
@rol_requerido("usuarios", "editar")
def actualizar_usuario(id_usuario):
    """Valida y guarda los cambios enviados desde el formulario de
    edicion, incluyendo rol y estado."""
    usuario = Usuario.query.get_or_404(id_usuario)
    # Sin .strip(): se guarda exactamente lo que valido _validar_datos_usuario.
    contrasena_nueva = request.form.get("contrasena", "")

    errores = _validar_datos_usuario(request.form, requiere_contrasena=False)
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("usuarios.editar_usuario", id_usuario=id_usuario))

    bloqueo = motivo_bloqueo_usuario(
        usuario, usuario_actual(),
        rol_nuevo=request.form["rol"], estado_nuevo=request.form.get("estado", "activo"),
    )
    if bloqueo:
        flash(bloqueo, "error")
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
@rol_requerido("usuarios", "eliminar")
def eliminar_usuario(id_usuario):
    """Elimina un usuario de la base de datos.

    Se implementa como POST (disparado desde un formulario con
    confirmacion en el navegador, ver lista.html) y no como GET,
    siguiendo el mismo estandar de codificacion que routes/clientes.py.
    """
    usuario = Usuario.query.get_or_404(id_usuario)
    bloqueo = motivo_bloqueo_usuario(usuario, usuario_actual(), eliminar=True)
    # Misma regla que la API: un usuario que gestiona proyectos no se
    # elimina (la llave foranea lo impediria con un error 500).
    if not bloqueo and usuario.proyectos:
        bloqueo = "No se puede eliminar: el usuario gestiona proyectos. Puede desactivarlo."
    if bloqueo:
        flash(bloqueo, "error")
        return redirect(url_for("usuarios.listar_usuarios"))
    nombre_eliminado = usuario.nombre_completo
    db.session.delete(usuario)
    db.session.commit()
    flash(f"Usuario '{nombre_eliminado}' eliminado.", "info")
    return redirect(url_for("usuarios.listar_usuarios"))


@usuarios_bp.route("/<int:id_usuario>/estado", methods=["POST"])
@rol_requerido("usuarios", "estado")
def cambiar_estado_usuario(id_usuario):
    """Activa un usuario inactivo o desactiva uno activo. No cambia
    nombre, correo, rol ni contraseña. El Administrador puede hacerlo
    con cualquier cuenta; el Gerente, solo con cuentas de Vendedor."""
    usuario = Usuario.query.get_or_404(id_usuario)
    if not puede_cambiar_estado(usuario_actual(), usuario):
        abort(403)
    estado_nuevo = "inactivo" if usuario.estado == "activo" else "activo"

    bloqueo = motivo_bloqueo_usuario(usuario, usuario_actual(), estado_nuevo=estado_nuevo)
    if bloqueo:
        flash(bloqueo, "error")
        return redirect(url_for("usuarios.listar_usuarios"))

    usuario.estado = estado_nuevo
    db.session.commit()
    accion = "activado" if estado_nuevo == "activo" else "desactivado"
    flash(f"Usuario '{usuario.nombre_completo}' {accion}.", "exito")
    return redirect(url_for("usuarios.listar_usuarios"))
