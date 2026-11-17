"""
tests/test_requisitos.py
------------------------
Pruebas que cierran las brechas de verificacion detectadas al escribir
docs/requisitos_y_casos_de_uso.md (ARKHE-RQ-001): requisitos que
estaban implementados pero no tenian una prueba automatica propia.

  RQ-01..RQ-03  RF-21  Editar un usuario (API y pantalla); la contrasena
                       se conserva si el campo queda vacio
  RQ-04..RQ-05  RF-14  La API responde 409 con un documento o correo
                       de cliente repetido
  RQ-06..RQ-09  RF-27  Proyecto: nombre repetido, gestor inactivo,
                       cliente o gestor inexistente y longitudes maximas
  RQ-10..RQ-11  RF-25  scripts/cambiar_contrasena.py

Como las demas, usan la base temporal de tests/conftest.py: nunca tocan
ARKHE_V1.
"""

import pytest

from models import db
from models.cliente import Cliente
from models.proyecto import Proyecto
from models.usuario import Usuario
from scripts import cambiar_contrasena
from tests.conftest import CLAVE, CORREOS, entrar_como

ADMIN, VENDEDOR = "Administrador", "Vendedor"
CLAVE_NUEVA = "OtraClave2026"


def puede_entrar(api, correo, contrasena):
    """True si esas credenciales abren sesion (cierra antes la actual)."""
    api.post("/logout")
    return api.post("/api/login", json={"correo": correo, "contrasena": contrasena}).status_code == 200


def usuario_guardado(app, id_usuario):
    """Los datos del usuario tal como estan en la base."""
    with app.app_context():
        usuario = db.session.get(Usuario, id_usuario)
        return {"nombre": usuario.nombre, "apellido": usuario.apellido, "correo": usuario.correo,
                "rol": usuario.rol, "estado": usuario.estado, "contrasena": usuario.contrasena}


