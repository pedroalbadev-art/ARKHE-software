# static/css/

`arkhe.css` es la única hoja de estilos del sistema. La cargan `templates/base.html`, la pantalla de inicio de sesión y la página de error.

- **Paleta** (variables al inicio del archivo): `#3A2F20`, `#4A3B26`, `#6E5A3C`, `#8A6F52` (color primario), `#C9A876`, `#F3ECDD` y `#E4D6BA`.
- **Colores de estado**, definidos una sola vez como variables: disponible / pagada, reservado / pendiente, vendido y en pago.
- **Diseño adaptable:** hasta 900 px de ancho el menú lateral se pliega y se abre con el botón de tres rayas; por debajo de 600 px el contenido pasa a una columna.

Las plantillas no llevan colores ni estilos fijos en línea: usan las clases de este archivo. La única excepción son los anchos y altos del gráfico del dashboard, que dependen de los datos.
