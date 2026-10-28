from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

def now(): return datetime.now(timezone.utc)

class Role(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(40),unique=True,nullable=False)
    users=db.relationship("User",back_populates="role")

class Company(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(160),nullable=False,index=True)
    tax_id=db.Column(db.String(40),unique=True)
    contact_name=db.Column(db.String(120)); email=db.Column(db.String(160)); phone=db.Column(db.String(40)); address=db.Column(db.String(240))
    active=db.Column(db.Boolean,default=True,nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    users=db.relationship("User",back_populates="company")
    tickets=db.relationship("Ticket",back_populates="company")

class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),nullable=False)
    email=db.Column(db.String(160),unique=True,nullable=False,index=True)
    password_hash=db.Column(db.String(255),nullable=False)
    role_id=db.Column(db.Integer,db.ForeignKey("role.id"),nullable=False)
    company_id=db.Column(db.Integer,db.ForeignKey("company.id"))
    phone=db.Column(db.String(40)); active=db.Column(db.Boolean,default=True,nullable=False)
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    role=db.relationship("Role",back_populates="users"); company=db.relationship("Company",back_populates="users")
    requested_tickets=db.relationship("Ticket",foreign_keys="Ticket.requester_id",back_populates="requester")
    assigned_tickets=db.relationship("Ticket",foreign_keys="Ticket.assignee_id",back_populates="assignee")
    def set_password(self,p): self.password_hash=generate_password_hash(p)
    def check_password(self,p): return check_password_hash(self.password_hash,p)
    @property
    def is_admin(self): return bool(self.role and self.role.name=="Administrador")
    @property
    def is_technician(self): return bool(self.role and self.role.name in ("Técnico","Soporte TI"))

class Category(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(80),unique=True,nullable=False); active=db.Column(db.Boolean,default=True,nullable=False)
    tickets=db.relationship("Ticket",back_populates="category")

class Asset(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(160),nullable=False); asset_type=db.Column(db.String(80),nullable=False)
    brand=db.Column(db.String(80)); model=db.Column(db.String(80)); serial_number=db.Column(db.String(120),unique=True)
    operating_system=db.Column(db.String(100)); location=db.Column(db.String(160)); status=db.Column(db.String(40),default="Activo",nullable=False)
    company_id=db.Column(db.Integer,db.ForeignKey("company.id")); company=db.relationship("Company")
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    tickets=db.relationship("Ticket",back_populates="asset")
    maintenance_records=db.relationship("MaintenanceRecord",back_populates="asset")

class Ticket(db.Model):
    id=db.Column(db.Integer,primary_key=True); public_id=db.Column(db.String(20),unique=True,index=True)
    title=db.Column(db.String(180),nullable=False); description=db.Column(db.Text,nullable=False)
    priority=db.Column(db.String(20),default="Media",nullable=False,index=True); status=db.Column(db.String(30),default="Abierto",nullable=False,index=True)
    category_id=db.Column(db.Integer,db.ForeignKey("category.id"),nullable=False); company_id=db.Column(db.Integer,db.ForeignKey("company.id"))
    requester_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False); assignee_id=db.Column(db.Integer,db.ForeignKey("user.id"))
    asset_id=db.Column(db.Integer,db.ForeignKey("asset.id")); diagnosis=db.Column(db.Text); resolution=db.Column(db.Text)
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False,index=True); updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now,nullable=False)
    first_response_at=db.Column(db.DateTime(timezone=True)); resolved_at=db.Column(db.DateTime(timezone=True))
    category=db.relationship("Category",back_populates="tickets"); company=db.relationship("Company",back_populates="tickets")
    requester=db.relationship("User",foreign_keys=[requester_id],back_populates="requested_tickets")
    assignee=db.relationship("User",foreign_keys=[assignee_id],back_populates="assigned_tickets")
    asset=db.relationship("Asset",back_populates="tickets")
    comments=db.relationship("TicketComment",back_populates="ticket",cascade="all, delete-orphan",order_by="TicketComment.created_at")
    history=db.relationship("TicketHistory",back_populates="ticket",cascade="all, delete-orphan",order_by="TicketHistory.created_at")

class TicketComment(db.Model):
    id=db.Column(db.Integer,primary_key=True); ticket_id=db.Column(db.Integer,db.ForeignKey("ticket.id"),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False); body=db.Column(db.Text,nullable=False)
    internal=db.Column(db.Boolean,default=False,nullable=False); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    ticket=db.relationship("Ticket",back_populates="comments"); user=db.relationship("User")

class TicketHistory(db.Model):
    id=db.Column(db.Integer,primary_key=True); ticket_id=db.Column(db.Integer,db.ForeignKey("ticket.id"),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False); action=db.Column(db.String(120),nullable=False)
    detail=db.Column(db.String(500)); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    ticket=db.relationship("Ticket",back_populates="history"); user=db.relationship("User")

class MaintenanceRecord(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(180),nullable=False); description=db.Column(db.Text)
    maintenance_type=db.Column(db.String(30),default="Preventivo",nullable=False); status=db.Column(db.String(30),default="Programado",nullable=False)
    scheduled_at=db.Column(db.DateTime(timezone=True)); completed_at=db.Column(db.DateTime(timezone=True))
    company_id=db.Column(db.Integer,db.ForeignKey("company.id")); asset_id=db.Column(db.Integer,db.ForeignKey("asset.id")); technician_id=db.Column(db.Integer,db.ForeignKey("user.id"))
    created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    asset=db.relationship("Asset",back_populates="maintenance_records"); company=db.relationship("Company"); technician=db.relationship("User")

class SecurityIncident(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(180),nullable=False); incident_type=db.Column(db.String(80),nullable=False)
    description=db.Column(db.Text,nullable=False); risk=db.Column(db.String(20),default="Medio",nullable=False); status=db.Column(db.String(30),default="Reportado",nullable=False)
    company_id=db.Column(db.Integer,db.ForeignKey("company.id")); asset_id=db.Column(db.Integer,db.ForeignKey("asset.id"))
    reported_by_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False); assignee_id=db.Column(db.Integer,db.ForeignKey("user.id"))
    containment=db.Column(db.Text); corrective_actions=db.Column(db.Text); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False); closed_at=db.Column(db.DateTime(timezone=True))
    company=db.relationship("Company"); asset=db.relationship("Asset"); reporter=db.relationship("User",foreign_keys=[reported_by_id]); assignee=db.relationship("User",foreign_keys=[assignee_id])

class KnowledgeArticle(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(180),nullable=False); category=db.Column(db.String(80),nullable=False)
    problem=db.Column(db.Text,nullable=False); steps=db.Column(db.Text,nullable=False); solution=db.Column(db.Text,nullable=False)
    visibility=db.Column(db.String(30),default="Interno",nullable=False); published=db.Column(db.Boolean,default=False,nullable=False)
    author_id=db.Column(db.Integer,db.ForeignKey("user.id"),nullable=False); updated_at=db.Column(db.DateTime(timezone=True),default=now,onupdate=now,nullable=False)
    author=db.relationship("User")

class AuditLog(db.Model):
    id=db.Column(db.Integer,primary_key=True); user_id=db.Column(db.Integer,db.ForeignKey("user.id")); action=db.Column(db.String(120),nullable=False)
    entity_type=db.Column(db.String(80),nullable=False); entity_id=db.Column(db.String(80)); detail=db.Column(db.String(500)); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)
    user=db.relationship("User")
