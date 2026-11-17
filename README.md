# ARKHE — Sistema de gestión inmobiliaria

Aplicación web para empresas que comercializan apartamentos. Permite llevar el ciclo completo de una venta: registrar clientes, crear proyectos y sus apartamentos, vender un apartamento y recibir los pagos hasta saldarlo.

Es de propósito general: no está atada a ninguna empresa en particular. Los datos de demostración son inventados.

**Autor:** Pedro Alba Méndez — Tecnólogo en Análisis y Desarrollo de Software (ADSO), SENA, ficha 3235890.
**Repositorio:** https://github.com/pedroalbadev-art/ARKHE-software

## Contenido

1. [Qué hace el sistema](#qué-hace-el-sistema)
2. [Tecnologías](#tecnologías)
3. [Instalación](#instalación)
4. [Usuarios de demostración](#usuarios-de-demostración)
5. [Roles y permisos](#roles-y-permisos)
6. [Reglas de negocio](#reglas-de-negocio)
7. [API REST](#api-rest)
8. [Pruebas](#pruebas)
9. [Seguridad](#seguridad)
10. [Estructura del proyecto](#estructura-del-proyecto)
11. [Limitaciones conocidas](#limitaciones-conocidas)

## Qué hace el sistema

| Módulo | Para qué sirve |
|---|---|
| Dashboard | Resumen con cifras reales: clientes, proyectos, apartamentos por estado, valor vendido, recaudo, saldo por cobrar y ventas de los últimos seis meses. |
| Clientes | Personas naturales (nombre y apellido): tanto los propietarios o promotores de un proyecto como los compradores. |
| Proyectos | Cada proyecto tiene un cliente propietario o promotor y un usuario gestor. El listado muestra cuántos apartamentos tiene y cuántos están disponibles, reservados y vendidos. |
| Apartamentos | Unidades de un proyecto, con área, habitaciones, baños, precio y estado. |
| Ventas | Venta de un apartamento a un cliente comprador. El estado (pendiente, en pago o pagada) se calcula a partir de los pagos. |
| Pagos | Abonos a una venta, hasta completar su valor. |
| Usuarios | Personas que inician sesión, con su rol y su estado (activo o inactivo). |

El flujo de trabajo es: **Cliente → Proyecto → Apartamento → Venta → Pago**.

Quedan fuera del alcance: inventario, materiales, obra y proveedores.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.13 (funciona desde 3.10) |
| Servidor web | Flask 3.1 |
| Acceso a datos | Flask-SQLAlchemy (ORM) con el driver PyMySQL |
| Base de datos | MySQL 8.4 |
| Interfaz | HTML con plantillas Jinja, CSS y JavaScript propios (sin frameworks) |
| Seguridad | `werkzeug.security` para las contraseñas, Flask-WTF para el token CSRF |
| Pruebas | pytest 9 y una colección de Postman |

Las versiones exactas están en `requirements.txt` y `requirements-dev.txt`.

## Instalación

### Requisitos

- Windows 10 u 11 con PowerShell.
- Python 3.10 o superior, con la opción *Add python.exe to PATH* marcada al instalarlo.
- MySQL 8 encendido y un usuario con permiso para crear bases de datos.

### Instalación automática

En PowerShell, dentro de la carpeta del proyecto:

```powershell
.\instalar.ps1
```

El instalador hace cuatro cosas:

1. Comprueba que Python esté instalado.
2. Crea el entorno virtual `venv\`.
3. Instala las dependencias.
4. Pregunta los datos de conexión a MySQL y el nombre de la base. Luego crea el archivo `.env` con una clave de sesión nueva, crea la base, sus seis tablas y carga los datos de demostración.

**Lo que el instalador nunca hace:**

- No modifica ni borra una base de datos que ya exista. Si el nombre elegido ya está en uso, se detiene con un mensaje y no cambia nada.
- No sobrescribe un archivo `.env` existente: lo usa tal como está.

**Si Windows bloquea el script** con el mensaje *"la ejecución de scripts está deshabilitada en este sistema"*, ejecútelo así. Esto lo permite solo esta vez y no cambia la configuración del equipo:

```powershell
powershell -ExecutionPolicy Bypass -File .\instalar.ps1
```

Si descargó el proyecto como ZIP y Windows lo marca como archivo de internet, desbloquéelo antes con `Unblock-File .\instalar.ps1`.

### Iniciar el sistema

```powershell
venv\Scripts\activate
python app.py
```

Abra http://localhost:5000 e inicie sesión con uno de los [usuarios de demostración](#usuarios-de-demostración).

### Instalación manual

Si prefiere hacerlo paso a paso:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
python scripts\preparar_base.py
```

`scripts\preparar_base.py` es la parte del instalador que crea el `.env`, la base y los datos. Para conectarse a una base que ya tiene, copie `.env.example` como `.env` y complete los valores a mano; si un valor contiene `#`, escríbalo entre comillas dobles.

### Otros scripts

| Comando | Para qué sirve |
|---|---|
| `python scripts\datos_demo.py` | Carga los datos de demostración. Solo funciona sobre una base vacía. |
| `python scripts\datos_demo.py --solo-usuarios` | Agrega únicamente los tres usuarios de demostración que falten, sin tocar los existentes. |
| `python scripts\cambiar_contrasena.py` | Restablece la contraseña de un usuario desde la consola, cuando nadie la recuerda. |

## Usuarios de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@arkhe.example` | `Admin#2026` |
| Vendedor | `vendedor@arkhe.example` | `Vendedor#2026` |
| Gerente | `gerente@arkhe.example` | `Gerente#2026` |

**Estas contraseñas son solo para pruebas.** Están publicadas en este archivo, así que cualquiera las conoce. Antes de usar el sistema con datos reales, cambie la de cada cuenta con:

```powershell
python scripts\cambiar_contrasena.py
```

El script pide el correo del usuario y la contraseña nueva dos veces, sin mostrarla en pantalla. Las cuentas de demostración que no se vayan a usar se pueden desactivar desde el módulo de Usuarios.

Los datos de demostración incluyen además seis clientes, dos proyectos, diez apartamentos, cuatro ventas (una pagada, dos en pago y una pendiente) y seis pagos.

## Roles y permisos

| Módulo | Administrador | Vendedor | Gerente |
|---|---|---|---|
| Dashboard | Consulta | Consulta | Consulta |
| Clientes | Consulta, crea, edita y elimina | Consulta, crea y edita | Consulta |
| Proyectos | Consulta, crea, edita y elimina | Consulta | Consulta |
| Apartamentos | Consulta, crea, edita y elimina | Consulta | Consulta |
| Ventas | Consulta, crea, edita y elimina | Consulta, crea y edita | Consulta |
| Pagos | Consulta, crea, edita y elimina | Consulta, crea y edita | Consulta |
| Usuarios | Consulta, crea, edita, elimina, activa y desactiva | Sin acceso | Consulta; activa y desactiva solo cuentas de Vendedor |

En resumen:

- **Eliminar** es exclusivo del Administrador en todos los módulos.
- El **Vendedor** opera clientes, ventas y pagos.
- El **Gerente** consulta todo y puede activar o desactivar cuentas de Vendedor.

La matriz está definida en un solo lugar (`PERMISOS`, en `utils/seguridad.py`). Cada ruta declara el permiso que exige con `@rol_requerido(módulo, acción)`; el menú y los botones se ocultan según el rol, pero quien decide es siempre el servidor. La API aplica la misma matriz.

Dos reglas protegen las cuentas: nadie puede eliminar ni desactivar la suya, y el sistema nunca puede quedar sin un Administrador activo.

## Reglas de negocio

- Al registrar una venta, el apartamento pasa a *vendido*. Si la venta se elimina, vuelve a *disponible*.
- Un apartamento vendido no puede cambiar de proyecto, de precio ni de estado. El área, las habitaciones y los baños sí se pueden corregir.
- Un apartamento se vende una sola vez.
- Los pagos son abonos: no pueden superar el saldo de la venta, su fecha no puede ser futura ni anterior a la fecha de la venta, y el método debe estar en la lista permitida.
- El estado de una venta no se guarda: se calcula. *Pendiente* sin pagos, *en pago* con abonos parciales y *pagada* con saldo en cero.
- Eliminaciones bloqueadas: un proyecto con apartamentos, un apartamento con venta, una venta con pagos, un cliente con proyectos o ventas, y un usuario que gestiona proyectos.

Todas las validaciones se hacen en el servidor. Los formularios ayudan con `required` y patrones, pero no se confía en ellos.

## API REST

Los mismos datos están disponibles como servicios JSON bajo `/api`, con las mismas validaciones y los mismos permisos que las pantallas.

| Método | Ruta | Acción | Respuesta correcta |
|---|---|---|---|
| POST | `/api/login` | Iniciar sesión | 200 |
| GET | `/api/<recurso>` | Listar | 200 |
| GET | `/api/<recurso>/<id>` | Consultar uno | 200 |
| POST | `/api/<recurso>` | Crear | 201 |
| PUT | `/api/<recurso>/<id>` | Actualizar | 200 |
| DELETE | `/api/<recurso>/<id>` | Eliminar | 200 |
| PUT | `/api/usuarios/<id>/estado` | Activar o desactivar un usuario | 200 |
| GET | `/api/resumen` | Cifras del dashboard | 200 |

Recursos: `clientes`, `usuarios`, `proyectos`, `apartamentos`, `ventas` y `pagos`. Filtros disponibles: `/api/apartamentos?estado=disponible`, `/api/ventas?estado=en-pago` y `/api/pagos?venta=<id>`.

**La API exige sesión.** Primero se llama a `POST /api/login` con `{"correo": "...", "contrasena": "..."}`; la respuesta trae la cookie de sesión, que debe enviarse en las peticiones siguientes.

| Código | Significado |
|---|---|
| 400 | El cuerpo no es JSON o los datos no pasan las validaciones: `{"errores": ["..."]}` |
| 401 | No hay sesión iniciada |
| 403 | El rol no tiene permiso para esa acción |
| 404 | El registro o la ruta no existe |
| 409 | La operación rompe una regla de negocio o un dato único ya existe |

La contraseña de un usuario nunca se devuelve, ni siquiera su hash.

## Pruebas

### pytest

```powershell
venv\Scripts\activate
pytest
```

Son 300 pruebas. No tocan la base de datos real: cada una usa una base temporal en memoria (SQLite) que se crea y se destruye sola.

| Archivo | Qué comprueba |
|---|---|
| `tests/test_validaciones.py`, `tests/test_formato.py` | Validadores y formato de valores. |
| `tests/test_reglas.py` | Reglas de negocio de ventas, pagos, eliminaciones y estado del apartamento. |
| `tests/test_auth.py` | Inicio y cierre de sesión, usuarios inactivos. |
| `tests/test_permisos.py` | La matriz de permisos en pantallas y API. |
| `tests/test_seguridad.py` | Token CSRF, mensajes de error, páginas de error, exigencia de JSON en la API y ausencia de CORS. |
| `tests/test_interfaz.py` | Confirmaciones, mensajes, estados vacíos, accesibilidad, CSP. |
| `tests/test_instalacion.py` | Esquema SQL, datos de demostración e instalador. |
| `tests/test_requisitos.py` | Edición de usuarios y de clientes, validaciones de proyectos, filtros de la API y el script de cambio de contraseña. |

### Postman

1. Con el servidor encendido, importe `docs/ARKHE_API.postman_collection.json` en Postman.
2. Abra la colección, pestaña **Variables**, y escriba el correo y la contraseña de un Administrador activo en `correo_login` y `contrasena_login`, **solo en la columna "Current value"**. Ese valor se queda en su Postman y no se exporta.
3. Ejecute la colección completa con el *Runner*.

La colección tiene 36 peticiones. La primera inicia sesión y Postman conserva la cookie para las demás. Cada petición crea lo que necesita y la última carpeta lo elimina, así que la base queda como estaba.

## Seguridad

- **Contraseñas:** se guarda solo su hash (`werkzeug.security`), nunca el texto.
- **Sesión:** cookie firmada con `SECRET_KEY`, `HttpOnly`, `SameSite=Lax` y con caducidad de ocho horas. Ninguna página se abre sin sesión; un usuario desactivado pierde el acceso en su siguiente petición.
- **CSRF:** todos los formularios llevan un token (Flask-WTF). La API queda exenta porque solo acepta cuerpos con `Content-Type: application/json`, que un formulario de otro sitio no puede enviar, y no tiene CORS habilitado.
- **Concurrencia:** al registrar o editar un pago, y al editar una venta, se bloquea la fila de la venta. Dos operaciones simultáneas sobre la misma venta no pueden dejar los pagos por encima de su valor.
- **XSS:** Jinja escapa todos los datos; las plantillas no llevan JavaScript en línea y la cabecera Content-Security-Policy solo permite scripts propios.
- **Inyección SQL:** todas las consultas pasan por el ORM, con parámetros.
- **Errores:** los mensajes al usuario no muestran detalles técnicos; el detalle queda en el registro del servidor.
- **Secretos:** el archivo `.env` no se sube al repositorio. Sin `SECRET_KEY`, la aplicación no arranca.

## Estructura del proyecto

```
ARKHE-software/
├── app.py                  Crea la aplicación y registra los módulos
├── config.py               Lee la configuración del archivo .env
├── instalar.ps1            Instalador para Windows
├── requirements.txt        Dependencias (versiones fijas)
├── models/                 Un modelo por tabla
├── routes/                 Un módulo por archivo, más auth.py (sesión) y api.py (API REST)
├── utils/
│   ├── seguridad.py        Sesión, matriz de permisos y decoradores
│   ├── validaciones.py     Validadores reutilizables
│   ├── resumen.py          Cifras del dashboard y de /api/resumen
│   └── formato.py          Formato de pesos y de métodos de pago
├── templates/              Plantillas Jinja (base.html y una carpeta por módulo)
├── static/                 arkhe.css, arkhe.js y el logo
├── scripts/                preparar_base.py, datos_demo.py y cambiar_contrasena.py
├── database/esquema.sql    Estructura de las seis tablas
├── tests/                  Pruebas con pytest
├── docs/                   Colección de Postman y documentos de entregas anteriores
├── assets/                 Reservada para material que no forma parte de la aplicación
└── Mockups/                Diseños de referencia de la interfaz
```

### Base de datos

| Tabla | Columnas |
|---|---|
| usuarios | id_usuario, nombre, apellido, correo (único), contrasena (hash), rol, estado |
| clientes | id_cliente, nombre, apellido, documento (único), correo (único), telefono |
| proyectos | id_proyecto, id_cliente, id_usuario, nombre_proyecto (único), direccion, ciudad, descripcion |
| apartamentos | id_apartamento, id_proyecto, numero_apartamento, area_m2, habitaciones, banos, precio, estado |
| ventas | id_venta, id_cliente, id_apartamento (único), fecha_venta, valor_venta |
| pagos | id_pago, id_venta, fecha_pago, monto, metodo_pago |

Varios valores se calculan y no se guardan, para no duplicar información: el nombre completo, el total pagado, el saldo y el estado de una venta, y el conteo de apartamentos por estado de un proyecto.

## Limitaciones conocidas

- **Sin paginación.** Los listados cargan todos los registros; el buscador y los filtros trabajan en el navegador sobre lo ya cargado. Con miles de registros haría falta paginar en el servidor.
- **Sin límite de intentos de inicio de sesión.** No hay bloqueo tras varios intentos fallidos.
- **Sin recuperación de contraseña por correo.** La restablece un Administrador o el script `scripts\cambiar_contrasena.py`.
- **Sin historial de cambios.** Las tablas no registran quién creó o modificó cada dato ni cuándo.
- **El estado reservado no se restaura.** Al anular la venta de un apartamento que estaba reservado, queda disponible y no reservado; si debía seguir reservado, se cambia manualmente.
- **Solo clientes persona natural.** Un cliente se registra con nombre y apellido. Los clientes empresa (razón social y NIT) son una mejora futura.
- **Métodos de pago.** Se guardan sin tilde ("Tarjeta de credito") y se muestran con tilde en pantalla; la API recibe y devuelve el valor sin tilde.
- **Servidor de desarrollo.** `python app.py` usa el servidor de Flask, pensado para desarrollo. Para un uso real haría falta un servidor de producción y HTTPS.
- **Instalador solo para Windows.** En otros sistemas se siguen los pasos de la instalación manual.
- **La cabecera CSP permite estilos en línea**, porque el gráfico del dashboard fija el tamaño de sus barras con el atributo `style`. Los scripts en línea sí están bloqueados.
