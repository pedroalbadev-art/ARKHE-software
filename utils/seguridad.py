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

from flask import abort, g, jsonify, redirect, request, session, url_for

from models import db
from models.usuario import Usuario

# Rutas que se pueden abrir sin sesion: el login (pantalla y API) y los
# archivos estaticos (CSS y logo, que la propia pantalla de login usa).
ENDPOINTS_PUBLICOS = {"auth.login", "api.api_login", "static"}

# ---------------------------------------------------------------------
# Matriz de permisos (aprobada por Pedro el 2026-11-12)
# ---------------------------------------------------------------------
# PERMISOS[modulo][accion] = roles que pueden hacer esa accion.
#   ver       consultar listados y detalles
#   editar    crear y modificar
#   eliminar  borrar
#   estado    activar o desactivar (solo existe en usuarios)
#
# Es el UNICO lugar donde se decide que puede hacer cada rol: las rutas
# (rol_requerido) y las plantillas (puede) consultan esta tabla.
ADMIN, VENDEDOR, GERENTE = "Administrador", "Vendedor", "Gerente"
TODOS = {ADMIN, VENDEDOR, GERENTE}

PERMISOS = {
    "dashboard":    {"ver": TODOS},
    # Eliminar es SOLO del Administrador en todos los modulos. El
    # Vendedor crea y edita clientes, ventas y pagos, pero no elimina.
    "clientes":     {"ver": TODOS, "editar": {ADMIN, VENDEDOR}, "eliminar": {ADMIN}},
    "proyectos":    {"ver": TODOS, "editar": {ADMIN}, "eliminar": {ADMIN}},
    "apartamentos": {"ver": TODOS, "editar": {ADMIN}, "eliminar": {ADMIN}},
    "ventas":       {"ver": TODOS, "editar": {ADMIN, VENDEDOR}, "eliminar": {ADMIN}},
    "pagos":        {"ver": TODOS, "editar": {ADMIN, VENDEDOR}, "eliminar": {ADMIN}},
    # El Gerente consulta los usuarios y puede activar o desactivar
    # cuentas de Vendedor (ver puede_cambiar_estado), pero no crear,
    # editar ni eliminar usuarios.
    "usuarios":     {"ver": {ADMIN, GERENTE}, "editar": {ADMIN}, "eliminar": {ADMIN},
                     "estado": {ADMIN, GERENTE}},
}


def puede(usuario, modulo, accion):
    """True si el rol del usuario tiene permitida la accion en el modulo.
    Un modulo o una accion que no esten en la matriz se niegan."""
    if usuario is None:
        return False
    return usuario.rol in PERMISOS.get(modulo, {}).get(accion, set())


def puede_cambiar_estado(actual, cuenta):
    """True si `actual` puede activar o desactivar la cuenta `cuenta`.

    La matriz dice QUE roles pueden cambiar estados; esta funcion agrega
    SOBRE QUE cuentas: el Administrador sobre cualquiera, el Gerente
    solo sobre cuentas de Vendedor (no de Administrador ni de otro
    Gerente). Depende de la cuenta destino, por eso no cabe en la matriz
    y se comprueba dentro de la ruta, despues de buscar al usuario."""
    if not puede(actual, "usuarios", "estado"):
        return False
    return actual.rol == ADMIN or cuenta.rol == VENDEDOR


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
    """Respuesta cuando NO hay sesion (no se sabe quien hace la peticion).

    - Pantallas: redirige al login recordando la pagina pedida
      (parametro `next`) para volver a ella despues de iniciar sesion.
    - API: responde 401 en JSON; un programa (o Postman) no puede usar
      una pantalla de login, necesita un codigo que pueda interpretar.
    """
    if request.blueprint == "api":
        return jsonify(error="Debe iniciar sesion (POST /api/login)."), 401
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
    respuesta (la redireccion o el 401), Flask la envia y no ejecuta la
    ruta. Cubre tambien la API (/api).
    """
    if request.endpoint in ENDPOINTS_PUBLICOS:
        return None
    if usuario_actual() is None:
        return _ir_al_login()
    return None


def rol_requerido(modulo, accion):
    """Decorador: la ruta solo se ejecuta si el rol del usuario tiene
    permitida `accion` en `modulo` segun la matriz PERMISOS.

        @ventas_bp.route("/<int:id>/eliminar", methods=["POST"])
        @rol_requerido("ventas", "eliminar")
        def eliminar_venta(id): ...

    Tres resultados posibles:
      - Sin sesion        -> 401 (API) o redireccion al login (pantallas).
                             "No se quien eres".
      - Sin permiso       -> 403. "Se quien eres, pero tu rol no puede".
      - Con permiso       -> se ejecuta la ruta.

    Es un decorador "con parametros": rol_requerido("ventas", "eliminar")
    devuelve el decorador de verdad (`decorador`), que es el que envuelve
    a la ruta. Por eso hay tres funciones, una dentro de otra.
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = usuario_actual()
            if usuario is None:
                return _ir_al_login()
            if not puede(usuario, modulo, accion):
                abort(403)  # lo convierte en respuesta el manejador de app.py
            return vista(*args, **kwargs)
        # Marca que deja ver que permiso exige la ruta. Una prueba
        # (tests/test_permisos.py) recorre todas las rutas y falla si
        # alguna no tiene esta marca, es decir, si quedo sin proteger.
        envoltura.permiso = (modulo, accion)
        return envoltura
    return decorador
