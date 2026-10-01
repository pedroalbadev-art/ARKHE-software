# ARKHE — Software de gestión inmobiliaria

Aplicación web para administrar clientes, usuarios, proyectos inmobiliarios, apartamentos, ventas y pagos. Proyecto formativo del programa ADSO (SENA), ficha 3235890.

- **Evidencia actual:** GA7-220501096-AA5-EV03 — Diseño y desarrollo de servicios web (proyecto)
- **Stack:** Python 3 · Flask · Flask-SQLAlchemy (ORM) · MySQL 8 (base de datos `ARKHE_V1`) · PyMySQL
- **Repositorio:** https://github.com/pedroalbadev-art/ARKHE-software

## Módulos

| Módulo | Evidencia | Ruta base |
|---|---|---|
| Inicio (panel con estadísticas) | AA5-EV03 | `/` |
| Clientes | AA3-EV01 | `/clientes/` |
| Usuarios | AA3-EV02 | `/usuarios/` |
| Proyectos | AA5-EV03 | `/proyectos/` |
| Apartamentos | AA5-EV03 | `/apartamentos/` |
| Ventas | AA5-EV03 | `/ventas/` |
| Pagos | AA5-EV03 | `/pagos/` |

El orden de construcción sigue las llaves foráneas: Clientes y Usuarios no dependen de nadie; Proyectos necesita a ambos; Apartamentos necesita Proyectos; Ventas necesita Clientes y Apartamentos; Pagos necesita Ventas.

## Estructura

```
ARKHE-software/
├── app.py                 Punto de entrada: crea la app y registra los 7 blueprints
├── config.py              Lee la conexión a MySQL desde .env
├── requirements.txt
├── models/                Una clase SQLAlchemy por tabla de ARKHE_V1
│   ├── cliente.py  usuario.py  proyecto.py
│   └── apartamento.py  venta.py  pago.py
├── routes/                Un blueprint por módulo (CRUD + reglas de negocio)
│   ├── dashboard.py  clientes.py  usuarios.py
│   └── proyectos.py  apartamentos.py  ventas.py  pagos.py
├── templates/
│   ├── base.html          Plantilla base: menu lateral con logo, encabezado y mensajes
│   ├── dashboard/inicio.html
│   └── clientes/ usuarios/ proyectos/ apartamentos/ ventas/ pagos/
│       └── lista.html  formulario.html
├── static/
│   ├── css/arkhe.css      Estilos de toda la aplicacion
│   └── img/               Logo de ARKHE (marca y logo completo)
├── utils/
│   ├── validaciones.py    Validaciones y conversores reutilizables
│   └── formato.py         Formato de pesos ($185.000.000)
└── database/              Referencias de esquema y conexión histórica
```

Las plantillas se piden siempre con el prefijo del módulo (`render_template("ventas/lista.html")`) y ningún blueprint define un `template_folder` propio. Así se evita que Flask confunda los `lista.html` de distintos módulos (problema ya corregido en AA3-EV02).

## Interfaz

Todas las pantallas comparten `templates/base.html`, construida a partir del mockup de Dashboard/Clientes de la evidencia de frontend (GA6-AA4-EV02): menú lateral bronce con el logo de ARKHE, encabezado blanco con el título de la página, y contenido en tarjetas blancas con la paleta dorado/bronce del logo.

- **Dashboard (`/`):** indicadores de clientes, proyectos, apartamentos disponibles, valor vendido y recaudado; gráfico de ventas de los últimos 6 meses; estado de apartamentos y de ventas; tablas de últimas ventas y últimos pagos. Todo sale de la base de datos, no hay datos fijos.
- **Listados:** tarjetas de resumen (Apartamentos, Ventas, Proyectos), barra con buscador y filtros (por estado, proyecto, rol o método de pago) y tabla con acciones Editar/Eliminar. El buscador y los filtros funcionan en el navegador sobre las filas ya cargadas.
- Algunos elementos de los mockups no se incluyeron porque la base de datos no tiene esas columnas: estado de clientes y de proyectos, usuario "@" y último acceso. El usuario conectado y "Cerrar sesión" tampoco se incluyeron, porque el inicio de sesión aún no está construido.

## Instalación

1. Crear y activar el entorno virtual:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
2. Instalar dependencias: `pip install -r requirements.txt`
3. Crear el archivo `.env` (ver `.env.example`) con `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` y `SECRET_KEY`. Si la contraseña tiene caracteres especiales como `#`, va entre comillas dobles.
4. Ejecutar: `python app.py` y abrir http://localhost:5000

La aplicación usa las tablas que ya existen en `ARKHE_V1`; no las crea ni las modifica.

## Esquema de la base de datos

Verificado contra la base real con `information_schema.COLUMNS` (los modelos usan exactamente estas columnas):

