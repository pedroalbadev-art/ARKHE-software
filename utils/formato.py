"""
utils/formato.py
----------------
Formato de valores para mostrar en pantalla.
"""

from decimal import Decimal


def formato_pesos(valor):
    """350000000 -> '$350.000.000' (pesos colombianos, sin decimales)."""
    try:
        numero = Decimal(valor or 0)
    except Exception:
        return valor
    return "$" + f"{numero:,.0f}".replace(",", ".")
