from datetime import datetime,timezone
from functools import wraps
from flask import Blueprint,render_template,request,redirect,url_for,flash,abort,make_response
from flask_login import login_user,logout_user,login_required,current_user
from sqlalchemy import func,or_
from .extensions import db
from .models import User,Role,Company,Category,Ticket,TicketComment,TicketHistory,Asset,MaintenanceRecord,SecurityIncident,KnowledgeArticle,AuditLog

main_bp=Blueprint("main",__name__); auth_bp=Blueprint("auth",__name__); tickets_bp=Blueprint("tickets",__name__); admin_bp=Blueprint("admin",__name__)
PRIORITIES=["Baja","Media","Alta","Crítica"]; STATUSES=["Abierto","En proceso","En espera","Resuelto","Cerrado"]
CATEGORIES=["Hardware","Software","Sistemas operativos","Redes","Conectividad","Mantenimiento","Seguridad informática","Ciberseguridad"]

def roles_required(*names):
    def dec(fn):
        @wraps(fn)
        @login_required
        def wrapped(*a,**kw):
            if not current_user.role or current_user.role.name not in names: abort(403)
            return fn(*a,**kw)
        return wrapped
    return dec

def audit(action,kind,entity_id=None,detail=None):
    db.session.add(AuditLog(user_id=current_user.id if current_user.is_authenticated else None,action=action,entity_type=kind,entity_id=str(entity_id) if entity_id else None,detail=detail))

def visible_tickets():
    q=Ticket.query
    if current_user.is_admin: return q
    if current_user.is_technician: return q.filter(Ticket.assignee_id==current_user.id)
    return q.filter(Ticket.requester_id==current_user.id)

def categories_ready():
    changed=False
    for n in CATEGORIES:
        if not Category.query.filter_by(name=n).first(): db.session.add(Category(name=n)); changed=True
    if changed: db.session.commit()

@main_bp.get("/")
def landing():
    return redirect(url_for("main.dashboard")) if current_user.is_authenticated else render_template("landing.html")

@main_bp.get("/dashboard")
@login_required
def dashboard():
    categories_ready(); q=visible_tickets()
    total=q.count(); opened=q.filter_by(status="Abierto").count(); process=q.filter_by(status="En proceso").count(); waiting=q.filter_by(status="En espera").count()
    critical=q.filter(Ticket.priority=="Crítica",Ticket.status.notin_(["Resuelto","Cerrado"])).count()
    recent=q.order_by(Ticket.created_at.desc()).limit(7).all()
    catrows=[(c.name,q.filter_by(category_id=c.id).count()) for c in Category.query.order_by(Category.name).all()]
    return render_template("dashboard.html",total=total,opened=opened,process=process,waiting=waiting,critical=critical,recent=recent,status_labels=STATUSES,status_values=[q.filter_by(status=s).count() for s in STATUSES],priority_labels=PRIORITIES,priority_values=[q.filter_by(priority=p).count() for p in PRIORITIES],category_labels=[x[0] for x in catrows],category_values=[x[1] for x in catrows])

