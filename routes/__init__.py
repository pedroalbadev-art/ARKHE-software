# Aquí van los "blueprints" de Flask: un archivo por módulo
# (usuarios.py, clientes.py, proyectos.py, apartamentos.py, ventas.py, pagos.py).
# Cada blueprint agrupa las rutas (URLs) de un módulo, en el mismo orden
# de dependencia por llave foránea definido en el plan de trabajo:
# Usuarios -> Clientes -> Proyectos -> Apartamentos -> Ventas -> Pagos.
