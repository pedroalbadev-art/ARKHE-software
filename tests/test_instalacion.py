"""
tests/test_instalacion.py
-------------------------
Pruebas del cierre del proyecto (prioridad 6 del CLAUDE.md): esquema
SQL, datos de demostracion y las piezas del instalador que se pueden
probar sin un servidor MySQL.

La creacion real de la base (instalar.ps1 contra MySQL) se prueba a
mano en una carpeta limpia; aqui se prueba todo lo demas.

  IS-01..IS-03  database/esquema.sql
  IS-04..IS-08  scripts/datos_demo.py
  IS-09..IS-13  scripts/preparar_base.py e instalar.ps1
  IS-14         Versiones fijas en requirements
"""

import re
from datetime import date
from pathlib import Path

import pytest
from dotenv import dotenv_values

from models import db
from models.apartamento import Apartamento
from models.cliente import Cliente
from models.pago import METODOS_PAGO, Pago
from models.proyecto import Proyecto
from models.usuario import Usuario
from models.venta import Venta
from routes.clientes import _validar_datos_cliente
from routes.usuarios import _validar_datos_usuario
from scripts import datos_demo
from scripts import preparar_base

RAIZ = Path(__file__).resolve().parent.parent
MODELOS = [Usuario, Cliente, Proyecto, Apartamento, Venta, Pago]


# ---------------------------------------------------------------------
# Esquema
# ---------------------------------------------------------------------
@pytest.fixture(scope="module")
def sentencias():
    return preparar_base.dividir_sql((RAIZ / "database" / "esquema.sql").read_text(encoding="utf-8"))


def test_is01_el_esquema_crea_las_seis_tablas_en_orden_de_dependencia(sentencias):
    tablas = [re.match(r"CREATE TABLE `(\w+)`", s).group(1) for s in sentencias]
    assert tablas == ["usuarios", "clientes", "proyectos", "apartamentos", "ventas", "pagos"]


def test_is02_el_esquema_no_borra_ni_elige_base(sentencias):
    # Cada sentencia es un CREATE TABLE: no hay DROP, DELETE, INSERT, USE
    # ni CREATE DATABASE. (ON DELETE RESTRICT, dentro de las llaves
    # foraneas, no es una sentencia DELETE.)
    assert len(sentencias) == 6
    for sentencia in sentencias:
        assert sentencia.startswith("CREATE TABLE `"), sentencia[:40]
        assert "DROP " not in sentencia.upper() and "TRUNCATE" not in sentencia.upper()
        assert "AUTO_INCREMENT=" not in sentencia          # los ID empiezan en 1


def test_is03_cada_columna_de_los_modelos_esta_en_el_esquema(sentencias):
    """Los modelos y el SQL de instalacion describen la misma estructura."""
    por_tabla = {re.match(r"CREATE TABLE `(\w+)`", s).group(1): s for s in sentencias}
    for modelo in MODELOS:
        sql = por_tabla[modelo.__tablename__]
        columnas_sql = set(re.findall(r"^\s+`(\w+)` ", sql, flags=re.M))
        columnas_modelo = {columna.name for columna in modelo.__table__.columns}
        assert columnas_sql == columnas_modelo, modelo.__tablename__
    assert "UNIQUE KEY `uq_apartamento_vendido` (`id_apartamento`)" in por_tabla["ventas"]
    assert por_tabla["pagos"].count("ON DELETE RESTRICT") == 1


# ---------------------------------------------------------------------
# Datos de demostracion
# ---------------------------------------------------------------------
@pytest.fixture
def demo(app):
    with app.app_context():
        creado = datos_demo.cargar_datos_demo()
    return creado


def test_is04_carga_completa_en_una_base_vacia(app, demo):
    assert demo == {"usuarios": 3, "clientes": 6, "proyectos": 2,
                    "apartamentos": 10, "ventas": 4, "pagos": 6}
    with app.app_context():
        assert [modelo.query.count() for modelo in MODELOS] == [3, 6, 2, 10, 4, 6]


def test_is05_los_datos_demo_cumplen_las_reglas_del_sistema(app, demo):
    hoy = date.today()
    with app.app_context():
        # Un usuario activo por rol.
        assert sorted(u.rol for u in Usuario.query.filter_by(estado="activo")) == \
            ["Administrador", "Gerente", "Vendedor"]
        # Hay ventas en los tres estados calculados.
        assert sorted(v.estado for v in Venta.query.all()) == ["en-pago", "en-pago", "pagada", "pendiente"]
        for venta in Venta.query.all():
            assert venta.apartamento.estado == "vendido"
            assert venta.fecha_venta <= hoy
            assert venta.saldo >= 0                               # los pagos no superan el valor
            for pago in venta.pagos:
                assert venta.fecha_venta <= pago.fecha_pago <= hoy
                assert pago.metodo_pago in METODOS_PAGO
        # Apartamentos: vendidos solo los que tienen venta; quedan disponibles y reservados.
        estados = [a.estado for a in Apartamento.query.all()]
        assert (estados.count("vendido"), estados.count("reservado"), estados.count("disponible")) == (4, 2, 4)
        assert all(a.estado != "vendido" or a.venta is not None for a in Apartamento.query.all())
        # El propietario de un proyecto no figura como comprador en las ventas demo.
        propietarios = {p.id_cliente for p in Proyecto.query.all()}
        assert propietarios.isdisjoint({v.id_cliente for v in Venta.query.all()})


def test_is06_los_datos_demo_pasan_las_validaciones_de_los_formularios():
    for cliente in datos_demo.CLIENTES_DEMO:
        assert _validar_datos_cliente(cliente) == [], cliente["correo"]
    for usuario in datos_demo.USUARIOS_DEMO:
        assert _validar_datos_usuario({**usuario, "estado": "activo"}, requiere_contrasena=True) == []


