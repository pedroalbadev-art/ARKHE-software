"""
tests/test_interfaz.py
----------------------
Pruebas de la interfaz (prioridad 4 del CLAUDE.md) que se pueden
comprobar leyendo el HTML que entrega el servidor. Lo visual (colores,
animacion del modal, foco) se revisa a mano en el navegador.

  IN-01..IN-03  Confirmacion antes de eliminar sin JavaScript en linea (XSS)
  IN-04..IN-05  Mensajes flash con icono y cierre
  IN-06..IN-08  Estados vacios con llamada a la accion
  IN-09..IN-12  Los modales conservan lo escrito cuando hay un error
"""

import re

import pytest

from models import db
from models.cliente import Cliente
from models.proyecto import Proyecto
from models.usuario import Usuario
from tests.conftest import CLAVE, entrar_como

ADMIN, VENDEDOR, GERENTE = "Administrador", "Vendedor", "Gerente"
LISTADOS = ["/clientes/", "/usuarios/", "/proyectos/", "/apartamentos/", "/ventas/", "/pagos/"]
NOMBRE_MALICIOSO = "x'); alert(1); ('<script>alert(2)</script>"


def html(api, ruta, **kwargs):
    respuesta = api.get(ruta, **kwargs)
    assert respuesta.status_code == 200, ruta
    return respuesta.get_data(as_text=True)


# ---------------------------------------------------------------------
# Confirmacion antes de eliminar (corrige el XSS del hallazgo A2)
# ---------------------------------------------------------------------
def test_in01_ninguna_pantalla_lleva_javascript_en_linea(api, datos):
    """Sin onclick/onsubmit/confirm() en el HTML, ningun dato escrito por
    un usuario puede terminar dentro de codigo JavaScript."""
    entrar_como(api, ADMIN)
    api.post("/api/ventas", json={"id_cliente": datos["id_cliente"],
                                  "id_apartamento": datos["id_apartamento"],
                                  "fecha_venta": datos["fecha_venta"], "valor_venta": 1000})
    paginas = ["/"] + LISTADOS + ["/clientes/1/editar", "/usuarios/1/editar", "/proyectos/nuevo",
                                  "/apartamentos/nuevo", "/ventas/nueva", "/pagos/nuevo"]
    for ruta in paginas:
        pagina = html(api, ruta)
        assert not re.search(r"\son[a-z]+\s*=", pagina), f"{ruta}: atributo on...= en linea"
        assert "confirm(" not in pagina, ruta
        assert "javascript:" not in pagina, ruta


def test_in02_un_nombre_malicioso_queda_como_dato_y_no_como_codigo(app, api, datos):
    with app.app_context():
        db.session.get(Proyecto, datos["id_proyecto"]).nombre_proyecto = NOMBRE_MALICIOSO
        db.session.commit()
    entrar_como(api, ADMIN)
    pagina = html(api, "/proyectos/")

    # El nombre va en un atributo de datos, con las comillas y los < > escapados.
    assert 'data-confirmar="¿Eliminar el proyecto x&#39;); alert(1); (&#39;&lt;script&gt;' in pagina
    # Nunca aparece como etiqueta real ni dentro de un manejador de eventos.
    assert "<script>alert(2)</script>" not in pagina
    assert "onsubmit" not in pagina


def test_in03_cada_formulario_de_eliminar_pide_confirmacion(api, datos):
    entrar_como(api, ADMIN)
    venta = api.post("/api/ventas", json={"id_cliente": datos["id_cliente"],
                                          "id_apartamento": datos["id_apartamento"],
                                          "fecha_venta": datos["fecha_venta"],
                                          "valor_venta": 1000}).get_json()
    api.post("/api/pagos", json={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                                 "monto": 100, "metodo_pago": "Efectivo"})
    api.post("/api/clientes", json={"nombre": "Eva", "apellido": "Diaz", "documento": "55667788",
                                    "correo": "eva@ejemplo.com", "telefono": "3009998877"})
    encontrados = 0
    for ruta in LISTADOS:
        pagina = html(api, ruta)
        for formulario in re.findall(r"<form\b[^>]*>", pagina):
            if "/eliminar" in formulario:
                encontrados += 1
                assert "data-confirmar=" in formulario, f"{ruta}: eliminar sin confirmacion"
        # La ventana de confirmacion y el script estan en todas las pantallas.
        assert 'id="modalConfirmar"' in pagina and "js/arkhe.js" in pagina
    assert encontrados >= 5      # clientes, usuarios, proyectos, apartamentos y pagos

    # Desactivar un usuario tambien se confirma, con su propio boton.
    assert 'data-confirmar-boton="Desactivar"' in html(api, "/usuarios/")


def test_in03b_el_script_usa_textcontent_y_no_innerhtml(api):
    script = api.get("/static/js/arkhe.js").get_data(as_text=True)
    assert "textContent" in script
    assert "innerHTML" not in script and "eval(" not in script


# ---------------------------------------------------------------------
# Mensajes flash
# ---------------------------------------------------------------------
def test_in04_mensaje_flash_con_icono_y_boton_de_cierre(api, datos):
    entrar_como(api, ADMIN)
    pagina = api.post("/clientes/nuevo", follow_redirects=True, data={
        "nombre": "Eva", "apellido": "Diaz", "documento": "55667788",
        "correo": "eva@ejemplo.com", "telefono": "3009998877"}).get_data(as_text=True)
    alerta = re.search(r'<div class="alert alert-exito".*?</div>', pagina, flags=re.S).group(0)
    assert "creado correctamente" in alerta
    assert 'class="alert-icono"' in alerta
    assert "data-cerrar-alerta" in alerta and 'aria-label="Cerrar mensaje"' in alerta


