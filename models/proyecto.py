"""
models/proyecto.py
------------------
Modelo SQLAlchemy para la tabla ARKHE_V1.proyectos

Relaciona proyectos con clientes (responsable) y usuarios (gestor).
"""

from models import db


class Proyecto(db.Model):
    """
    Representa un proyecto inmobiliario.

    Relaciones:
      - Pertenece a un Cliente (id_cliente FK, responsable del proyecto)
      - Tiene un Usuario gestor (id_usuario FK, usuario que lo administra)
      - Tiene muchos Apartamentos (relación inversa: apartamentos)
    """

    __tablename__ = "proyectos"

    id_proyecto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey("clientes.id_cliente"), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre_proyecto = db.Column(db.String(150), nullable=False, unique=True)
    direccion = db.Column(db.String(200), nullable=False)
    ciudad = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Relaciones hacia otras tablas
    cliente = db.relationship(
        "Cliente",
        backref="proyectos"
    )
    usuario = db.relationship(
        "Usuario",
        backref="proyectos"
    )

    @property
    def resumen_apartamentos(self):
        """Cuantos apartamentos tiene el proyecto y cuantos hay en cada
        estado: {"total": 12, "disponible": 7, "reservado": 2, "vendido": 3}.

        Es un valor CALCULADO (no una columna): se cuenta cada vez a
        partir de los apartamentos del proyecto, asi nunca queda
        desactualizado y no se duplica informacion en la base (3FN),
        igual que Venta.estado."""
        conteo = {"total": len(self.apartamentos), "disponible": 0, "reservado": 0, "vendido": 0}
        for apartamento in self.apartamentos:
            estado = (apartamento.estado or "").lower()
            if estado in conteo:
                conteo[estado] += 1
        return conteo

    def __repr__(self):
        return f"<Proyecto {self.nombre_proyecto}>"