| Tabla | Columnas |
|---|---|
| clientes | id_cliente (PK), nombre, apellido, documento (UNIQUE), correo (UNIQUE), telefono |
| usuarios | id_usuario (PK), nombre, apellido, correo (UNIQUE), contrasena (hash), rol, estado |
| proyectos | id_proyecto (PK), id_cliente (FK), id_usuario (FK), nombre_proyecto (UNIQUE), direccion, ciudad, descripcion |
| apartamentos | id_apartamento (PK), id_proyecto (FK), numero_apartamento, area_m2, habitaciones, banos, precio, estado |
| ventas | id_venta (PK), id_cliente (FK), id_apartamento (FK, UNIQUE), fecha_venta, valor_venta |
| pagos | id_pago (PK), id_venta (FK), fecha_pago, monto, metodo_pago |

Valores que se calculan en Python y no se guardan (para no duplicar datos, 3FN):

- `Cliente.nombre_completo` y `Usuario.nombre_completo`.
- `Venta.total_pagado` (suma de sus pagos), `Venta.saldo` y `Venta.estado`: *pendiente* sin pagos, *en-pago* con pagos parciales, *pagada* con saldo en cero.

## Endpoints

Todos los módulos nuevos siguen el mismo patrón (`<id>` es la llave primaria):

| Método | Ruta | Acción |
|---|---|---|
| GET | `/<modulo>/` | Listar |
| GET | `/<modulo>/nuevo` (en Ventas: `/ventas/nueva`) | Formulario de creación |
| POST | `/<modulo>/crear` | Crear |
| GET | `/<modulo>/<id>/editar` | Formulario de edición |
| POST | `/<modulo>/<id>/actualizar` | Guardar cambios |
| POST | `/<modulo>/<id>/eliminar` | Eliminar |

Además, `GET /pagos/?venta=<id>` filtra los pagos de una venta y `GET /pagos/nuevo?venta=<id>` abre el formulario con esa venta elegida.

Clientes y Usuarios conservan sus rutas originales: `GET /`, `POST /nuevo`, `GET` y `POST /<id>/editar`, `POST /<id>/eliminar`.

## Validaciones (todas en el backend)

Los formularios tienen `required`, `min`, `max` y patrones como ayuda, pero todas las reglas se vuelven a revisar en Python antes de guardar. Si algo falla, el formulario se muestra de nuevo con los mensajes de error y los datos escritos.

**Proyectos**
- Nombre obligatorio, único, máximo 150 caracteres. Dirección obligatoria, máximo 200.
- Ciudad: solo letras y espacios, máximo 100.
- El cliente debe existir y el usuario gestor debe existir y estar activo.

**Apartamentos**
- El proyecto debe existir.
- Número obligatorio, máximo 20 caracteres (letras, números, guion y espacios), único dentro del proyecto.
- Área mayor que 0 y hasta 9999.99 m². Habitaciones y baños: enteros entre 1 y 10. Precio mayor que 0.
- Estado: *disponible* o *reservado* (apartado por un cliente). El estado *vendido* lo pone solo el módulo de Ventas.

**Ventas**
- El cliente y el apartamento deben existir, y el apartamento debe estar disponible o reservado.
- Fecha válida y no futura. Valor mayor que 0.
- Al editar, el valor no puede quedar por debajo de lo ya pagado, y la fecha no puede ser posterior al primer pago.

**Pagos**
- La venta debe existir.
- Fecha válida, no futura y no anterior a la fecha de la venta.
- Monto mayor que 0 y sin superar el saldo pendiente (al editar no se cuenta el propio pago).
- Método de pago dentro de la lista permitida: Efectivo, Transferencia, Tarjeta de credito, Tarjeta debito, Cheque o Credito hipotecario.

**Clientes y Usuarios** (evidencias anteriores)
- Nombre y apellido solo con letras; documento de 6 a 15 dígitos; teléfono de 7 a 15 dígitos; correo con formato válido.
- Documento y correo únicos. Contraseña de mínimo 8 caracteres, guardada como hash con `werkzeug.security`.
- Rol: Administrador, Vendedor o Gerente. Estado: activo o inactivo.

## Reglas de negocio

- Un apartamento se vende una sola vez (`ventas.id_apartamento` es UNIQUE).
- Al registrar una venta, el apartamento pasa a *vendido*. Si la venta se elimina, o se cambia a otro apartamento, el anterior vuelve a *disponible*. Los dos cambios se guardan en una misma transacción.
- No se puede eliminar un proyecto que tenga apartamentos, un apartamento que tenga venta, ni una venta que tenga pagos. En esos casos se muestra un mensaje claro en vez de un error de base de datos.

## Prueba sugerida

1. Crear un cliente y un usuario activo.
2. Crear un proyecto (probar una ciudad con números para ver el error).
3. Crear dos apartamentos (probar el mismo número repetido para ver el error).
4. Registrar una venta: el apartamento pasa a *vendido*.
5. Registrar un pago parcial (la venta queda *en-pago*) y luego otro por el saldo (queda *pagada*).
6. Intentar un pago mayor que el saldo, y eliminar una venta con pagos: ambos se rechazan.
7. Revisar el panel de inicio: estados y recaudo actualizados.

## Autor

Pedro Alba Méndez — ADSO, SENA, ficha 3235890.
