# Eyv Digital Soluciones — Mesa de Ayuda

Plataforma web inicial para tickets, clientes, técnicos, inventario, mantenimiento, incidentes de seguridad, base de conocimiento, analítica y sugerencias locales por reglas.

## Tecnologías
Python + Flask, PostgreSQL + SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF/CSRF, HTML/CSS/JavaScript y Chart.js.

## Ejecutar localmente en Windows
1. Instala Python 3.12 y PostgreSQL.
2. Crea una base de datos llamada `eyv_digital`.
3. En PowerShell, desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edita `.env` y define `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`. Ejemplo de URL:
`postgresql+psycopg://postgres:TU_CLAVE@localhost:5432/eyv_digital`

No subas `.env` a GitHub. Usa una contraseña larga y única.

En instalación nueva:
```powershell
flask --app run.py db init
flask --app run.py db migrate -m "Esquema inicial"
flask --app run.py db upgrade
flask --app run.py init-admin
flask --app run.py run --debug
```
Abre `http://127.0.0.1:5000`. No repitas `db init` si ya existe la carpeta `migrations`.

## Crear datos ficticios
Con el administrador creado:
`flask --app run.py seed-demo`

Los datos de demostración son ficticios. No ejecutes en producción si ya existen empresas registradas.

## Publicar en GitHub y Render
- Sube el contenido del ZIP al repositorio.
- En Render crea PostgreSQL y un Web Service enlazado al repositorio.
- Build: `pip install -r requirements.txt`
- Start: `flask --app run.py init-admin && gunicorn run:app` para la primera versión (crea las tablas y el administrador si no existe).
- Define `DATABASE_URL` con la URL de conexión de PostgreSQL y `SECRET_KEY` como secreto.
- Define `ADMIN_EMAIL` y `ADMIN_PASSWORD` como variables privadas. El comando de inicio ejecuta `init-admin` de forma idempotente: crea tablas/roles faltantes y el administrador si no existe. En versiones futuras, añade migraciones versionadas y cambia el comando de inicio a `flask --app run.py db upgrade && gunicorn run:app`.
- `/health` comprueba conexión y estado básico.

`render.yaml` propone un Blueprint; verifica el plan/precio vigente de Render antes de desplegar. La disponibilidad gratuita, almacenamiento y condiciones de la base de datos pueden cambiar.

## Módulos incluidos
- Página pública y login.
- Dashboard con indicadores y gráficas.
- Tickets, comentarios, historial, asignación y filtros.
- Clientes y empresas.
- Usuarios y roles base.
- Inventario.
- Mantenimientos.
- Incidentes de seguridad.
- Base de conocimiento.
- Analítica y exportación CSV.
- Asistente de clasificación por reglas.
- Auditoría.
- Tema claro/oscuro y diseño adaptable.

## Consideraciones importantes
Es una base de desarrollo para revisión y ampliación, no una auditoría de seguridad ni una garantía de producción. Antes de trabajar con clientes reales:
- Ejecuta pruebas de integración en PostgreSQL.
- Revisa aislamiento multiempresa y permisos de todos los módulos.
- Añade paginación y límites de intentos de acceso.
- Completa edición/estado de mantenimientos y edición de artículos.
- Configura copias de seguridad, HTTPS y política de retención.
- Implementa pruebas automatizadas y recuperación de contraseña.
- Revisa logs, consultas y exportaciones con datos reales.

El asistente inteligente utiliza reglas locales deterministas; no es un modelo de machine learning entrenado ni utiliza servicios externos.
