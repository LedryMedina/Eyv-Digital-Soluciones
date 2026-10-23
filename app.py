import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esta-clave-en-produccion")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "eyv_digital_soluciones"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name"), "current_role": session.get("role")}

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM usuarios WHERE email=%s AND activo=1 LIMIT 1", (email,))
            user = cur.fetchone()
            cur.close(); conn.close()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["nombre"]
                session["role"] = user["rol"]
                return redirect(url_for("dashboard"))
            flash("Correo o contraseña incorrectos.", "danger")
        except Error as e:
            flash(f"No fue posible conectar con MySQL: {e}", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    data = {"tickets": 0, "open": 0, "progress": 0, "resolved": 0, "pending": 0, "clients": 0, "equipment": 0}
    recent = []
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) total FROM tickets"); data["tickets"] = cur.fetchone()["total"]
        for status, key in [("Abierto","open"),("En progreso","progress"),("Resuelto","resolved"),("Pendiente","pending")]:
            cur.execute("SELECT COUNT(*) total FROM tickets WHERE estado=%s", (status,))
            data[key] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM clientes"); data["clients"] = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) total FROM equipos"); data["equipment"] = cur.fetchone()["total"]
        cur.execute("""SELECT t.id,t.titulo,t.categoria,t.prioridad,t.estado,t.fecha_creacion,
                              c.nombre cliente, COALESCE(u.nombre,'Sin asignar') tecnico
                       FROM tickets t
                       LEFT JOIN clientes c ON c.id=t.cliente_id
                       LEFT JOIN usuarios u ON u.id=t.tecnico_id
                       ORDER BY t.fecha_creacion DESC LIMIT 8""")
        recent = cur.fetchall()
        cur.close(); conn.close()
    except Error:
        pass
    return render_template("dashboard.html", data=data, recent=recent)

@app.route("/tickets")
@login_required
def tickets():
    rows = []
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("""SELECT t.*, c.nombre cliente, COALESCE(u.nombre,'Sin asignar') tecnico
                       FROM tickets t
                       LEFT JOIN clientes c ON c.id=t.cliente_id
                       LEFT JOIN usuarios u ON u.id=t.tecnico_id
                       ORDER BY t.fecha_creacion DESC""")
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Error as e:
        flash(str(e), "danger")
    return render_template("tickets.html", tickets=rows)

@app.route("/tickets/nuevo", methods=["GET","POST"])
@login_required
def new_ticket():
    if request.method == "POST":
        form = request.form
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("""INSERT INTO tickets
                (cliente_id, titulo, descripcion, categoria, prioridad, estado, tecnico_id)
                VALUES (%s,%s,%s,%s,%s,'Abierto',%s)""",
                (form["cliente_id"], form["titulo"], form["descripcion"], form["categoria"],
                 form["prioridad"], form.get("tecnico_id") or None))
            conn.commit(); cur.close(); conn.close()
            flash("Ticket creado correctamente.", "success")
            return redirect(url_for("tickets"))
        except Error as e:
            flash(str(e), "danger")
    return render_template("ticket_form.html", clients=get_clients(), technicians=get_technicians())

@app.route("/tickets/<int:ticket_id>", methods=["GET","POST"])
@login_required
def ticket_detail(ticket_id):
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        if request.method == "POST":
            cur.execute("""UPDATE tickets SET estado=%s, prioridad=%s, tecnico_id=%s,
                           solucion=%s WHERE id=%s""",
                        (request.form["estado"], request.form["prioridad"],
                         request.form.get("tecnico_id") or None, request.form.get("solucion",""), ticket_id))
            conn.commit()
            flash("Ticket actualizado.", "success")
        cur.execute("""SELECT t.*, c.nombre cliente, c.email cliente_email,
                              COALESCE(u.nombre,'Sin asignar') tecnico
                       FROM tickets t LEFT JOIN clientes c ON c.id=t.cliente_id
                       LEFT JOIN usuarios u ON u.id=t.tecnico_id WHERE t.id=%s""", (ticket_id,))
        ticket = cur.fetchone()
        cur.close(); conn.close()
        if not ticket:
            return render_template("404.html"), 404
        return render_template("ticket_detail.html", ticket=ticket, technicians=get_technicians())
    except Error as e:
        flash(str(e), "danger")
        return redirect(url_for("tickets"))

