"""
tests/test_auth.py
------------------
Pruebas del inicio y cierre de sesion (prioridad 1 del CLAUDE.md).

  AU-01..AU-03  Ninguna pagina se abre sin sesion
  AU-04..AU-09  Inicio de sesion
  AU-10..AU-12  Cierre y vigencia de la sesion
  AU-13..AU-14  Redireccion despues del login (parametro next)
  AU-15..AU-16  Decorador login_requerido y regla de la contrasena

La fixture `datos` (conftest.py) crea al usuario activo
luis@ejemplo.com / ClaveSegura1.
"""

import pytest

from models import db
from models.cliente import Cliente
from models.usuario import Usuario
from utils import seguridad
from utils.seguridad import login_requerido
from utils.validaciones import es_contrasena_valida

CORREO = "luis@ejemplo.com"
CLAVE = "ClaveSegura1"

PAGINAS = ["/", "/clientes/", "/usuarios/", "/proyectos/", "/apartamentos/",
           "/ventas/", "/pagos/", "/proyectos/nuevo", "/ventas/nueva"]


def entrar(api, correo=CORREO, contrasena=CLAVE, **extra):
    return api.post("/login", data={"correo": correo, "contrasena": contrasena, **extra})


def tiene_sesion(api):
    with api.session_transaction() as sesion:
        return "id_usuario" in sesion


def cambiar_estado(app, id_usuario, estado):
    with app.app_context():
        db.session.get(Usuario, id_usuario).estado = estado
        db.session.commit()


# ---------------------------------------------------------------------
# Ninguna pagina sin sesion
# ---------------------------------------------------------------------
@pytest.mark.parametrize("pagina", PAGINAS)
def test_au01_sin_sesion_toda_pagina_redirige_al_login(api, datos, pagina):
    respuesta = api.get(pagina)
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/login")


def test_au02_sin_sesion_no_se_puede_modificar_nada(app, api, datos):
    respuesta = api.post(f"/clientes/{datos['id_cliente']}/eliminar")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/login")
    # El cliente sigue existiendo: la ruta no llego a ejecutarse.
    with app.app_context():
        assert db.session.get(Cliente, datos["id_cliente"]) is not None


def test_au03_login_y_estaticos_se_abren_sin_sesion(api, datos):
    respuesta = api.get("/login")
    assert respuesta.status_code == 200
    assert "Iniciar sesión" in respuesta.get_data(as_text=True)
    assert api.get("/static/css/arkhe.css").status_code == 200


# ---------------------------------------------------------------------
# Inicio de sesion
# ---------------------------------------------------------------------
def test_au04_login_correcto_abre_la_sesion(api, datos):
    respuesta = entrar(api)
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/"

    inicio = api.get("/")
    assert inicio.status_code == 200
    pagina = inicio.get_data(as_text=True)
    assert "Luis Mora" in pagina          # usuario conectado en el encabezado
    assert "Cerrar sesión" in pagina


def test_au05_el_correo_no_distingue_mayusculas(api, datos):
    assert entrar(api, correo="  LUIS@Ejemplo.com ").status_code == 302
    assert tiene_sesion(api)


def test_au06_contrasena_incorrecta_no_entra(api, datos):
    respuesta = entrar(api, contrasena="ClaveEquivocada")
    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in respuesta.get_data(as_text=True)
    assert not tiene_sesion(api)


def test_au07_mismo_mensaje_si_el_correo_no_existe(api, datos):
    """No se revela si un correo esta registrado o no."""
    inexistente = entrar(api, correo="nadie@ejemplo.com").get_data(as_text=True)
    assert "Correo o contraseña incorrectos." in inexistente
    assert not tiene_sesion(api)


def test_au08_usuario_inactivo_no_puede_entrar(app, api, datos):
    cambiar_estado(app, datos["id_usuario"], "inactivo")
    respuesta = entrar(api)
    assert respuesta.status_code == 200
    assert "inactiva" in respuesta.get_data(as_text=True)
    assert not tiene_sesion(api)
    assert api.get("/").status_code == 302


def test_au09_la_cookie_no_lleva_contrasena_ni_rol(api, datos):
    entrar(api)
    with api.session_transaction() as sesion:
        assert set(sesion.keys()) <= {"id_usuario", "_permanent"}


# ---------------------------------------------------------------------
# Cierre y vigencia de la sesion
# ---------------------------------------------------------------------
def test_au10_logout_cierra_la_sesion(api, datos):
    entrar(api)
    respuesta = api.post("/logout")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/login"
    assert not tiene_sesion(api)
    assert api.get("/clientes/").status_code == 302


def test_au11_logout_solo_acepta_post(api, datos):
    entrar(api)
    assert api.get("/logout").status_code == 405
    assert tiene_sesion(api)


def test_au12_desactivar_al_usuario_le_cierra_la_sesion_abierta(app, api, datos):
    entrar(api)
    assert api.get("/").status_code == 200
    cambiar_estado(app, datos["id_usuario"], "inactivo")
    assert api.get("/").status_code == 302
    assert not tiene_sesion(api)


# ---------------------------------------------------------------------
# Redireccion despues del login
# ---------------------------------------------------------------------
def test_au13_despues_del_login_vuelve_a_la_pagina_pedida(api, datos):
    pedido = api.get("/pagos/?venta=3")
    assert pedido.headers["Location"] == "/login?next=/pagos/?venta%3D3"
    assert entrar(api, next="/pagos/?venta=3").headers["Location"] == "/pagos/?venta=3"


@pytest.mark.parametrize("destino", ["https://sitio-malicioso.com", "//sitio-malicioso.com",
                                     "/\\sitio-malicioso.com", "javascript:alert(1)"])
def test_au14_next_externo_se_ignora(api, datos, destino):
    assert entrar(api, next=destino).headers["Location"] == "/"


# ---------------------------------------------------------------------
# Decorador y regla de contrasena
# ---------------------------------------------------------------------
def test_au15_decorador_login_requerido(app, api, datos, monkeypatch):
    """Se prueba el decorador solo, sobre una ruta de prueba que la
    proteccion global deja pasar."""
    @app.route("/_prueba")
    @login_requerido
    def _prueba():
        return "contenido protegido"

    monkeypatch.setattr(seguridad, "ENDPOINTS_PUBLICOS",
                        seguridad.ENDPOINTS_PUBLICOS | {"_prueba"})

    sin_sesion = api.get("/_prueba")
    assert sin_sesion.status_code == 302
    assert sin_sesion.headers["Location"] == "/login?next=/_prueba"

    entrar(api)
    assert api.get("/_prueba").get_data(as_text=True) == "contenido protegido"


@pytest.mark.parametrize("valor, esperado", [
    ("Clave con espacio", True),     # espacios en medio: permitidos
    (" ClaveSegura1", False),        # espacio al inicio
    ("ClaveSegura1 ", False),        # espacio al final
])
def test_au16_contrasena_sin_espacios_en_los_extremos(valor, esperado):
    assert es_contrasena_valida(valor) == esperado
