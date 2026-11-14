"""
scripts/datos_demo.py
---------------------
Carga datos de demostracion para poder recorrer el sistema recien
instalado: tres usuarios (uno por rol), clientes, dos proyectos con sus
apartamentos, ventas y pagos.

Uso (en la raiz del proyecto, con el entorno virtual activo):

    python scripts/datos_demo.py                  Carga todo. Solo funciona
                                                  si la base esta VACIA.
    python scripts/datos_demo.py --solo-usuarios  Agrega unicamente los tres
                                                  usuarios de demostracion
                                                  que no existan todavia.

Reglas de seguridad de este script:
  - Nunca borra ni modifica registros existentes.
  - La carga completa se niega a correr si alguna tabla ya tiene datos.
  - --solo-usuarios no toca a los usuarios que ya existen: solo crea los
    de demostracion cuyo correo aun no este registrado.

Los datos son inventados (personas, documentos y correos ficticios). El
sistema es de proposito general: nada de esto lo ata a una empresa real.

Las fechas se calculan hacia atras desde el dia en que se ejecuta, para
que el grafico de ventas del dashboard siempre tenga meses recientes y
se cumplan las reglas de negocio (ninguna fecha futura, ningun pago
anterior a su venta).
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Permite importar app, models y utils aunque el script este en scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import db  # noqa: E402
from models.apartamento import Apartamento  # noqa: E402
from models.cliente import Cliente  # noqa: E402
from models.pago import Pago  # noqa: E402
from models.proyecto import Proyecto  # noqa: E402
from models.usuario import Usuario  # noqa: E402
from models.venta import Venta  # noqa: E402

# ---------------------------------------------------------------------
# Usuarios de demostracion (documentados en el README).
# El dominio ".example" esta reservado para ejemplos: no existe en internet.
# ---------------------------------------------------------------------
USUARIOS_DEMO = [
    {"nombre": "Laura", "apellido": "Restrepo Gil", "correo": "admin@arkhe.example",
     "rol": "Administrador", "contrasena": "Admin#2026"},
    {"nombre": "Camilo", "apellido": "Vargas Soto", "correo": "vendedor@arkhe.example",
     "rol": "Vendedor", "contrasena": "Vendedor#2026"},
    {"nombre": "Sandra", "apellido": "Molina Reyes", "correo": "gerente@arkhe.example",
     "rol": "Gerente", "contrasena": "Gerente#2026"},
]

# Los dos primeros son propietarios / promotores de proyectos; los demas, compradores.
CLIENTES_DEMO = [
    {"nombre": "Ricardo", "apellido": "Salazar Peña", "documento": "79456123",
     "correo": "ricardo.salazar@correo.example", "telefono": "3104567890"},
    {"nombre": "Marcela", "apellido": "Ortiz Duarte", "documento": "52789456",
     "correo": "marcela.ortiz@correo.example", "telefono": "3156789012"},
    {"nombre": "Andrés", "apellido": "Gómez Rincón", "documento": "1032456789",
     "correo": "andres.gomez@correo.example", "telefono": "3001234567"},
    {"nombre": "Luisa Fernanda", "apellido": "Castro Mejía", "documento": "1018765432",
     "correo": "luisa.castro@correo.example", "telefono": "3209876543"},
    {"nombre": "Jorge Iván", "apellido": "Herrera Pardo", "documento": "80123987",
     "correo": "jorge.herrera@correo.example", "telefono": "3112345678"},
    {"nombre": "Paola", "apellido": "Méndez Vargas", "documento": "1090456321",
     "correo": "paola.mendez@correo.example", "telefono": "3187654321"},
]

# correo del propietario, correo del gestor y apartamentos:
# (numero, area m2, habitaciones, banos, precio, estado inicial)
PROYECTOS_DEMO = [
    {"nombre_proyecto": "Mirador del Río", "direccion": "Calle 45 # 12-30", "ciudad": "Medellín",
     "descripcion": "Torre de seis pisos con zonas comunes y parqueadero cubierto.",
     "propietario": "ricardo.salazar@correo.example", "gestor": "admin@arkhe.example",
     "apartamentos": [
         ("101", "58.50", 2, 2, 285000000, "disponible"),
         ("102", "64.00", 3, 2, 320000000, "disponible"),
         ("201", "58.50", 2, 2, 292000000, "disponible"),
         ("202", "64.00", 3, 2, 328000000, "reservado"),
         ("301", "72.30", 3, 2, 365000000, "disponible"),
         ("302", "72.30", 3, 3, 372000000, "disponible"),
     ]},
    {"nombre_proyecto": "Altos de la Sabana", "direccion": "Carrera 7 # 180-45", "ciudad": "Bogotá",
     "descripcion": "Conjunto cerrado de apartamentos con vista a los cerros.",
     "propietario": "marcela.ortiz@correo.example", "gestor": "gerente@arkhe.example",
     "apartamentos": [
         ("Torre A-101", "48.00", 2, 1, 240000000, "disponible"),
         ("Torre A-102", "48.00", 2, 1, 240000000, "disponible"),
         ("Torre A-201", "55.75", 2, 2, 276000000, "reservado"),
         ("Torre A-202", "55.75", 2, 2, 279000000, "disponible"),
     ]},
]

# proyecto, apartamento, correo del comprador, hace cuantos dias, valor y
# pagos: (dias despues de la venta, monto, metodo)
VENTAS_DEMO = [
    # Pagada por completo.
    ("Mirador del Río", "101", "andres.gomez@correo.example", 160, 285000000, [
        (0, 85000000, "Transferencia"),
        (45, 100000000, "Credito hipotecario"),
        (90, 100000000, "Credito hipotecario"),
    ]),
    # En pago (abonos parciales).
    ("Mirador del Río", "102", "luisa.castro@correo.example", 95, 320000000, [
        (0, 64000000, "Transferencia"),
        (40, 50000000, "Cheque"),
    ]),
    # En pago, con un solo abono.
    ("Altos de la Sabana", "Torre A-101", "jorge.herrera@correo.example", 40, 240000000, [
        (3, 48000000, "Tarjeta debito"),
    ]),
    # Pendiente (sin pagos todavia).
    ("Mirador del Río", "201", "paola.mendez@correo.example", 12, 292000000, []),
]


class BaseConDatos(Exception):
    """La carga completa se pidio sobre una base que ya tiene registros."""


def _crear_usuarios():
    """Crea los usuarios de demostracion que no existan. Devuelve los
    correos creados. Nunca modifica un usuario existente."""
    creados = []
    for datos in USUARIOS_DEMO:
        existe = Usuario.query.filter(db.func.lower(Usuario.correo) == datos["correo"]).first()
        if existe:
            continue
        usuario = Usuario(nombre=datos["nombre"], apellido=datos["apellido"],
                          correo=datos["correo"], rol=datos["rol"], estado="activo")
        usuario.establecer_contrasena(datos["contrasena"])  # se guarda el hash, no el texto
        db.session.add(usuario)
        creados.append(datos["correo"])
    return creados


def cargar_datos_demo(solo_usuarios=False, hoy=None):
    """Carga los datos de demostracion en la base de la app activa (hay
    que llamarla dentro de un app_context). Devuelve un diccionario con
    lo que creo. Todo va en una sola transaccion: si algo falla, no queda
    nada a medias."""
    hoy = hoy or date.today()

    if solo_usuarios:
        creados = _crear_usuarios()
        db.session.commit()
        return {"usuarios": len(creados)}

    for modelo in (Usuario, Cliente, Proyecto, Apartamento, Venta, Pago):
        if modelo.query.count() > 0:
            raise BaseConDatos(
                f"La tabla '{modelo.__tablename__}' ya tiene registros. La carga completa solo "
                "se hace sobre una base vacia; no se modifico nada. Para agregar unicamente "
                "los usuarios de demostracion use:  python scripts/datos_demo.py --solo-usuarios"
            )

    try:
        _crear_usuarios()
        db.session.add_all(Cliente(**datos) for datos in CLIENTES_DEMO)
        db.session.flush()  # asigna los ID sin cerrar la transaccion

        usuario_por_correo = {u.correo: u for u in Usuario.query.all()}
        cliente_por_correo = {c.correo: c for c in Cliente.query.all()}
        apartamento_por_clave = {}

        for datos in PROYECTOS_DEMO:
            proyecto = Proyecto(
                nombre_proyecto=datos["nombre_proyecto"], direccion=datos["direccion"],
                ciudad=datos["ciudad"], descripcion=datos["descripcion"],
                id_cliente=cliente_por_correo[datos["propietario"]].id_cliente,
                id_usuario=usuario_por_correo[datos["gestor"]].id_usuario,
            )
            db.session.add(proyecto)
            db.session.flush()
            for numero, area, habitaciones, banos, precio, estado in datos["apartamentos"]:
                apartamento = Apartamento(
                    id_proyecto=proyecto.id_proyecto, numero_apartamento=numero, area_m2=area,
                    habitaciones=habitaciones, banos=banos, precio=precio, estado=estado,
                )
                db.session.add(apartamento)
                apartamento_por_clave[(datos["nombre_proyecto"], numero)] = apartamento
        db.session.flush()

        total_pagos = 0
        for proyecto, numero, comprador, hace_dias, valor, pagos in VENTAS_DEMO:
            apartamento = apartamento_por_clave[(proyecto, numero)]
            fecha_venta = hoy - timedelta(days=hace_dias)
            venta = Venta(id_cliente=cliente_por_correo[comprador].id_cliente,
                          id_apartamento=apartamento.id_apartamento,
                          fecha_venta=fecha_venta, valor_venta=valor)
            apartamento.estado = "vendido"  # misma regla que al registrar una venta
            db.session.add(venta)
            db.session.flush()
            for dias_despues, monto, metodo in pagos:
                db.session.add(Pago(id_venta=venta.id_venta, monto=monto, metodo_pago=metodo,
                                    fecha_pago=fecha_venta + timedelta(days=dias_despues)))
                total_pagos += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {
        "usuarios": len(USUARIOS_DEMO),
        "clientes": len(CLIENTES_DEMO),
        "proyectos": len(PROYECTOS_DEMO),
        "apartamentos": len(apartamento_por_clave),
        "ventas": len(VENTAS_DEMO),
        "pagos": total_pagos,
    }


def mostrar_usuarios_demo():
    print("\nUsuarios de demostracion:")
    for datos in USUARIOS_DEMO:
        print(f"  {datos['rol']:<14} {datos['correo']:<26} {datos['contrasena']}")
    print("Son contraseñas publicas (estan en el README): cambielas o desactive\n"
          "estas cuentas antes de usar el sistema con datos reales.")


def main():
    from app import create_app

    solo_usuarios = "--solo-usuarios" in sys.argv[1:]
    app = create_app()
    with app.app_context():
        try:
            creado = cargar_datos_demo(solo_usuarios=solo_usuarios)
        except BaseConDatos as error:
            print(error)
            return 1
    print("Datos de demostracion cargados:", ", ".join(f"{n} {tabla}" for tabla, n in creado.items()))
    mostrar_usuarios_demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
