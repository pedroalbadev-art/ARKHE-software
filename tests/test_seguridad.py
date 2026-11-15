"""
tests/test_seguridad.py
-----------------------
Pruebas de la seguridad de formularios y del manejo de errores
(prioridad 3 del CLAUDE.md).

  SG-01..SG-05  Token CSRF en los formularios (la API queda exenta)
  SG-06         Los mensajes de error no muestran datos tecnicos
  SG-07..SG-08  Eliminaciones con dependencias desde las pantallas
  SG-09..SG-10  Longitudes maximas (validadas en Python, no en la base)
  SG-11..SG-13  Paginas de error 404 y 500, en HTML y en JSON
  SG-14..SG-15  Cabeceras de seguridad y configuracion
  SG-16..SG-18  La API solo acepta cuerpos JSON y no habilita CORS
"""

import json
import re

import pytest

from app import create_app
from config import Config
from models import db
from models.cliente import Cliente
from models.usuario import Usuario
from routes.clientes import _validar_datos_cliente
from routes.usuarios import _validar_datos_usuario
from tests.conftest import CLAVE, CORREOS, HASH_CLAVE, ConfigPruebasConCsrf, entrar_como

ADMIN = "Administrador"
CLIENTE = {"nombre": "Eva", "apellido": "Diaz", "documento": "55667788",
           "correo": "eva@ejemplo.com", "telefono": "3009998877"}


# ---------------------------------------------------------------------
# CSRF (estas pruebas usan una app con la proteccion ACTIVADA)
# ---------------------------------------------------------------------
@pytest.fixture
def web(datos_csrf):
    return datos_csrf.test_client()


@pytest.fixture
def datos_csrf():
    """App con CSRF activo y un Administrador para iniciar sesion."""
    aplicacion = create_app(ConfigPruebasConCsrf)
    with aplicacion.app_context():
        db.create_all()
        db.session.add(Usuario(nombre="Luis", apellido="Mora", correo=CORREOS[ADMIN],
                               contrasena=HASH_CLAVE, rol=ADMIN, estado="activo"))
        db.session.commit()
    yield aplicacion
    with aplicacion.app_context():
        db.session.remove()
        db.drop_all()


def token_de(web, pagina):
    """Lee el token oculto de un formulario, como haria el navegador."""
    html = web.get(pagina).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def entrar_con_token(web):
    token = token_de(web, "/login")
    return web.post("/login", data={"correo": CORREOS[ADMIN], "contrasena": CLAVE,
                                    "csrf_token": token})


def test_sg01_login_sin_token_se_rechaza(web):
    respuesta = web.post("/login", data={"correo": CORREOS[ADMIN], "contrasena": CLAVE})
    assert respuesta.status_code == 400
    assert "Formulario vencido" in respuesta.get_data(as_text=True)
    assert web.get("/").status_code == 302          # no se abrio sesion


def test_sg02_login_con_token_funciona(web):
    assert entrar_con_token(web).status_code == 302
    assert web.get("/").status_code == 200


def test_sg03_un_post_sin_token_no_modifica_nada(datos_csrf, web):
    entrar_con_token(web)

    sin_token = web.post("/clientes/nuevo", data=CLIENTE)
    assert sin_token.status_code == 400
    falso = web.post("/clientes/nuevo", data={**CLIENTE, "csrf_token": "inventado"})
    assert falso.status_code == 400
    with datos_csrf.app_context():
        assert Cliente.query.count() == 0

    con_token = web.post("/clientes/nuevo", data={**CLIENTE, "csrf_token": token_de(web, "/clientes/")})
    assert con_token.status_code == 302
    with datos_csrf.app_context():
        assert Cliente.query.count() == 1


def test_sg04_todos_los_formularios_post_llevan_token(datos_csrf, web):
    """Recorre las pantallas y comprueba que cada <form method="post">
    tenga su campo csrf_token. Protege contra olvidarlo en un formulario nuevo."""
    paginas = ["/login"]
    for pagina in paginas:
        _revisar_formularios(web, pagina)

    entrar_con_token(web)
    web.post("/clientes/nuevo", data={**CLIENTE, "csrf_token": token_de(web, "/clientes/")})
    for pagina in ["/", "/clientes/", "/clientes/1/editar", "/usuarios/", "/usuarios/1/editar",
                   "/proyectos/", "/proyectos/nuevo", "/apartamentos/", "/apartamentos/nuevo",
                   "/ventas/", "/ventas/nueva", "/pagos/", "/pagos/nuevo"]:
        _revisar_formularios(web, pagina)


