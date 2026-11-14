# CLAUDE.md — ARKHE

## Qué es este proyecto
ARKHE es un ERP web de gestión inmobiliaria **de propósito general**: sirve a cualquier empresa que comercializa apartamentos. Es el proyecto formativo de Pedro Alba Méndez (Tecnólogo ADSO, SENA, ficha 3235890). Los datos de demostración son inventados: no acoples nada a una empresa concreta.

- **Alcance:** clientes, usuarios, proyectos, apartamentos, ventas y pagos.
- **Fuera de alcance:** inventario, materiales, obra, proveedores.
- **Flujo de negocio:** Cliente → Proyecto → Apartamento → Venta → Pago. Usuario → gestiona Proyectos.
- **Estado:** las tareas T1 a T6 de la rama `mejoras-fable` están terminadas (autenticación, roles, CSRF, interfaz, instalador y README). El `README.md` es la documentación para personas; este archivo resume lo que hay que respetar al cambiar el código.

## Stack (no cambiarlo)
- Python 3.13, Flask 3.1, Flask-SQLAlchemy con PyMySQL, MySQL 8.4 (base de datos `ARKHE_V1`).
- HTML/CSS/JS propios con plantillas Jinja.
- Flask-WTF, solo por `CSRFProtect`.
- `python-dotenv` lee el `.env` (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY y, opcional, FLASK_DEBUG). Si un valor tiene `#`, va entre comillas dobles.
- Contraseñas: `werkzeug.security` (`generate_password_hash` / `check_password_hash`).
- Versiones fijas (`==`) en `requirements.txt` (ejecución) y `requirements-dev.txt` (agrega pytest).
- Pruebas: pytest 9 (`tests/`) y la colección de Postman `docs/ARKHE_API.postman_collection.json` (36 peticiones, 37 tests).
- **No** introducir frameworks nuevos (nada de FastAPI, Django, React, etc.). Existe una API FastAPI hecha por otro integrante: queda fuera de este repositorio y no se integra.

## Estructura
- `app.py`: `create_app()` registra los blueprints, la exigencia de sesión, CSRF, las cabeceras de seguridad (CSP) y las páginas de error. `config.py` lee el `.env`.
- `models/`: un modelo por tabla.
- `routes/`: un blueprint por módulo, más `auth.py` (login y logout) y `api.py` (API REST JSON bajo `/api`).
- `utils/`:
  - `seguridad.py`: sesión (`usuario_actual`, `exigir_sesion`), matriz `PERMISOS` y decorador `rol_requerido`.
  - `validaciones.py`: funciones `validar_datos_*` y validadores reutilizables. Las usan **tanto** los formularios **como** la API: no dupliques validaciones.
  - `resumen.py`: cifras del dashboard y de `/api/resumen`, calculadas en un solo lugar.
  - `formato.py`: formato de pesos y de métodos de pago.
- `templates/base.html`: layout común (menú lateral bronce, logo, encabezado). `templates/_componentes.html`: macros reutilizables (mensajes flash, estados vacíos). Los demás templates viven en `templates/<modulo>/...`, más `auth/login.html` y `errores/error.html`.
  - **Regla:** usa siempre `render_template("<modulo>/archivo.html")`, con el prefijo del módulo. No declares `template_folder` en los blueprints, porque los nombres de plantilla colisionan.
- `static/css/arkhe.css`, `static/js/arkhe.js`, `static/img/`: estilos, comportamiento común (modales, confirmaciones, alertas) y logos.
- `scripts/`: `preparar_base.py` (crea `.env`, base y datos), `datos_demo.py` y `cambiar_contrasena.py`.
- `instalar.ps1`: instalador para Windows.
- `database/esquema.sql`: estructura de las seis tablas.
- `tests/`: `conftest.py` crea una base SQLite en memoria; las pruebas nunca tocan `ARKHE_V1`.
- `docs/`: colección de Postman y evidencias de entregas anteriores. `Mockups/`: los 8 mockups HTML de referencia visual y `logo.jpg`.