# ---------------------------------------------------------------------
# RF-21  Editar un usuario
# ---------------------------------------------------------------------
def test_rq01_editar_usuario_por_la_api_sin_contrasena_conserva_la_actual(app, api, datos):
    entrar_como(api, ADMIN)
    antes = usuario_guardado(app, datos["id_vendedor"])

    respuesta = api.put(f"/api/usuarios/{datos['id_vendedor']}",
                        json={"nombre": "Verónica", "apellido": "Soto Ruiz",
                              "correo": "veronica@ejemplo.com", "rol": "Gerente", "estado": "activo"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert (cuerpo["nombre"], cuerpo["apellido"], cuerpo["correo"], cuerpo["rol"]) == \
        ("Verónica", "Soto Ruiz", "veronica@ejemplo.com", "Gerente")
    assert "contrasena" not in cuerpo

    despues = usuario_guardado(app, datos["id_vendedor"])
    assert despues["rol"] == "Gerente" and despues["correo"] == "veronica@ejemplo.com"
    # No se envio contrasena: el hash guardado es exactamente el mismo.
    assert despues["contrasena"] == antes["contrasena"]
    assert puede_entrar(api, "veronica@ejemplo.com", CLAVE)


def test_rq02_editar_usuario_por_la_api_con_contrasena_la_cambia(app, api, datos):
    entrar_como(api, ADMIN)
    respuesta = api.put(f"/api/usuarios/{datos['id_vendedor']}",
                        json={"nombre": "Vera", "apellido": "Soto", "correo": CORREOS[VENDEDOR],
                              "rol": VENDEDOR, "estado": "activo", "contrasena": CLAVE_NUEVA})
    assert respuesta.status_code == 200

    # Se guarda el hash de la nueva, nunca el texto.
    guardada = usuario_guardado(app, datos["id_vendedor"])["contrasena"]
    assert guardada != CLAVE_NUEVA and CLAVE_NUEVA not in guardada
    assert not puede_entrar(api, CORREOS[VENDEDOR], CLAVE)
    assert puede_entrar(api, CORREOS[VENDEDOR], CLAVE_NUEVA)

    # Una contrasena nueva que no cumple la regla se rechaza y no cambia nada.
    entrar_como(api, ADMIN)
    corta = api.put(f"/api/usuarios/{datos['id_usuario']}",
                    json={"nombre": "Luis", "apellido": "Mora", "correo": CORREOS[ADMIN],
                          "rol": ADMIN, "estado": "activo", "contrasena": "corta"})
    assert corta.status_code == 400
    assert puede_entrar(api, CORREOS[ADMIN], CLAVE)


def test_rq03_editar_usuario_por_la_pantalla(app, api, datos):
    entrar_como(api, ADMIN)
    id_vendedor = datos["id_vendedor"]
    antes = usuario_guardado(app, id_vendedor)

    # El formulario llega con los datos actuales.
    formulario = api.get(f"/usuarios/{id_vendedor}/editar")
    assert formulario.status_code == 200
    assert 'value="Vera"' in formulario.get_data(as_text=True)

    # Campo de contrasena vacio: se guardan los demas datos y la contrasena sigue igual.
    respuesta = api.post(f"/usuarios/{id_vendedor}/editar", follow_redirects=True,
                         data={"nombre": "Vera Lucía", "apellido": "Soto", "correo": CORREOS[VENDEDOR],
                               "rol": VENDEDOR, "estado": "inactivo", "contrasena": ""})
    assert respuesta.status_code == 200
    assert "actualizado." in respuesta.get_data(as_text=True)
    despues = usuario_guardado(app, id_vendedor)
    assert despues["nombre"] == "Vera Lucía" and despues["estado"] == "inactivo"
    assert despues["contrasena"] == antes["contrasena"]

    # Con contrasena nueva: se cambia, y al reactivar la cuenta entra con ella.
    api.post(f"/usuarios/{id_vendedor}/editar",
             data={"nombre": "Vera Lucía", "apellido": "Soto", "correo": CORREOS[VENDEDOR],
                   "rol": VENDEDOR, "estado": "activo", "contrasena": CLAVE_NUEVA})
    assert usuario_guardado(app, id_vendedor)["contrasena"] != antes["contrasena"]
    assert not puede_entrar(api, CORREOS[VENDEDOR], CLAVE)
    assert puede_entrar(api, CORREOS[VENDEDOR], CLAVE_NUEVA)

    # Un correo que ya usa otra cuenta se rechaza con mensaje y no se guarda.
    entrar_como(api, ADMIN)
    repetido = api.post(f"/usuarios/{id_vendedor}/editar", follow_redirects=True,
                        data={"nombre": "Vera", "apellido": "Soto", "correo": CORREOS["Gerente"],
                              "rol": VENDEDOR, "estado": "activo", "contrasena": ""})
    assert "Ya existe un usuario registrado con ese correo." in repetido.get_data(as_text=True)
    assert usuario_guardado(app, id_vendedor)["correo"] == CORREOS[VENDEDOR]


# ---------------------------------------------------------------------
# RF-14  Cliente sin duplicados, por la API (409)
# ---------------------------------------------------------------------
OTRO_CLIENTE = {"nombre": "Eva", "apellido": "Diaz", "documento": "55667788",
                "correo": "eva@ejemplo.com", "telefono": "3009998877"}
MENSAJE_CLIENTE_REPETIDO = "Ya existe un cliente registrado con ese documento o correo."


@pytest.mark.parametrize("campo, valor", [
    ("documento", "10203040"),           # el documento del cliente de la fixture
    ("correo", "ana@ejemplo.com"),       # su correo
])
def test_rq04_la_api_responde_409_al_crear_un_cliente_repetido(app, api, datos, campo, valor):
    entrar_como(api, VENDEDOR)
    respuesta = api.post("/api/clientes", json={**OTRO_CLIENTE, campo: valor})
    assert respuesta.status_code == 409
    assert respuesta.get_json() == {"error": MENSAJE_CLIENTE_REPETIDO}
    with app.app_context():
        assert Cliente.query.count() == 1          # no se guardo el segundo


def test_rq05_la_api_responde_409_al_editar_un_cliente_con_datos_de_otro(app, api, datos):
    entrar_como(api, VENDEDOR)
    otro = api.post("/api/clientes", json=OTRO_CLIENTE)
    assert otro.status_code == 201
    id_otro = otro.get_json()["id_cliente"]

    for campo, valor in (("documento", "10203040"), ("correo", "ana@ejemplo.com")):
        respuesta = api.put(f"/api/clientes/{id_otro}", json={**OTRO_CLIENTE, campo: valor})
        assert respuesta.status_code == 409, campo
        assert respuesta.get_json() == {"error": MENSAJE_CLIENTE_REPETIDO}
    with app.app_context():
        guardado = db.session.get(Cliente, id_otro)
        assert (guardado.documento, guardado.correo) == ("55667788", "eva@ejemplo.com")

    # Guardar un cliente con sus propios datos no es un duplicado.
    assert api.put(f"/api/clientes/{id_otro}", json=OTRO_CLIENTE).status_code == 200


# ---------------------------------------------------------------------
# RF-27  Validaciones del proyecto
# ---------------------------------------------------------------------
def cuerpo_proyecto(datos, **cambios):
    cuerpo = {"nombre_proyecto": "Torre Nueva", "direccion": "Carrera 7 # 10-20", "ciudad": "Cali",
              "id_cliente": datos["id_cliente"], "id_usuario": datos["id_usuario"]}
    cuerpo.update(cambios)
    return cuerpo


def total_proyectos(app):
    with app.app_context():
        return Proyecto.query.count()


def test_rq06_el_nombre_del_proyecto_no_se_repite(app, api, datos):
    entrar_como(api, ADMIN)
    # "Torre Prueba" es el proyecto de la fixture.
    repetido = api.post("/api/proyectos", json=cuerpo_proyecto(datos, nombre_proyecto="Torre Prueba"))
    assert repetido.status_code == 400
    assert repetido.get_json()["errores"] == ["Ya existe un proyecto con este nombre."]
    assert total_proyectos(app) == 1

    nuevo = api.post("/api/proyectos", json=cuerpo_proyecto(datos))
    assert nuevo.status_code == 201
    id_nuevo = nuevo.get_json()["id_proyecto"]
    # Al editar tampoco puede tomar el nombre de otro proyecto...
    al_editar = api.put(f"/api/proyectos/{id_nuevo}", json=cuerpo_proyecto(datos, nombre_proyecto="Torre Prueba"))
    assert al_editar.status_code == 400
    assert al_editar.get_json()["errores"] == ["Ya existe un proyecto con este nombre."]
    # ...pero si conservar el suyo.
    assert api.put(f"/api/proyectos/{id_nuevo}", json=cuerpo_proyecto(datos, ciudad="Medellin")).status_code == 200

    # El mismo mensaje sale por la pantalla.
    pantalla = api.post("/proyectos/crear", data=cuerpo_proyecto(datos, nombre_proyecto="Torre Prueba"))
    assert "Ya existe un proyecto con este nombre." in pantalla.get_data(as_text=True)
    assert total_proyectos(app) == 2


def test_rq07_el_gestor_del_proyecto_debe_estar_activo(app, api, datos):
    entrar_como(api, ADMIN)
    with app.app_context():
        db.session.get(Usuario, datos["id_vendedor"]).estado = "inactivo"
        db.session.commit()

    respuesta = api.post("/api/proyectos", json=cuerpo_proyecto(datos, id_usuario=datos["id_vendedor"]))
    assert respuesta.status_code == 400
    assert respuesta.get_json()["errores"] == ["El usuario debe estar activo para gestionar un proyecto."]
    assert total_proyectos(app) == 1

    # El formulario de la pantalla ni siquiera ofrece a un usuario inactivo como gestor.
    formulario = api.get("/proyectos/nuevo").get_data(as_text=True)
    assert "Luis Mora" in formulario and "Vera Soto" not in formulario

    # Con un gestor activo, el mismo proyecto si se crea.
    assert api.post("/api/proyectos", json=cuerpo_proyecto(datos, id_usuario=datos["id_gerente"])).status_code == 201


@pytest.mark.parametrize("cambios, mensaje", [
    ({"id_cliente": 999999}, "El cliente seleccionado no existe."),
    ({"id_cliente": ""}, "Debe seleccionar un cliente."),
    ({"id_usuario": 999999}, "El usuario seleccionado no existe."),
    ({"id_usuario": ""}, "Debe seleccionar un usuario gestor."),
    ({"nombre_proyecto": "   "}, "El nombre del proyecto es requerido."),
    ({"direccion": ""}, "La dirección es requerida."),
    ({"ciudad": ""}, "La ciudad es requerida."),
    ({"ciudad": "Cali 2"}, "La ciudad solo puede contener letras y espacios (sin números)."),
])
def test_rq08_datos_obligatorios_y_existentes_del_proyecto(app, api, datos, cambios, mensaje):
    entrar_como(api, ADMIN)
    respuesta = api.post("/api/proyectos", json=cuerpo_proyecto(datos, **cambios))
    assert respuesta.status_code == 400
    assert respuesta.get_json()["errores"] == [mensaje]
    assert total_proyectos(app) == 1


@pytest.mark.parametrize("campo, maximo, mensaje", [
    ("nombre_proyecto", 150, "El nombre no puede exceder 150 caracteres."),
    ("direccion", 200, "La dirección no puede exceder 200 caracteres."),
    ("ciudad", 100, "La ciudad no puede exceder 100 caracteres."),
])
def test_rq09_longitud_maxima_en_proyectos(app, api, datos, campo, maximo, mensaje):
    entrar_como(api, ADMIN)
    # Un caracter de mas: se rechaza con mensaje (y no con un error de la base).
    largo = api.post("/api/proyectos", json=cuerpo_proyecto(datos, **{campo: "a" * (maximo + 1)}))
    assert largo.status_code == 400
    assert largo.get_json()["errores"] == [mensaje]
    assert total_proyectos(app) == 1
    # Justo en el limite: se acepta.
    assert api.post("/api/proyectos", json=cuerpo_proyecto(datos, **{campo: "a" * maximo})).status_code == 201


# ---------------------------------------------------------------------
# RF-25  scripts/cambiar_contrasena.py
# ---------------------------------------------------------------------
@pytest.fixture
def ejecutar_script(app, monkeypatch):
    """Ejecuta main() del script contra la base de pruebas. El script
    crea su propia app (MySQL real): aqui se le entrega la de pruebas, y
    se responden por el las preguntas que haria en la consola."""
    def ejecutar(correo, *contrasenas):
        respuestas = iter(contrasenas)
        monkeypatch.setattr(cambiar_contrasena, "create_app", lambda: app)
        monkeypatch.setattr("builtins.input", lambda _pregunta: correo)
        monkeypatch.setattr(cambiar_contrasena, "getpass", lambda _pregunta: next(respuestas))
        return cambiar_contrasena.main()
    return ejecutar


def test_rq10_el_script_cambia_solo_la_contrasena_de_ese_usuario(app, api, datos, ejecutar_script, capsys):
    antes = {rol: usuario_guardado(app, datos[clave])
             for rol, clave in (("vendedor", "id_vendedor"), ("admin", "id_usuario"), ("gerente", "id_gerente"))}

    # El correo se busca sin distinguir mayusculas, como en el login.
    assert ejecutar_script("VERA@ejemplo.com", CLAVE_NUEVA, CLAVE_NUEVA) == 0
    salida = capsys.readouterr().out
    assert "Contraseña cambiada para Vera Soto" in salida
    assert CLAVE_NUEVA not in salida                      # la contrasena no se imprime

    vendedor = usuario_guardado(app, datos["id_vendedor"])
    assert vendedor["contrasena"] != antes["vendedor"]["contrasena"]
    assert vendedor["contrasena"] != CLAVE_NUEVA          # se guarda el hash
    # Ningun otro dato del usuario cambio...
    assert {k: v for k, v in vendedor.items() if k != "contrasena"} == \
        {k: v for k, v in antes["vendedor"].items() if k != "contrasena"}
    # ...ni ningun otro usuario.
    assert usuario_guardado(app, datos["id_usuario"]) == antes["admin"]
    assert usuario_guardado(app, datos["id_gerente"]) == antes["gerente"]
    with app.app_context():
        assert Usuario.query.count() == 3

    assert not puede_entrar(api, CORREOS[VENDEDOR], CLAVE)
    assert puede_entrar(api, CORREOS[VENDEDOR], CLAVE_NUEVA)


@pytest.mark.parametrize("correo, contrasenas, aviso", [
    ("nadie@ejemplo.com", (), "No existe ningun usuario"),
    (CORREOS[VENDEDOR], (CLAVE_NUEVA, "Distinta2026"), "Las contraseñas no coinciden"),
    (CORREOS[VENDEDOR], ("corta", "corta"), "Contraseña no valida"),
    (CORREOS[VENDEDOR], (" ConEspacios1", " ConEspacios1"), "Contraseña no valida"),
])
def test_rq11_el_script_no_cambia_nada_si_algo_falla(app, api, datos, ejecutar_script, capsys,
                                                    correo, contrasenas, aviso):
    antes = usuario_guardado(app, datos["id_vendedor"])
    assert ejecutar_script(correo, *contrasenas) == 1
    salida = capsys.readouterr().out
    assert aviso in salida and "No se cambio nada." in salida
    assert usuario_guardado(app, datos["id_vendedor"]) == antes
    assert puede_entrar(api, CORREOS[VENDEDOR], CLAVE)
