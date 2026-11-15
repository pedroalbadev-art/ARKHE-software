"""
tests/test_reglas.py
--------------------
Pruebas de las reglas de negocio ya implementadas (las que el CLAUDE.md
pide no romper), ejercidas a traves de la API REST contra una base
temporal (ver tests/conftest.py). Sirven de red de seguridad: si un
cambio futuro rompe una regla, alguna de estas pruebas falla.

  RN-01..RN-04  Ventas: estado del apartamento
  RN-05..RN-09  Pagos: abonos y estado calculado de la venta
  RN-10..RN-14  Eliminaciones bloqueadas (409)
  RN-15..RN-17  Contrato de la API (404, 400, contrasena oculta)
  RN-18..RN-20  Ventas: cambio de apartamento al editar (API y pantalla)
  RN-21..RN-23  Apartamento vendido: aviso al pedir otro estado
"""

import html

import pytest
from sqlalchemy.exc import IntegrityError

from models import db
from models.proyecto import Proyecto
from routes.apartamentos import AVISO_ESTADO_VENDIDO

from tests.conftest import entrar_como

VALOR = 200000000


@pytest.fixture(autouse=True)
def _sesion_de_administrador(api, datos):
    """La API exige sesion: todas las pruebas de este archivo se
    ejecutan como Administrador (el rol que puede hacer todo), porque
    aqui se prueban las reglas de negocio, no los permisos."""
    entrar_como(api, "Administrador")


def crear_venta(api, datos, **cambios):
    cuerpo = {"id_cliente": datos["id_cliente"], "id_apartamento": datos["id_apartamento"],
              "fecha_venta": datos["fecha_venta"], "valor_venta": VALOR}
    cuerpo.update(cambios)
    return api.post("/api/ventas", json=cuerpo)


def crear_pago(api, datos, id_venta, monto, **cambios):
    cuerpo = {"id_venta": id_venta, "fecha_pago": datos["fecha_pago"],
              "monto": monto, "metodo_pago": "Transferencia"}
    cuerpo.update(cambios)
    return api.post("/api/pagos", json=cuerpo)


def estado_apartamento(api, datos):
    return api.get(f"/api/apartamentos/{datos['id_apartamento']}").get_json()["estado"]


def cuerpo_apartamento(datos, numero="101", **cambios):
    cuerpo = {"id_proyecto": datos["id_proyecto"], "numero_apartamento": numero,
              "area_m2": 60, "habitaciones": 3, "banos": 2, "precio": VALOR,
              "estado": "disponible"}
    cuerpo.update(cambios)
    return cuerpo


def crear_otro_apartamento(api, datos, estado="reservado"):
    """Segundo apartamento del mismo proyecto; devuelve su ID."""
    respuesta = api.post("/api/apartamentos", json=cuerpo_apartamento(datos, "102", estado=estado))
    assert respuesta.status_code == 201, respuesta.get_json()
    return respuesta.get_json()["id_apartamento"]


def estado_de(api, id_apartamento):
    return api.get(f"/api/apartamentos/{id_apartamento}").get_json()["estado"]


def cuerpo_venta(datos, id_apartamento):
    return {"id_cliente": datos["id_cliente"], "id_apartamento": id_apartamento,
            "fecha_venta": datos["fecha_venta"], "valor_venta": VALOR}


@pytest.fixture
def venta(api, datos):
    """Una venta ya registrada; devuelve su ID."""
    return crear_venta(api, datos).get_json()["id_venta"]


