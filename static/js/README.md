# static/js/

`arkhe.js` contiene todo el JavaScript del sistema: ventanas modales, confirmación antes de eliminar, cierre de mensajes, buscador y filtros de las tablas, menú plegable en celular y la sugerencia de precio al registrar una venta.

**Regla:** las plantillas no llevan JavaScript en línea (ni `<script>` con código ni `onclick="..."`). Cada elemento declara lo que necesita con un atributo `data-...` y este archivo le da el comportamiento:

| Atributo | Efecto |
|---|---|
| `data-abrir-modal="id"` | Abre la ventana modal con ese `id`. |
| `data-cerrar-modal` | Cierra la ventana modal que lo contiene. |
| `data-cerrar-alerta` | Quita un mensaje. |
| `data-confirmar="texto"` | El formulario pide confirmación antes de enviarse. |
| `data-alternar-menu` / `data-cerrar-menu` | Abre o cierra el menú lateral en pantallas pequeñas. |

Así los datos escritos por los usuarios nunca se mezclan con código (el texto se inserta con `textContent`), y la cabecera Content-Security-Policy puede prohibir cualquier script que no venga de este archivo.
