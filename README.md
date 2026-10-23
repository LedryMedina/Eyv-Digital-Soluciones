# Eyv Digital Soluciones — Mesa de Ayuda

Sistema web académico para gestionar soporte técnico, seguridad informática y ciberseguridad.

## Tecnologías
- Frontend: HTML5, CSS3 y JavaScript
- Backend: Python + Flask
- Base de datos: MySQL
- Despliegue: GitHub + Render

## Instalación local

1. Instalar Python 3.11+ y MySQL/XAMPP.
2. Crear la base de datos ejecutando `database/eyv_digital_soluciones.sql` en phpMyAdmin.
3. Copiar `.env.example` como `.env` y ajustar las credenciales.
4. Crear entorno virtual:
   `python -m venv .venv`
5. Activarlo en Windows:
   `.venv\Scripts\activate`
6. Instalar dependencias:
   `pip install -r requirements.txt`
7. Ejecutar:
   `python app.py`
8. Abrir:
   `http://127.0.0.1:5000`

## Usuario inicial
- Correo: admin@eyvdigital.com
- Contraseña: Admin123!

Cambia esta contraseña antes de usar el sistema en un entorno real.

## Render
Este proyecto puede desplegarse como servicio Python. Build command:
`pip install -r requirements.txt`

Start command:
`gunicorn app:app`

Las variables de entorno deben configurarse en Render. Para producción se recomienda utilizar una base de datos MySQL administrada compatible con tu aplicación o adaptar el conector a PostgreSQL si el proveedor elegido no ofrece MySQL.
