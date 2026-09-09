"""
models/usuario.py
------------------
Modelo de datos del Usuario (empleados de la inmobiliaria que usan
ARKHE: Administrador, Vendedor o Gerente).

Representa la tabla `usuarios` de ARKHE_V1, verificada con
`DESCRIBE ARKHE_V1.usuarios;` el 2026-09-09 (evidencia
GA7-220501096-AA3-EV02). Igual que paso con `clientes` en
GA7-AA3-EV01, el diseño original documentado suponia una columna
unica "nombre_completo" y una columna "usuario" (nombre de usuario
para el login) que NO existen en la tabla real: el esquema real
separa nombre/apellido en columnas distintas, y el inicio de sesion
del sistema se hara por `correo` (que ya es UNIQUE), no por un
username aparte.

En esta misma evidencia se agrego ademas la columna `estado`
(no existia en el diseño original ni en la tabla real hasta ahora),
mediante:
    ALTER TABLE ARKHE_V1.usuarios
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'activo' AFTER rol;
para que el rol Gerente pueda desactivar la cuenta de otro usuario
(ej. un Vendedor que ya no trabaja ahi) sin borrar su historial de
proyectos/ventas asociado.

La contraseña NUNCA se guarda en texto plano: se guarda su hash,
generado con werkzeug.security (libreria que ya viene incluida al
instalar Flask, no hay que agregar nada nuevo a requirements.txt). Un
hash es una transformacion de un solo sentido: a partir del hash no
se puede recuperar la contraseña original, pero si se puede verificar
si una contraseña ingresada coincide con el hash guardado.
"""

from werkzeug.security import check_password_hash, generate_password_hash

from models import db


class Usuario(db.Model):
    """Representa un usuario interno de ARKHE (quien administra el
    sistema, gestiona proyectos o registra ventas).

    Corresponde 1 a 1 con la tabla `usuarios` de ARKHE_V1.
    """

    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(150), nullable=False, unique=True)
    contrasena = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="activo")

    @property
    def nombre_completo(self):
        """Combina nombre y apellido para mostrarlos juntos en las
        plantillas, igual que en models/cliente.py."""
        return f"{self.nombre} {self.apellido}"

    def establecer_contrasena(self, contrasena_en_texto_plano):
        """Calcula el hash de la contraseña recibida y lo guarda en
        el atributo `contrasena`, en vez de guardar el texto plano.
        Se usa tanto al crear un usuario como al cambiar su
        contraseña desde el formulario de edicion."""
        self.contrasena = generate_password_hash(contrasena_en_texto_plano)

    def verificar_contrasena(self, contrasena_en_texto_plano):
        """Compara una contraseña en texto plano (la que alguien
        escribiria en un formulario de inicio de sesion) contra el
        hash guardado. Todavia no se usa en ninguna ruta -- queda
        lista para cuando se construya el modulo de login."""
        return check_password_hash(self.contrasena, contrasena_en_texto_plano)

    def __repr__(self):
        """Representacion legible del objeto, util al depurar."""
        return f"<Usuario {self.id_usuario} - {self.nombre_completo} ({self.rol})>"
