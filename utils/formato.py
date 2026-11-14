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


# Los metodos de pago se guardan en la base (y los recibe la API) sin
# tilde: "Tarjeta de credito". Cambiar el valor guardado obligaria a
# modificar los pagos ya registrados y el contrato de la API, asi que el
# dato se deja igual y solo se "traduce" en el momento de mostrarlo.
ETIQUETAS_METODO_PAGO = {
    "Tarjeta de credito": "Tarjeta de crédito",
    "Tarjeta debito": "Tarjeta débito",
    "Credito hipotecario": "Crédito hipotecario",
}


def etiqueta_metodo(valor):
    """'Tarjeta de credito' -> 'Tarjeta de crédito'. Un metodo que no
    este en la tabla (por ejemplo 'Efectivo') se muestra tal cual."""
    return ETIQUETAS_METODO_PAGO.get(valor, valor)
