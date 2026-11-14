"""
routes/auth.py
--------------
Inicio y cierre de sesion.

  GET  /login    Muestra el formulario.
  POST /login    Verifica correo y contrasena y abre la sesion.
  POST /logout   Cierra la sesion.

Decisiones de seguridad:
  - El login es por correo (la tabla usuarios no tiene nombre de usuario).
  - La contrasena se compara con Usuario.verificar_contrasena(), que usa
    el hash guardado; nunca se compara ni se guarda texto plano.
  - Un mismo mensaje para "correo no registrado" y "contrasena
    incorrecta", para no revelar que correos existen en el sistema.
  - Un usuario inactivo no puede entrar.
  - Cerrar sesion es POST (no un enlace) para que otra pagina no pueda
    cerrarla con una simple imagen o enlace.
"""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import db
from models.usuario import Usuario
from utils.seguridad import usuario_actual

auth_bp = Blueprint("auth", __name__)

MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."
MENSAJE_INACTIVO = "Su cuenta está inactiva. Comuníquese con el administrador."

# Hash de relleno: cuando el correo no existe se compara igual contra
# este hash, para que la respuesta tarde lo mismo que con un correo real
# y el tiempo de respuesta no delate que correos estan registrados.
_HASH_DE_RELLENO = generate_password_hash("relleno-sin-uso")


def _destino_seguro(destino):
    """Solo se acepta volver a una ruta interna ("/clientes/"). Se
    rechaza cualquier direccion externa ("https://...", "//sitio.com")
    para que un enlace de login manipulado no lleve a otro sitio."""
    if destino and destino.startswith("/") and not destino.startswith(("//", "/\\")):
        return destino
    return url_for("dashboard.inicio")


def autenticar(correo, contrasena):
    """Verifica las credenciales y, si son correctas, abre la sesion.
    La usan la pantalla de login y POST /api/login, para que las reglas
    sean las mismas en ambos. Devuelve (usuario, None) si entro, o
    (None, mensaje_de_error) si no."""
    correo = (correo or "").strip()
    # La contrasena no se recorta: se compara tal como se escribio.
    contrasena = contrasena or ""
    usuario = Usuario.query.filter(db.func.lower(Usuario.correo) == correo.lower()).first()

    if usuario is None:
        check_password_hash(_HASH_DE_RELLENO, contrasena)
        return None, MENSAJE_CREDENCIALES
    if not usuario.verificar_contrasena(contrasena):
        return None, MENSAJE_CREDENCIALES
    if usuario.estado != "activo":
        # Solo se llega aqui con la contrasena correcta, asi que el
        # mensaje no revela nada a quien no conoce la cuenta.
        return None, MENSAJE_INACTIVO

    # session.clear() descarta cualquier dato de una sesion anterior
    # antes de abrir la nueva.
    session.clear()
    session["id_usuario"] = usuario.id_usuario
    # permanent=True hace que la sesion caduque segun
    # PERMANENT_SESSION_LIFETIME (config.py) y no dure para siempre.
    session.permanent = True
    return usuario, None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_actual() is not None:
        return redirect(url_for("dashboard.inicio"))

    destino = request.values.get("next", "")
    correo = request.form.get("correo", "").strip()

    if request.method == "POST":
        usuario, error = autenticar(correo, request.form.get("contrasena", ""))
        if usuario is not None:
            return redirect(_destino_seguro(destino))
        flash(error, "error")

    return render_template("auth/login.html", correo=correo, destino=destino)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.login"))
