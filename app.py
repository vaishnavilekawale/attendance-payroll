from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import cv2
import numpy as np
from datetime import datetime, date
import json

from config import config, Config
from database import db, init_db
from models import Admin, Employee, Attendance, Payroll, Settings
from ai_engine import FaceRecognitionEngine, FaceDetectionEngine, FaceCapture, train_all_employees
from attendance import AttendanceManager
from payroll import PayrollCalculator
from email_service import EmailService
from pdf_generator import PDFGenerator

app = Flask(__name__)
app.config.from_object(config['default'])

# Initialize database
init_db(app)

# Initialize services (will be initialized within app context)
attendance_manager = None
payroll_calculator = None
email_service = None
pdf_generator = None

def get_services():
    global attendance_manager, payroll_calculator, email_service, pdf_generator
    if attendance_manager is None:
        attendance_manager = AttendanceManager()
    if payroll_calculator is None:
        payroll_calculator = PayrollCalculator()
    if email_service is None:
        email_service = EmailService()
    if pdf_generator is None:
        pdf_generator = PDFGenerator()
    return attendance_manager, payroll_calculator, email_service, pdf_generator

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# ==================== AUTH ROUTES ====================

@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            admin.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    
    # Initialize services
    am, _, _, _ = get_services()
    
    # Today's attendance stats
    today_attendance = Attendance.query.filter_by(date=today).all()
    present = len([a for a in today_attendance if a.status == 'present'])
    absent = len([a for a in today_attendance if a.status == 'absent'])
    late = len([a for a in today_attendance if a.late_entry])
    
    # Employee stats
    total_employees = Employee.query.filter_by(status='active').count()
    
    # Payroll status
    current_month = datetime.now().month
    current_year = datetime.now().year
    payroll_generated = Payroll.query.filter_by(month=current_month, year=current_year).count()
    
    # Recent attendance
    recent_attendance = Attendance.query.order_by(Attendance.created_at.desc()).limit(10).all()
    
    # Department stats
    dept_stats = am.get_department_stats(today, today)
    
    return render_template('dashboard.html',
                         present=present,
                         absent=absent,
                         late=late,
                         total_employees=total_employees,
                         payroll_generated=payroll_generated,
                         recent_attendance=recent_attendance,
                         dept_stats=dept_stats)

# ==================== EMPLOYEE ROUTES ====================

