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
    assert "El teléfono debe contener solo números" in modal
    assert pagina.count("El teléfono debe contener solo números") == 1
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


# =====================================================================
# T5b: textos, accesibilidad, CSP, proyectos y resumen unico
#
#   IN-13..IN-14  Tildes y titulos sin repetir la marca
#   IN-15..IN-16  Content Security Policy y cero JavaScript en linea
#   IN-17..IN-19  Accesibilidad y diseño para celular
#   IN-20..IN-22  Proyectos: propietario / promotor y conteo calculado
#   IN-23..IN-24  Dashboard y /api/resumen usan el mismo calculo
# =====================================================================
PANTALLAS = ["/"] + LISTADOS + ["/clientes/1/editar", "/usuarios/1/editar", "/proyectos/nuevo",
                                "/proyectos/1/editar", "/apartamentos/nuevo", "/apartamentos/1/editar",
                                "/ventas/nueva", "/pagos/nuevo"]

SIN_TILDE = ["Gestion ", "Telefono", "Numero ", "electronico", "Metodo", "Direccion",
             "Descripcion", "Ubicacion", "Ultimas", "Ultimos", "ultimos", "Minimo",
             ">Area", "Aun no", "automaticamente", " modulo ", "Sesion"]


def texto_visible(pagina):
    """Quita etiquetas y atributos: deja solo lo que la persona lee."""
    return re.sub(r"<[^>]+>", " ", pagina)


def test_in13_textos_con_tilde_en_todas_las_pantallas(api, datos):
    entrar_como(api, ADMIN)
    for ruta in PANTALLAS:
        pagina = html(api, ruta)
        visible = texto_visible(pagina) + " ".join(re.findall(r'(?:placeholder|title|aria-label)="([^"]*)"', pagina))
        for palabra in SIN_TILDE:
            assert palabra not in visible, f"{ruta}: falta la tilde en '{palabra.strip()}'"


def test_in14_la_marca_no_se_repite_en_titulos_ni_menu(api, datos):
    entrar_como(api, ADMIN)
    for ruta in PANTALLAS:
        pagina = html(api, ruta)
        titulo = re.search(r"<title>(.*?)</title>", pagina, flags=re.S).group(1)
        encabezado = re.search(r"<h1>(.*?)</h1>", pagina, flags=re.S).group(1)
        assert "ARKHE" not in titulo and "ARKHE" not in encabezado, ruta
        assert titulo.strip() and encabezado.strip()
        # Aparece una sola vez en toda la pagina: junto al logo del menu.
        assert texto_visible(pagina).count("ARKHE") == 1, ruta


def test_in15_cabecera_csp(api, datos):
    for respuesta in (api.get("/login"), api.get("/api/clientes")):
        csp = respuesta.headers["Content-Security-Policy"]
        directivas = dict(parte.strip().split(" ", 1) for parte in csp.split(";"))
        assert directivas["default-src"] == "'self'"
        assert directivas["script-src"] == "'self'"          # sin 'unsafe-inline' ni 'unsafe-eval'
        assert directivas["object-src"] == "'none'"
        assert directivas["frame-ancestors"] == "'none'"
        assert directivas["form-action"] == "'self'"


def test_in16_ninguna_pantalla_tiene_script_en_linea(api, datos):
    """Con script-src 'self' el navegador bloquearia cualquier <script>
    sin archivo: esta prueba avisa antes de que algo deje de funcionar."""
    entrar_como(api, ADMIN)
    for ruta in PANTALLAS + ["/no-existe"]:
        pagina = api.get(ruta).get_data(as_text=True)
        for etiqueta in re.findall(r"<script\b[^>]*>", pagina):
            assert 'src="/static/js/' in etiqueta, f"{ruta}: script en linea"
    api.post("/logout")
    assert "<script>" not in api.get("/login").get_data(as_text=True)


def test_in17_cada_campo_tiene_su_etiqueta(api, datos):
    """Accesibilidad: todo campo visible tiene <label for="..."> o aria-label."""
    entrar_como(api, ADMIN)
    for ruta in PANTALLAS:
        pagina = html(api, ruta)
        etiquetas = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', pagina))
        for campo in re.findall(r"<(?:input|select|textarea)\b[^>]*>", pagina):
            if 'type="hidden"' in campo:
                continue
            identificador = re.search(r'\bid="([^"]+)"', campo)
            con_etiqueta = identificador and identificador.group(1) in etiquetas
            assert con_etiqueta or "aria-label=" in campo, f"{ruta}: campo sin etiqueta -> {campo[:90]}"


