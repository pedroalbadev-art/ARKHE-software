"""
routes/api.py
-------------
API REST de ARKHE (GA7-220501096-AA5-EV03).

Expone los mismos datos de las pantallas HTML como servicios web que
reciben y responden JSON, para que otros sistemas (o Postman) puedan
consultarlos y modificarlos.

Recursos (todos bajo el prefijo /api):

    clientes, usuarios, proyectos, apartamentos, ventas, pagos

Para cada recurso:

    GET    /api/<recurso>          Listar todos
    GET    /api/<recurso>/<id>     Consultar uno
    POST   /api/<recurso>          Crear (cuerpo JSON)
    PUT    /api/<recurso>/<id>     Actualizar (cuerpo JSON con todos los campos)
    DELETE /api/<recurso>/<id>     Eliminar

Ademas: GET /api muestra el indice de servicios y GET /api/resumen
devuelve las cifras del dashboard.

Metodos reutilizables: la API NO repite las reglas de validacion. Usa
las mismas funciones validar_datos_* que usan los formularios HTML
(routes/proyectos.py, apartamentos.py, ventas.py, pagos.py, clientes.py
y usuarios.py). Si una regla cambia, cambia en un solo lugar para las
pantallas y para la API.

Codigos de respuesta HTTP:
    200 OK            consulta, actualizacion o eliminacion correcta
    201 Created       registro creado
    400 Bad Request   el cuerpo no es JSON o los datos no pasan las validaciones
    404 Not Found     el registro no existe
    409 Conflict      la operacion rompe una regla de negocio (ej. eliminar
                      una venta que tiene pagos) o un dato unico ya existe
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from models import db
from models.apartamento import Apartamento
from models.cliente import Cliente
from models.pago import Pago
from models.proyecto import Proyecto
from models.usuario import Usuario
from models.venta import Venta
from routes.apartamentos import validar_datos_apartamento
from routes.clientes import _validar_datos_cliente as validar_datos_cliente
from routes.pagos import validar_datos_pago
from routes.proyectos import validar_datos_proyecto
from routes.usuarios import _validar_datos_usuario as validar_datos_usuario
from routes.ventas import validar_datos_venta

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------

def _numero(valor):
    """Decimal de la base de datos -> numero JSON."""
    return float(valor) if isinstance(valor, Decimal) else valor


def _leer_json():
    """Lee el cuerpo JSON de la peticion y lo convierte a un diccionario
    de textos, igual a como llegan los datos de un formulario HTML. Asi
    las funciones validar_datos_* sirven sin cambios para ambos casos.
    Devuelve None si el cuerpo no es un objeto JSON."""
    cuerpo = request.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return None
    return {clave: ("" if valor is None else str(valor)) for clave, valor in cuerpo.items()}


def _error_json():
    return jsonify(errores=["El cuerpo de la peticion debe ser un objeto JSON (Content-Type: application/json)."]), 400


def _errores(lista):
    return jsonify(errores=lista), 400


def _no_existe(recurso, id):
    return jsonify(error=f"{recurso} con id {id} no existe."), 404


def _conflicto(mensaje):
    return jsonify(error=mensaje), 409


def _guardar(objeto=None):
    """Hace commit; si la base de datos rechaza un dato unico duplicado
    devuelve el mensaje de conflicto, si no None."""
    try:
        if objeto is not None:
            db.session.add(objeto)
        db.session.commit()
        return None
    except IntegrityError:
        db.session.rollback()
        return "La base de datos rechazo la operacion: un dato que debe ser unico ya existe."


# ---------------------------------------------------------------------
# Conversion de modelos a diccionarios (lo que se responde en JSON)
# ---------------------------------------------------------------------

def cliente_a_dict(c):
    return dict(id_cliente=c.id_cliente, nombre=c.nombre, apellido=c.apellido,
                nombre_completo=c.nombre_completo, documento=c.documento,
                correo=c.correo, telefono=c.telefono)


def usuario_a_dict(u):
    # La contrasena (ni siquiera su hash) nunca se incluye en la respuesta.
    return dict(id_usuario=u.id_usuario, nombre=u.nombre, apellido=u.apellido,
                nombre_completo=u.nombre_completo, correo=u.correo,
                rol=u.rol, estado=u.estado)


def proyecto_a_dict(p):
    return dict(id_proyecto=p.id_proyecto, nombre_proyecto=p.nombre_proyecto,
                direccion=p.direccion, ciudad=p.ciudad, descripcion=p.descripcion,
                id_cliente=p.id_cliente, cliente=p.cliente.nombre_completo,
                id_usuario=p.id_usuario, gestor=p.usuario.nombre_completo,
                total_apartamentos=len(p.apartamentos))


def apartamento_a_dict(a):
    return dict(id_apartamento=a.id_apartamento, id_proyecto=a.id_proyecto,
                proyecto=a.proyecto.nombre_proyecto,
                numero_apartamento=a.numero_apartamento, area_m2=_numero(a.area_m2),
                habitaciones=a.habitaciones, banos=a.banos, precio=_numero(a.precio),
                estado=a.estado, id_venta=a.venta.id_venta if a.venta else None)


def pago_a_dict(p):
    return dict(id_pago=p.id_pago, id_venta=p.id_venta,
                fecha_pago=p.fecha_pago.isoformat(), monto=_numero(p.monto),
                metodo_pago=p.metodo_pago)


def venta_a_dict(v, con_pagos=False):
    datos = dict(id_venta=v.id_venta, id_cliente=v.id_cliente,
                 cliente=v.cliente.nombre_completo, id_apartamento=v.id_apartamento,
                 apartamento=v.apartamento.numero_apartamento,
                 proyecto=v.apartamento.proyecto.nombre_proyecto,
                 fecha_venta=v.fecha_venta.isoformat(), valor_venta=_numero(v.valor_venta),
                 total_pagado=_numero(v.total_pagado), saldo=_numero(v.saldo),
                 estado=v.estado)
    if con_pagos:
        datos["pagos"] = [pago_a_dict(p) for p in v.pagos]
    return datos


# ---------------------------------------------------------------------
# Indice y resumen
# ---------------------------------------------------------------------

@api_bp.route("", methods=["GET"])
@api_bp.route("/", methods=["GET"])
def indice():
    recursos = ["clientes", "usuarios", "proyectos", "apartamentos", "ventas", "pagos"]
    return jsonify(
        servicio="API REST de ARKHE",
        recursos={r: f"/api/{r}" for r in recursos},
        metodos={
            "GET /api/<recurso>": "Listar",
            "GET /api/<recurso>/<id>": "Consultar uno",
            "POST /api/<recurso>": "Crear (JSON)",
            "PUT /api/<recurso>/<id>": "Actualizar (JSON)",
            "DELETE /api/<recurso>/<id>": "Eliminar",
        },
        extras={"GET /api/resumen": "Cifras del dashboard",
                "GET /api/pagos?venta=<id>": "Pagos de una venta"},
    )


@api_bp.route("/resumen", methods=["GET"])
def resumen():
    ventas = Venta.query.all()
    vendido = sum((Decimal(v.valor_venta) for v in ventas), Decimal("0"))
    recaudado = sum((v.total_pagado for v in ventas), Decimal("0"))
    return jsonify(
        clientes=Cliente.query.count(),
        usuarios=Usuario.query.count(),
        proyectos=Proyecto.query.count(),
        apartamentos={e: Apartamento.query.filter_by(estado=e).count()
                      for e in ("disponible", "reservado", "vendido")},
        ventas={e: sum(1 for v in ventas if v.estado == e)
                for e in ("pendiente", "en-pago", "pagada")},
        valor_vendido=float(vendido),
        recaudado=float(recaudado),
        saldo_por_cobrar=float(vendido - recaudado),
    )


# ---------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------

@api_bp.route("/clientes", methods=["GET"])
def api_listar_clientes():
    return jsonify([cliente_a_dict(c) for c in Cliente.query.order_by(Cliente.id_cliente).all()])


@api_bp.route("/clientes/<int:id>", methods=["GET"])
def api_obtener_cliente(id):
    cliente = db.session.get(Cliente, id)
    return jsonify(cliente_a_dict(cliente)) if cliente else _no_existe("El cliente", id)


def _aplicar_cliente(cliente, datos):
    for campo in ("nombre", "apellido", "documento", "correo", "telefono"):
        setattr(cliente, campo, datos[campo].strip())


@api_bp.route("/clientes", methods=["POST"])
def api_crear_cliente():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores = validar_datos_cliente(datos)
    if errores:
        return _errores(errores)
    cliente = Cliente()
    _aplicar_cliente(cliente, datos)
    conflicto = _guardar(cliente)
    if conflicto:
        return _conflicto("Ya existe un cliente registrado con ese documento o correo.")
    return jsonify(cliente_a_dict(cliente)), 201


@api_bp.route("/clientes/<int:id>", methods=["PUT"])
def api_actualizar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente:
        return _no_existe("El cliente", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores = validar_datos_cliente(datos)
    if errores:
        return _errores(errores)
    _aplicar_cliente(cliente, datos)
    if _guardar():
        return _conflicto("Ya existe un cliente registrado con ese documento o correo.")
    return jsonify(cliente_a_dict(cliente))


@api_bp.route("/clientes/<int:id>", methods=["DELETE"])
def api_eliminar_cliente(id):
    cliente = db.session.get(Cliente, id)
    if not cliente:
        return _no_existe("El cliente", id)
    if cliente.proyectos or cliente.ventas:
        return _conflicto("No se puede eliminar: el cliente tiene proyectos o ventas asociados.")
    db.session.delete(cliente)
    db.session.commit()
    return jsonify(mensaje=f"Cliente {id} eliminado.")


# ---------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------

@api_bp.route("/usuarios", methods=["GET"])
def api_listar_usuarios():
    return jsonify([usuario_a_dict(u) for u in Usuario.query.order_by(Usuario.id_usuario).all()])


@api_bp.route("/usuarios/<int:id>", methods=["GET"])
def api_obtener_usuario(id):
    usuario = db.session.get(Usuario, id)
    return jsonify(usuario_a_dict(usuario)) if usuario else _no_existe("El usuario", id)


@api_bp.route("/usuarios", methods=["POST"])
def api_crear_usuario():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    datos.setdefault("estado", "activo")  # igual que el formulario: inicia activo
    errores = validar_datos_usuario(datos, requiere_contrasena=True)
    if errores:
        return _errores(errores)
    usuario = Usuario(nombre=datos["nombre"].strip(), apellido=datos["apellido"].strip(),
                      correo=datos["correo"].strip(), rol=datos["rol"], estado=datos["estado"])
    usuario.establecer_contrasena(datos["contrasena"])
    if _guardar(usuario):
        return _conflicto("Ya existe un usuario registrado con ese correo.")
    return jsonify(usuario_a_dict(usuario)), 201


@api_bp.route("/usuarios/<int:id>", methods=["PUT"])
def api_actualizar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return _no_existe("El usuario", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    nueva_contrasena = datos.get("contrasena", "").strip()
    errores = validar_datos_usuario(datos, requiere_contrasena=False)
    if errores:
        return _errores(errores)
    usuario.nombre = datos["nombre"].strip()
    usuario.apellido = datos["apellido"].strip()
    usuario.correo = datos["correo"].strip()
    usuario.rol = datos["rol"]
    usuario.estado = datos.get("estado", usuario.estado)
    if nueva_contrasena:
        usuario.establecer_contrasena(nueva_contrasena)
    if _guardar():
        return _conflicto("Ya existe un usuario registrado con ese correo.")
    return jsonify(usuario_a_dict(usuario))


@api_bp.route("/usuarios/<int:id>", methods=["DELETE"])
def api_eliminar_usuario(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        return _no_existe("El usuario", id)
    if usuario.proyectos:
        return _conflicto("No se puede eliminar: el usuario gestiona proyectos. Puede desactivarlo (estado 'inactivo').")
    db.session.delete(usuario)
    db.session.commit()
    return jsonify(mensaje=f"Usuario {id} eliminado.")


# ---------------------------------------------------------------------
# Proyectos
# ---------------------------------------------------------------------

@api_bp.route("/proyectos", methods=["GET"])
def api_listar_proyectos():
    return jsonify([proyecto_a_dict(p) for p in Proyecto.query.order_by(Proyecto.id_proyecto).all()])


@api_bp.route("/proyectos/<int:id>", methods=["GET"])
def api_obtener_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    return jsonify(proyecto_a_dict(proyecto)) if proyecto else _no_existe("El proyecto", id)


@api_bp.route("/proyectos", methods=["POST"])
def api_crear_proyecto():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios = validar_datos_proyecto(datos)
    if errores:
        return _errores(errores)
    proyecto = Proyecto(**limpios)
    if _guardar(proyecto):
        return _conflicto("Ya existe un proyecto con este nombre.")
    return jsonify(proyecto_a_dict(proyecto)), 201


@api_bp.route("/proyectos/<int:id>", methods=["PUT"])
def api_actualizar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _no_existe("El proyecto", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios = validar_datos_proyecto(datos, proyecto)
    if errores:
        return _errores(errores)
    for campo, valor in limpios.items():
        setattr(proyecto, campo, valor)
    if _guardar():
        return _conflicto("Ya existe un proyecto con este nombre.")
    return jsonify(proyecto_a_dict(proyecto))


@api_bp.route("/proyectos/<int:id>", methods=["DELETE"])
def api_eliminar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _no_existe("El proyecto", id)
    if proyecto.apartamentos:
        return _conflicto("No se puede eliminar: el proyecto tiene apartamentos registrados.")
    db.session.delete(proyecto)
    db.session.commit()
    return jsonify(mensaje=f"Proyecto {id} eliminado.")


# ---------------------------------------------------------------------
# Apartamentos
# ---------------------------------------------------------------------

@api_bp.route("/apartamentos", methods=["GET"])
def api_listar_apartamentos():
    consulta = Apartamento.query
    if request.args.get("estado"):
        consulta = consulta.filter_by(estado=request.args["estado"])
    if request.args.get("proyecto"):
        consulta = consulta.filter_by(id_proyecto=request.args.get("proyecto", type=int))
    return jsonify([apartamento_a_dict(a) for a in consulta.order_by(Apartamento.id_apartamento).all()])


@api_bp.route("/apartamentos/<int:id>", methods=["GET"])
def api_obtener_apartamento(id):
    apto = db.session.get(Apartamento, id)
    return jsonify(apartamento_a_dict(apto)) if apto else _no_existe("El apartamento", id)


@api_bp.route("/apartamentos", methods=["POST"])
def api_crear_apartamento():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    datos.setdefault("estado", "disponible")
    errores, limpios = validar_datos_apartamento(datos)
    if errores:
        return _errores(errores)
    apto = Apartamento(**limpios)
    _guardar(apto)
    return jsonify(apartamento_a_dict(apto)), 201


@api_bp.route("/apartamentos/<int:id>", methods=["PUT"])
def api_actualizar_apartamento(id):
    apto = db.session.get(Apartamento, id)
    if not apto:
        return _no_existe("El apartamento", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios = validar_datos_apartamento(datos, apto)
    if errores:
        return _errores(errores)
    for campo, valor in limpios.items():
        setattr(apto, campo, valor)
    _guardar()
    return jsonify(apartamento_a_dict(apto))


@api_bp.route("/apartamentos/<int:id>", methods=["DELETE"])
def api_eliminar_apartamento(id):
    apto = db.session.get(Apartamento, id)
    if not apto:
        return _no_existe("El apartamento", id)
    if apto.venta is not None:
        return _conflicto("No se puede eliminar: el apartamento ya tiene una venta registrada.")
    db.session.delete(apto)
    db.session.commit()
    return jsonify(mensaje=f"Apartamento {id} eliminado.")


# ---------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------

@api_bp.route("/ventas", methods=["GET"])
def api_listar_ventas():
    ventas = Venta.query.order_by(Venta.id_venta).all()
    estado = request.args.get("estado")
    return jsonify([venta_a_dict(v) for v in ventas if not estado or v.estado == estado])


@api_bp.route("/ventas/<int:id>", methods=["GET"])
def api_obtener_venta(id):
    venta = db.session.get(Venta, id)
    return jsonify(venta_a_dict(venta, con_pagos=True)) if venta else _no_existe("La venta", id)


@api_bp.route("/ventas", methods=["POST"])
def api_crear_venta():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios, apartamento = validar_datos_venta(datos)
    if errores:
        return _errores(errores)
    venta = Venta(**limpios)
    apartamento.estado = "vendido"  # misma regla que el formulario HTML
    if _guardar(venta):
        return _conflicto("El apartamento ya tiene una venta registrada.")
    return jsonify(venta_a_dict(venta, con_pagos=True)), 201


@api_bp.route("/ventas/<int:id>", methods=["PUT"])
def api_actualizar_venta(id):
    venta = db.session.get(Venta, id)
    if not venta:
        return _no_existe("La venta", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios, apartamento_nuevo = validar_datos_venta(datos, venta)
    if errores:
        return _errores(errores)
    if venta.id_apartamento != apartamento_nuevo.id_apartamento:
        venta.apartamento.estado = "disponible"
        apartamento_nuevo.estado = "vendido"
    for campo, valor in limpios.items():
        setattr(venta, campo, valor)
    if _guardar():
        return _conflicto("El apartamento ya tiene una venta registrada.")
    return jsonify(venta_a_dict(venta, con_pagos=True))


@api_bp.route("/ventas/<int:id>", methods=["DELETE"])
def api_eliminar_venta(id):
    venta = db.session.get(Venta, id)
    if not venta:
        return _no_existe("La venta", id)
    if venta.pagos:
        return _conflicto("No se puede eliminar: la venta tiene pagos registrados. Elimine primero sus pagos.")
    venta.apartamento.estado = "disponible"
    db.session.delete(venta)
    db.session.commit()
    return jsonify(mensaje=f"Venta {id} eliminada. El apartamento volvio a estar disponible.")


# ---------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------

@api_bp.route("/pagos", methods=["GET"])
def api_listar_pagos():
    consulta = Pago.query
    if request.args.get("venta"):
        consulta = consulta.filter_by(id_venta=request.args.get("venta", type=int))
    return jsonify([pago_a_dict(p) for p in consulta.order_by(Pago.fecha_pago, Pago.id_pago).all()])


@api_bp.route("/pagos/<int:id>", methods=["GET"])
def api_obtener_pago(id):
    pago = db.session.get(Pago, id)
    return jsonify(pago_a_dict(pago)) if pago else _no_existe("El pago", id)


@api_bp.route("/pagos", methods=["POST"])
def api_crear_pago():
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios = validar_datos_pago(datos)
    if errores:
        return _errores(errores)
    pago = Pago(**limpios)
    _guardar(pago)
    return jsonify(pago_a_dict(pago)), 201


@api_bp.route("/pagos/<int:id>", methods=["PUT"])
def api_actualizar_pago(id):
    pago = db.session.get(Pago, id)
    if not pago:
        return _no_existe("El pago", id)
    datos = _leer_json()
    if datos is None:
        return _error_json()
    errores, limpios = validar_datos_pago(datos, pago)
    if errores:
        return _errores(errores)
    for campo, valor in limpios.items():
        setattr(pago, campo, valor)
    _guardar()
    return jsonify(pago_a_dict(pago))


@api_bp.route("/pagos/<int:id>", methods=["DELETE"])
def api_eliminar_pago(id):
    pago = db.session.get(Pago, id)
    if not pago:
        return _no_existe("El pago", id)
    db.session.delete(pago)
    db.session.commit()
    return jsonify(mensaje=f"Pago {id} eliminado.")