# ---------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------
class TestVentas:

    def test_rn01_registrar_venta_deja_el_apartamento_vendido(self, api, datos):
        respuesta = crear_venta(api, datos)
        assert respuesta.status_code == 201
        assert estado_apartamento(api, datos) == "vendido"

    def test_rn02_eliminar_venta_devuelve_el_apartamento_a_disponible(self, api, datos, venta):
        assert api.delete(f"/api/ventas/{venta}").status_code == 200
        assert estado_apartamento(api, datos) == "disponible"

    def test_rn03_un_apartamento_no_se_vende_dos_veces(self, api, datos, venta):
        respuesta = crear_venta(api, datos)
        assert respuesta.status_code == 400
        assert "errores" in respuesta.get_json()

    def test_rn04_la_fecha_de_venta_no_puede_ser_futura(self, api, datos):
        respuesta = crear_venta(api, datos, fecha_venta=datos["manana"])
        assert respuesta.status_code == 400
        assert estado_apartamento(api, datos) == "disponible"

    def test_rn18_cambiar_el_apartamento_de_una_venta_por_la_api(self, api, datos, venta):
        """El anterior vuelve a disponible y el nuevo (que estaba
        reservado) pasa a vendido."""
        nuevo = crear_otro_apartamento(api, datos, estado="reservado")
        respuesta = api.put(f"/api/ventas/{venta}", json=cuerpo_venta(datos, nuevo))
        assert respuesta.status_code == 200, respuesta.get_json()
        assert respuesta.get_json()["id_apartamento"] == nuevo
        assert estado_apartamento(api, datos) == "disponible"
        assert estado_de(api, nuevo) == "vendido"
        # El anterior quedo libre de verdad: ya no tiene venta asociada.
        anterior = api.get(f"/api/apartamentos/{datos['id_apartamento']}").get_json()
        assert anterior["id_venta"] is None

    def test_rn19_cambiar_el_apartamento_de_una_venta_por_la_pantalla(self, api, datos, venta):
        nuevo = crear_otro_apartamento(api, datos, estado="disponible")
        respuesta = api.post(f"/ventas/{venta}/actualizar", data=cuerpo_venta(datos, nuevo))
        assert respuesta.status_code == 302  # guardo y redirige al listado
        assert estado_apartamento(api, datos) == "disponible"
        assert estado_de(api, nuevo) == "vendido"

    def test_rn20_no_se_cambia_la_venta_a_un_apartamento_ya_vendido(self, api, datos, venta):
        """Si el apartamento destino ya esta vendido, se rechaza y
        ningun estado cambia."""
        otro = crear_otro_apartamento(api, datos, estado="disponible")
        assert crear_venta(api, datos, id_apartamento=otro).status_code == 201
        respuesta = api.put(f"/api/ventas/{venta}", json=cuerpo_venta(datos, otro))
        assert respuesta.status_code == 400
        assert estado_apartamento(api, datos) == "vendido"
        assert estado_de(api, otro) == "vendido"


# ---------------------------------------------------------------------
# Apartamento vendido: su estado solo cambia al anular la venta
# ---------------------------------------------------------------------
class TestEstadoDeApartamentoVendido:

    def test_rn21_la_api_avisa_y_conserva_vendido(self, api, datos, venta):
        """Pedir otro estado no es un error (200): los demas campos se
        guardan, el estado sigue en vendido y la respuesta lo explica."""
        respuesta = api.put(f"/api/apartamentos/{datos['id_apartamento']}",
                            json=cuerpo_apartamento(datos, estado="disponible", habitaciones=4))
        assert respuesta.status_code == 200
        cuerpo = respuesta.get_json()
        assert cuerpo["estado"] == "vendido"
        assert cuerpo["habitaciones"] == 4
        assert cuerpo["aviso"] == AVISO_ESTADO_VENDIDO

    def test_rn22_la_pantalla_muestra_el_aviso(self, api, datos, venta):
        respuesta = api.post(f"/apartamentos/{datos['id_apartamento']}/actualizar",
                             data=cuerpo_apartamento(datos, estado="reservado"),
                             follow_redirects=True)
        assert respuesta.status_code == 200
        pagina = html.unescape(respuesta.get_data(as_text=True))
        assert AVISO_ESTADO_VENDIDO in pagina
        assert "actualizado correctamente" in pagina
        assert estado_apartamento(api, datos) == "vendido"

    def test_rn23_sin_cambio_de_estado_no_hay_aviso(self, api, datos, venta):
        ruta = f"/api/apartamentos/{datos['id_apartamento']}"
        # Vendido que envia "vendido" o no envia estado: nada que avisar.
        assert "aviso" not in api.put(ruta, json=cuerpo_apartamento(datos, estado="vendido")).get_json()
        sin_estado = cuerpo_apartamento(datos)
        del sin_estado["estado"]
        assert "aviso" not in api.put(ruta, json=sin_estado).get_json()
        # El formulario de un apartamento vendido no envia el campo estado.
        pagina = api.post(f"/apartamentos/{datos['id_apartamento']}/actualizar",
                          data=sin_estado, follow_redirects=True).get_data(as_text=True)
        assert AVISO_ESTADO_VENDIDO not in html.unescape(pagina)
        # Apartamento sin venta: el cambio de estado se aplica, sin aviso.
        libre = crear_otro_apartamento(api, datos, estado="disponible")
        cuerpo = api.put(f"/api/apartamentos/{libre}",
                         json=cuerpo_apartamento(datos, "102", estado="reservado")).get_json()
        assert cuerpo["estado"] == "reservado"
        assert "aviso" not in cuerpo