def test_in18_menu_accesible_y_plegable(api, datos):
    entrar_como(api, ADMIN)
    pagina = html(api, "/ventas/")
    assert 'href="#contenido"' in pagina and 'id="contenido"' in pagina        # saltar al contenido
    assert 'aria-label="Menú principal"' in pagina
    # Solo la opcion del modulo actual se marca como pagina actual.
    assert pagina.count('aria-current="page"') == 1
    assert re.search(r'href="/ventas/"[^>]*aria-current="page"', pagina)
    # Boton del menu para celular, enlazado con el menu que controla.
    boton = re.search(r"<button[^>]*data-alternar-menu[^>]*>", pagina).group(0)
    assert 'aria-controls="menuLateral"' in boton and 'aria-expanded="false"' in boton
    assert 'id="menuLateral"' in pagina and "data-cerrar-menu" in pagina


def test_in19_estilos_paleta_completa_y_vista_de_celular(api):
    css = api.get("/static/css/arkhe.css").get_data(as_text=True)
    for color in ("#3A2F20", "#6E5A3C", "#8A6F52", "#C9A876", "#F3ECDD", "#E4D6BA", "#4A3B26"):
        assert color in css, f"falta el color {color} de la paleta"
    assert "@media (max-width: 900px)" in css and ".menu-abierto .sidebar" in css
    assert "prefers-reduced-motion" in css
    # Los CSS antiguos que nadie cargaba ya no existen.
    assert api.get("/static/css/clientes.css").status_code == 404
    assert api.get("/static/css/usuarios.css").status_code == 404


def test_in20_proyecto_aclara_que_el_cliente_es_el_propietario(api, datos):
    entrar_como(api, ADMIN)
    formulario = html(api, "/proyectos/nuevo")
    assert "Cliente propietario / promotor *" in formulario
    assert "no un comprador" in formulario
    assert "<th>Propietario / promotor</th>" in html(api, "/proyectos/")


def _agregar_apartamentos(id_proyecto):
    from models.apartamento import Apartamento

    for numero, estado in (("102", "reservado"), ("103", "vendido"), ("104", "vendido")):
        db.session.add(Apartamento(id_proyecto=id_proyecto, numero_apartamento=numero,
                                   area_m2=50, habitaciones=2, banos=1, precio=1000, estado=estado))
    db.session.commit()


def test_in21_resumen_de_apartamentos_del_proyecto_es_calculado(app, datos):
    with app.app_context():
        proyecto = db.session.get(Proyecto, datos["id_proyecto"])
        assert proyecto.resumen_apartamentos == {"total": 1, "disponible": 1, "reservado": 0, "vendido": 0}

        _agregar_apartamentos(proyecto.id_proyecto)
        # Sin guardar nada extra: el conteo cambia solo porque cambiaron los apartamentos.
        assert proyecto.resumen_apartamentos == {"total": 4, "disponible": 1, "reservado": 1, "vendido": 2}
        # No es una columna de la tabla.
        assert "resumen_apartamentos" not in Proyecto.__table__.columns


def test_in22_listado_de_proyectos_muestra_el_conteo_por_estado(app, api, datos):
    with app.app_context():
        _agregar_apartamentos(datos["id_proyecto"])
    entrar_como(api, GERENTE)
    visible = " ".join(texto_visible(html(api, "/proyectos/")).split())
    assert "4 en total" in visible
    assert "1 disponible 1 reservado 2 vendidos" in visible


CLAVES_RESUMEN = ["clientes", "usuarios", "proyectos", "apartamentos", "ventas",
                  "valor_vendido", "recaudado", "saldo_por_cobrar"]


def _venta_con_abono(api, datos):
    venta = api.post("/api/ventas", json={"id_cliente": datos["id_cliente"],
                                          "id_apartamento": datos["id_apartamento"],
                                          "fecha_venta": datos["fecha_venta"],
                                          "valor_venta": 200000000}).get_json()
    api.post("/api/pagos", json={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                                 "monto": 50000000, "metodo_pago": "Efectivo"})


def test_in23_api_resumen_conserva_su_contrato_y_usa_el_calculo_comun(app, api, datos):
    from utils.resumen import calcular_resumen

    entrar_como(api, ADMIN)
    _venta_con_abono(api, datos)

    cuerpo = api.get("/api/resumen").get_json()
    assert list(cuerpo.keys()) == CLAVES_RESUMEN                     # mismas claves, mismo orden
    assert cuerpo["apartamentos"] == {"disponible": 0, "reservado": 0, "vendido": 1}
    assert cuerpo["ventas"] == {"pendiente": 0, "en-pago": 1, "pagada": 0}
    assert (cuerpo["valor_vendido"], cuerpo["recaudado"], cuerpo["saldo_por_cobrar"]) == (200000000, 50000000, 150000000)
    assert (cuerpo["clientes"], cuerpo["usuarios"], cuerpo["proyectos"]) == (1, 3, 1)

    with app.app_context():
        cifras = calcular_resumen()
    assert {clave: float(valor) if clave in CLAVES_RESUMEN[5:] else valor
            for clave, valor in cifras.items()} == cuerpo


