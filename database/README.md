# database/

Estructura de la base de datos del sistema.

| Archivo | Qué es |
|---|---|
| `esquema.sql` | Las 6 tablas (`usuarios`, `clientes`, `proyectos`, `apartamentos`, `ventas`, `pagos`) con sus llaves primarias, llaves foráneas y restricciones `UNIQUE`. Se generó con `SHOW CREATE TABLE` sobre la base real, así que es una copia exacta de la estructura con la que el sistema fue desarrollado y probado. No contiene datos. |

## Cómo se usa

No hace falta ejecutar el SQL a mano: `instalar.ps1` (o `python scripts/preparar_base.py`) crea una base **nueva**, ejecuta `esquema.sql` y carga los datos de demostración. El instalador nunca modifica ni borra una base que ya exista.

`esquema.sql` no incluye `CREATE DATABASE` ni `USE`: el nombre de la base lo elige quien instala.

## Conexión

La aplicación se conecta con **Flask-SQLAlchemy** (ORM) y el driver **PyMySQL**. Los datos de conexión se leen del archivo `.env` en `config.py`; los modelos están en `models/`, uno por tabla.

## Si cambia la estructura

Cualquier cambio en las tablas se hace primero en MySQL, luego en el modelo correspondiente de `models/`, y por último se vuelve a generar `esquema.sql` para que una instalación nueva quede igual. Consulta para comparar los modelos con la base real:

```sql
SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'ARKHE_V1'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```
