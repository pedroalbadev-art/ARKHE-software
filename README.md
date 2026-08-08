# ARKHE — software

ERP de gestión inmobiliaria (clientes, proyectos, apartamentos, ventas,
pagos, usuarios). Backend en Python/Flask, base de datos MySQL (ARKHE_V1).

## Estructura del proyecto

- `app.py` — punto de entrada de la aplicación.
- `routes/` — un blueprint de Flask por módulo (usuarios, clientes, proyectos, apartamentos, ventas, pagos).
- `models/` — representación en Python de cada tabla de ARKHE_V1.
- `templates/` — plantillas HTML (Jinja2), basadas en los mockups ya construidos.
- `static/css/` — hojas de estilo.
- `static/js/` — interactividad de cada módulo.
- `database/` — configuración de conexión a MySQL.
- `docs/` — notas técnicas internas.
- `assets/` — imágenes y recursos estáticos.

## Cómo levantar el entorno (primera vez)

Abre esta carpeta en VS Code, abre una terminal (Terminal > New Terminal) y ejecuta:

```
python -m venv venv
```

Esto crea el entorno virtual (la carpeta `venv/`, ya excluida en `.gitignore`).

Actívalo:

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (cmd): `venv\Scripts\activate.bat`

Vas a ver `(venv)` al inicio de la línea de la terminal cuando esté activo.

Instala las dependencias del proyecto:

```
pip install -r requirements.txt
```

Corre la aplicación de prueba:

```
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador — si ves el mensaje "ARKHE está
funcionando", el entorno quedó bien configurado.

## Control de versiones

Este proyecto usa Git (local) / GitHub (remoto), como práctica transversal
desde esta etapa hasta la entrega, según lo definido en el plan de trabajo.
