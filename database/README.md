# database/

Configuración de conexión a MySQL (ARKHE_V1).

**Decisión tomada en la evidencia GA7-220501096-AA3-EV01 (2026-09-05):**
el proyecto usa **Flask-SQLAlchemy** como ORM. La configuración de
conexión vive en `config.py` (raíz del proyecto) y se inicializa junto
con la app en `models/__init__.py` y `app.py`. `db.py`, en esta
carpeta, era la conexión manual inicial (mysql-connector-python) creada
al configurar el entorno; queda como referencia histórica, ya sin uso
— ver el aviso dentro del archivo.

Los scripts SQL oficiales (`ARKHE_V1.sql`) siguen viviendo en tu
carpeta de evidencias GA6 (`ADSO/ADSO/ARKHE`) — aquí solo hay copias de
referencia del esquema de cada tabla a medida que se van codificando
los módulos (ver `clientes_esquema_referencia.sql`).