@app.route("/clientes")
@login_required
def clients():
    return render_template("clients.html", clients=get_clients())

@app.route("/clientes/nuevo", methods=["GET","POST"])
@login_required
def new_client():
    if request.method == "POST":
        try:
            conn=get_db(); cur=conn.cursor()
            cur.execute("""INSERT INTO clientes (nombre,email,telefono,empresa) VALUES (%s,%s,%s,%s)""",
                        (request.form["nombre"],request.form["email"],request.form["telefono"],request.form["empresa"]))
            conn.commit(); cur.close(); conn.close()
            flash("Cliente registrado.", "success"); return redirect(url_for("clients"))
        except Error as e: flash(str(e), "danger")
    return render_template("client_form.html")

@app.route("/equipos")
@login_required
def equipment():
    rows=[]
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("""SELECT e.*, c.nombre cliente FROM equipos e
                       LEFT JOIN clientes c ON c.id=e.cliente_id ORDER BY e.id DESC""")
        rows=cur.fetchall(); cur.close(); conn.close()
    except Error as e: flash(str(e),"danger")
    return render_template("equipment.html", equipment=rows)

@app.route("/equipos/nuevo", methods=["GET","POST"])
@login_required
def new_equipment():
    if request.method=="POST":
        try:
            conn=get_db(); cur=conn.cursor()
            cur.execute("""INSERT INTO equipos (cliente_id,tipo,marca,modelo,serial,estado)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (request.form["cliente_id"],request.form["tipo"],request.form["marca"],
                         request.form["modelo"],request.form["serial"],request.form["estado"]))
            conn.commit(); cur.close(); conn.close()
            flash("Equipo registrado.","success"); return redirect(url_for("equipment"))
        except Error as e: flash(str(e),"danger")
    return render_template("equipment_form.html", clients=get_clients())

@app.route("/tecnicos")
@login_required
def technicians():
    return render_template("technicians.html", technicians=get_technicians())

@app.route("/mantenimientos")
@login_required
def maintenance():
    return render_template("maintenance.html")

@app.route("/incidentes-seguridad")
@login_required
def security_incidents():
    return render_template("security_incidents.html")

@app.route("/base-conocimientos")
@login_required
def knowledge():
    articles = [
        ("Restablecimiento de contraseña","Pasos generales para validar identidad y restablecer credenciales."),
        ("Diagnóstico de conectividad","Comprobar enlace, IP, DNS y conectividad antes de escalar."),
        ("Phishing","Identificar mensajes sospechosos y reportarlos al área de seguridad."),
        ("Mantenimiento preventivo","Lista básica de revisión de equipos y periféricos.")
    ]
    return render_template("knowledge.html", articles=articles)

@app.route("/reportes")
@login_required
def reports():
    return render_template("reports.html")

@app.route("/usuarios")
@login_required
def users():
    rows=[]
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id,nombre,email,rol,activo,fecha_creacion FROM usuarios ORDER BY id DESC")
        rows=cur.fetchall(); cur.close(); conn.close()
    except Error as e: flash(str(e),"danger")
    return render_template("users.html", users=rows)

@app.route("/configuracion")
@login_required
def configuration():
    return render_template("configuration.html")

@app.route("/perfil")
@login_required
def profile():
    return render_template("profile.html")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

def get_clients():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id,nombre,email,telefono,empresa FROM clientes ORDER BY nombre")
        rows=cur.fetchall(); cur.close(); conn.close(); return rows
    except Error:
        return []

def get_technicians():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT id,nombre,email FROM usuarios WHERE rol IN ('Administrador','Técnico') AND activo=1 ORDER BY nombre")
        rows=cur.fetchall(); cur.close(); conn.close(); return rows
    except Error:
        return []

if __name__ == "__main__":
    app.run(debug=True)