## Esquema real de ARKHE_V1 (verificado; manda sobre cualquier documento)
- **usuarios**: id_usuario PK, nombre, apellido, correo UNIQUE, contrasena (hash, 255), rol, estado (DEFAULT 'activo').
  - Roles válidos: Administrador, Vendedor, Gerente.
  - Estados válidos: activo, inactivo.
  - No existe columna `usuario`: el login es por correo.
- **clientes**: id_cliente PK, nombre, apellido, documento UNIQUE, correo UNIQUE, telefono. No tiene `direccion`.
- **proyectos**: id_proyecto PK, id_cliente FK, id_usuario FK, nombre_proyecto UNIQUE, direccion, ciudad, descripcion (NULL).
- **apartamentos**: id_apartamento PK, id_proyecto FK, numero_apartamento, area_m2, habitaciones, banos, precio, estado (disponible / reservado / vendido).
- **ventas**: id_venta PK, id_cliente FK, id_apartamento FK UNIQUE, fecha_venta, valor_venta. No tiene columna `estado`: el estado se calcula a partir de los pagos.
- **pagos**: id_pago PK, id_venta FK, fecha_pago, monto, metodo_pago.

Ninguna tabla tiene `fecha_creacion` ni `id_usuario` en clientes o ventas. **Antes de modificar o crear un modelo**, verifica contra la base real con esta consulta:

