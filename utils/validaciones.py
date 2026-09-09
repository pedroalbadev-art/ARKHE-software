"""
utils/validaciones.py
----------------------
Funciones de validacion de contenido, reutilizadas por routes/clientes.py
y routes/usuarios.py (y por los modulos que se agreguen despues, como
Proyectos). Se centralizan aqui en vez de repetir la misma logica en
cada archivo de rutas, siguiendo el principio DRY (no te repitas) -- el
mismo criterio que ya se aplico para no repetir estilos CSS entre
modulos.

Contexto (evidencia GA7-220501096-AA3-EV02): antes de esta evidencia,
los formularios de ARKHE solo validaban con el atributo "required" del
HTML (que un dato no venga vacio) y con las restricciones NOT NULL /
UNIQUE de la base de datos. Eso protege contra campos vacios, pero no
contra datos con formato invalido (ej. un correo sin "@", un documento
con letras). Estas funciones cierran esa brecha en el backend, que es
la capa que de verdad protege la base de datos (la validacion HTML es
solo la primera linea de defensa, un usuario tecnico la puede saltar).

Cada funcion "es_..." devuelve True/False y no lanza excepciones ante
un valor vacio o None -- así se puede usar directamente sobre datos
que vienen de request.form.get(...), que pueden no existir.
"""

import re

# Letras (con tildes y enie), espacios: para nombre y apellido.
PATRON_SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜáéíóúüÑñ ]+$")

# Formato de correo simple: algo@algo.algo, sin espacios.
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ROLES_VALIDOS = {"Administrador", "Vendedor", "Gerente"}
ESTADOS_VALIDOS = {"activo", "inactivo"}


def es_texto_valido(valor):
    """Solo letras y espacios, no vacio. Usado para nombre y apellido
    (rechaza numeros y caracteres especiales, ej. 'Toby$')."""
    valor = (valor or "").strip()
    return bool(valor) and bool(PATRON_SOLO_LETRAS.match(valor))


def es_correo_valido(valor):
    """Formato basico de correo electronico."""
    valor = (valor or "").strip()
    return bool(valor) and bool(PATRON_CORREO.match(valor))


def es_solo_digitos(valor, minimo, maximo):
    """Solo numeros, con una longitud entre minimo y maximo digitos.
    Usado como base para documento y telefono."""
    valor = (valor or "").strip()
    return valor.isdigit() and minimo <= len(valor) <= maximo


def es_documento_valido(valor):
    return es_solo_digitos(valor, minimo=6, maximo=15)


def es_telefono_valido(valor):
    return es_solo_digitos(valor, minimo=7, maximo=15)


def es_contrasena_valida(valor, minimo=8):
    """Longitud minima. La contraseña en si (texto plano) solo pasa
    por esta funcion antes de ser hasheada -- nunca se guarda tal
    cual en la base de datos (ver models/usuario.py)."""
    return bool(valor) and len(valor) >= minimo


def es_rol_valido(valor):
    """El campo `rol` en la base de datos es VARCHAR libre (no un
    ENUM de MySQL): la lista de valores permitidos se controla aqui,
    en el codigo Python, no en el motor de la base de datos."""
    return valor in ROLES_VALIDOS


def es_estado_valido(valor):
    return valor in ESTADOS_VALIDOS
