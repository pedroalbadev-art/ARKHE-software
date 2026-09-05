"""
routes/clientes.py
-------------------
Rutas (endpoints) del modulo de Clientes: listar, crear, editar y
eliminar. Es un Blueprint de Flask, es decir, un grupo de rutas
relacionadas que se registra en app.py bajo el prefijo /clientes.

Estandar de codificacion seguido en este archivo:
- Nombres de funcion en snake_case describiendo la accion (verbo +
  sustantivo): listar_clientes, crear_cliente, editar_cliente, etc.
- Cada funcion tiene un docstring explicando que hace y por que.
- Las eliminaciones y modificaciones se hacen por POST, nunca por GET,
  para que un simple enlace (o un rastreador de buscador) no pueda
  borrar o cambiar datos por accidente.
- Los campos nombre, apellido, documento, correo y telefono se leen
  con request.form[...] (no .get) porque la tabla real los exige
  NOT NULL: si llegaran vacios, es mejor que Flask lo rechace de una
  vez con un error claro, en vez de intentar guardar un dato invalido.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import db
from models.cliente import Cliente

# template_folder apunta a la carpeta propia de este modulo dentro de
# templates/ (templates/clientes/), separada de la de otros modulos
# futuros (templates/proyectos/, templates/ventas/, etc.).
clientes_bp = Blueprint(
    "clientes", __name__, template_folder="../templates/clientes"
)


@clientes_bp.route("/")
def listar_clientes():
    """Muestra la tabla con todos los clientes registrados, ordenados
    alfabeticamente por nombre."""
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("lista.html", clientes=clientes)


@clientes_bp.route("/nuevo", methods=["POST"])
def crear_cliente():
    """Recibe los datos del formulario modal 'Nuevo Cliente' (definido
    en lista.html) y crea el registro correspondiente en la base de
    datos."""
    nuevo_cliente = Cliente(
        nombre=request.form["nombre"],
        apellido=request.form["apellido"],
        documento=request.form["documento"],
        correo=request.form["correo"],
        telefono=request.form["telefono"],
    )
    db.session.add(nuevo_cliente)
    db.session.commit()
    flash(f"Cliente '{nuevo_cliente.nombre_completo}' creado correctamente.", "exito")
    return redirect(url_for("clientes.listar_clientes"))


@clientes_bp.route("/<int:id_cliente>/editar", methods=["GET"])
def editar_cliente(id_cliente):
    """Muestra el formulario de edicion precargado con los datos
    actuales del cliente indicado.

    get_or_404 busca el cliente por su llave primaria y, si no existe,
    responde automaticamente con un error 404 en vez de que el
    programa falle con una excepcion sin control.
    """
    cliente = Cliente.query.get_or_404(id_cliente)
    return render_template("formulario.html", cliente=cliente)


@clientes_bp.route("/<int:id_cliente>/editar", methods=["POST"])
def actualizar_cliente(id_cliente):
    """Guarda los cambios enviados desde el formulario de edicion."""
    cliente = Cliente.query.get_or_404(id_cliente)
    cliente.nombre = request.form["nombre"]
    cliente.apellido = request.form["apellido"]
    cliente.documento = request.form["documento"]
    cliente.correo = request.form["correo"]
    cliente.telefono = request.form["telefono"]
    db.session.commit()
    flash(f"Cliente '{cliente.nombre_completo}' actualizado.", "exito")
    return redirect(url_for("clientes.listar_clientes"))


@clientes_bp.route("/<int:id_cliente>/eliminar", methods=["POST"])
def eliminar_cliente(id_cliente):
    """Elimina un cliente de la base de datos.

    Se implementa como POST (disparado desde un formulario con
    confirmacion en el navegador, ver lista.html) y no como GET,
    siguiendo el estandar de codificacion de no realizar operaciones
    que cambian datos a traves de enlaces simples.
    """
    cliente = Cliente.query.get_or_404(id_cliente)
    nombre_eliminado = cliente.nombre_completo
    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente '{nombre_eliminado}' eliminado.", "info")
    return redirect(url_for("clientes.listar_clientes"))