```sql
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT
FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='ARKHE_V1' ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

**No** alteres la base de datos sin explicar antes el cambio y recibir la aprobación de Pedro. Si cambia el esquema, actualiza también `database/esquema.sql`.

## Autenticación y seguridad (ya implementadas; no debilitarlas)
- **Sesión:** login por correo (`/login`, `POST /api/login`). `exigir_sesion` corre antes de cada petición: solo el login y `static` son públicos. La cookie guarda solo el ID; el usuario se lee de la base en cada petición, así que una cuenta inactiva o eliminada pierde el acceso de inmediato. Cookie `HttpOnly`, `SameSite=Lax`, caduca a las 8 horas.
- **`SECRET_KEY`:** solo desde el `.env`; sin ella la aplicación no arranca.
- **CSRF:** `CSRFProtect` cubre toda la app; cada formulario POST lleva `csrf_token`. La API está exenta porque solo acepta JSON.
- **CSP:** `script-src 'self'`. Las plantillas **no** llevan JavaScript en línea (ni `<script>` con código, ni `onclick`): los elementos declaran atributos `data-...` y `static/js/arkhe.js` les da el comportamiento. Los estilos en línea sí están permitidos.
- **Errores:** los mensajes al usuario no muestran detalles técnicos; 403, 404, 500 y CSRF responden con página propia o JSON en la API.

## Roles y permisos
La matriz vive en un solo lugar: `PERMISOS`, en `utils/seguridad.py`. Toda ruta nueva lleva `@rol_requerido(modulo, accion)` (una prueba falla si falta); las plantillas ocultan botones con `puede(modulo, accion)`, pero quien decide es el servidor. La API aplica la misma matriz. **No cambies la matriz sin la aprobación de Pedro.**

| Módulo | Administrador | Vendedor | Gerente |
|---|---|---|---|
| Dashboard | Consulta | Consulta | Consulta |
| Clientes, Ventas, Pagos | Todo | Consulta, crea y edita | Consulta |
| Proyectos, Apartamentos | Todo | Consulta | Consulta |
| Usuarios | Todo | Sin acceso | Consulta; activa y desactiva solo Vendedores |

- **Eliminar** es exclusivo del Administrador en todos los módulos.
- Nadie puede eliminar ni desactivar su propia cuenta, y el sistema nunca queda sin un Administrador activo.

## Reglas de negocio ya implementadas (no romperlas)
- Al registrar una venta, el apartamento pasa a "vendido". Si se elimina la venta, vuelve a "disponible".
- Los pagos son abonos:
  - No pueden superar el saldo de la venta.
  - La fecha no puede ser futura ni anterior a la fecha de venta.
  - El método debe estar en la lista permitida.
- El estado de la venta se calcula: pendiente, en-pago o pagada.
- Eliminaciones bloqueadas, en pantallas y en la API:
  - proyecto con apartamentos;
  - apartamento con venta;
  - venta con pagos;
  - cliente con proyectos o ventas;
  - usuario que gestiona proyectos.
- Códigos de la API:
  - 400: validación, con `{"errores": [...]}`;
  - 401: sin sesión;
  - 403: el rol no tiene permiso;
  - 404: registro no encontrado;
  - 409: regla de negocio o dato duplicado.
- La API nunca devuelve la contraseña.

## Comandos (Windows, PowerShell, en la raíz del repo)
- Instalación completa: `.\instalar.ps1` (crea `venv\`, instala dependencias, crea `.env`, la base y los datos de demostración). Nunca modifica una base existente ni sobrescribe un `.env`. Si Windows lo bloquea: `powershell -ExecutionPolicy Bypass -File .\instalar.ps1`.
- Instalación manual: `python -m venv venv`, `venv\Scripts\activate`, `pip install -r requirements-dev.txt`, `python scripts\preparar_base.py`.
- Activar el entorno: `venv\Scripts\activate`
- Ejecutar la app: `python app.py` (http://localhost:5000)
- Pruebas: `pytest`
- Datos de demostración: `python scripts\datos_demo.py` (solo sobre una base vacía; `--solo-usuarios` agrega los tres usuarios de demostración que falten).
- Restablecer una contraseña: `python scripts\cambiar_contrasena.py`
- API: correr la colección de Postman con el Runner (lo hace Pedro). La primera petición inicia sesión con las variables `correo_login` y `contrasena_login`, que se escriben **solo en "Current value"**: las credenciales nunca se guardan en el JSON de la colección.

## Red de seguridad (obligatoria)
Un cambio no se da por terminado si `pytest` no pasa completo o si se rompe algún endpoint cubierto por la colección de Postman (36 peticiones, 37 tests). Si un cambio altera un contrato de la API, avisa a Pedro para actualizar la colección. Cada funcionalidad nueva lleva sus pruebas en `tests/`.

## Limitaciones conocidas (documentadas en el README; no son errores por corregir sin pedirlo)
- Sin paginación: los listados cargan todo y el buscador filtra en el navegador.
- Sin límite de intentos de inicio de sesión.
- Sin recuperación de contraseña por correo: la restablece un Administrador o `scripts\cambiar_contrasena.py`.
- Sin historial de cambios (quién creó o modificó cada dato).
- Concurrencia: la validación del saldo de un pago no usa bloqueo de fila.
- Un apartamento vendido todavía puede cambiarse de proyecto o de precio. Al eliminar la venta de un apartamento que estaba reservado, queda disponible y no reservado.
- Los métodos de pago se guardan sin tilde ("Tarjeta de credito") y se muestran con tilde; la API usa el valor sin tilde.
- `python app.py` usa el servidor de desarrollo de Flask: para uso real haría falta un servidor de producción y HTTPS.
- El instalador es solo para Windows.
- La CSP permite estilos en línea, por el gráfico del dashboard.

Paleta: `#3A2F20` `#6E5A3C` `#8A6F52` (primario) `#C9A876` `#F3ECDD` `#E4D6BA` `#4A3B26`.

## Cómo trabajar con Pedro
- Pedro es aprendiz y **debe poder sustentar todo**. Antes de una pieza técnica nueva, explica en pocas líneas qué es y por qué se hace así. Al terminar cada tarea, resume qué archivos cambiaron, qué hace cada cambio y cómo verificarlo.
- Antes de un cambio grande, presenta un plan y espera la aprobación. Haz cambios pequeños y verificables, con un commit por tarea. Mensajes de commit en español, con prefijos `feat:`, `fix:`, `docs:`, `test:`, `style:`.
- Usa `git add` con rutas específicas, nunca `git add .`. No subas `.env`, `venv/`, `Claude outputs/` ni `.pytest_cache/`.
- No inventes resultados: solo afirma que algo funciona si lo ejecutaste y lo viste.
- No crees archivos duplicados ni "versiones alternativas" de un módulo. No elimines funcionalidad existente sin autorización.
- Escribe todos los textos de la interfaz y los comentarios en español. En el texto visible, evita repetir "ARKHE" en exceso: usa "el sistema".