@app.route('/employees')
@login_required
def employees():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    query = Employee.query.filter_by(status='active')
    
    if search:
        query = query.filter(
            (Employee.name.contains(search)) |
            (Employee.employee_id.contains(search)) |
            (Employee.department.contains(search))
        )
    
    employees = query.order_by(Employee.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('add_employee.html', employees=employees, search=search)

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        # Generate employee ID
        last_employee = Employee.query.order_by(Employee.id.desc()).first()
        if last_employee:
            new_id = f"EMP{last_employee.id + 1:04d}"
        else:
            new_id = "EMP0001"
        
        # Handle profile photo
        profile_photo = None
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{new_id}_{file.filename}")
                profile_photo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(profile_photo)
                profile_photo = f"uploads/{filename}"
        
        employee = Employee(
            employee_id=new_id,
            name=request.form.get('name'),
            department=request.form.get('department'),
            designation=request.form.get('designation'),
            basic_salary=float(request.form.get('basic_salary')),
            joining_date=datetime.strptime(request.form.get('joining_date'), '%Y-%m-%d').date(),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            profile_photo=profile_photo,
            status='active'
        )
        
        db.session.add(employee)
        db.session.commit()
        
        flash(f'Employee {new_id} added successfully', 'success')
        return redirect(url_for('employees'))
    
    return render_template('add_employee.html')

@app.route('/employees/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    employees = Employee.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        employee.name = request.form.get('name')
        employee.department = request.form.get('department')
        employee.designation = request.form.get('designation')
        employee.basic_salary = float(request.form.get('basic_salary'))
        employee.email = request.form.get('email')
        employee.phone = request.form.get('phone')
        employee.address = request.form.get('address')
        
        # Handle profile photo
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{employee.employee_id}_{file.filename}")
                profile_photo = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(profile_photo)
                employee.profile_photo = f"uploads/{filename}"
        
        db.session.commit()
        flash('Employee updated successfully', 'success')
        return redirect(url_for('employees'))
    
    return render_template('add_employee.html', employee=employee, employees=employees)

@app.route('/employees/delete/<int:id>')
@login_required
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    
    # Remove from face recognition
    recognizer = FaceRecognitionEngine()
    recognizer.remove_employee(str(employee.id))
    
    # Delete employee
    db.session.delete(employee)
    db.session.commit()
    
    flash('Employee deleted successfully', 'success')
    return redirect(url_for('employees'))

@app.route('/employees/<int:id>')
@login_required
def view_employee(id):
    employee = Employee.query.get_or_404(id)
    attendance = Attendance.query.filter_by(employee_id=id).order_by(Attendance.date.desc()).limit(30).all()
    employees = Employee.query.filter_by(status='active').all()
    return render_template('add_employee.html', employee=employee, attendance=attendance, employees=employees)

# ==================== FACE REGISTRATION ROUTES ====================

@app.route('/face-registration/<int:id>')
@login_required
def face_registration(id):
    employee = Employee.query.get_or_404(id)
    employees = Employee.query.filter_by(status='active').all()
    return render_template('add_employee.html', employee=employee, employees=employees, face_registration=True)

@app.route('/capture-face/<int:id>', methods=['POST'])
@login_required
def capture_face(id):
    employee = Employee.query.get_or_404(id)
    num_images = int(request.form.get('num_images', 20))
    
    capture = FaceCapture(str(employee.id), num_images)
    
    try:
        cap = capture.start_capture()
        captured = 0
        
        while captured < num_images:
            ret, frame = capture.capture_frame()
            if ret:
                captured = capture.captured_count
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        capture.stop_capture()
        
        # Update employee
        employee.face_images_count = captured
        db.session.commit()
        
        # Train AI
        recognizer = FaceRecognitionEngine()
        image_paths = capture.get_captured_images()
        trained_count = recognizer.train_employee(str(employee.id), employee.name, image_paths)
        
        flash(f'Captured {captured} images and trained {trained_count} encodings', 'success')
        return redirect(url_for('view_employee', id=id))
    
    except Exception as e:
        capture.stop_capture()
        flash(f'Error capturing faces: {str(e)}', 'danger')
        return redirect(url_for('face_registration', id=id))

@app.route('/train-ai')
@login_required
def train_ai():
    try:
        train_all_employees()
        flash('AI model trained successfully for all employees', 'success')
    except Exception as e:
        flash(f'Error training AI: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# ==================== ATTENDANCE ROUTES ====================

@app.route('/attendance')
@login_required
def attendance():
    today = date.today()
    attendances = Attendance.query.filter_by(date=today).order_by(Attendance.in_time.desc()).all()
    return render_template('attendance.html', attendances=attendances, today=today)

@app.route('/attendance/mark', methods=['POST'])
@login_required
def mark_attendance():
    employee_id = int(request.form.get('employee_id'))
    confidence = float(request.form.get('confidence', 0.0)) if request.form.get('confidence') else None
    
    am, _, _, _ = get_services()
    result = am.mark_attendance(employee_id, confidence)
    
    return jsonify(result)

@app.route('/attendance/history')
@login_required
def attendance_history():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    
    am, _, _, _ = get_services()
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        attendances = am.get_attendance_by_date_range(start_date, end_date, employee_id)
    else:
        attendances = Attendance.query.order_by(Attendance.date.desc()).limit(100).all()
    
    employees = Employee.query.filter_by(status='active').all()
    
    return render_template('attendance.html', attendances=attendances, employees=employees)

# ==================== PAYROLL ROUTES ====================

@app.route('/payroll')
@login_required
def payroll():
    month = request.args.get('month', datetime.now().month, type=int)
    year = request.args.get('year', datetime.now().year, type=int)
    
    _, pc, _, _ = get_services()
    payrolls = Payroll.query.filter_by(month=month, year=year).order_by(Payroll.net_salary.desc()).all()
    summary = pc.get_payroll_summary(year, month)
    
    return render_template('payroll.html', payrolls=payrolls, summary=summary, month=month, year=year)

@app.route('/payroll/calculate', methods=['POST'])
@login_required
def calculate_payroll():
    month = int(request.form.get('month'))
    year = int(request.form.get('year'))
    
    try:
        _, pc, _, _ = get_services()
        pc.calculate_monthly_payroll(year, month)
        flash(f'Payroll calculated for {month}/{year}', 'success')
    except Exception as e:
        flash(f'Error calculating payroll: {str(e)}', 'danger')
    
    return redirect(url_for('payroll', month=month, year=year))

@app.route('/payroll/payslip/<int:id>')
@login_required
def generate_payslip(id):
    payroll = Payroll.query.get_or_404(id)
    employee = Employee.query.get_or_404(payroll.employee_id)
    
    # Generate PDF
    filename = f"payslip_{employee.employee_id}_{payroll.month}_{payroll.year}.pdf"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    _, _, _, pg = get_services()
    pg.generate_payslip(payroll, employee, output_path)
    
    # Update payroll
    payroll.payslip_generated = True
    payroll.payslip_path = f"uploads/{filename}"
    db.session.commit()
    
    return send_file(output_path, as_attachment=True, download_name=filename)

@app.route('/payroll/send-email/<int:id>')
@login_required
def send_payslip_email(id):
    payroll = Payroll.query.get_or_404(id)
    employee = Employee.query.get_or_404(payroll.employee_id)
    
    if not payroll.payslip_path:
        flash('Please generate payslip first', 'warning')
        return redirect(url_for('payroll'))
    
    payslip_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(payroll.payslip_path))
    
    _, _, es, _ = get_services()
    result = es.send_payslip(
        employee.email,
        employee.name,
        payslip_path,
        payroll.month,
        payroll.year
    )
    
    if result['success']:
        payroll.email_sent = True
        db.session.commit()
        flash(f'Payslip sent to {employee.email}', 'success')
    else:
        flash(f'Error sending email: {result["message"]}', 'danger')
    
    return redirect(url_for('payroll'))

# ==================== REPORTS ROUTES ====================

@app.route('/reports')
@login_required
def reports():
    """Display attendance report in HTML
    
    Handles both single employee and all employees reports.
    Passes employee object to template for conditional display.
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    report_type = request.args.get('type', 'daily')
    
    am, _, _, _ = get_services()
    
    attendances = []
    employees = Employee.query.filter_by(status='active').all()
    employee = None  # Will hold Employee object if specific employee selected
    
    if start_date and end_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # FIX: Check if employee_id is provided and not empty string
        # Empty string from HTML select means "All Employees"
        if employee_id and employee_id.strip():
            employee = Employee.query.get(int(employee_id))
            attendances = am.get_attendance_by_date_range(start_date, end_date, employee_id)
        else:
            # All Employees report
            attendances = am.get_attendance_by_date_range(start_date, end_date, None)
    
    return render_template('reports.html', 
                         attendances=attendances, 
                         employees=employees,
                         employee=employee,  # Pass employee object for conditional display
                         start_date=start_date,
                         end_date=end_date,
                         report_type=report_type)

@app.route('/reports/export')
@login_required
def export_report():
    """Export attendance report as PDF
    
    Handles both single employee and all employees reports.
    For all employees reports, passes employee=None to PDF generator.
    """
    report_type = request.args.get('type', 'pdf')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    
    am, _, _, pg = get_services()
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # FIX: Check if employee_id is provided and not empty string
    # Empty string from HTML select means "All Employees"
    if employee_id and employee_id.strip():
        # Single Employee report
        employee = Employee.query.get(int(employee_id))
        if employee:
            attendances = am.get_attendance_by_date_range(start_date, end_date, employee_id)
            filename = f"attendance_report_{employee.employee_id}_{start_date}_to_{end_date}.pdf"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pg.generate_attendance_report(attendances, employee, str(start_date), str(end_date), output_path)
        else:
            return jsonify({'success': False, 'message': 'Employee not found'})
    else:
        # All Employees report - pass employee=None
        attendances = am.get_attendance_by_date_range(start_date, end_date, None)
        filename = f"attendance_summary_{start_date}_to_{end_date}.pdf"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        pg.generate_attendance_report(attendances, None, str(start_date), str(end_date), output_path)
    
    if not os.path.exists(output_path):
        return jsonify({'success': False, 'message': 'PDF generation failed'})
    
    return send_file(output_path, as_attachment=True, download_name=filename)

# ==================== SETTINGS ROUTES ====================

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    settings = Settings.get_settings()
    
    if request.method == 'POST':
        settings.company_name = request.form.get('company_name')
        settings.office_start_time = request.form.get('office_start_time')
        settings.office_end_time = request.form.get('office_end_time')
        settings.grace_period_minutes = int(request.form.get('grace_period_minutes'))
        settings.working_hours_per_day = float(request.form.get('working_hours_per_day'))
        settings.late_deduction_enabled = request.form.get('late_deduction_enabled') == 'on'
        settings.late_deduction_per_occurrence = float(request.form.get('late_deduction_per_occurrence'))
        settings.overtime_enabled = request.form.get('overtime_enabled') == 'on'
        settings.overtime_rate = float(request.form.get('overtime_rate'))
        settings.face_recognition_tolerance = float(request.form.get('face_recognition_tolerance'))
        settings.min_face_images_required = int(request.form.get('min_face_images_required'))
        
        # Handle logo upload
        if 'company_logo' in request.files:
            file = request.files['company_logo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"company_logo_{file.filename}")
                logo_path = os.path.join('static/images', filename)
                file.save(logo_path)
                settings.company_logo = f"static/images/{filename}"
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('settings'))
    
    # Test email connection
    email_test = None
    if request.args.get('test_email'):
        _, _, es, _ = get_services()
        email_test = es.test_email_connection()
    
    return render_template('settings.html', settings=settings, email_test=email_test)

# ==================== API ROUTES ====================

@app.route('/api/recognize-face', methods=['POST'])
@login_required
def recognize_face_api():
    """
    API endpoint for face recognition

    Supports optimized recognition when employee_id is provided.
    If employee_id is provided, only compares against that employee's images.
    """

    if 'image' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No image provided'
        })

    file = request.files['image']

    # Employee Code from frontend (Example: EMP0002)
    employee_code = request.form.get('employee_id')

    # Internal Database ID (Example: 2)
    target_employee_id = None

    if employee_code:
        employee = Employee.query.filter_by(employee_id=employee_code).first()

        if not employee:
            return jsonify({
                'success': False,
                'message': 'Employee ID not found.'
            })

        target_employee_id = str(employee.id)

    if file:
        try:
            # Read image
            npimg = np.frombuffer(file.read(), np.uint8)
            frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

            if frame is None:
                return jsonify({
                    'success': False,
                    'message': 'Invalid image'
                })

            # Face Recognition
            recognizer = FaceRecognitionEngine()

            results = recognizer.recognize_face(
                frame,
                tolerance=app.config['FACE_RECOGNITION_TOLERANCE'],
                target_employee_id=target_employee_id
            )

            # ================= DEBUG =================
            print("\n" + "=" * 60)
            print("FACE RECOGNITION DEBUG")
            print("=" * 60)
            print("Employee Code :", employee_code)
            print("Target ID     :", target_employee_id)
            print("Results       :", results)

            if results:
                print("Name       :", results[0].get('name'))
                print("Employee ID:", results[0].get('employee_id'))
                print("Confidence :", results[0].get('confidence'))
            else:
                print("No Results Returned")

            print("=" * 60 + "\n")
            # ========================================

            if results and results[0]["name"] != "Unknown":

                employee = Employee.query.get(results[0]["employee_id"])

                if employee:
                    return jsonify({
                        "success": True,
                        "employee_id": employee.id,
                        "employee_id_str": employee.employee_id,
                        "name": employee.name,
                        "department": employee.department,
                        "confidence": results[0]["confidence"]
                    })

                print("Employee exists in AI but NOT found in database.")

            else:
                print("Face Recognized as UNKNOWN")

            return jsonify({
                "success": False,
                "message": "Face does not match Employee ID."
            })

        except Exception as e:
            print("\nERROR IN recognize_face_api:", str(e))

            return jsonify({
                "success": False,
                "message": str(e)
            })

    return jsonify({
        "success": False,
        "message": "No file uploaded"
    })

@app.route('/api/verify-employee-id/<employee_id>', methods=['GET'])
@login_required
def verify_employee_id(employee_id):
    """API endpoint to verify employee ID exists and is active
    
    Used for optimized face recognition - verifies employee before starting camera.
    """
    try:
        # Search by employee_id (e.g., EMP0001)
        employee = Employee.query.filter_by(employee_id=employee_id).first()
        
        if employee:
            # Check if employee is active
            if employee.status != 'active':
                return jsonify({
                    'success': False,
                    'message': f'Employee {employee_id} is not active'
                })
            
            # Check if employee has face images registered
            dataset_folder = os.path.join(Config.DATASET_FOLDER, str(employee.id))
            has_face_images = os.path.exists(dataset_folder) and len([f for f in os.listdir(dataset_folder) if f.endswith(('.jpg', '.jpeg', '.png'))]) > 0
            
            if not has_face_images:
                return jsonify({
                    'success': False,
                    'message': f'Employee {employee_id} has no face images registered. Please register face images first.'
                })
            
            return jsonify({
                'success': True,
                'message': 'Employee ID verified successfully',
                'employee_id': employee.id,
                'name': employee.name,
                'department': employee.department,
                'employee_id_str': employee.employee_id
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Employee ID {employee_id} not found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error verifying employee ID: {str(e)}'
        })

@app.route('/api/mark-attendance', methods=['POST'])
@login_required
def mark_attendance_api():
    """API endpoint to mark attendance"""
    employee_id = int(request.form.get('employee_id'))
    confidence = float(request.form.get('confidence', 0.0))
    
    am, _, _, _ = get_services()
    result = am.mark_attendance(employee_id, confidence)
    return jsonify(result)

@app.route('/api/mark-attendance-by-id', methods=['POST'])
@login_required
def mark_attendance_by_id_api():
    """API endpoint to mark attendance by Employee ID (fallback)"""
    employee_id_str = request.form.get('employee_id')
    
    if not employee_id_str:
        return jsonify({'success': False, 'message': 'Employee ID is required'})
    
    # Find employee by employee_id string (e.g., EMP0001)
    employee = Employee.query.filter_by(employee_id=employee_id_str).first()
    
    if not employee:
        return jsonify({'success': False, 'message': 'Employee not found'})
    
    if employee.status != 'active':
        return jsonify({'success': False, 'message': 'Employee is not active'})
    
    # Check attendance for today
    today = date.today()
    attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
    
    am, _, _, _ = get_services()
    
    if not attendance:
        # Create Punch In
        result = am.mark_attendance(employee.id, 0.0)
        return result
    elif attendance.in_time and not attendance.out_time:
        # Create Punch Out
        result = am.mark_attendance(employee.id, 0.0)
        return result
    else:
        # Both Punch In and Punch Out exist
        return jsonify({
            'success': False,
            'message': 'Attendance already completed for today'
        })

@app.route('/api/upload-face-image', methods=['POST'])
@login_required
def upload_face_image():
    """API endpoint to upload face image for training"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'})
    
    file = request.files['image']
    employee_id = request.form.get('employee_id')
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    try:
        # Create dataset folder for employee if it doesn't exist
        dataset_folder = os.path.join(Config.DATASET_FOLDER, employee_id)
        os.makedirs(dataset_folder, exist_ok=True)
        
        # Save image with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}.jpg"
        file_path = os.path.join(dataset_folder, filename)
        file.save(file_path)
        
        # Update employee face_images_count
        employee = Employee.query.filter_by(id=int(employee_id)).first()
        if employee:
            # Count actual images in the folder
            image_count = len([f for f in os.listdir(dataset_folder) if f.endswith(('.jpg', '.jpeg', '.png'))])
            employee.face_images_count = image_count
            db.session.commit()
        
        return jsonify({'success': True, 'message': 'Image saved successfully', 'count': employee.face_images_count if employee else 0})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/train-face-model', methods=['POST'])
@login_required
def train_face_model():
    """API endpoint to train face recognition model for an employee"""
    employee_id = request.form.get('employee_id')
    
    if not employee_id:
        return jsonify({'success': False, 'message': 'Employee ID required'})
    
    try:
        employee = Employee.query.filter_by(id=int(employee_id)).first()
        if not employee:
            return jsonify({'success': False, 'message': 'Employee not found'})
        
        # Get image paths
        dataset_folder = os.path.join(Config.DATASET_FOLDER, employee_id)
        if not os.path.exists(dataset_folder):
            return jsonify({'success': False, 'message': 'No face images found for this employee'})
        
        image_paths = [os.path.join(dataset_folder, f) for f in os.listdir(dataset_folder) 
                      if f.endswith(('.jpg', '.jpeg', '.png'))]
        
        if len(image_paths) < Config.MIN_FACE_IMAGES_REQUIRED:
            return jsonify({'success': False, 'message': f'Need at least {Config.MIN_FACE_IMAGES_REQUIRED} images, found {len(image_paths)}'})
        
        # Train the model using DeepFace
        recognizer = FaceRecognitionEngine()
        trained_count = recognizer.train_employee(str(employee.id), employee.name, image_paths)
        
        if trained_count > 0:
            return jsonify({'success': True, 'message': f'Successfully trained with {trained_count} face encodings', 'count': trained_count})
        else:
            return jsonify({'success': False, 'message': 'Training failed - no faces detected in images. Please ensure: 1) Face is clearly visible, 2) Good lighting, 3) Images are not blurry, 4) Try capturing new images with better conditions'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Training error: {str(e)}'})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('login.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('login.html'), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['DATASET_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TRAINED_MODEL_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