def _revisar_formularios(web, pagina):
    respuesta = web.get(pagina)
    assert respuesta.status_code == 200, pagina
    html = respuesta.get_data(as_text=True)
    formularios = re.findall(r'<form\b[^>]*method="post"[^>]*>(.*?)</form>', html, flags=re.S | re.I)
    assert formularios, f"{pagina}: se esperaba al menos un formulario POST"
    for contenido in formularios:
        assert 'name="csrf_token"' in contenido, f"{pagina}: formulario sin token CSRF"


def test_sg05_la_api_queda_exenta_del_token(web):
    entrada = web.post("/api/login", json={"correo": CORREOS[ADMIN], "contrasena": CLAVE})
    assert entrada.status_code == 200
    assert web.post("/api/clientes", json=CLIENTE).status_code == 201


# ---------------------------------------------------------------------
# Mensajes de error sin datos sensibles
# ---------------------------------------------------------------------
def test_sg06_un_error_de_base_de_datos_no_se_muestra_al_usuario(api, datos, monkeypatch):
    entrar_como(api, ADMIN)

    def fallar():
        raise RuntimeError("SELECT contrasena FROM usuarios -- detalle interno")

    monkeypatch.setattr(db.session, "commit", fallar)
    respuesta = api.post("/proyectos/crear", data={
        "nombre_proyecto": "Torre Nueva", "direccion": "Calle 9", "ciudad": "Cali",
        "id_cliente": datos["id_cliente"], "id_usuario": datos["id_usuario"]})

    pagina = respuesta.get_data(as_text=True)
    assert "Error al crear proyecto. Intente de nuevo" in pagina
    assert "detalle interno" not in pagina and "SELECT" not in pagina


# ---------------------------------------------------------------------
# Eliminaciones con dependencias, desde las pantallas
# ---------------------------------------------------------------------
def test_sg07_eliminar_cliente_con_proyectos_muestra_mensaje(app, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.post(f"/clientes/{datos['id_cliente']}/eliminar", follow_redirects=True)
    assert respuesta.status_code == 200          # antes: error 500
    assert "No se puede eliminar: el cliente tiene proyectos o ventas" in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Cliente, datos["id_cliente"]) is not None


def test_sg08_eliminar_usuario_que_gestiona_proyectos_muestra_mensaje(app, api, datos):
    # Otro Administrador intenta eliminar al que gestiona el proyecto.
    entrar_como(api, ADMIN)
    api.post("/api/usuarios", json={"nombre": "Otro", "apellido": "Admin", "correo": "otro@ejemplo.com",
                                    "contrasena": CLAVE, "rol": ADMIN})
    api.post("/logout")
    api.post("/api/login", json={"correo": "otro@ejemplo.com", "contrasena": CLAVE})

    respuesta = api.post(f"/usuarios/{datos['id_usuario']}/eliminar", follow_redirects=True)
    assert respuesta.status_code == 200
    assert "el usuario gestiona proyectos" in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Usuario, datos["id_usuario"]) is not None


# ---------------------------------------------------------------------
# Longitudes maximas (regla en Python; no depende del motor de base)
# ---------------------------------------------------------------------
LARGO_CORREO = "a" * 141 + "@ejemplo.com"          # 153 caracteres


@pytest.mark.parametrize("campo, valor, valido", [
    ("nombre", "a" * 100, True),
    ("nombre", "a" * 101, False),
    ("apellido", "b" * 100, True),
    ("apellido", "b" * 101, False),
    ("correo", "a" * 138 + "@ejemplo.com", True),    # 150 exactos
    ("correo", LARGO_CORREO, False),
])
def test_sg09_longitud_maxima_en_clientes_y_usuarios(campo, valor, valido):
    cliente = {**CLIENTE, campo: valor}
    usuario = {"nombre": "Eva", "apellido": "Diaz", "correo": "eva@ejemplo.com",
               "rol": "Vendedor", "estado": "activo", campo: valor}
    errores_cliente = _validar_datos_cliente(cliente)
    errores_usuario = _validar_datos_usuario(usuario, requiere_contrasena=False)
    assert (errores_cliente == []) is valido
    assert (errores_usuario == []) is valido
    if not valido:
        assert "no puede exceder" in errores_cliente[0]


