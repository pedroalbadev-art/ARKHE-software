# app.py
# Punto de entrada de la aplicación ARKHE (ERP inmobiliario).
# Por ahora es solo una prueba para confirmar que el entorno (venv + Flask)
# quedó bien configurado. Los módulos reales (Usuarios, Clientes, Proyectos,
# Apartamentos, Ventas, Pagos) se irán agregando como blueprints en routes/.

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "ARKHE está funcionando. Entorno configurado correctamente."


if __name__ == "__main__":
    # debug=True recarga automáticamente el servidor cuando guardas cambios,
    # útil mientras desarrollas. Se debe desactivar antes de producción.
    app.run(debug=True)
