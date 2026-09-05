-- clientes_esquema_referencia.sql
-- --------------------------------
-- Copia de referencia de la tabla `clientes`, verificada directamente
-- contra la base de datos real con `DESCRIBE ARKHE_V1.clientes;`
-- el 2026-09-05 (la version anterior de este archivo asumia columnas
-- que no coincidian con la tabla real: "nombre_completo" y
-- "direccion" no existen; el nombre esta dividido en nombre/apellido
-- y no hay columna de direccion).
--
-- NO es el script oficial de creacion de la base de datos -- ese
-- sigue viviendo en la carpeta de evidencias GA6 -- se incluye aqui
-- solo como referencia rapida para verificar el modelo Cliente
-- (models/cliente.py) contra el esquema real.

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nombre     VARCHAR(100) NOT NULL,
    apellido   VARCHAR(100) NOT NULL,
    documento  VARCHAR(20)  NOT NULL UNIQUE,
    correo     VARCHAR(150) NOT NULL UNIQUE,
    telefono   VARCHAR(20)  NOT NULL
);
