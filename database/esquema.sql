-- database/esquema.sql
-- ----------------------------------------------------------------------
-- Estructura de la base de datos del sistema: las 6 tablas, con sus
-- llaves primarias, llaves foraneas y restricciones UNIQUE.
--
-- Generado el 2026-11-13 con SHOW CREATE TABLE sobre la base real
-- (MySQL 8.4.8), es decir, es una copia exacta de la estructura con la
-- que el sistema fue desarrollado y probado. No contiene datos.
--
-- No incluye CREATE DATABASE ni USE: el nombre de la base lo elige quien
-- instala. Lo ejecuta scripts/preparar_base.py sobre una base recien
-- creada y vacia (ver instalar.ps1 y el README).
--
-- Las tablas van en un orden que respeta las llaves foraneas:
--   usuarios, clientes -> proyectos -> apartamentos -> ventas -> pagos
-- ----------------------------------------------------------------------

CREATE TABLE `usuarios` (
  `id_usuario` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `correo` varchar(150) NOT NULL,
  `contrasena` varchar(255) NOT NULL,
  `rol` varchar(50) NOT NULL,
  `estado` varchar(20) NOT NULL DEFAULT 'activo',
  PRIMARY KEY (`id_usuario`),
  UNIQUE KEY `correo` (`correo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Tabla de usuarios del sistema ARKHE';

CREATE TABLE `clientes` (
  `id_cliente` int NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `documento` varchar(20) NOT NULL,
  `correo` varchar(150) NOT NULL,
  `telefono` varchar(20) NOT NULL,
  PRIMARY KEY (`id_cliente`),
  UNIQUE KEY `documento` (`documento`),
  UNIQUE KEY `correo` (`correo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `proyectos` (
  `id_proyecto` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `id_usuario` int NOT NULL,
  `nombre_proyecto` varchar(150) NOT NULL,
  `direccion` varchar(200) NOT NULL,
  `ciudad` varchar(100) NOT NULL,
  `descripcion` text,
  PRIMARY KEY (`id_proyecto`),
  UNIQUE KEY `nombre_proyecto` (`nombre_proyecto`),
  KEY `fk_proyectos_cliente` (`id_cliente`),
  KEY `fk_proyectos_usuario` (`id_usuario`),
  CONSTRAINT `fk_proyectos_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id_cliente`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_proyectos_usuario` FOREIGN KEY (`id_usuario`) REFERENCES `usuarios` (`id_usuario`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `apartamentos` (
  `id_apartamento` int NOT NULL AUTO_INCREMENT,
  `id_proyecto` int NOT NULL,
  `numero_apartamento` varchar(20) NOT NULL,
  `area_m2` decimal(10,2) NOT NULL,
  `habitaciones` int NOT NULL,
  `banos` int NOT NULL,
  `precio` decimal(15,2) NOT NULL,
  `estado` varchar(20) NOT NULL,
  PRIMARY KEY (`id_apartamento`),
  UNIQUE KEY `uq_apartamento` (`id_proyecto`,`numero_apartamento`),
  CONSTRAINT `fk_apartamentos_proyecto` FOREIGN KEY (`id_proyecto`) REFERENCES `proyectos` (`id_proyecto`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `ventas` (
  `id_venta` int NOT NULL AUTO_INCREMENT,
  `id_cliente` int NOT NULL,
  `id_apartamento` int NOT NULL,
  `fecha_venta` date NOT NULL,
  `valor_venta` decimal(15,2) NOT NULL,
  PRIMARY KEY (`id_venta`),
  UNIQUE KEY `uq_apartamento_vendido` (`id_apartamento`),
  KEY `fk_ventas_cliente` (`id_cliente`),
  CONSTRAINT `fk_ventas_apartamento` FOREIGN KEY (`id_apartamento`) REFERENCES `apartamentos` (`id_apartamento`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_ventas_cliente` FOREIGN KEY (`id_cliente`) REFERENCES `clientes` (`id_cliente`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `pagos` (
  `id_pago` int NOT NULL AUTO_INCREMENT,
  `id_venta` int NOT NULL,
  `fecha_pago` date NOT NULL,
  `monto` decimal(15,2) NOT NULL,
  `metodo_pago` varchar(50) NOT NULL,
  PRIMARY KEY (`id_pago`),
  KEY `fk_pagos_venta` (`id_venta`),
  CONSTRAINT `fk_pagos_venta` FOREIGN KEY (`id_venta`) REFERENCES `ventas` (`id_venta`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
