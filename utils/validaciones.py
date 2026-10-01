"""
utils/validaciones.py (v2)
---------------------------
Funciones de validacion de contenido, reutilizadas por todos los modulos.

Actualizado 2026-09-30 (GA7-AA5-EV03):
  - Agregada validar_solo_letras() para ciudad (solo letras y espacios)
"""

import re

# Letras (con tildes y enie), espacios: para nombre y apellido.
PATRON_SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜáéíóúüÑñ ]+$")

# Formato de correo simple: algo@algo.algo, sin espacios.
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ROLES_VALIDOS = {"Administrador", "Vendedor", "Gerente"}
ESTADOS_VALIDOS = {"activo", "inactivo"}


def validar_no_vacio(valor):
    """
    Valida que un campo no esté vacío.
    Retorna True si el valor tiene contenido después de .strip()
    """
    return bool((valor or "").strip())


def validar_lengitud(valor, min_len=0, max_len=None):
    """
    Valida la longitud de un campo.

    Args:
        valor: el string a validar
        min_len: longitud mínima (por defecto 0)
        max_len: longitud máxima (por defecto None = sin límite)

    Retorna True si la longitud está dentro del rango
    """
    valor = (valor or "").strip()
    longitud = len(valor)

    if max_len is not None:
        return min_len <= longitud <= max_len
    else:
        return longitud >= min_len


def validar_solo_letras(valor):
    """
    Valida que un campo contenga SOLO letras y espacios.
    Rechaza números y caracteres especiales.
    Usado para ciudad, campos de nombre, etc.
    """
    valor = (valor or "").strip()
    return bool(valor) and bool(PATRON_SOLO_LETRAS.match(valor))


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


# ---------------------------------------------------------------------
# Conversores agregados en GA7-AA5-EV03 (Proyectos, Apartamentos,
# Ventas, Pagos). Cada uno devuelve el valor convertido o None si el
# texto recibido del formulario no es valido, para que las rutas puedan
# validar sin repetir bloques try/except en cada campo.
# ---------------------------------------------------------------------

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Numero de apartamento: letras, numeros, guion y espacios (ej. "301", "Torre A-502").
PATRON_NUMERO_APTO = re.compile(r"^[A-Za-z0-9\- ]+$")


def a_entero(valor):
    """'3' -> 3. Texto vacio, decimal o con letras -> None."""
    try:
        return int(str(valor).strip())
    except (ValueError, TypeError):
        return None


def a_decimal(valor):
    """'350000000.50' -> Decimal. Acepta solo numeros con punto decimal
    (sin separadores de miles). Texto invalido -> None."""
    try:
        numero = Decimal(str(valor).strip())
    except (InvalidOperation, ValueError, TypeError):
        return None
    return numero if numero.is_finite() else None


def a_fecha(valor):
    """'2026-09-30' (formato de <input type="date">) -> date. Invalido -> None."""
    try:
        return datetime.strptime((valor or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def es_fecha_futura(fecha):
    return fecha > date.today()


def es_numero_apto_valido(valor):
    valor = (valor or "").strip()
    return bool(valor) and bool(PATRON_NUMERO_APTO.match(valor))


# Tope para columnas DECIMAL(15,2): 13 digitos enteros.
MAXIMO_DECIMAL_15_2 = Decimal("9999999999999.99")
