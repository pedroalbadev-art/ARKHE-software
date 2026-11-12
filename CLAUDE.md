# CLAUDE.md — ARKHE

## Qué es este proyecto
ARKHE es un ERP web de gestión inmobiliaria **de propósito general**: sirve a cualquier empresa que comercializa apartamentos. Es el proyecto formativo de Pedro Alba Méndez (Tecnólogo ADSO, SENA, ficha 3235890). Krea Arquitectura / Tabora House solo es un caso de ejemplo para los datos de prueba: no acoples nada a esa empresa.

- **Alcance:** clientes, usuarios, proyectos, apartamentos, ventas y pagos.
- **Fuera de alcance:** inventario, materiales, obra, proveedores.
- **Flujo de negocio:** Cliente → Proyecto → Apartamento → Venta → Pago. Usuario → gestiona Proyectos.

## Stack (no cambiarlo)
- Python 3.13, Flask, Flask-SQLAlchemy, MySQL 8.4 (base de datos `ARKHE_V1`).
- HTML/CSS/JS con plantillas Jinja.
- `python-dotenv` lee el `.env` (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY). Si un valor tiene `#`, va entre comillas dobles.
- Contraseñas: `werkzeug.security` (`generate_password_hash` / `check_password_hash`).
- Pruebas: pytest 9 (`tests/`) y la colección de Postman `docs/ARKHE_API.postman_collection.json` (35 peticiones con tests).
- **No** introducir frameworks nuevos (nada de FastAPI, Django, React, etc.). Existe una API FastAPI hecha por otro integrante: queda fuera de este repositorio y no se integra.

## Estructura
- `app.py` registra los blueprints. `config.py` lee el `.env`.
- `models/`: un modelo por tabla.
- `routes/`: un blueprint por módulo, más `api.py` (API REST JSON bajo `/api`).
- `utils/validaciones.py`: funciones `validar_datos_*` y validadores reutilizables. Las usan **tanto** los formularios **como** la API: no dupliques validaciones.
- `templates/base.html`: layout común (menú lateral bronce, logo, encabezado). Los demás templates viven en `templates/<modulo>/...`.
  - **Regla:** usa siempre `render_template("<modulo>/archivo.html")`, con el prefijo del módulo. No declares `template_folder` en los blueprints, porque los nombres de plantilla colisionan.
- `static/css/arkhe.css`, `static/img/`: estilos y logos.
- `Mockups/`: los 8 mockups HTML de referencia visual y `logo.jpg`.
- `database/`: copias de referencia del SQL.
- `docs/`: notas técnicas y la colección de Postman.

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

**No** alteres la base de datos sin explicar antes el cambio y recibir la aprobación de Pedro.

## Reglas de negocio ya implementadas (no romperlas)
- Al registrar una venta, el apartamento pasa a "vendido". Si se elimina la venta, vuelve a "disponible".
- Los pagos son abonos:
  - No pueden superar el saldo de la venta.
  - La fecha no puede ser futura ni anterior a la fecha de venta.
  - El método debe estar en la lista permitida.
- El estado de la venta se calcula: pendiente, en-pago o pagada.
- Eliminaciones bloqueadas:
  - proyecto con apartamentos;
  - apartamento con venta;
  - venta con pagos;
  - en la API, además, cliente con proyectos o ventas y usuario que gestiona proyectos.
- Códigos de la API:
  - 400: validación, con `{"errores": [...]}`;
  - 404: registro no encontrado;
  - 409: regla de negocio o dato duplicado.
- La API nunca devuelve la contraseña.

## Comandos (Windows, PowerShell, en la raíz del repo)
- Activar el entorno: `venv\Scripts\activate`
- Ejecutar la app: `python app.py`
- Pruebas: `pytest`
- API: correr la colección de Postman con el Runner (lo hace Pedro).

## Red de seguridad (obligatoria)
Un cambio no se da por terminado si `pytest` no pasa completo o si se rompe algún endpoint cubierto por la colección de Postman (35/35). Si un cambio altera un contrato de la API, avisa a Pedro para actualizar la colección.

## Prioridades del trabajo actual (rama `mejoras-fable`)
1. **Autenticación real:** login por correo con `verificar_contrasena()` (ya existe en el modelo), sesión de Flask, logout, y los usuarios inactivos no pueden entrar.
2. **Roles y protección de rutas:** ninguna página sin sesión.
   - Administrador gestiona usuarios.
   - Vendedor opera clientes y ventas.
   - Gerente consulta.
   - Antes de implementar la matriz de permisos, proponla a Pedro.
3. **Seguridad de formularios:** CSRF, mensajes de error sin datos sensibles, `SECRET_KEY` desde `.env`.
4. **Estética profesional,** siguiendo la paleta dorado/bronce y los mockups:
   - pantalla de login con la marca;
   - dashboard con datos reales (`/api/resumen`);
   - confirmación antes de eliminar;
   - mensajes flash con estilo;
   - estados vacíos;
   - diseño responsive.
5. **Pruebas nuevas** para cada funcionalidad que agregues (login, permisos), en `tests/`.
6. **Cierre:**
   - script de instalación (venv, dependencias, base de datos, datos de demostración);
   - README profesional.

Paleta: `#3A2F20` `#6E5A3C` `#8A6F52` (primario) `#C9A876` `#F3ECDD` `#E4D6BA` `#4A3B26`.

## Cómo trabajar con Pedro
- Pedro es aprendiz y **debe poder sustentar todo**. Antes de una pieza técnica nueva, explica en pocas líneas qué es y por qué se hace así. Al terminar cada tarea, resume qué archivos cambiaron, qué hace cada cambio y cómo verificarlo.
- Antes de un cambio grande, presenta un plan y espera la aprobación. Haz cambios pequeños y verificables, con un commit por tarea. Mensajes de commit en español, con prefijos `feat:`, `fix:`, `docs:`, `test:`, `style:`.
- Usa `git add` con rutas específicas, nunca `git add .`. No subas `.env`, `venv/`, `Claude outputs/` ni `.pytest_cache/`.
- No inventes resultados: solo afirma que algo funciona si lo ejecutaste y lo viste.
- No crees archivos duplicados ni "versiones alternativas" de un módulo. No elimines funcionalidad existente sin autorización.
- Escribe todos los textos de la interfaz y los comentarios en español. En el texto visible, evita repetir "ARKHE" en exceso: usa "el sistema".
