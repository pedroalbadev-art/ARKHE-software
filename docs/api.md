# Referencia de la API REST

## Control del documento

| Dato | Valor |
|---|---|
| Código | ARKHE-API-001 |
| Documento | Referencia de la API REST |
| Versión | 1.0 |
| Fecha | 2026-11-14 |
| Elaborado por | Pedro Alba Méndez |

### Historial de cambios

| Versión | Fecha | Autor | Descripción |
|---|---|---|---|
| 1.0 | 2026-11-14 | Pedro Alba Méndez | Versión inicial. |

Detalla, recurso por recurso, qué campos recibe la API, un ejemplo para crear cada registro, la respuesta que devuelve y cómo informa los errores. La visión general (autenticación, permisos y códigos) está en el [manual técnico](manual_tecnico.md#4-api-rest).

Los ejemplos de respuesta se tomaron de salidas reales de la API, obtenidas el 2026-11-14 sobre una base de pruebas. En el ejemplo de inicio de sesión se usó el Administrador de demostración.

## Contenido

1. [Reglas generales](#1-reglas-generales)
2. [Inicio de sesión](#2-inicio-de-sesión)
3. [Clientes](#3-clientes)
4. [Usuarios](#4-usuarios)
5. [Proyectos](#5-proyectos)
6. [Apartamentos](#6-apartamentos)
7. [Ventas](#7-ventas)
8. [Pagos](#8-pagos)
9. [Resumen](#9-resumen)
10. [Estructura de los errores](#10-estructura-de-los-errores)

## 1. Reglas generales

- **Dirección base:** `http://localhost:5000/api` en una instalación local.
- **Sesión:** todas las rutas, salvo `POST /api/login`, exigen la cookie de sesión.
- **Cuerpo en JSON:** toda petición `POST` o `PUT` debe llevar la cabecera `Content-Type: application/json` y un objeto JSON. Sin esa cabecera la respuesta es 400, aunque el texto sea JSON válido.
- **Actualizar (`PUT`) reemplaza el registro:** se envían todos los campos obligatorios, no solo los que cambian.
- **Números:** se aceptan como número (`185000000`) o como texto (`"185000000"`), siempre sin separadores de miles. Los valores de dinero están en pesos colombianos (COP).
- **Fechas:** en formato `AAAA-MM-DD`, por ejemplo `"2026-11-02"`.
- **Respuestas:** crear devuelve 201 con el registro creado; consultar y actualizar devuelven 200 con el registro; eliminar devuelve 200 con `{"mensaje": "..."}`.
- **CORS:** no está habilitado. La API está pensada para programas (como Postman) o para páginas servidas por el mismo sistema, no para páginas web de otros sitios.

Las cinco operaciones de cada recurso:

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/<recurso>` | Listar |
| GET | `/api/<recurso>/<id>` | Consultar uno |
| POST | `/api/<recurso>` | Crear |
| PUT | `/api/<recurso>/<id>` | Actualizar |
| DELETE | `/api/<recurso>/<id>` | Eliminar |

## 2. Inicio de sesión

`POST /api/login`

| Campo | Obligatorio | Descripción |
|---|---|---|
| correo | Sí | Correo del usuario. No distingue mayúsculas de minúsculas. |
| contrasena | Sí | Contraseña. |

```json
{"correo": "admin@arkhe.example", "contrasena": "Admin#2026"}
```

Respuesta 200. Trae además la cookie de sesión, que debe enviarse en las peticiones siguientes:

```json
{
  "mensaje": "Sesion iniciada.",
  "usuario": {
    "id_usuario": 1,
    "nombre": "Laura",
    "apellido": "Restrepo Gil",
    "nombre_completo": "Laura Restrepo Gil",
    "correo": "admin@arkhe.example",
    "rol": "Administrador",
    "estado": "activo"
  }
}
```

Con credenciales incorrectas o una cuenta inactiva responde 401:

```json
{"error": "Correo o contraseña incorrectos."}
```

## 3. Clientes

Personas naturales. Todos los campos son obligatorios.

| Campo | Obligatorio | Reglas |
|---|---|---|
| nombre | Sí | Solo letras y espacios. Máximo 100 caracteres. |
| apellido | Sí | Solo letras y espacios. Máximo 100 caracteres. |
| documento | Sí | Solo números, de 6 a 15 dígitos. Único. |
| correo | Sí | Formato de correo. Máximo 150 caracteres. Único. |
| telefono | Sí | Solo números, de 7 a 15 dígitos. |

`POST /api/clientes`

```json
{
  "nombre": "Ana",
  "apellido": "Rojas",
  "documento": "10203040",
  "correo": "ana@ejemplo.com",
  "telefono": "3001234567"
}
```

Respuesta 201:

```json
{
  "id_cliente": 1,
  "nombre": "Ana",
  "apellido": "Rojas",
  "nombre_completo": "Ana Rojas",
  "documento": "10203040",
  "correo": "ana@ejemplo.com",
  "telefono": "3001234567"
}
```

Particularidades:

- Un documento o correo repetido responde 409.
- No se puede eliminar un cliente con proyectos o ventas (409).

## 4. Usuarios

| Campo | Obligatorio | Reglas |
|---|---|---|
| nombre | Sí | Solo letras y espacios. Máximo 100 caracteres. |
| apellido | Sí | Solo letras y espacios. Máximo 100 caracteres. |
| correo | Sí | Formato de correo. Máximo 150 caracteres. Único. |
| contrasena | Sí al crear; opcional al actualizar | Mínimo 8 caracteres, sin espacios al inicio ni al final. Al actualizar, si no se envía o va vacía, la contraseña no cambia. |
| rol | Sí | `Administrador`, `Vendedor` o `Gerente`. |
| estado | No | `activo` o `inactivo`. Al crear, por defecto `activo`. Al actualizar, si no se envía, se conserva el actual. |

`POST /api/usuarios`

```json
{
  "nombre": "Camilo",
  "apellido": "Vargas",
  "correo": "camilo@ejemplo.com",
  "contrasena": "ClaveSegura1",
  "rol": "Vendedor"
}
```

Respuesta 201. La contraseña nunca se devuelve, ni siquiera su hash:

```json
{
  "id_usuario": 2,
  "nombre": "Camilo",
  "apellido": "Vargas",
  "nombre_completo": "Camilo Vargas",
  "correo": "camilo@ejemplo.com",
  "rol": "Vendedor",
  "estado": "activo"
}
```

### Activar o desactivar

`PUT /api/usuarios/<id>/estado`

| Campo | Obligatorio | Reglas |
|---|---|---|
| estado | Sí | `activo` o `inactivo`. |

```json
{"estado": "inactivo"}
```

Responde 200 con el usuario actualizado. El Administrador puede cambiar cualquier cuenta; el Gerente, solo cuentas de Vendedor (403 en otro caso).

Particularidades:

- Un correo repetido responde 409.
- Responden 409: eliminar o desactivar la propia cuenta, dejar el sistema sin un Administrador activo, y eliminar un usuario que gestiona proyectos.

## 5. Proyectos

| Campo | Obligatorio | Reglas |
|---|---|---|
| id_cliente | Sí | ID de un cliente existente (propietario o promotor). |
| id_usuario | Sí | ID de un usuario existente y activo (gestor). |
| nombre_proyecto | Sí | Máximo 150 caracteres. Único. |
| direccion | Sí | Máximo 200 caracteres. |
| ciudad | Sí | Solo letras y espacios. Máximo 100 caracteres. |
| descripcion | No | Texto libre. |

`POST /api/proyectos`

```json
{
  "id_cliente": 1,
  "id_usuario": 1,
  "nombre_proyecto": "Torre Mirador",
  "direccion": "Calle 10 # 5-20",
  "ciudad": "Medellin",
  "descripcion": "Torre de 12 pisos"
}
```

Respuesta 201:

```json
{
  "id_proyecto": 1,
  "nombre_proyecto": "Torre Mirador",
  "direccion": "Calle 10 # 5-20",
  "ciudad": "Medellin",
  "descripcion": "Torre de 12 pisos",
  "id_cliente": 1,
  "cliente": "Ana Rojas",
  "id_usuario": 1,
  "gestor": "Laura Restrepo Gil",
  "total_apartamentos": 0
}
```

Particularidades:

- Un nombre de proyecto repetido responde 400, dentro de la lista de errores.
- No se puede eliminar un proyecto con apartamentos (409).

## 6. Apartamentos

| Campo | Obligatorio | Reglas |
|---|---|---|
| id_proyecto | Sí | ID de un proyecto existente. |
| numero_apartamento | Sí | Letras, números, guion y espacios. Máximo 20 caracteres. Único dentro del proyecto. |
| area_m2 | Sí | Mayor que 0 y hasta 9999.99. |
| habitaciones | Sí | Entero entre 1 y 10. |
| banos | Sí | Entero entre 1 y 10. |
| precio | Sí | Mayor que 0, en COP. |
| estado | No al crear; sí al actualizar | `disponible` o `reservado`. Al crear, por defecto `disponible`. `vendido` no se puede enviar: lo asigna la venta. |

`POST /api/apartamentos`

```json
{
  "id_proyecto": 1,
  "numero_apartamento": "301",
  "area_m2": 54.3,
  "habitaciones": 2,
  "banos": 2,
  "precio": 185000000
}
```

Respuesta 201. `id_venta` es `null` mientras el apartamento no se haya vendido:

```json
{
  "id_apartamento": 1,
  "id_proyecto": 1,
  "proyecto": "Torre Mirador",
  "numero_apartamento": "301",
  "area_m2": 54.3,
  "habitaciones": 2,
  "banos": 2,
  "precio": 185000000.0,
  "estado": "disponible",
  "id_venta": null
}
```

Filtros del listado: `?estado=disponible` y `?proyecto=<id>`.

### Apartamento vendido

Cuando el apartamento tiene una venta, al actualizarlo:

- **El proyecto y el precio no se pueden cambiar.** Enviar un valor distinto responde 400.
- **El área, las habitaciones y los baños sí se pueden corregir.**
- **El estado se conserva en `vendido`.** No hace falta enviarlo. Si se envía otro, la respuesta sigue siendo 200 y trae un campo adicional `aviso`:

```json
{
  "id_apartamento": 1,
  "id_proyecto": 1,
  "proyecto": "Torre Mirador",
  "numero_apartamento": "301",
  "area_m2": 54.3,
  "habitaciones": 2,
  "banos": 2,
  "precio": 185000000.0,
  "estado": "vendido",
  "id_venta": 1,
  "aviso": "El estado de un apartamento vendido solo cambia al anular su venta: el apartamento sigue como 'vendido'."
}
```

Otras particularidades:

- Un número repetido dentro del mismo proyecto responde 400.
- No se puede eliminar un apartamento con venta (409).

## 7. Ventas

Todos los campos son obligatorios.

| Campo | Obligatorio | Reglas |
|---|---|---|
| id_cliente | Sí | ID de un cliente existente (comprador). |
| id_apartamento | Sí | ID de un apartamento `disponible` o `reservado`. |
| fecha_venta | Sí | `AAAA-MM-DD`. No puede ser futura. |
| valor_venta | Sí | Mayor que 0, en COP. |

`POST /api/ventas`

```json
{
  "id_cliente": 1,
  "id_apartamento": 1,
  "fecha_venta": "2026-11-02",
  "valor_venta": 180000000
}
```

Respuesta 201. `total_pagado`, `saldo` y `estado` son valores calculados:

```json
{
  "id_venta": 1,
  "id_cliente": 1,
  "cliente": "Ana Rojas",
  "id_apartamento": 1,
  "apartamento": "301",
  "proyecto": "Torre Mirador",
  "fecha_venta": "2026-11-02",
  "valor_venta": 180000000.0,
  "total_pagado": 0.0,
  "saldo": 180000000.0,
  "estado": "pendiente",
  "pagos": []
}
```

Particularidades:

- La lista `pagos` viene al crear, actualizar y consultar una venta por su ID. El listado general no la incluye.
- Filtro del listado: `?estado=pendiente`, `?estado=en-pago` o `?estado=pagada`.
- Al crear la venta, el apartamento pasa a `vendido`. Al eliminarla, queda `disponible`.
- Al actualizar: si se cambia el apartamento, el anterior queda `disponible` y el nuevo `vendido`. La fecha no puede quedar posterior al primer pago, ni el valor por debajo de lo ya pagado.
- Vender un apartamento que no está disponible responde 400.
- No se puede eliminar una venta con pagos (409).

## 8. Pagos

Todos los campos son obligatorios.

| Campo | Obligatorio | Reglas |
|---|---|---|
| id_venta | Sí | ID de una venta existente. |
| fecha_pago | Sí | `AAAA-MM-DD`. No puede ser futura ni anterior a la fecha de la venta. |
| monto | Sí | Mayor que 0 y no mayor que el saldo de la venta, en COP. |
| metodo_pago | Sí | `Efectivo`, `Transferencia`, `Tarjeta de credito`, `Tarjeta debito`, `Cheque` o `Credito hipotecario`. Se escriben exactamente así, sin tilde. |

`POST /api/pagos`

```json
{
  "id_venta": 1,
  "fecha_pago": "2026-11-05",
  "monto": 50000000,
  "metodo_pago": "Transferencia"
}
```

Respuesta 201:

```json
{
  "id_pago": 1,
  "id_venta": 1,
  "fecha_pago": "2026-11-05",
  "monto": 50000000.0,
  "metodo_pago": "Transferencia"
}
```

Después de este pago, `GET /api/ventas/1` muestra la venta con `"total_pagado": 50000000.0`, `"saldo": 130000000.0` y `"estado": "en-pago"`.

Particularidades:

- Filtro del listado: `?venta=<id>`.
- Al actualizar un pago, su propio monto no cuenta contra el saldo.
- Un monto que supera el saldo responde 400.

## 9. Resumen

`GET /api/resumen` devuelve las mismas cifras del dashboard. No recibe parámetros.

```json
{
  "clientes": 1,
  "usuarios": 2,
  "proyectos": 1,
  "apartamentos": {
    "disponible": 0,
    "reservado": 0,
    "vendido": 1
  },
  "ventas": {
    "pendiente": 0,
    "en-pago": 1,
    "pagada": 0
  },
  "valor_vendido": 180000000.0,
  "recaudado": 50000000.0,
  "saldo_por_cobrar": 130000000.0
}
```

## 10. Estructura de los errores

Hay dos formas de respuesta de error, según el código.

### Errores de validación: 400

Traen la clave `errores` con una **lista**, porque pueden fallar varios campos a la vez:

```json
{
  "errores": [
    "El nombre solo puede contener letras y espacios.",
    "El apellido solo puede contener letras y espacios.",
    "El documento debe contener solo números (6 a 15 dígitos).",
    "El correo electrónico no tiene un formato válido.",
    "El teléfono debe contener solo números (7 a 15 dígitos)."
  ]
}
```

El mismo formato se usa cuando el cuerpo no es JSON o falta la cabecera:

```json
{
  "errores": [
    "El cuerpo de la peticion debe ser un objeto JSON (Content-Type: application/json)."
  ]
}
```

### Los demás errores: 401, 403, 404, 409 y 500

Traen la clave `error` con **un solo mensaje**:

| Código | Cuándo | Ejemplo de cuerpo |
|---|---|---|
| 401 | No hay sesión. | `{"error": "Debe iniciar sesion (POST /api/login)."}` |
| 401 | Login con credenciales incorrectas. | `{"error": "Correo o contraseña incorrectos."}` |
| 403 | El rol no tiene permiso. | `{"error": "Su rol no tiene permiso para realizar esta accion."}` |
| 404 | El registro no existe. | `{"error": "El cliente con id 999 no existe."}` |
| 404 | La ruta no existe. | `{"error": "La ruta o el registro solicitado no existe."}` |
| 409 | Dato único repetido. | `{"error": "Ya existe un cliente registrado con ese documento o correo."}` |
| 409 | Regla de negocio. | `{"error": "No se puede eliminar: la venta tiene pagos registrados. Elimine primero sus pagos."}` |
| 500 | Error no previsto. | `{"error": "Error interno del servidor."}` |

Ningún mensaje de error incluye detalles técnicos del servidor ni de la base de datos.
