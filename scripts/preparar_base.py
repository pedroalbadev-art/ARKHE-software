"""
scripts/preparar_base.py
------------------------
Segunda parte de la instalacion (la lanza instalar.ps1, pero tambien se
puede ejecutar a mano con el entorno virtual activo):

    python scripts/preparar_base.py

Que hace, en orden:
  1. Lee el .env si existe; si no, pregunta los datos de conexion a MySQL
     y el nombre de la base (la contraseña no se muestra al escribirla).
  2. Se conecta a MySQL y comprueba si esa base YA EXISTE. Si existe, se
     detiene con un mensaje y no cambia nada.
  3. Escribe el .env con una SECRET_KEY nueva (solo si no habia .env).
  4. Crea la base vacia y ejecuta database/esquema.sql (las 6 tablas).
  5. Carga los datos de demostracion (scripts/datos_demo.py).

Reglas de seguridad:
  - NUNCA modifica ni borra una base que ya exista: no hay ningun DROP en
    este archivo, y la base se crea con CREATE DATABASE (sin IF NOT
    EXISTS), que falla si el nombre ya esta en uso.
  - NUNCA sobrescribe un .env existente.

El SQL se ejecuta con PyMySQL (la misma libreria que usa la aplicacion),
asi no hace falta tener mysql.exe en el PATH de Windows.
"""

import os
import re
import secrets
import sys
from getpass import getpass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ENV = RAIZ / ".env"
RUTA_ESQUEMA = RAIZ / "database" / "esquema.sql"
CLAVES_CONEXION = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")

# Permite importar app, models y scripts.datos_demo desde scripts/.
sys.path.insert(0, str(RAIZ))


# ---------------------------------------------------------------------
# Funciones sin efectos (se prueban en tests/test_instalacion.py)
# ---------------------------------------------------------------------
def nombre_base_valido(nombre):
    """Solo letras, numeros y guion bajo (maximo 64, el limite de MySQL).
    El nombre de una base no se puede pasar como parametro de una
    consulta, asi que se valida aqui antes de escribirlo en el SQL."""
    return bool(re.fullmatch(r"[A-Za-z0-9_]{1,64}", nombre or ""))


def linea_env(clave, valor):
    """CLAVE="valor", entre comillas dobles para que un '#' o un espacio
    en la contraseña no se interprete como comentario. Las barras y las
    comillas del valor se escapan."""
    escapado = str(valor).replace("\\", "\\\\").replace('"', '\\"')
    return f'{clave}="{escapado}"'


def contenido_env(datos, secret_key):
    """Texto completo del archivo .env."""
    lineas = [
        "# Archivo generado por la instalacion (scripts/preparar_base.py).",
        "# Contiene la contraseña de MySQL y la clave de sesion: NO se sube a GitHub.",
        "",
    ]
    lineas += [linea_env(clave, datos[clave]) for clave in CLAVES_CONEXION]
    lineas += [
        "",
        "# Clave con la que Flask firma la sesion. Generada al azar en la instalacion.",
        linea_env("SECRET_KEY", secret_key),
        "",
        "# 1 activa el modo depuracion. Solo para desarrollo en su propio equipo.",
        "FLASK_DEBUG=0",
        "",
    ]
    return "\n".join(lineas)


def dividir_sql(texto):
    """Separa un archivo .sql en sentencias. Quita las lineas de
    comentario (-- ...) y corta en cada ';' de fin de linea."""
    sin_comentarios = "\n".join(
        linea for linea in texto.splitlines() if not linea.lstrip().startswith("--")
    )
    return [parte.strip() for parte in re.split(r";[ \t]*(?:\n|$)", sin_comentarios) if parte.strip()]


# ---------------------------------------------------------------------
# Acceso a MySQL
# ---------------------------------------------------------------------
def conectar(datos, base=None):
    import pymysql

    return pymysql.connect(
        host=datos["DB_HOST"], port=int(datos["DB_PORT"]), user=datos["DB_USER"],
        password=datos["DB_PASSWORD"], database=base, charset="utf8mb4",
    )


def base_existe(conexion, nombre):
    """Consulta de solo lectura: ¿hay una base con ese nombre?"""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s", (nombre,)
        )
        return cursor.fetchone() is not None


