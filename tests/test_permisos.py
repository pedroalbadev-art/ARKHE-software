"""
tests/test_permisos.py
----------------------
Pruebas de roles y proteccion de rutas (prioridad 2 del CLAUDE.md),
segun la matriz aprobada (utils/seguridad.py, PERMISOS):

  Administrador  todo.
  Vendedor       crea y edita clientes, ventas y pagos; solo consulta
                 proyectos y apartamentos; no entra a usuarios; NO
                 elimina en ningun modulo.
  Gerente        consulta todo y puede activar/desactivar cuentas de
                 Vendedor (no de Administrador ni de otro Gerente);
                 no crea, edita ni elimina nada.

  PE-01..PE-02  Ninguna ruta sin permiso declarado; matriz
  PE-03..PE-06  API: 401 sin sesion, login, 403 sin permiso
  PE-07..PE-10  Pantallas por rol
  PE-11..PE-15  Proteccion de cuentas (propia cuenta, ultimo Administrador)
"""

import pytest

from models import db
from models.usuario import Usuario
from tests.conftest import CLAVE, CORREOS, entrar_como
from utils.seguridad import ENDPOINTS_PUBLICOS, PERMISOS, puede

ADMIN, VENDEDOR, GERENTE = "Administrador", "Vendedor", "Gerente"
RECURSOS = ("clientes", "usuarios", "proyectos", "apartamentos", "ventas", "pagos")


class _Rol:
    """Usuario minimo para probar puede() sin base de datos."""
    def __init__(self, rol):
        self.rol = rol


def estado_de(app, id_usuario):
    with app.app_context():
        return db.session.get(Usuario, id_usuario).estado


# ---------------------------------------------------------------------
# Matriz
# ---------------------------------------------------------------------
def test_pe01_todas_las_rutas_declaran_su_permiso(app):
    """Si alguien agrega una ruta y olvida @rol_requerido, esta prueba
    falla: ninguna ruta puede quedar abierta a cualquier rol por olvido."""
    sin_permiso = []
    for regla in app.url_map.iter_rules():
        if regla.endpoint in ENDPOINTS_PUBLICOS or regla.endpoint == "auth.logout":
            continue
        permiso = getattr(app.view_functions[regla.endpoint], "permiso", None)
        if permiso is None:
            sin_permiso.append(regla.endpoint)
        else:
            modulo, accion = permiso
            assert accion in PERMISOS[modulo], f"{regla.endpoint}: permiso inexistente {permiso}"
    assert sin_permiso == []


@pytest.mark.parametrize("rol, modulo, accion, esperado", [
    (ADMIN, "usuarios", "eliminar", True),
    (ADMIN, "ventas", "eliminar", True),
    (VENDEDOR, "clientes", "editar", True),
    (VENDEDOR, "ventas", "editar", True),
    (VENDEDOR, "pagos", "editar", True),
    (VENDEDOR, "clientes", "eliminar", False),   # eliminar: solo el Administrador
    (ADMIN, "clientes", "eliminar", True),
    (VENDEDOR, "ventas", "eliminar", False),     # solo el Administrador
    (VENDEDOR, "pagos", "eliminar", False),      # solo el Administrador
    (VENDEDOR, "proyectos", "editar", False),
    (VENDEDOR, "apartamentos", "editar", False),
    (VENDEDOR, "usuarios", "ver", False),
    (GERENTE, "ventas", "ver", True),
    (GERENTE, "usuarios", "ver", True),
    (GERENTE, "usuarios", "estado", True),       # activar / desactivar
    (GERENTE, "usuarios", "editar", False),
    (GERENTE, "usuarios", "eliminar", False),
    (GERENTE, "clientes", "editar", False),
    (GERENTE, "pagos", "editar", False),
    (ADMIN, "modulo-inexistente", "ver", False),
    (ADMIN, "ventas", "accion-inexistente", False),
])
def test_pe02_matriz_de_permisos(rol, modulo, accion, esperado):
    assert puede(_Rol(rol), modulo, accion) is esperado
    assert puede(None, modulo, accion) is False


