from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    designation = db.Column(db.String(50), nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    joining_date = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    profile_photo = db.Column(db.String(255))
    face_images_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='active')  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True, cascade='all, delete-orphan')
    payroll_records = db.relationship('Payroll', backref='employee', lazy=True, cascade='all, delete-orphan')

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    total_hours = db.Column(db.Float, default=0.0)
    late_entry = db.Column(db.Boolean, default=False)
    early_exit = db.Column(db.Boolean, default=False)
    overtime_hours = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='absent')  # present, absent, half_day, late
    confidence = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique employee per day
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_employee_date'),)

class Payroll(db.Model):
    __tablename__ = 'payroll'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    basic_salary = db.Column(db.Float, nullable=False)
    working_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    absent_days = db.Column(db.Integer, default=0)
    half_days = db.Column(db.Integer, default=0)
    late_days = db.Column(db.Integer, default=0)
    total_hours_worked = db.Column(db.Float, default=0.0)
    overtime_hours = db.Column(db.Float, default=0.0)
    per_day_salary = db.Column(db.Float, default=0.0)
    absent_deduction = db.Column(db.Float, default=0.0)
    half_day_deduction = db.Column(db.Float, default=0.0)
    late_deduction = db.Column(db.Float, default=0.0)
    overtime_bonus = db.Column(db.Float, default=0.0)
    gross_salary = db.Column(db.Float, nullable=False)
    net_salary = db.Column(db.Float, nullable=False)
    payslip_generated = db.Column(db.Boolean, default=False)
    payslip_path = db.Column(db.String(255))
    email_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Ensure unique employee per month
    __table_args__ = (db.UniqueConstraint('employee_id', 'month', 'year', name='unique_employee_month'),)

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), default='AI Attendance System')
    company_logo = db.Column(db.String(255))
    office_start_time = db.Column(db.String(5), default='09:00')
    office_end_time = db.Column(db.String(5), default='18:00')
    grace_period_minutes = db.Column(db.Integer, default=15)
    working_hours_per_day = db.Column(db.Float, default=9.0)
    late_deduction_enabled = db.Column(db.Boolean, default=False)
    late_deduction_per_occurrence = db.Column(db.Float, default=0.0)
    overtime_enabled = db.Column(db.Boolean, default=True)
    overtime_rate = db.Column(db.Float, default=1.5)
    face_recognition_tolerance = db.Column(db.Float, default=0.6)
    min_face_images_required = db.Column(db.Integer, default=20)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings

class WorkingHours(db.Model):
    __tablename__ = 'working_hours'
    
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    in_time = db.Column(db.DateTime, nullable=False)
    out_time = db.Column(db.DateTime)
    total_hours = db.Column(db.Float, default=0.0)
    is_late = db.Column(db.Boolean, default=False)
    is_early_exit = db.Column(db.Boolean, default=False)
    overtime_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