# ---------------------------------------------------------------------
# Pagos (abonos)
# ---------------------------------------------------------------------
class TestPagos:

    def test_rn05_el_pago_no_puede_superar_el_saldo(self, api, datos, venta):
        assert crear_pago(api, datos, venta, VALOR + 1).status_code == 400
        # Con un abono previo, el tope es el saldo restante, no el valor total.
        assert crear_pago(api, datos, venta, 150000000).status_code == 201
        assert crear_pago(api, datos, venta, 50000001).status_code == 400
        assert crear_pago(api, datos, venta, 50000000).status_code == 201

    def test_rn06_la_fecha_de_pago_no_puede_ser_futura(self, api, datos, venta):
        assert crear_pago(api, datos, venta, 1000, fecha_pago=datos["manana"]).status_code == 400

    def test_rn07_la_fecha_de_pago_no_puede_ser_anterior_a_la_venta(self, api, datos, venta):
        respuesta = crear_pago(api, datos, venta, 1000, fecha_pago=datos["antes_de_la_venta"])
        assert respuesta.status_code == 400

    def test_rn08_el_metodo_de_pago_debe_estar_en_la_lista(self, api, datos, venta):
        assert crear_pago(api, datos, venta, 1000, metodo_pago="Bitcoin").status_code == 400

    def test_rn09_el_estado_de_la_venta_se_calcula_con_los_pagos(self, api, datos, venta):
        def consultar():
            return api.get(f"/api/ventas/{venta}").get_json()

        assert consultar()["estado"] == "pendiente"

        crear_pago(api, datos, venta, 80000000)
        parcial = consultar()
        assert parcial["estado"] == "en-pago"
        assert parcial["total_pagado"] == 80000000
        assert parcial["saldo"] == 120000000

        crear_pago(api, datos, venta, 120000000)
        final = consultar()
        assert final["estado"] == "pagada"
        assert final["saldo"] == 0


# ---------------------------------------------------------------------
# Eliminaciones bloqueadas
# ---------------------------------------------------------------------
class TestEliminacionesBloqueadas:

    def test_rn10_proyecto_con_apartamentos(self, api, datos):
        assert api.delete(f"/api/proyectos/{datos['id_proyecto']}").status_code == 409

    def test_rn11_apartamento_con_venta(self, api, datos, venta):
        assert api.delete(f"/api/apartamentos/{datos['id_apartamento']}").status_code == 409

    def test_rn12_venta_con_pagos(self, api, datos, venta):
        crear_pago(api, datos, venta, 1000)
        assert api.delete(f"/api/ventas/{venta}").status_code == 409
        assert estado_apartamento(api, datos) == "vendido"

    def test_rn13_cliente_con_proyectos_o_ventas(self, api, datos):
        assert api.delete(f"/api/clientes/{datos['id_cliente']}").status_code == 409

    def test_rn14_usuario_que_gestiona_proyectos(self, api, datos):
        assert api.delete(f"/api/usuarios/{datos['id_usuario']}").status_code == 409


# ---------------------------------------------------------------------
# Contrato de la API
# ---------------------------------------------------------------------
class TestContratoApi:

    def test_rn15_registro_inexistente_responde_404(self, api, datos):
        for recurso in ("clientes", "usuarios", "proyectos", "apartamentos", "ventas", "pagos"):
            assert api.get(f"/api/{recurso}/999999").status_code == 404

    def test_rn16_datos_invalidos_responden_400_con_lista_de_errores(self, api, datos):
        respuesta = api.post("/api/clientes", json={"nombre": "Ana1", "apellido": "",
                                                    "documento": "abc", "correo": "sin-arroba",
                                                    "telefono": "12"})
        assert respuesta.status_code == 400
        assert len(respuesta.get_json()["errores"]) == 5

    def test_rn17_la_api_nunca_devuelve_la_contrasena(self, api, datos):
        respuesta = api.post("/api/usuarios", json={"nombre": "Eva", "apellido": "Diaz",
                                                    "correo": "eva@ejemplo.com",
                                                    "contrasena": "ClaveSegura1", "rol": "Vendedor"})
        assert respuesta.status_code == 201
        for usuario in [respuesta.get_json()] + api.get("/api/usuarios").get_json():
            assert "contrasena" not in usuario
            assert "ClaveSegura1" not in str(usuario)


# ---------------------------------------------------------------------
# La base de pruebas se comporta como MySQL con las llaves foraneas
# ---------------------------------------------------------------------
def test_la_base_de_pruebas_exige_llaves_foraneas(app):
    """Si PRAGMA foreign_keys no estuviera activo, SQLite aceptaria un
    proyecto con un cliente inexistente y las pruebas de arriba darian
    una falsa tranquilidad."""
    with app.app_context():
        db.session.add(Proyecto(id_cliente=999, id_usuario=999, nombre_proyecto="Huerfano",
                                direccion="Calle 1", ciudad="Cali"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
