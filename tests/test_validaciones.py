"""
tests/test_validaciones.py
--------------------------
Pruebas unitarias (pytest) de utils/validaciones.py.
Evidencia GA9-220501096-AA1-EV01 - Taller sobre codificacion de modulos.

Cada clase agrupa los casos de prueba de un modulo de ARKHE y cada
caso lleva un ID (CP-xx) para la trazabilidad con la tabla de casos de
prueba del documento:

  CP-01..CP-04  Modulo Clientes   (HU-01 Registrar cliente)
  CP-05..CP-08  Modulo Usuarios   (HU-02 Registrar usuario)
  CP-09..CP-12  Modulo Pagos      (abonos a una venta)

Ejecutar desde la raiz del proyecto (con el venv activo):
    pytest
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from utils.validaciones import (
    a_decimal,
    a_entero,
    a_fecha,
    es_contrasena_valida,
    es_correo_valido,
    es_documento_valido,
    es_estado_valido,
    es_fecha_futura,
    es_rol_valido,
    es_telefono_valido,
    es_texto_valido,
)


# ---------------------------------------------------------------------
# Modulo Clientes (HU-01)
# ---------------------------------------------------------------------
class TestClientes:

    # CP-01: nombre y apellido solo aceptan letras (con tildes y ñ) y espacios
    @pytest.mark.parametrize("valor, esperado", [
        ("María José", True),
        ("Núñez", True),
        ("Toby$", False),
        ("Juan123", False),
        ("   ", False),
        ("", False),
    ])
    def test_cp01_nombre_solo_letras(self, valor, esperado):
        assert es_texto_valido(valor) == esperado

    # CP-02: documento solo digitos, entre 6 y 15
    @pytest.mark.parametrize("valor, esperado", [
        ("1023456789", True),
        ("123456", True),             # limite inferior
        ("12345", False),             # un digito menos
        ("1234567890123456", False),  # 16 digitos
        ("10A3456789", False),        # con letra
    ])
    def test_cp02_documento(self, valor, esperado):
        assert es_documento_valido(valor) == esperado

    # CP-03: correo con formato usuario@dominio.ext
    @pytest.mark.parametrize("valor, esperado", [
        ("cliente@arkhe.com", True),
        ("cliente@arkhe", False),
        ("cliente arkhe@mail.com", False),
        ("", False),
    ])
    def test_cp03_correo(self, valor, esperado):
        assert es_correo_valido(valor) == esperado

    # CP-04: telefono solo digitos, entre 7 y 15
    @pytest.mark.parametrize("valor, esperado", [
        ("3001234567", True),
        ("6011234", True),     # fijo de 7 digitos
        ("300-123", False),
        ("123456", False),
    ])
    def test_cp04_telefono(self, valor, esperado):
        assert es_telefono_valido(valor) == esperado


# ---------------------------------------------------------------------
# Modulo Usuarios (HU-02)
# ---------------------------------------------------------------------
class TestUsuarios:

    # CP-05: contraseña de minimo 8 caracteres
    @pytest.mark.parametrize("valor, esperado", [
        ("Arkhe2026", True),
        ("12345678", True),   # exactamente 8
        ("1234567", False),   # 7 caracteres
        ("", False),
    ])
    def test_cp05_contrasena_longitud(self, valor, esperado):
        assert es_contrasena_valida(valor) == esperado

    # CP-06: una contraseña formada solo por espacios NO debe aceptarse
    def test_cp06_contrasena_solo_espacios(self):
        assert es_contrasena_valida("        ") is False

    # CP-07: solo se aceptan los roles definidos (evita rol inyectado)
    @pytest.mark.parametrize("valor, esperado", [
        ("Administrador", True),
        ("Vendedor", True),
        ("Gerente", True),
        ("SuperAdmin", False),
        ("administrador", False),
    ])
    def test_cp07_rol(self, valor, esperado):
        assert es_rol_valido(valor) == esperado

    # CP-08: estado del usuario activo / inactivo
    @pytest.mark.parametrize("valor, esperado", [
        ("activo", True),
        ("inactivo", True),
        ("bloqueado", False),
    ])
    def test_cp08_estado(self, valor, esperado):
        assert es_estado_valido(valor) == esperado


# ---------------------------------------------------------------------
# Modulo Pagos (conversores usados por routes/pagos.py)
# ---------------------------------------------------------------------
class TestPagos:

    # CP-09: id de la venta debe ser un entero
    @pytest.mark.parametrize("valor, esperado", [
        ("3", 3),
        ("3.5", None),
        ("abc", None),
        ("", None),
    ])
    def test_cp09_id_venta_entero(self, valor, esperado):
        assert a_entero(valor) == esperado

    # CP-10: monto del abono como decimal, sin separadores de miles
    @pytest.mark.parametrize("valor, esperado", [
        ("350000000", Decimal("350000000")),
        ("1500000.50", Decimal("1500000.50")),
        ("1.500.000", None),
        ("abc", None),
        ("NaN", None),
    ])
    def test_cp10_monto_decimal(self, valor, esperado):
        assert a_decimal(valor) == esperado

    # CP-11: fecha en formato AAAA-MM-DD (<input type="date">)
    @pytest.mark.parametrize("valor, esperado", [
        ("2026-09-30", date(2026, 9, 30)),
        ("30/09/2026", None),
        ("2026-02-30", None),   # fecha inexistente
        ("", None),
    ])
    def test_cp11_fecha_pago(self, valor, esperado):
        assert a_fecha(valor) == esperado

    # CP-12: la fecha de pago no puede ser futura
    def test_cp12_fecha_futura(self):
        hoy = date.today()
        assert es_fecha_futura(hoy + timedelta(days=1)) is True
        assert es_fecha_futura(hoy) is False
        assert es_fecha_futura(hoy - timedelta(days=1)) is False
