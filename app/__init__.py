import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from .extensions import db
from .models import User, Role
from .routes import main_bp, auth_bp, tickets_bp, admin_bp

login_manager=LoginManager()
migrate=Migrate()
csrf=CSRFProtect()

def normalize_url(url):
    if url.startswith("postgres://"): return url.replace("postgres://","postgresql+psycopg://",1)
    if url.startswith("postgresql://") and "+psycopg" not in url: return url.replace("postgresql://","postgresql+psycopg://",1)
    return url

def create_app():
    app=Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("SECRET_KEY","dev-only-change-this-key"),SQLALCHEMY_DATABASE_URI=normalize_url(os.environ.get("DATABASE_URL","sqlite:///eyv_dev.db")),SQLALCHEMY_TRACK_MODIFICATIONS=False,MAX_CONTENT_LENGTH=8*1024*1024,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax",SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE","false").lower()=="true")
    db.init_app(app); migrate.init_app(app,db); login_manager.init_app(app); csrf.init_app(app)
    login_manager.login_view="auth.login"; login_manager.login_message="Inicia sesión para continuar."
    app.register_blueprint(main_bp); app.register_blueprint(auth_bp,url_prefix="/auth"); app.register_blueprint(tickets_bp,url_prefix="/tickets"); app.register_blueprint(admin_bp,url_prefix="/admin")
    @login_manager.user_loader
    def load_user(uid):
        try: return db.session.get(User,int(uid))
        except (ValueError,TypeError): return None
    @app.context_processor
    def globals_template(): return {"company_name":"Eyv Digital Soluciones"}
    @app.errorhandler(403)
    def forbidden(e): return render_template("errors/403.html"),403
    @app.errorhandler(404)
    def not_found(e): return render_template("errors/404.html"),404
    @app.get("/health")
    def health():
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
        return {"status":"ok","database":"connected"}
    @app.cli.command("init-admin")
    def init_admin():
        db.create_all()
        for role_name in ["Administrador","Técnico","Soporte TI","Cliente"]:
            if not Role.query.filter_by(name=role_name).first(): db.session.add(Role(name=role_name))
        db.session.commit()
        email=os.environ.get("ADMIN_EMAIL","admin@eyvdigital.local").strip().lower()
        password=os.environ.get("ADMIN_PASSWORD")
        if not password:
            print("Configura ADMIN_PASSWORD antes de crear el administrador."); return
        if User.query.filter_by(email=email).first():
            print("La cuenta ya existe; no se cambió la contraseña."); return
        role=Role.query.filter_by(name="Administrador").first()
        user=User(name=os.environ.get("ADMIN_NAME","Administrador Eyv"),email=email,role=role,active=True)
        user.set_password(password); db.session.add(user); db.session.commit()
        print("Administrador creado. Cambia la contraseña tras el primer acceso.")
    @app.cli.command("seed-demo")
    def seed_demo():
        from .models import Company,Category,Ticket,Asset
        db.create_all()
        admin=User.query.filter_by(email=os.environ.get("ADMIN_EMAIL","admin@eyvdigital.local").lower()).first()
        if not admin: print("Primero ejecuta flask --app run.py init-admin."); return
        if Company.query.first(): print("Ya existen empresas; se evita duplicar la demo."); return
        company=Company(name="Empresa Demo Ficticia",contact_name="Contacto de demostración",email="demo@example.com",phone="0000000000")
        techrole=Role.query.filter_by(name="Técnico").first()
        tech=User(name="Técnico Demo",email="tecnico@example.com",role=techrole,company=company,active=True); tech.set_password("DemoTecnico123!")
        db.session.add_all([company,tech]); db.session.flush()
        names=["Hardware","Software","Sistemas operativos","Redes","Conectividad","Mantenimiento","Seguridad informática","Ciberseguridad"]
        cats={}
        for name in names:
            cat=Category.query.filter_by(name=name).first()
            if not cat: cat=Category(name=name); db.session.add(cat)
            cats[name]=cat
        asset=Asset(name="Portátil de demostración",asset_type="Portátil",brand="Marca ficticia",model="Demo",serial_number="DEMO-0001",company=company,status="Activo")
        db.session.add(asset); db.session.flush()
        examples=[("Equipo no enciende","El equipo de demostración no inicia.","Alta","Abierto","Hardware"),("Revisión de conectividad","Verificar la conexión de red de la empresa ficticia.","Media","En proceso","Redes"),("Correo sospechoso","Ejemplo ficticio para practicar registro defensivo.","Crítica","En espera","Ciberseguridad"),("Mantenimiento preventivo","Revisión general de un equipo ficticio.","Baja","Resuelto","Mantenimiento")]
        for title,desc,priority,status,cat in examples:
            t=Ticket(title=title,description=desc,priority=priority,status=status,category=cats[cat],company=company,requester=admin,assignee=tech,asset=asset)
            db.session.add(t); db.session.flush(); t.public_id=f"EYV-{t.id:05d}"; db.session.add(TicketHistory(ticket=t,user=admin,action="Ticket de demostración creado",detail="Datos ficticios"))
        db.session.commit(); print("Datos ficticios de demostración creados.")
    return app