def crear_base_y_tablas(datos):
    nombre = datos["DB_NAME"]
    sentencias = dividir_sql(RUTA_ESQUEMA.read_text(encoding="utf-8"))

    conexion = conectar(datos)
    try:
        with conexion.cursor() as cursor:
            # Sin IF NOT EXISTS a proposito: si la base apareciera entre la
            # comprobacion y este punto, MySQL lo rechaza y no se toca.
            cursor.execute(f"CREATE DATABASE `{nombre}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
    finally:
        conexion.close()

    conexion = conectar(datos, base=nombre)
    try:
        with conexion.cursor() as cursor:
            for sentencia in sentencias:
                cursor.execute(sentencia)
        conexion.commit()
    finally:
        conexion.close()
    return len(sentencias)


# ---------------------------------------------------------------------
# Preguntas por consola
# ---------------------------------------------------------------------
def preguntar(texto, por_defecto):
    respuesta = input(f"  {texto} [{por_defecto}]: ").strip()
    return respuesta or por_defecto


def pedir_datos():
    print("\nDatos de conexion a MySQL (Enter acepta el valor entre corchetes):")
    datos = {
        "DB_HOST": preguntar("Servidor", "localhost"),
        "DB_PORT": preguntar("Puerto", "3306"),
        "DB_USER": preguntar("Usuario", "root"),
        "DB_PASSWORD": getpass("  Contraseña (no se muestra al escribir): "),
    }
    while True:
        datos["DB_NAME"] = preguntar("Nombre de la base de datos NUEVA", "ARKHE_DEMO")
        if nombre_base_valido(datos["DB_NAME"]):
            return datos
        print("  Nombre no valido: use solo letras, numeros y guion bajo (sin espacios).")


def leer_env_existente():
    from dotenv import dotenv_values

    valores = dotenv_values(RUTA_ENV)
    faltan = [clave for clave in CLAVES_CONEXION if not valores.get(clave) and clave != "DB_PASSWORD"]
    if faltan:
        raise SystemExit(f"El archivo .env existe pero le faltan: {', '.join(faltan)}. "
                         "Corrijalo a mano (ver .env.example); no se modifico nada.")
    datos = {clave: valores.get(clave) or "" for clave in CLAVES_CONEXION}
    if not nombre_base_valido(datos["DB_NAME"]):
        raise SystemExit("El DB_NAME del .env no es valido (solo letras, numeros y guion bajo).")
    return datos


def explicar_error_de_conexion(error):
    codigo = error.args[0] if getattr(error, "args", None) else None
    print("\nNo se pudo conectar a MySQL. No se modifico nada.")
    if codigo == 1045:
        print("  Usuario o contraseña incorrectos.")
    elif codigo in (2003, 2002):
        print("  El servidor no responde: revise que MySQL este encendido y el servidor y puerto.")
    elif codigo == 1044:
        print("  Ese usuario de MySQL no tiene permiso para crear bases de datos.")
    else:
        print(f"  Detalle: {error}")


# ---------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------
def main():
    import pymysql

    os.chdir(RAIZ)
    print("Preparacion de la base de datos")
    print("-------------------------------")

    habia_env = RUTA_ENV.exists()
    if habia_env:
        print("Ya existe un archivo .env: se usan sus datos de conexion y NO se modifica.")
        datos = leer_env_existente()
    else:
        datos = pedir_datos()
    nombre = datos["DB_NAME"]

    # 1) Comprobar ANTES de escribir o crear cualquier cosa.
    try:
        conexion = conectar(datos)
    except (pymysql.MySQLError, RuntimeError) as error:
        explicar_error_de_conexion(error)
        return 1
    try:
        existe = base_existe(conexion, nombre)
    finally:
        conexion.close()

    if existe:
        print(f"\nLa base de datos '{nombre}' YA EXISTE. La instalacion se detiene y no la toca:")
        print("este instalador nunca modifica ni borra una base existente.")
        if habia_env:
            print("Si quiere instalar en una base nueva, cambie DB_NAME en el .env (o quite el .env")
            print("para que el instalador pregunte los datos) y vuelva a ejecutarlo.")
        else:
            print("Vuelva a ejecutar el instalador y elija otro nombre. No se creo el archivo .env.")
        return 2

    # 2) El .env (solo si no existia).
    if not habia_env:
        RUTA_ENV.write_text(contenido_env(datos, secrets.token_hex(32)), encoding="utf-8", newline="\n")
        print("\nArchivo .env creado con una SECRET_KEY nueva.")

    # 3) Base y tablas.
    try:
        tablas = crear_base_y_tablas(datos)
    except pymysql.MySQLError as error:
        print(f"\nError al crear la base o sus tablas: {error}")
        print(f"Si la base '{nombre}' quedo creada a medias, eliminela usted desde MySQL Workbench")
        print("antes de reintentar (el instalador no borra bases).")
        return 1
    print(f"Base de datos '{nombre}' creada con {tablas} tablas.")

    # 4) Datos de demostracion. La app se importa aqui, despues de que
    #    existe el .env, porque config.py lo lee al importarse.
    from app import create_app
    from scripts.datos_demo import cargar_datos_demo, mostrar_usuarios_demo

    app = create_app()
    with app.app_context():
        creado = cargar_datos_demo()
    print("Datos de demostracion cargados:", ", ".join(f"{n} {tabla}" for tabla, n in creado.items()))
    mostrar_usuarios_demo()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInstalacion cancelada.")
        sys.exit(1)
