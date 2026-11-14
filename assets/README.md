# assets/

Carpeta reservada para material de trabajo que **no forma parte de la aplicación**: archivos fuente del logo, capturas de pantalla para la documentación, diagramas, etc. Hoy está vacía.

Lo que la aplicación sí usa en ejecución está en `static/`:

- `static/img/`: el logo.
- `static/css/arkhe.css`: los estilos.
- `static/js/arkhe.js`: el JavaScript.

Flask solo publica en el navegador el contenido de `static/`; nada de lo que se guarde aquí queda accesible desde la web.
