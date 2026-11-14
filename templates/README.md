# templates/

Plantillas HTML que Flask completa con datos reales (motor Jinja).

| Archivo o carpeta | Qué contiene |
|---|---|
| `base.html` | Diseño común de todas las pantallas: menú lateral, encabezado con el usuario conectado, mensajes y la ventana de confirmación. Las demás plantillas la extienden con `{% extends "base.html" %}`. |
| `_componentes.html` | Macros reutilizables: `alertas()` (mensajes con icono y cierre) y `estado_vacio()` (tabla sin registros, con botón para crear el primero). |
| `auth/login.html` | Pantalla de inicio de sesión. |
| `errores/error.html` | Página común para los errores 400, 403, 404 y 500. |
| `dashboard/` | Panel de inicio. |
| `clientes/`, `usuarios/`, `proyectos/`, `apartamentos/`, `ventas/`, `pagos/` | `lista.html` y `formulario.html` de cada módulo. |

## Reglas

- **Siempre con el prefijo del módulo:** `render_template("ventas/lista.html")`. Ningún blueprint declara `template_folder`, porque todos los módulos tienen un `lista.html` y sus nombres chocarían.
- **Sin JavaScript en línea:** nada de `<script>` con código ni `onclick="..."`. El comportamiento se declara con atributos `data-...` y lo implementa `static/js/arkhe.js`.
- **Todo formulario POST lleva el token CSRF:** `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- **Los botones se muestran según el rol** con `{% if puede('ventas', 'eliminar') %}`. Es solo comodidad: el permiso lo comprueba el servidor.
- **Sin colores fijos:** se usan las clases de `static/css/arkhe.css`.
- **No se usa el filtro `|safe`:** Jinja escapa todos los datos para evitar XSS.

Dos pruebas automáticas revisan que ninguna pantalla tenga JavaScript en línea ni un formulario POST sin token.
