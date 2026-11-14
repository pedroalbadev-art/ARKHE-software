# docs/

Documentación de apoyo. La documentación principal del sistema es el `README.md` de la raíz.

| Archivo o carpeta | Qué contiene |
|---|---|
| `ARKHE_API.postman_collection.json` | Colección de Postman para probar la API REST: 36 peticiones. La primera inicia sesión; las demás crean, consultan, actualizan y eliminan cada recurso, e incluyen casos de error (400, 404 y 409). |
| `evidencias/` | Documentos de entregas académicas anteriores. Se conservan como registro histórico y describen el proyecto tal como estaba en ese momento, no su estado actual. |

## Cómo usar la colección de Postman

1. Con el servidor encendido (`python app.py`), importe el archivo en Postman.
2. Abra la colección, pestaña **Variables**, y escriba el correo y la contraseña de un Administrador activo en `correo_login` y `contrasena_login`, **solo en la columna "Current value"**. Ese valor no se exporta, así que ninguna contraseña queda en el repositorio.
3. Ejecute la colección completa con el *Runner*.

La última carpeta elimina todo lo que la colección creó, de modo que la base queda como estaba.

Si un cambio modifica el contrato de la API (rutas, cuerpos o códigos de respuesta), hay que actualizar esta colección en el mismo cambio.

## evidencias/

| Archivo | Qué es |
|---|---|
| `INSTRUCCIONES_ENTREGA.txt` | Lista de verificación de la evidencia GA7-220501096-AA5-EV03. Sus pasos corresponden a una versión anterior, sin inicio de sesión. |
| `enlace_repositorio.txt` | Enlace al repositorio y relación de evidencias desarrolladas en él. |
