"""
utils/seguridad.py
------------------
Piezas de la autenticacion que comparten todos los modulos:

  - usuario_actual():  quien tiene la sesion abierta (o None).
  - login_requerido:   decorador que exige sesion en una ruta.
  - exigir_sesion():   la misma regla, aplicada a TODA la aplicacion
                       desde app.py antes de atender cada peticion.

Como funciona la sesion de Flask: al iniciar sesion se guarda el ID del
usuario en `session`. Flask envia ese dato al navegador dentro de una
cookie FIRMADA con SECRET_KEY: el navegador la devuelve en cada
peticion y Flask comprueba la firma. Si alguien altera la cookie (por
ejemplo, para poner el ID de otro usuario), la firma deja de coincidir
y Flask la descarta. En la cookie solo viaja el ID, nunca la contrasena
ni el rol: el rol se lee de la base de datos en cada peticion.
"""

from functools import wraps

from flask import g, redirect, request, session, url_for

from models import db
from models.usuario import Usuario

# Rutas que se pueden abrir sin sesion: la pantalla de login y los
# archivos estaticos (CSS y logo, que la propia pantalla de login usa).
ENDPOINTS_PUBLICOS = {"auth.login", "static"}


def usuario_actual():
    """Devuelve el Usuario con sesion abierta, o None.

    Se consulta la base en cada peticion (y no se confia solo en la
    cookie) para que un usuario desactivado o eliminado pierda el acceso
    de inmediato, aunque su sesion siga abierta en el navegador.
    El resultado se guarda en `g` (un espacio que dura una sola
    peticion) para no repetir la consulta dentro de la misma peticion.
    """
    if "usuario_actual" not in g:
        usuario = None
        id_usuario = session.get("id_usuario")
        if id_usuario is not None:
            usuario = db.session.get(Usuario, id_usuario)
            if usuario is None or usuario.estado != "activo":
                session.clear()
                usuario = None
        g.usuario_actual = usuario
    return g.usuario_actual


def _ir_al_login():
    """Redirige al login recordando la pagina pedida (parametro `next`)
    para volver a ella despues de iniciar sesion."""
    destino = request.full_path.rstrip("?") if request.method == "GET" else None
    return redirect(url_for("auth.login", next=destino))


def login_requerido(vista):
    """Decorador: la ruta decorada solo se ejecuta si hay sesion; si no,
    se redirige al login.

    Un decorador es una funcion que envuelve a otra. `@login_requerido`
    sobre una ruta equivale a `ruta = login_requerido(ruta)`: Flask
    termina llamando a `envoltura`, que primero revisa la sesion y solo
    despues llama a la ruta original. @wraps conserva el nombre de la
    ruta original, que Flask usa para url_for().
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            return _ir_al_login()
        return vista(*args, **kwargs)
    return envoltura


def exigir_sesion():
    """Se registra en app.py con before_request: corre antes de CADA
    peticion. Asi ninguna pagina queda sin proteger por olvido (una ruta
    nueva queda protegida aunque nadie le ponga el decorador).

    Si devuelve None, la peticion sigue su curso normal; si devuelve una
    respuesta (la redireccion), Flask la envia y no ejecuta la ruta.

    La API (/api) se protege en la tarea de roles, junto con su propio
    inicio de sesion y la actualizacion de la coleccion de Postman.
    """
    if request.endpoint in ENDPOINTS_PUBLICOS or request.blueprint == "api":
        return None
    if usuario_actual() is None:
        return _ir_al_login()
    return None
