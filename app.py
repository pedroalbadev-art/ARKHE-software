"""
app.py
------
Punto de entrada de la aplicacion ARKHE (ERP inmobiliario).

Registra TODOS los modulos construidos como blueprints de Flask:
  - Dashboard (página de inicio)
  - Clientes (GA7-220501096-AA3-EV01)
  - Usuarios (GA7-220501096-AA3-EV02)
  - Proyectos (GA7-220501096-AA5-EV03)
  - Apartamentos (GA7-220501096-AA5-EV03)
  - Ventas (GA7-220501096-AA5-EV03)
  - Pagos (GA7-220501096-AA5-EV03)
  - API REST /api (GA7-220501096-AA5-EV03)

Este archivo cierra la evidencia GA7-220501096-AA5-EV03 "Diseño y desarrollo de
servicios web - proyecto" con los 4 módulos finales construidos + Dashboard.

Para ejecutar el proyecto (con el entorno virtual activo y las
dependencias de requirements.txt instaladas):
    python app.py

Los módulos están organizados por carpetas:
  - models/        : Definición de modelos SQLAlchemy (ORM)
  - routes/        : Blueprints con CRUD y lógica de negocio
  - templates/     : Templates HTML por módulo
  - static/        : CSS y assets estáticos
  - utils/         : Funciones utilitarias compartidas
"""

from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFError, CSRFProtect

from config import Config
from models import db
from routes.dashboard import dashboard_bp
from routes.clientes import clientes_bp
from routes.usuarios import usuarios_bp
from routes.proyectos import proyectos_bp
from routes.apartamentos import apartamentos_bp
from routes.ventas import ventas_bp
from routes.pagos import pagos_bp
from routes.api import api_bp
from routes.auth import auth_bp
from utils.seguridad import es_api, exigir_sesion, puede, puede_cambiar_estado, usuario_actual

# Content Security Policy: le dice al navegador de donde puede cargar
# cada tipo de recurso. Es una segunda barrera contra el XSS: aunque un
# dato malicioso llegara a una pagina, el navegador no lo ejecutaria.
#   default-src 'self'      todo, por defecto, solo desde este servidor.
#   script-src 'self'       solo archivos .js propios: se bloquea cualquier
#                           <script> escrito en la pagina y los onclick="".
#   style-src ... inline    hojas de estilo propias y atributos style=""
#                           (el grafico del dashboard fija el alto de cada
#                           barra con style; un estilo no ejecuta codigo).
#   img-src 'self' data:    imagenes propias.
#   object-src 'none'       sin complementos del navegador.
#   base-uri / form-action  los formularios solo envian a este servidor.
#   frame-ancestors 'none'  la app no se incrusta en otro sitio.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])

# Extension de proteccion CSRF (Flask-WTF). Se crea aqui y se conecta a
# la app dentro de create_app(), igual que `db`.
csrf = CSRFProtect()