def test_in05_el_login_tambien_muestra_los_mensajes_con_estilo(api, datos):
    pagina = api.post("/login", data={"correo": "nadie@ejemplo.com", "contrasena": "x"}).get_data(as_text=True)
    assert 'class="alert alert-error" role="alert"' in pagina
    assert 'class="alert-icono"' in pagina


# ---------------------------------------------------------------------
# Estados vacios
# ---------------------------------------------------------------------
@pytest.mark.parametrize("ruta, titulo, boton", [
    ("/ventas/", "Aún no hay ventas registradas", "+ Nueva Venta"),
    ("/pagos/", "Aún no hay pagos registrados", "+ Registrar Pago"),
])
def test_in06_estado_vacio_con_llamada_a_la_accion(api, datos, ruta, titulo, boton):
    entrar_como(api, VENDEDOR)
    pagina = html(api, ruta)
    vacio = re.search(r'<td colspan="\d+" class="vacio">.*?</td>', pagina, flags=re.S).group(0)
    assert titulo in vacio and boton in vacio and 'class="vacio-icono"' in vacio


def test_in07_estado_vacio_sin_boton_si_el_rol_no_puede_crear(api, datos):
    entrar_como(api, GERENTE)
    for ruta in ("/ventas/", "/pagos/"):
        vacio = re.search(r'<td colspan="\d+" class="vacio">.*?</td>', html(api, ruta), flags=re.S).group(0)
        assert "Aún no hay" in vacio
        assert "btn-primary" not in vacio
    assert "+ Nueva Venta" not in html(api, "/")       # tampoco en el dashboard


def test_in08_estado_vacio_de_clientes_abre_el_modal(app, api):
    """Sin clientes, el boton del estado vacio abre el modal de creacion."""
    with app.app_context():
        admin = Usuario(nombre="Luis", apellido="Mora", correo="solo@ejemplo.com",
                        rol=ADMIN, estado="activo")
        admin.establecer_contrasena(CLAVE)
        db.session.add(admin)
        db.session.commit()
    api.post("/api/login", json={"correo": "solo@ejemplo.com", "contrasena": CLAVE})
    vacio = re.search(r'<td colspan="6" class="vacio">.*?</td>', html(api, "/clientes/"), flags=re.S).group(0)
    assert 'data-abrir-modal="modalNuevo"' in vacio and "+ Nuevo Cliente" in vacio


# ---------------------------------------------------------------------
# Los modales conservan lo escrito
# ---------------------------------------------------------------------
def test_in09_cliente_invalido_reabre_el_modal_con_lo_escrito(app, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.post("/clientes/nuevo", data={
        "nombre": "Eva Maria", "apellido": "Diaz", "documento": "55667788",
        "correo": "eva@ejemplo.com", "telefono": "12"})          # telefono invalido
    assert respuesta.status_code == 200
    pagina = respuesta.get_data(as_text=True)

    assert 'class="modal-overlay abierto" id="modalNuevo"' in pagina
    for valor in ("Eva Maria", "Diaz", "55667788", "eva@ejemplo.com"):
        assert f'value="{valor}"' in pagina
    # El error se muestra DENTRO del modal (fuera quedaria tapado), una sola vez.
    modal = pagina[pagina.index('id="modalNuevo"'):]
    assert "El telefono debe contener solo numeros" in modal
    assert pagina.count("El telefono debe contener solo numeros") == 1
    with app.app_context():
        assert Cliente.query.filter_by(documento="55667788").count() == 0


def test_in10_cliente_duplicado_reabre_el_modal_con_lo_escrito(api, datos):
    entrar_como(api, ADMIN)
    pagina = api.post("/clientes/nuevo", data={
        "nombre": "Otra", "apellido": "Persona", "documento": "10203040",     # ya existe
        "correo": "otra@ejemplo.com", "telefono": "3001112233"}).get_data(as_text=True)
    assert 'class="modal-overlay abierto"' in pagina
    assert "Ya existe un cliente" in pagina and 'value="otra@ejemplo.com"' in pagina


def test_in11_usuario_invalido_reabre_el_modal_sin_devolver_la_contrasena(api, datos):
    entrar_como(api, ADMIN)
    pagina = api.post("/usuarios/nuevo", data={
        "nombre": "Eva", "apellido": "Diaz", "correo": "sin-arroba",
        "contrasena": "SecretoLargo99", "rol": "Gerente"}).get_data(as_text=True)

    assert 'class="modal-overlay abierto" id="modalNuevo"' in pagina
    assert 'value="Eva"' in pagina and 'value="sin-arroba"' in pagina
    assert '<option value="Gerente" selected>' in pagina          # conserva el rol elegido
    assert "SecretoLargo99" not in pagina                          # la contrasena nunca vuelve


def test_in12_el_listado_normal_no_abre_el_modal(api, datos):
    entrar_como(api, ADMIN)
    for ruta in ("/clientes/", "/usuarios/"):
        pagina = html(api, ruta)
        assert 'class="modal-overlay" id="modalNuevo"' in pagina
        assert "modal-overlay abierto" not in pagina
