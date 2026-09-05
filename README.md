# ARKHE — software

ERP de gestión inmobiliaria (clientes, proyectos, apartamentos, ventas,
pagos, usuarios). Backend en Python/Flask, base de datos MySQL (ARKHE_V1).

## Estructura del proyecto

- `app.py` — punto de entrada de la aplicación.
- `config.py` — configuración de conexión a MySQL (lee `.env`).
- `routes/` — un blueprint de Flask por módulo (usuarios, clientes, proyectos, apartamentos, ventas, pagos).
- `models/` — representación en Python de cada tabla de ARKHE_V1 (Flask-SQLAlchemy).
- `templates/` — plantillas HTML (Jinja2), basadas en los mockups ya construidos (carpeta `ADSO/ADSO/ARKHE`).
- `static/css/` — hojas de estilo.
- `static/js/` — interactividad de cada módulo.
- `database/` — copias de referencia del esquema y conexión histórica (ver `database/README.md`).
- `docs/` — notas técnicas internas.
- `assets/` — imágenes y recursos estáticos.

## Cómo levantar el entorno

Abre esta carpeta en VS Code, abre una terminal (Terminal > New Terminal) y ejecuta:

```
python -m venv venv
```

Esto crea el entorno virtual (la carpeta `venv/`, ya excluida en `.gitignore`). Si ya existe (viene de la configuración inicial), solo actívalo:

- Windows (PowerShell): `venv\Scripts\Activate.ps1`
- Windows (cmd): `venv\Scripts\activate.bat`

Vas a ver `(venv)` al inicio de la línea de la terminal cuando esté activo.

Instala las dependencias del proyecto:

```
pip install -r requirements.txt
```

Asegúrate de tener un archivo `.env` (copiado de `.env.example`) con tus credenciales reales de MySQL.

Corre la aplicación:

```
python app.py
```

Abre `http://127.0.0.1:5000` en el navegador — debería redirigirte al listado de clientes.

## Módulo de Clientes (evidencia GA7-220501096-AA3-EV01)

Primer módulo real codificado, con CRUD completo (crear, listar, editar, eliminar), probado antes de la entrega. Cómo cumple los indicadores del instrumento de evaluación:

| Indicador | Cómo se cumple |
|---|---|
| Selecciona y aplica un framework | **Flask** + **Flask-SQLAlchemy** (ORM) |
| Integra herramientas de almacenamiento de datos | Conexión real a **MySQL** (`ARKHE_V1`) vía Flask-SQLAlchemy + PyMySQL |
| Usa estándar de codificación y comentarios | **PEP 8** + docstrings y comentarios explicativos en todos los archivos |

Nota de diseño: el mockup original incluye los campos "Tipo de Documento" y "Estado", que no existen en la tabla `clientes` ya aprobada en GA6. Este módulo respeta el esquema de base de datos ya entregado; ver comentario en `models/cliente.py`.

## Control de versiones

Este proyecto usa Git (local) / GitHub (remoto), como práctica transversal
desde esta etapa hasta la entrega, según lo definido en el plan de trabajo.