def test_sg10_la_api_responde_400_y_no_500_con_un_nombre_demasiado_largo(api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.post("/api/clientes", json={**CLIENTE, "nombre": "a" * 101})
    assert respuesta.status_code == 400
    assert respuesta.get_json()["errores"] == ["El nombre no puede exceder 100 caracteres."]


# ---------------------------------------------------------------------
# Paginas de error
# ---------------------------------------------------------------------
def test_sg11_404_con_pagina_propia_y_json_en_la_api(api, datos):
    assert api.get("/api/no-existe").status_code == 401      # sin sesion: 401 en JSON
    entrar_como(api, ADMIN)

    pagina = api.get("/no-existe")
    assert pagina.status_code == 404
    assert "Página no encontrada" in pagina.get_data(as_text=True)
    assert api.get("/clientes/999999/editar").status_code == 404

    json_api = api.get("/api/no-existe")
    assert json_api.status_code == 404
    assert "error" in json_api.get_json()


@pytest.fixture
def app_con_fallo(app):
    """Agrega dos rutas que fallan a proposito y desactiva la
    propagacion de excepciones, para que actue el manejador del 500
    igual que en el servidor real."""
    app.config["PROPAGATE_EXCEPTIONS"] = False

    def fallar():
        raise RuntimeError("detalle interno que no debe verse")

    app.add_url_rule("/_falla", "falla", fallar)
    app.add_url_rule("/api/_falla", "falla_api", fallar)
    return app


def test_sg12_500_en_pantalla_sin_detalles(app_con_fallo, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.get("/_falla")
    assert respuesta.status_code == 500
    pagina = respuesta.get_data(as_text=True)
    assert "Error inesperado" in pagina
    assert "detalle interno" not in pagina and "Traceback" not in pagina


def test_sg13_500_en_la_api_responde_json(app_con_fallo, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.get("/api/_falla")
    assert respuesta.status_code == 500
    assert respuesta.get_json() == {"error": "Error interno del servidor."}


# ---------------------------------------------------------------------
# Cabeceras y configuracion
# ---------------------------------------------------------------------
def test_sg14_cabeceras_de_seguridad(api, datos):
    for respuesta in (api.get("/login"), api.get("/api/clientes")):
        assert respuesta.headers["X-Frame-Options"] == "DENY"
        assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
        assert respuesta.headers["Referrer-Policy"] == "same-origin"


def test_sg15_secret_key_obligatoria_y_cookie_protegida(app):
    class SinClave(Config):
        SECRET_KEY = None

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(SinClave)

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert create_app(ConfigPruebasConCsrf).config["WTF_CSRF_ENABLED"] is True


# ---------------------------------------------------------------------
# La API solo acepta JSON y no habilita CORS
# ---------------------------------------------------------------------
# Por que importa: la API esta exenta del token CSRF (SG-05). Esa
# exencion es segura solo si un formulario HTML de otro sitio no puede
# hacerle peticiones validas. Un formulario unicamente sabe enviar tres
# tipos de cuerpo (los de abajo), nunca application/json; y sin CORS, el
# JavaScript de otro sitio tampoco puede enviar JSON con la cookie.
TIPOS_DE_FORMULARIO = ["text/plain", "application/x-www-form-urlencoded",
                       "multipart/form-data", None]


@pytest.mark.parametrize("tipo", TIPOS_DE_FORMULARIO)
def test_sg16_la_api_rechaza_cuerpos_que_no_declaran_json(api, datos, tipo):
    """Aunque el texto del cuerpo sea JSON valido, sin la cabecera
    Content-Type: application/json se responde 400 y no se guarda nada."""
    entrar_como(api, ADMIN)
    cuerpo = json.dumps(CLIENTE)

    respuesta = api.post("/api/clientes", data=cuerpo, content_type=tipo)
    assert respuesta.status_code == 400
    assert "application/json" in respuesta.get_json()["errores"][0]
    assert all(c["documento"] != CLIENTE["documento"] for c in api.get("/api/clientes").get_json())

    # Tambien al actualizar: el registro queda como estaba.
    ruta = f"/api/clientes/{datos['id_cliente']}"
    assert api.put(ruta, data=cuerpo, content_type=tipo).status_code == 400
    assert api.get(ruta).get_json()["nombre"] == "Ana"

    # Con la cabecera correcta, el mismo cuerpo si se acepta.
    assert api.post("/api/clientes", data=cuerpo,
                    content_type="application/json").status_code == 201


@pytest.mark.parametrize("tipo", TIPOS_DE_FORMULARIO)
def test_sg17_el_login_de_la_api_tambien_exige_json(api, datos, tipo):
    api.post("/logout")
    credenciales = json.dumps({"correo": CORREOS[ADMIN], "contrasena": CLAVE})
    assert api.post("/api/login", data=credenciales, content_type=tipo).status_code == 400
    assert api.get("/api/clientes").status_code == 401  # no se abrio sesion


def test_sg18_la_api_no_habilita_cors(api, datos):
    """Ninguna respuesta autoriza a otro origen: sin cabeceras
    Access-Control-*, el navegador impide que el JavaScript de otro
    sitio lea la API o le envie JSON."""
    entrar_como(api, ADMIN)
    origen = {"Origin": "https://otro-sitio.example"}
    consulta = api.get("/api/clientes", headers=origen)
    previa = api.options("/api/clientes", headers={
        **origen,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    for respuesta in (consulta, previa):
        cabeceras = [nombre.lower() for nombre, _ in respuesta.headers]
        assert not [c for c in cabeceras if c.startswith("access-control-")]