def create_app(clase_config=Config):
    """Crea y configura la aplicacion Flask (patron "application
    factory").

    Se usa una funcion en vez de crear la app directamente a nivel de
    modulo porque asi es mas facil crear varias instancias de la
    aplicacion sin que se interfieran entre si (por ejemplo, una
    instancia para desarrollo y otra para pruebas automatizadas).

    `clase_config` es la clase de configuracion a usar. Por defecto es
    Config (MySQL, datos del .env); las pruebas pasan otra que apunta a
    una base temporal (ver tests/conftest.py), para no tocar ARKHE_V1.
    """
    app = Flask(__name__)
    app.config.from_object(clase_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "Falta SECRET_KEY en el archivo .env. Genere una con:\n"
            '    python -c "import secrets; print(secrets.token_hex(32))"\n'
            "y agreguela al .env como SECRET_KEY=<valor generado>."
        )

    # Conecta la extension Flask-SQLAlchemy con esta instancia de la app.
    db.init_app(app)

    # Autenticacion: antes de CADA peticion se comprueba que haya sesion
    # (ver utils/seguridad.py). Solo el login y los archivos estaticos
    # quedan abiertos.
    app.before_request(exigir_sesion)

    # Deja disponible {{ usuario_actual }} en todas las plantillas (el
    # encabezado muestra el nombre, el rol y el boton "Cerrar sesion").
    # Tambien deja {{ puede('ventas', 'eliminar') }} para que las
    # plantillas oculten los botones que el rol no puede usar. Ocultar
    # es solo comodidad: quien protege de verdad es rol_requerido.
    @app.context_processor
    def _datos_de_sesion():
        try:
            usuario = usuario_actual()
        except Exception:
            # Si la base de datos no responde, la pagina de error debe
            # poder mostrarse igual (sin datos de usuario).
            usuario = None
        return {
            "usuario_actual": usuario,
            "puede": lambda modulo, accion: puede(usuario, modulo, accion),
            "puede_cambiar_estado": lambda cuenta: puede_cambiar_estado(usuario, cuenta),
        }

    # Proteccion CSRF: todo POST de un formulario debe traer el token
    # oculto csrf_token (ver las plantillas). Se activa aqui para TODA la
    # app, asi un formulario nuevo queda protegido sin recordar nada mas.
    csrf.init_app(app)

    # Cabeceras de seguridad en todas las respuestas:
    #  - X-Frame-Options: la app no se puede incrustar en un <iframe> de
    #    otro sitio (evita que la "disfracen" para robar clics).
    #  - X-Content-Type-Options: el navegador no adivina el tipo de un
    #    archivo; respeta el que declara el servidor.
    #  - Referrer-Policy: no se envia la direccion interna a otros sitios.
    @app.after_request
    def _cabeceras_de_seguridad(respuesta):
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("Referrer-Policy", "same-origin")
        respuesta.headers.setdefault("Content-Security-Policy", CSP)
        return respuesta

    # ---- Paginas de error ----
    # Cada error responde JSON si la peticion es de la API y una pagina
    # con el estilo del sistema si es de una pantalla. Ninguna muestra
    # detalles tecnicos: el detalle queda en el registro del servidor.
    def _error(codigo, titulo, mensaje, mensaje_api=None):
        if es_api():
            return jsonify(error=mensaje_api or mensaje), codigo
        return render_template("errores/error.html", codigo=codigo,
                               titulo=titulo, mensaje=mensaje), codigo

    # 403: hay sesion, pero el rol no tiene permiso (rol_requerido).
    @app.errorhandler(403)
    def _sin_permiso(_error_recibido):
        return _error(403, "Acceso no permitido",
                      "Su rol no tiene permiso para realizar esta acción.",
                      "Su rol no tiene permiso para realizar esta accion.")

    @app.errorhandler(404)
    def _no_encontrado(_error_recibido):
        return _error(404, "Página no encontrada",
                      "La página o el registro que busca no existe o fue eliminado.",
                      "La ruta o el registro solicitado no existe.")

    # 400 por token CSRF ausente, vencido o que no coincide.
    @app.errorhandler(CSRFError)
    def _csrf_invalido(_error_recibido):
        return _error(400, "Formulario vencido",
                      "El formulario venció o no es válido. Vuelva a la página "
                      "anterior, recárguela e intente de nuevo.")

    # 500: cualquier error no previsto. Se deshace la transaccion a
    # medias y se registra el detalle; al usuario solo se le avisa.
    @app.errorhandler(500)
    def _error_interno(_error_recibido):
        db.session.rollback()
        return _error(500, "Error inesperado",
                      "Ocurrió un error inesperado. Intente de nuevo; si el "
                      "problema continúa, avise al administrador.",
                      "Error interno del servidor.")

    # Registra los blueprints (grupos de rutas) de cada modulo.
    # Login y logout (/login, /logout) y el dashboard se registran sin
    # url_prefix; el dashboard es la raíz (/).
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    # El resto de módulos tienen su prefijo
    app.register_blueprint(clientes_bp, url_prefix="/clientes")
    app.register_blueprint(usuarios_bp, url_prefix="/usuarios")
    app.register_blueprint(proyectos_bp, url_prefix="/proyectos")
    app.register_blueprint(apartamentos_bp, url_prefix="/apartamentos")
    app.register_blueprint(ventas_bp, url_prefix="/ventas")
    app.register_blueprint(pagos_bp, url_prefix="/pagos")

    # API REST (respuestas JSON) para consumir los mismos datos desde
    # otros sistemas o desde Postman. Ver routes/api.py.
    app.register_blueprint(api_bp, url_prefix="/api")

    # La API queda exenta del token CSRF: no usa formularios HTML. Solo
    # acepta cuerpos JSON (un formulario de otro sitio no puede
    # enviarlos) y la cookie de sesion va con SameSite=Lax, asi que el
    # navegador no la adjunta en peticiones POST/PUT/DELETE que vengan
    # de otro sitio. Sigue exigiendo sesion y rol.
    csrf.exempt(api_bp)

    # Respuestas JSON en el orden en que se definen los campos y con
    # tildes legibles (sin convertirlas a \u00e1, etc.).
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    return app


if __name__ == "__main__":
    # La app se crea aqui (y no a nivel de modulo) para que importar
    # este archivo desde las pruebas no abra una conexion a MySQL.
    # El modo depuracion sale del .env (FLASK_DEBUG=1) y esta apagado
    # por defecto: con el encendido, el depurador permite ejecutar
    # codigo desde el navegador, asi que nunca debe quedar activo en
    # un servidor al que entren otras personas.
    app = create_app()
    app.run(debug=app.config["DEBUG"])
