"""
scripts/cambiar_contrasena.py
-----------------------------
Cambia la contraseña de UN usuario existente, desde la consola. Sirve
para recuperar el acceso cuando nadie recuerda una contraseña (las
contraseñas se guardan como hash y no se pueden "ver" ni recuperar).

Uso (en la raiz del proyecto, con el entorno virtual activo):
    python scripts/cambiar_contrasena.py

Solo modifica la columna `contrasena` del usuario indicado. No crea
usuarios ni toca ningun otro dato.
"""

import sys
from getpass import getpass
from pathlib import Path

# Permite importar app, models y utils aunque el script este en scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from models import db  # noqa: E402
from models.usuario import Usuario  # noqa: E402
from utils.validaciones import es_contrasena_valida  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        correo = input("Correo del usuario: ").strip()
        # Misma busqueda que el login: sin distinguir mayusculas.
        usuario = Usuario.query.filter(db.func.lower(Usuario.correo) == correo.lower()).first()
        if usuario is None:
            print(f"No existe ningun usuario con el correo '{correo}'. No se cambio nada.")
            return 1

        print(f"Usuario encontrado: {usuario.nombre_completo} ({usuario.rol}, {usuario.estado})")

        # getpass lee del teclado sin mostrar lo que se escribe.
        nueva = getpass("Nueva contraseña (no se muestra al escribir): ")
        confirmacion = getpass("Repita la nueva contraseña: ")

        if nueva != confirmacion:
            print("Las contraseñas no coinciden. No se cambio nada.")
            return 1
        # La misma regla que usan el formulario de usuarios y la API.
        if not es_contrasena_valida(nueva):
            print("Contraseña no valida: minimo 8 caracteres, sin espacios "
                  "al inicio ni al final. No se cambio nada.")
            return 1

        usuario.establecer_contrasena(nueva)  # guarda el hash, no el texto
        db.session.commit()

        print(f"Contraseña cambiada para {usuario.nombre_completo} <{usuario.correo}>.")
        if usuario.estado != "activo":
            print("Aviso: este usuario esta inactivo y no podra iniciar sesion.")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado. No se cambio nada.")
        sys.exit(1)
