"""
tests/test_formato.py
---------------------
Pruebas unitarias (pytest) de utils/formato.py.

  CP-13  Formato de pesos colombianos mostrado en ventas y pagos
"""

import pytest

from utils.formato import formato_pesos


# CP-13: los valores se muestran como $350.000.000 (punto de miles, sin decimales)
@pytest.mark.parametrize("valor, esperado", [
    (350000000, "$350.000.000"),
    ("1500000", "$1.500.000"),
    (0, "$0"),
    (None, "$0"),
])
def test_cp13_formato_pesos(valor, esperado):
    assert formato_pesos(valor) == esperado