# ---------------------------------------------------------------------
# API: 401 y 403
# ---------------------------------------------------------------------
def test_pe03_api_sin_sesion_responde_401_en_json(api, datos):
    rutas = ["/api", "/api/resumen"] + [f"/api/{r}" for r in RECURSOS]
    for ruta in rutas:
        respuesta = api.get(ruta)
        assert respuesta.status_code == 401, ruta
        assert "error" in respuesta.get_json()
    assert api.post("/api/clientes", json={}).status_code == 401
    assert api.delete(f"/api/clientes/{datos['id_cliente']}").status_code == 401
    # Ya no se puede crear un Administrador sin haber iniciado sesion.
    assert api.post("/api/usuarios", json={"nombre": "Eva", "apellido": "Diaz",
                                           "correo": "eva@ejemplo.com", "contrasena": CLAVE,
                                           "rol": "Administrador"}).status_code == 401


def test_pe04_api_login(api, datos):
    mala = api.post("/api/login", json={"correo": CORREOS[ADMIN], "contrasena": "incorrecta"})
    assert mala.status_code == 401
    assert api.get("/api/clientes").status_code == 401

    assert api.post("/api/login", data="no es json").status_code == 400

    buena = api.post("/api/login", json={"correo": CORREOS[ADMIN], "contrasena": CLAVE})
    assert buena.status_code == 200
    cuerpo = buena.get_json()
    assert cuerpo["usuario"]["rol"] == ADMIN
    assert "contrasena" not in cuerpo["usuario"]
    assert api.get("/api/clientes").status_code == 200


def test_pe05_api_usuario_inactivo_no_inicia_sesion(app, api, datos):
    with app.app_context():
        db.session.get(Usuario, datos["id_vendedor"]).estado = "inactivo"
        db.session.commit()
    respuesta = api.post("/api/login", json={"correo": CORREOS[VENDEDOR], "contrasena": CLAVE})
    assert respuesta.status_code == 401


CLIENTE_NUEVO = {"nombre": "Eva", "apellido": "Diaz", "documento": "55667788",
                 "correo": "eva@ejemplo.com", "telefono": "3009998877"}


@pytest.mark.parametrize("rol, metodo, ruta, permitido", [
    # Consultar: todos (usuarios: no el Vendedor).
    (VENDEDOR, "get", "/api/proyectos", True),
    (GERENTE, "get", "/api/ventas", True),
    (GERENTE, "get", "/api/usuarios", True),
    (VENDEDOR, "get", "/api/usuarios", False),
    (VENDEDOR, "get", "/api/resumen", True),
    # Crear / editar.
    (VENDEDOR, "post", "/api/clientes", True),
    (GERENTE, "post", "/api/clientes", False),
    (VENDEDOR, "post", "/api/proyectos", False),
    (VENDEDOR, "post", "/api/apartamentos", False),
    (VENDEDOR, "post", "/api/usuarios", False),
    (GERENTE, "post", "/api/usuarios", False),
    (GERENTE, "post", "/api/ventas", False),
    (GERENTE, "post", "/api/pagos", False),
    # Eliminar, en cualquier modulo: solo el Administrador.
    (VENDEDOR, "delete", "/api/clientes/1", False),
    (VENDEDOR, "delete", "/api/ventas/1", False),
    (VENDEDOR, "delete", "/api/pagos/1", False),
    (GERENTE, "delete", "/api/clientes/1", False),
    (GERENTE, "delete", "/api/usuarios/1", False),
])
def test_pe06_api_403_segun_el_rol(api, datos, rol, metodo, ruta, permitido):
    entrar_como(api, rol)
    cuerpo = CLIENTE_NUEVO if metodo == "post" else None
    respuesta = getattr(api, metodo)(ruta, json=cuerpo)
    if permitido:
        assert respuesta.status_code in (200, 201), respuesta.get_json()
    else:
        assert respuesta.status_code == 403
        assert "error" in respuesta.get_json()


# ---------------------------------------------------------------------
# Pantallas por rol
# ---------------------------------------------------------------------
LISTADOS = ["/", "/clientes/", "/proyectos/", "/apartamentos/", "/ventas/", "/pagos/"]


@pytest.mark.parametrize("rol", [ADMIN, VENDEDOR, GERENTE])
def test_pe07_todos_los_roles_consultan_los_listados(api, datos, rol):
    entrar_como(api, rol)
    for pagina in LISTADOS:
        assert api.get(pagina).status_code == 200, pagina