@auth_bp.route("/login",methods=["GET","POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("main.dashboard"))
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        user=User.query.filter_by(email=email,active=True).first()
        if user and user.check_password(password):
            login_user(user,remember=False); flash("Bienvenido a Eyv Digital Soluciones.","success")
            return redirect(url_for("main.dashboard"))
        flash("Correo o contraseña incorrectos, o cuenta inactiva.","danger")
    return render_template("login.html")

@auth_bp.post("/logout")
@login_required
def logout():
    logout_user(); flash("Sesión cerrada correctamente.","success"); return redirect(url_for("main.landing"))

@tickets_bp.get("/")
@login_required
def tickets_index():
    q=visible_tickets(); status=request.args.get("status",""); priority=request.args.get("priority",""); search=request.args.get("q","").strip()
    if status in STATUSES: q=q.filter_by(status=status)
    if priority in PRIORITIES: q=q.filter_by(priority=priority)
    if search:
        like=f"%{search}%"; q=q.filter(or_(Ticket.title.ilike(like),Ticket.description.ilike(like),Ticket.public_id.ilike(like)))
    tickets=q.order_by(Ticket.created_at.desc()).all()
    return render_template("tickets.html",tickets=tickets,statuses=STATUSES,priorities=PRIORITIES,selected_status=status,selected_priority=priority,search=search)

@tickets_bp.route("/new",methods=["GET","POST"])
@login_required
def ticket_new():
    categories_ready(); categories=Category.query.filter_by(active=True).order_by(Category.name).all()
    companies=Company.query.filter_by(active=True).order_by(Company.name).all() if current_user.is_admin else ([current_user.company] if current_user.company else [])
    aq=Asset.query
    if not current_user.is_admin: aq=aq.filter_by(company_id=current_user.company_id)
    assets=aq.order_by(Asset.name).all()
    if request.method=="POST":
        title=request.form.get("title","").strip(); desc=request.form.get("description","").strip()
        cat=db.session.get(Category,request.form.get("category_id",type=int)); priority=request.form.get("priority","Media")
        company_id=request.form.get("company_id",type=int) if current_user.is_admin else current_user.company_id
        company=db.session.get(Company,company_id) if company_id else current_user.company
        asset_id=request.form.get("asset_id",type=int); asset=db.session.get(Asset,asset_id) if asset_id else None
        if not title or not desc or not cat or priority not in PRIORITIES: flash("Completa los campos obligatorios.","danger")
        elif not current_user.is_admin and not current_user.is_technician and current_user.company_id is None: flash("Tu usuario debe estar asociado a una empresa para crear solicitudes.","danger")
        elif asset and not current_user.is_admin and asset.company_id!=current_user.company_id: abort(403)
        elif current_user.is_admin and company_id and not company: flash("Empresa no válida.","danger")
        else:
            t=Ticket(title=title,description=desc,category=cat,priority=priority,company=company,requester=current_user,asset=asset)
            db.session.add(t); db.session.flush(); t.public_id=f"EYV-{t.id:05d}"
            db.session.add(TicketHistory(ticket=t,user=current_user,action="Ticket creado",detail=f"Prioridad inicial: {priority}")); audit("crear","ticket",t.id,title); db.session.commit()
            flash(f"Solicitud {t.public_id} creada.","success"); return redirect(url_for("tickets.ticket_detail",ticket_id=t.id))
    return render_template("ticket_form.html",categories=categories,priorities=PRIORITIES,companies=companies,assets=assets)

@tickets_bp.route("/<int:ticket_id>",methods=["GET","POST"])
@login_required
def ticket_detail(ticket_id):
    t=db.session.get_or_404(Ticket,ticket_id)
    if not current_user.is_admin and not (current_user.is_technician and t.assignee_id==current_user.id) and t.requester_id!=current_user.id: abort(403)
    technicians=User.query.join(Role).filter(Role.name.in_(["Técnico","Soporte TI"]),User.active.is_(True)).order_by(User.name).all() if current_user.is_admin else []
    if request.method=="POST":
        action=request.form.get("action")
        if action=="comment":
            body=request.form.get("body","").strip(); internal=request.form.get("internal")=="on" and current_user.is_admin
            if not body: flash("El comentario no puede estar vacío.","danger")
            else:
                db.session.add(TicketComment(ticket=t,user=current_user,body=body,internal=internal))
                db.session.add(TicketHistory(ticket=t,user=current_user,action="Comentario añadido",detail="Nota interna" if internal else "Comentario visible"))
                if not t.first_response_at and current_user.id!=t.requester_id: t.first_response_at=datetime.now(timezone.utc)
                audit("comentario","ticket",t.id); db.session.commit(); flash("Comentario registrado.","success")
            return redirect(url_for("tickets.ticket_detail",ticket_id=t.id))
        if not current_user.is_admin and not (current_user.is_technician and t.assignee_id==current_user.id): abort(403)
        if action=="update":
            status=request.form.get("status",t.status); priority=request.form.get("priority",t.priority)
            if status not in STATUSES or priority not in PRIORITIES: flash("Estado o prioridad no válidos.","danger")
            else:
                old=t.status; t.status=status; t.priority=priority; t.diagnosis=request.form.get("diagnosis","").strip()[:10000]; t.resolution=request.form.get("resolution","").strip()[:10000]
                t.resolved_at=datetime.now(timezone.utc) if status in ("Resuelto","Cerrado") else None
                db.session.add(TicketHistory(ticket=t,user=current_user,action="Ticket actualizado",detail=f"{old} → {status}; prioridad {priority}")); audit("actualizar","ticket",t.id); db.session.commit(); flash("Ticket actualizado.","success")
            return redirect(url_for("tickets.ticket_detail",ticket_id=t.id))
        if action=="assign" and current_user.is_admin:
            assignee=db.session.get(User,request.form.get("assignee_id",type=int)) if request.form.get("assignee_id") else None
            if assignee and (not assignee.is_technician or not assignee.active): flash("Técnico no válido.","danger")
            else:
                t.assignee=assignee; db.session.add(TicketHistory(ticket=t,user=current_user,action="Asignación modificada",detail=assignee.name if assignee else "Sin asignar")); audit("asignar","ticket",t.id); db.session.commit(); flash("Asignación actualizada.","success")
            return redirect(url_for("tickets.ticket_detail",ticket_id=t.id))
        abort(400)
    comments=[c for c in t.comments if not c.internal or current_user.is_admin]
    return render_template("ticket_detail.html",ticket=t,statuses=STATUSES,priorities=PRIORITIES,technicians=technicians,comments=comments)

@admin_bp.before_request
@login_required
def admin_guard():
    if not current_user.is_authenticated: return redirect(url_for("auth.login"))
    if not current_user.is_admin: abort(403)

@admin_bp.get("/")
def admin_home():
    from .models import SecurityIncident
    return render_template("admin_home.html",users_count=User.query.count(),companies_count=Company.query.count(),assets_count=Asset.query.count(),incidents_count=SecurityIncident.query.count())

@admin_bp.route("/companies",methods=["GET","POST"])
def companies():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if not name: flash("Nombre obligatorio.","danger")
        else:
            c=Company(name=name,contact_name=request.form.get("contact_name","").strip(),email=request.form.get("email","").strip().lower() or None,phone=request.form.get("phone","").strip(),address=request.form.get("address","").strip())
            db.session.add(c); audit("crear","empresa",detail=name); db.session.commit(); flash("Empresa creada.","success"); return redirect(url_for("admin.companies"))
    return render_template("companies.html",companies=Company.query.order_by(Company.name).all())

@admin_bp.route("/users",methods=["GET","POST"])
def users():
    roles=Role.query.order_by(Role.name).all(); companies=Company.query.order_by(Company.name).all()
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        role=db.session.get(Role,request.form.get("role_id",type=int)); company=db.session.get(Company,request.form.get("company_id",type=int)) if request.form.get("company_id") else None
        if not name or not email or len(password)<10 or not role: flash("Completa los campos y utiliza contraseña de mínimo 10 caracteres.","danger")
        elif User.query.filter_by(email=email).first(): flash("Ese correo ya existe.","danger")
        else:
            u=User(name=name,email=email,role=role,company=company,phone=request.form.get("phone","").strip(),active=True); u.set_password(password)
            db.session.add(u); audit("crear","usuario",detail=email); db.session.commit(); flash("Usuario creado.","success"); return redirect(url_for("admin.users"))
    return render_template("users.html",users=User.query.order_by(User.created_at.desc()).all(),roles=roles,companies=companies)

@admin_bp.post("/users/<int:user_id>/toggle")
def toggle_user(user_id):
    u=db.session.get_or_404(User,user_id)
    if u.id==current_user.id: flash("No puedes desactivar tu propia cuenta.","warning")
    else: u.active=not u.active; audit("cambiar estado","usuario",u.id); db.session.commit(); flash("Estado actualizado.","success")
    return redirect(url_for("admin.users"))

@admin_bp.route("/assets",methods=["GET","POST"])
def assets():
    companies=Company.query.order_by(Company.name).all()
    if request.method=="POST":
        name=request.form.get("name","").strip(); typ=request.form.get("asset_type","").strip(); serial=request.form.get("serial_number","").strip() or None
        if not name or not typ: flash("Nombre y tipo son obligatorios.","danger")
        elif serial and Asset.query.filter_by(serial_number=serial).first(): flash("El número de serie ya existe.","danger")
        else:
            a=Asset(name=name,asset_type=typ,brand=request.form.get("brand","").strip(),model=request.form.get("model","").strip(),serial_number=serial,operating_system=request.form.get("operating_system","").strip(),location=request.form.get("location","").strip(),company_id=request.form.get("company_id",type=int) or None)
            db.session.add(a); audit("crear","equipo",detail=name); db.session.commit(); flash("Equipo registrado.","success"); return redirect(url_for("admin.assets"))
    return render_template("assets.html",assets=Asset.query.order_by(Asset.created_at.desc()).all(),companies=companies)

@admin_bp.route("/maintenance",methods=["GET","POST"])
def maintenance():
    companies=Company.query.order_by(Company.name).all(); assets=Asset.query.order_by(Asset.name).all()
    techs=User.query.join(Role).filter(Role.name.in_(["Técnico","Soporte TI"]),User.active.is_(True)).all()
    if request.method=="POST":
        title=request.form.get("title","").strip()
        if not title: flash("El título es obligatorio.","danger")
        else:
            try: scheduled=datetime.fromisoformat(request.form.get("scheduled_at","")) if request.form.get("scheduled_at") else None
            except ValueError: scheduled=None
            r=MaintenanceRecord(title=title,description=request.form.get("description","").strip(),maintenance_type=request.form.get("maintenance_type","Preventivo"),scheduled_at=scheduled,company_id=request.form.get("company_id",type=int) or None,asset_id=request.form.get("asset_id",type=int) or None,technician_id=request.form.get("technician_id",type=int) or None)
            db.session.add(r); audit("crear","mantenimiento",detail=title); db.session.commit(); flash("Mantenimiento programado.","success"); return redirect(url_for("admin.maintenance"))
    return render_template("maintenance.html",records=MaintenanceRecord.query.order_by(MaintenanceRecord.created_at.desc()).all(),companies=companies,assets=assets,technicians=techs)

@admin_bp.route("/incidents",methods=["GET","POST"])
def incidents():
    from .models import SecurityIncident
    companies=Company.query.order_by(Company.name).all(); assets=Asset.query.order_by(Asset.name).all()
    techs=User.query.join(Role).filter(Role.name.in_(["Técnico","Soporte TI"]),User.active.is_(True)).all()
    if request.method=="POST":
        title=request.form.get("title","").strip(); desc=request.form.get("description","").strip()
        if not title or not desc: flash("Título y descripción obligatorios.","danger")
        else:
            i=SecurityIncident(title=title,incident_type=request.form.get("incident_type","Otro"),description=desc,risk=request.form.get("risk","Medio"),company_id=request.form.get("company_id",type=int) or None,asset_id=request.form.get("asset_id",type=int) or None,reported_by_id=current_user.id,assignee_id=request.form.get("assignee_id",type=int) or None)
            db.session.add(i); audit("crear","incidente_seguridad",detail=title); db.session.commit(); flash("Incidente registrado.","success"); return redirect(url_for("admin.incidents"))
    return render_template("incidents.html",records=SecurityIncident.query.order_by(SecurityIncident.created_at.desc()).all(),companies=companies,assets=assets,technicians=techs)

@admin_bp.post("/incidents/<int:incident_id>/update")
def update_incident(incident_id):
    from .models import SecurityIncident
    i=db.session.get_or_404(SecurityIncident,incident_id); i.status=request.form.get("status",i.status); i.risk=request.form.get("risk",i.risk)
    i.containment=request.form.get("containment","").strip(); i.corrective_actions=request.form.get("corrective_actions","").strip()
    if i.status=="Cerrado": i.closed_at=datetime.now(timezone.utc)
    audit("actualizar","incidente_seguridad",i.id,i.status); db.session.commit(); flash("Incidente actualizado.","success"); return redirect(url_for("admin.incidents"))

@admin_bp.route("/knowledge",methods=["GET","POST"])
def knowledge():
    if request.method=="POST":
        title=request.form.get("title","").strip(); problem=request.form.get("problem","").strip(); steps=request.form.get("steps","").strip(); solution=request.form.get("solution","").strip()
        if not all([title,problem,steps,solution]): flash("Completa los campos obligatorios.","danger")
        else:
            a=KnowledgeArticle(title=title,category=request.form.get("category","General"),problem=problem,steps=steps,solution=solution,visibility=request.form.get("visibility","Interno"),published=request.form.get("published")=="on",author=current_user)
            db.session.add(a); audit("crear","articulo",detail=title); db.session.commit(); flash("Artículo guardado.","success"); return redirect(url_for("admin.knowledge"))
    return render_template("knowledge.html",articles=KnowledgeArticle.query.order_by(KnowledgeArticle.updated_at.desc()).all(),categories=CATEGORIES)

@admin_bp.get("/analytics")
def analytics():
    status=db.session.query(Ticket.status,func.count(Ticket.id)).group_by(Ticket.status).all()
    priority=db.session.query(Ticket.priority,func.count(Ticket.id)).group_by(Ticket.priority).all()
    category=db.session.query(Category.name,func.count(Ticket.id)).outerjoin(Ticket).group_by(Category.id).all()
    tech=db.session.query(User.name,func.count(Ticket.id)).join(Ticket,Ticket.assignee_id==User.id,isouter=True).join(Role).filter(Role.name.in_(["Técnico","Soporte TI"])).group_by(User.id).all()
    return render_template("analytics.html",status_rows=status,priority_rows=priority,category_rows=category,tech_rows=tech,total=Ticket.query.count())

@admin_bp.get("/ai")
def ai(): return render_template("ai.html")

@admin_bp.post("/ai/suggest")
def ai_suggest():
    text=request.form.get("description","").strip().lower()
    if not text: flash("Escribe una descripción para analizar.","danger"); return redirect(url_for("admin.ai"))
    rules=[
      (["phishing","correo sospechoso","enlace sospechoso","suplantación"],"Ciberseguridad","Alta","No abras enlaces ni adjuntos; conserva el mensaje y repórtalo al equipo autorizado."),
      (["virus","malware","ransomware","archivo malicioso"],"Seguridad informática","Crítica","Aísla el equipo según el procedimiento autorizado y escala al responsable de seguridad."),
      (["wifi","internet","red","conectividad","router"],"Redes","Media","Verifica conexión física, alcance y si el problema afecta a uno o varios usuarios."),
      (["pantalla","no enciende","teclado","disco","hardware"],"Hardware","Media","Registra síntomas, equipo afectado y cambios recientes antes de realizar pruebas."),
      (["instalar","aplicación","programa","software","error"],"Software","Media","Registra aplicación, sistema operativo, mensaje exacto y pasos para reproducir el error."),
      (["lento","mantenimiento","limpieza","sobrecalienta"],"Mantenimiento","Baja","Revisa recursos, ventilación y estado general según el procedimiento autorizado.")]
    found=next((r for keys,*r in rules if any(k in text for k in keys)),None)
    if found: category,priority,recommendation=found; basis="Coincidencia con palabras clave; no es un modelo entrenado."
    else: category,priority,recommendation="Software","Media","Solicita más detalles, registra el mensaje de error y reproduce el problema en un entorno autorizado."; basis="Sugerencia general; requiere validación técnica."
    return render_template("ai.html",result={"category":category,"priority":priority,"recommendation":recommendation,"basis":basis},description=request.form.get("description",""))

@admin_bp.get("/audit")
def audit_page(): return render_template("audit.html",logs=AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all())

@admin_bp.get("/export/tickets.csv")
def export_tickets():
    import csv,io
    out=io.StringIO(); w=csv.writer(out); w.writerow(["Ticket","Título","Estado","Prioridad","Categoría","Empresa","Solicitante","Técnico","Creado"])
    for t in Ticket.query.order_by(Ticket.created_at.desc()).all():
        w.writerow([t.public_id or t.id,t.title,t.status,t.priority,t.category.name if t.category else "",t.company.name if t.company else "",t.requester.name if t.requester else "",t.assignee.name if t.assignee else "",t.created_at.isoformat() if t.created_at else ""])
    res=make_response("\\ufeff"+out.getvalue()); res.headers["Content-Type"]="text/csv; charset=utf-8"; res.headers["Content-Disposition"]="attachment; filename=eyv_tickets.csv"; return res