def test_is07_los_usuarios_demo_pueden_iniciar_sesion(api, demo):
    for usuario in datos_demo.USUARIOS_DEMO:
        respuesta = api.post("/api/login", json={"correo": usuario["correo"],
                                                 "contrasena": usuario["contrasena"]})
        assert respuesta.status_code == 200
        assert respuesta.get_json()["usuario"]["rol"] == usuario["rol"]
        api.post("/logout")


def test_is08_la_carga_no_toca_una_base_con_datos(app, datos):
    """`datos` ya creo registros: la carga completa se niega y --solo-usuarios
    agrega los tres de demostracion sin modificar los existentes."""
    with app.app_context():
        antes = {u.correo: (u.rol, u.estado, u.contrasena) for u in Usuario.query.all()}

        with pytest.raises(datos_demo.BaseConDatos):
            datos_demo.cargar_datos_demo()
        assert Usuario.query.count() == 3 and Cliente.query.count() == 1      # nada cambio

        assert datos_demo.cargar_datos_demo(solo_usuarios=True) == {"usuarios": 3}
        assert Usuario.query.count() == 6
        for correo, valores in antes.items():
            usuario = Usuario.query.filter_by(correo=correo).one()
            assert (usuario.rol, usuario.estado, usuario.contrasena) == valores
        # Repetirlo no duplica nada.
        assert datos_demo.cargar_datos_demo(solo_usuarios=True) == {"usuarios": 0}
        assert Usuario.query.count() == 6 and Cliente.query.count() == 1


# ---------------------------------------------------------------------
# Instalador
# ---------------------------------------------------------------------
@pytest.mark.parametrize("nombre, valido", [
    ("ARKHE_DEMO", True),
    ("arkhe2026", True),
    ("", False),
    ("con espacio", False),
    ("demo`; DROP DATABASE ARKHE_V1; --", False),      # intento de inyeccion
    ("demo-guion", False),
    ("a" * 65, False),
])
def test_is09_nombre_de_base_valido(nombre, valido):
    assert preparar_base.nombre_base_valido(nombre) is valido


@pytest.mark.parametrize("contrasena", ["simple", "con#numeral", 'con"comillas', "con espacio ",
                                        "con\\barra", "ñandú$%&=", ""])
def test_is10_el_env_generado_se_lee_igual_que_se_escribio(tmp_path, contrasena):
    """Una contraseña con #, comillas o barras debe sobrevivir al .env."""
    datos = {"DB_HOST": "localhost", "DB_PORT": "3306", "DB_USER": "root",
             "DB_PASSWORD": contrasena, "DB_NAME": "ARKHE_DEMO"}
    archivo = tmp_path / ".env"
    archivo.write_text(preparar_base.contenido_env(datos, "clave-de-prueba"), encoding="utf-8")
    leido = dotenv_values(archivo)
    assert {clave: leido[clave] for clave in datos} == datos
    assert leido["SECRET_KEY"] == "clave-de-prueba" and leido["FLASK_DEBUG"] == "0"


def test_is11_dividir_sql_ignora_comentarios():
    sql = "-- comentario; con punto y coma\nCREATE TABLE a (x int);\n\n-- otro\nCREATE TABLE b (\n  y int\n);\n"
    assert preparar_base.dividir_sql(sql) == ["CREATE TABLE a (x int)", "CREATE TABLE b (\n  y int\n)"]


def test_is12_el_instalador_nunca_borra_ni_sobrescribe():
    """Revision del codigo fuente: sin DROP, sin CREATE ... IF NOT EXISTS
    y con la comprobacion de existencia antes de escribir el .env."""
    codigo = (RAIZ / "scripts" / "preparar_base.py").read_text(encoding="utf-8")
    # Se quita la descripcion inicial del archivo (que menciona la palabra
    # DROP para explicar que no se usa) y las lineas de comentario.
    sin_descripcion = codigo.split('"""', 2)[2]
    ejecutable = "\n".join(linea for linea in sin_descripcion.splitlines()
                           if not linea.lstrip().startswith("#"))
    assert "DROP" not in ejecutable.upper()
    assert "CREATE DATABASE IF NOT EXISTS" not in ejecutable.upper()
    assert "DELETE FROM" not in ejecutable.upper() and "TRUNCATE" not in ejecutable.upper()
    # Orden dentro de main(): comprobar -> escribir .env -> crear base.
    principal = ejecutable[ejecutable.index("def main():"):]
    assert principal.index("base_existe(") < principal.index("RUTA_ENV.write_text") < principal.index("crear_base_y_tablas(")
    # El .env solo se escribe si no existia.
    assert "if not habia_env:\n        RUTA_ENV.write_text" in principal


def test_is13_instalar_ps1_explica_el_bloqueo_y_no_usa_mysql_exe():
    script = (RAIZ / "instalar.ps1").read_bytes()
    assert all(byte < 128 for byte in script), "instalar.ps1 debe ser ASCII puro (PowerShell 5.1)"
    texto = script.decode("ascii")
    assert "-ExecutionPolicy Bypass" in texto and "Unblock-File" in texto
    assert "scripts\\preparar_base.py" in texto
    sin_comentarios = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("#"))
    assert "mysql.exe" not in sin_comentarios and "mysql " not in sin_comentarios.lower()
    assert "Remove-Item" not in sin_comentarios


# ---------------------------------------------------------------------
# Dependencias
# ---------------------------------------------------------------------
def test_is14_versiones_fijas_en_requirements():
    for archivo in ("requirements.txt", "requirements-dev.txt"):
        for linea in (RAIZ / archivo).read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or linea.startswith("-r "):
                continue
            assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][0-9A-Za-z.]*", linea), f"{archivo}: '{linea}' sin version fija"