@pytest.mark.parametrize("rol, metodo, ruta, permitido", [
    (ADMIN, "get", "/usuarios/", True),
    (GERENTE, "get", "/usuarios/", True),
    (VENDEDOR, "get", "/usuarios/", False),
    (VENDEDOR, "get", "/ventas/nueva", True),
    (VENDEDOR, "get", "/pagos/nuevo", True),
    (VENDEDOR, "get", "/proyectos/nuevo", False),
    (VENDEDOR, "get", "/apartamentos/nuevo", False),
    (GERENTE, "get", "/ventas/nueva", False),
    (GERENTE, "get", "/pagos/nuevo", False),
    (GERENTE, "get", "/clientes/1/editar", False),
    (GERENTE, "get", "/usuarios/1/editar", False),
    (GERENTE, "post", "/usuarios/nuevo", False),
    (GERENTE, "post", "/usuarios/1/eliminar", False),
    (GERENTE, "post", "/clientes/nuevo", False),
    (VENDEDOR, "post", "/clientes/1/eliminar", False),
    (VENDEDOR, "post", "/ventas/1/eliminar", False),
    (VENDEDOR, "post", "/pagos/1/eliminar", False),
    (VENDEDOR, "post", "/proyectos/1/eliminar", False),
    (VENDEDOR, "post", "/usuarios/1/estado", False),
])
def test_pe08_pantallas_403_segun_el_rol(api, datos, rol, metodo, ruta, permitido):
    entrar_como(api, rol)
    respuesta = getattr(api, metodo)(ruta)
    if permitido:
        assert respuesta.status_code == 200
    else:
        assert respuesta.status_code == 403
        assert "no tiene permiso" in respuesta.get_data(as_text=True)


def test_pe09_el_menu_y_los_botones_dependen_del_rol(api, datos):
    entrar_como(api, VENDEDOR)
    assert 'href="/usuarios/"' not in api.get("/").get_data(as_text=True)
    clientes = api.get("/clientes/").get_data(as_text=True)
    assert "+ Nuevo Cliente" in clientes and "Editar" in clientes
    # Se busca el boton de la fila (clase accion-eliminar): la palabra
    # "Eliminar" tambien esta en la ventana de confirmacion comun.
    assert "accion-eliminar" not in clientes          # el Vendedor no elimina
    assert "+ Nuevo Proyecto" not in api.get("/proyectos/").get_data(as_text=True)

    entrar_como(api, GERENTE)
    assert 'href="/usuarios/"' in api.get("/").get_data(as_text=True)
    clientes = api.get("/clientes/").get_data(as_text=True)
    assert "+ Nuevo Cliente" not in clientes and "accion-eliminar" not in clientes
    usuarios = api.get("/usuarios/").get_data(as_text=True)
    # Hay 3 usuarios, pero el boton solo aparece en la fila del Vendedor.
    assert usuarios.count(">Desactivar<") == 1
    assert "+ Nuevo Usuario" not in usuarios and "accion-editar" not in usuarios
    assert "accion-eliminar" not in usuarios

    entrar_como(api, ADMIN)
    usuarios = api.get("/usuarios/").get_data(as_text=True)
    assert "+ Nuevo Usuario" in usuarios and "accion-editar" in usuarios and "accion-eliminar" in usuarios


def test_pe10_el_gerente_activa_y_desactiva_usuarios(app, api, datos):
    entrar_como(api, GERENTE)
    id_vendedor = datos["id_vendedor"]

    assert api.post(f"/usuarios/{id_vendedor}/estado").status_code == 302
    assert estado_de(app, id_vendedor) == "inactivo"
    assert api.post(f"/usuarios/{id_vendedor}/estado").status_code == 302
    assert estado_de(app, id_vendedor) == "activo"

    # Tambien por la API, y solo el estado: el PUT completo le esta prohibido.
    respuesta = api.put(f"/api/usuarios/{id_vendedor}/estado", json={"estado": "inactivo"})
    assert respuesta.status_code == 200 and respuesta.get_json()["estado"] == "inactivo"
    assert api.put(f"/api/usuarios/{id_vendedor}/estado", json={"estado": "otro"}).status_code == 400
    assert api.put(f"/api/usuarios/{id_vendedor}", json={}).status_code == 403