def test_in24_el_dashboard_muestra_las_mismas_cifras_que_la_api(api, datos):
    entrar_como(api, ADMIN)
    _venta_con_abono(api, datos)
    visible = " ".join(texto_visible(html(api, "/")).split())
    assert "$200.000.000" in visible          # valor vendido
    assert "$50.000.000" in visible           # recaudado
    assert "$150.000.000" in visible          # saldo por cobrar
    assert "25% del valor vendido" in visible


# ---------------------------------------------------------------------
# IN-25..IN-27  Tildes en mensajes de validacion y metodos de pago
# ---------------------------------------------------------------------
def test_in25_los_mensajes_de_validacion_llevan_tilde(api, datos):
    """Los mismos mensajes salen por la pantalla y por la API."""
    entrar_como(api, ADMIN)
    errores = api.post("/api/clientes", json={"nombre": "Eva", "apellido": "Diaz", "documento": "abc",
                                              "correo": "sin-arroba", "telefono": "12"}).get_json()["errores"]
    assert errores == [
        "El documento debe contener solo números (6 a 15 dígitos).",
        "El correo electrónico no tiene un formato válido.",
        "El teléfono debe contener solo números (7 a 15 dígitos).",
    ]
    apartamento = api.post("/api/apartamentos", json={}).get_json()["errores"]
    assert "El número de apartamento es obligatorio." in apartamento
    assert "El área debe ser un número mayor que 0 y hasta 9999.99 m²." in apartamento
    assert "Los baños deben ser un número entero entre 1 y 10." in apartamento


@pytest.mark.parametrize("guardado, mostrado", [
    ("Tarjeta de credito", "Tarjeta de crédito"),
    ("Tarjeta debito", "Tarjeta débito"),
    ("Credito hipotecario", "Crédito hipotecario"),
    ("Efectivo", "Efectivo"),                 # sin traduccion: se muestra igual
    ("Otro metodo", "Otro metodo"),           # desconocido: tampoco falla
])
def test_in26_etiqueta_de_metodo_de_pago(guardado, mostrado):
    from utils.formato import etiqueta_metodo

    assert etiqueta_metodo(guardado) == mostrado


def test_in27_el_metodo_se_muestra_con_tilde_pero_se_guarda_igual(app, api, datos):
    from models.pago import METODOS_PAGO, Pago

    entrar_como(api, ADMIN)
    venta = api.post("/api/ventas", json={"id_cliente": datos["id_cliente"],
                                          "id_apartamento": datos["id_apartamento"],
                                          "fecha_venta": datos["fecha_venta"],
                                          "valor_venta": 200000000}).get_json()
    # El formulario envia el valor guardado (sin tilde), no la etiqueta.
    respuesta = api.post("/pagos/crear", data={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                                               "monto": "1000", "metodo_pago": "Tarjeta de credito"})
    assert respuesta.status_code == 302

    # La base y la API conservan el valor original.
    assert "Tarjeta de credito" in METODOS_PAGO
    with app.app_context():
        assert Pago.query.one().metodo_pago == "Tarjeta de credito"
    assert api.get("/api/pagos").get_json()[0]["metodo_pago"] == "Tarjeta de credito"
    # ...y la API sigue rechazando la version con tilde: su contrato no cambio.
    con_tilde = api.post("/api/pagos", json={"id_venta": venta["id_venta"], "fecha_pago": datos["fecha_pago"],
                                             "monto": 1000, "metodo_pago": "Tarjeta de crédito"})
    assert con_tilde.status_code == 400

    # Las pantallas lo muestran con tilde; el value del filtro y del formulario sigue igual.
    lista = html(api, "/pagos/")
    assert "<td>Tarjeta de crédito</td>" in lista
    assert '<option value="Tarjeta de credito">Tarjeta de crédito</option>' in lista
    assert 'data-filtro-metodo="Tarjeta de credito"' in lista
    formulario = html(api, "/pagos/nuevo")
    assert re.search(r'<option value="Tarjeta de credito"\s*>Tarjeta de crédito</option>', formulario)
    assert "Tarjeta de crédito" in html(api, "/")          # ultimos pagos del dashboard
