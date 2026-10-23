CREATE DATABASE IF NOT EXISTS eyv_digital_soluciones
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE eyv_digital_soluciones;

DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('Administrador','Técnico','Cliente') NOT NULL DEFAULT 'Técnico',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    email VARCHAR(150),
    telefono VARCHAR(40),
    empresa VARCHAR(150),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    tipo VARCHAR(80) NOT NULL,
    marca VARCHAR(80),
    modelo VARCHAR(100),
    serial VARCHAR(120),
    estado ENUM('Activo','En mantenimiento','Fuera de servicio') DEFAULT 'Activo',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_equipo_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    tecnico_id INT NULL,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    categoria ENUM('Hardware','Software','Redes y conectividad','Sistemas operativos',
                   'Mantenimiento','Seguridad informática','Ciberseguridad','Otro') NOT NULL,
    prioridad ENUM('Baja','Media','Alta','Crítica') NOT NULL DEFAULT 'Media',
    estado ENUM('Abierto','En progreso','Pendiente','Resuelto','Cerrado') NOT NULL DEFAULT 'Abierto',
    solucion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ticket_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_ticket_tecnico FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

INSERT INTO usuarios (nombre,email,password_hash,rol) VALUES
('Administrador Eyv','admin@eyvdigital.com',
'pbkdf2:sha256:600000$eyvadmin$7e9f0d5e8b6d2b7e8f2f9d8c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b','Administrador'),
('Carlos Técnico','tecnico@eyvdigital.com',
'pbkdf2:sha256:600000$eyvtec$8e9f0d5e8b6d2b7e8f2f9d8c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0c','Técnico');

INSERT INTO clientes (nombre,email,telefono,empresa) VALUES
('Empresa Demo','cliente@empresa.com','3000000000','Empresa Demo S.A.S.'),
('Cliente Prueba','prueba@empresa.com','3010000000','Cliente Prueba');

INSERT INTO equipos (cliente_id,tipo,marca,modelo,serial,estado) VALUES
(1,'Computador','Dell','OptiPlex 7090','EVY-001','Activo'),
(1,'Portátil','Lenovo','ThinkPad E14','EVY-002','En mantenimiento'),
(2,'Impresora','HP','LaserJet Pro','EVY-003','Activo');

INSERT INTO tickets (cliente_id,tecnico_id,titulo,descripcion,categoria,prioridad,estado) VALUES
(1,2,'Falla de conectividad','El equipo presenta pérdida intermitente de conexión a la red.','Redes y conectividad','Alta','En progreso'),
(1,2,'Actualización de software','Se requiere instalar una actualización autorizada.','Software','Media','Abierto'),
(2,NULL,'Equipo no enciende','Se solicita diagnóstico inicial del equipo.','Hardware','Crítica','Pendiente');