# ---------------------------------------------------------------------
# Proteccion de cuentas
# ---------------------------------------------------------------------
def test_pe11_nadie_desactiva_ni_elimina_su_propia_cuenta(app, api, datos):
    # Se crea un segundo Administrador para que la regla del "ultimo
    # Administrador" no intervenga: lo que se prueba es la propia cuenta.
    entrar_como(api, ADMIN)
    otro = api.post("/api/usuarios", json={"nombre": "Otro", "apellido": "Admin",
                                           "correo": "otro@ejemplo.com", "contrasena": CLAVE,
                                           "rol": ADMIN}).get_json()
    api.post("/logout")
    api.post("/api/login", json={"correo": "otro@ejemplo.com", "contrasena": CLAVE})
    propio = otro["id_usuario"]

    desactivar = api.put(f"/api/usuarios/{propio}/estado", json={"estado": "inactivo"})
    assert desactivar.status_code == 409
    assert "propia cuenta" in desactivar.get_json()["error"]
    api.post(f"/usuarios/{propio}/estado")          # tambien por la pantalla
    assert estado_de(app, propio) == "activo"

    eliminar = api.delete(f"/api/usuarios/{propio}")
    assert eliminar.status_code == 409
    assert "propia cuenta" in eliminar.get_json()["error"]

    # El Gerente tampoco puede con la suya: su cuenta no es de Vendedor (403).
    entrar_como(api, GERENTE)
    assert api.post(f"/usuarios/{datos['id_gerente']}/estado").status_code == 403
    assert estado_de(app, datos["id_gerente"]) == "activo"


def test_pe12_el_gerente_no_cambia_el_estado_de_administradores_ni_gerentes(app, api, datos):
    entrar_como(api, ADMIN)
    otro_gerente = api.post("/api/usuarios", json={"nombre": "Otra", "apellido": "Gerente",
                                                   "correo": "gerente2@ejemplo.com",
                                                   "contrasena": CLAVE, "rol": GERENTE}).get_json()

    entrar_como(api, GERENTE)
    for id_cuenta in (datos["id_usuario"], otro_gerente["id_usuario"]):
        por_api = api.put(f"/api/usuarios/{id_cuenta}/estado", json={"estado": "inactivo"})
        assert por_api.status_code == 403
        assert api.post(f"/usuarios/{id_cuenta}/estado").status_code == 403
        assert estado_de(app, id_cuenta) == "activo"

    # El Administrador si puede con cualquiera (aqui, con un Gerente).
    entrar_como(api, ADMIN)
    assert api.post(f"/usuarios/{otro_gerente['id_usuario']}/estado").status_code == 302
    assert estado_de(app, otro_gerente["id_usuario"]) == "inactivo"


def test_pe13_el_ultimo_administrador_no_puede_quitarse_el_rol(app, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.put(f"/api/usuarios/{datos['id_usuario']}",
                        json={"nombre": "Luis", "apellido": "Mora", "correo": CORREOS[ADMIN],
                              "rol": VENDEDOR, "estado": "activo"})
    assert respuesta.status_code == 409
    with app.app_context():
        assert db.session.get(Usuario, datos["id_usuario"]).rol == ADMIN


def test_pe14_con_dos_administradores_si_se_puede_desactivar_a_uno(app, api, datos):
    entrar_como(api, ADMIN)
    nuevo = api.post("/api/usuarios", json={"nombre": "Otro", "apellido": "Admin",
                                            "correo": "otro@ejemplo.com", "contrasena": CLAVE,
                                            "rol": ADMIN}).get_json()
    respuesta = api.put(f"/api/usuarios/{nuevo['id_usuario']}/estado", json={"estado": "inactivo"})
    assert respuesta.status_code == 200
    # Un Administrador inactivo se puede eliminar: sigue quedando uno activo.
    assert api.delete(f"/api/usuarios/{nuevo['id_usuario']}").status_code == 200


def test_pe15_el_administrador_si_elimina_ventas_y_pagos(api, datos):
    entrar_como(api, VENDEDOR)
    venta = api.post("/api/ventas", json={"id_cliente": datos["id_cliente"],
                                          "id_apartamento": datos["id_apartamento"],
                                          "fecha_venta": datos["fecha_venta"],
                                          "valor_venta": 200000000}).get_json()
    pago = api.post("/api/pagos", json={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                                        "monto": 1000, "metodo_pago": "Efectivo"}).get_json()
    # El Vendedor los registro y puede editarlos, pero no eliminarlos.
    assert api.put(f"/api/pagos/{pago['id_pago']}",
                   json={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                         "monto": 2000, "metodo_pago": "Efectivo"}).status_code == 200
    assert api.delete(f"/api/pagos/{pago['id_pago']}").status_code == 403
    assert api.delete(f"/api/ventas/{venta['id_venta']}").status_code == 403

    entrar_como(api, ADMIN)
    assert api.delete(f"/api/pagos/{pago['id_pago']}").status_code == 200
    assert api.delete(f"/api/ventas/{venta['id_venta']}").status_code == 200
