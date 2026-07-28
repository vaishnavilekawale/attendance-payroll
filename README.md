# AI Employee Attendance Monitoring and Payroll Management System

A complete production-ready system for employee attendance tracking using AI face recognition and automated payroll management.

## Features

- **AI Face Recognition**: Automatic employee identification using face recognition
- **Attendance Tracking**: IN/OUT punch with automatic working hours calculation
- **Payroll Management**: Automated salary calculation based on attendance
- **PDF Payslips**: Generate professional payslip PDFs with QR codes
- **Email Integration**: Automatic payslip delivery via email
- **Reports**: Comprehensive attendance and payroll reports
- **Dashboard**: Real-time statistics and charts
- **Multi-Database Support**: SQLite (default) and MySQL

## Tech Stack

### Backend
- Python 3.12
- Flask
- SQLAlchemy
- Flask-Migrate

### AI/Computer Vision
- OpenCV
- MediaPipe Face Detection
- face_recognition
- NumPy

### Frontend
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Chart.js

### Database
- SQLite (default)
- MySQL (configurable)

### Other
- ReportLab (PDF generation)
- qrcode (QR code generation)
- SMTP (Email)

## Project Structure

```
attendance_ai/
│
├── app.py                      # Main Flask application
├── config.py                   # Configuration settings
├── database.py                 # Database initialization
├── models.py                   # Database models
├── ai_engine.py                # Face detection and recognition
├── payroll.py                  # Payroll calculation
├── attendance.py               # Attendance management
├── email_service.py           # Email service
├── pdf_generator.py           # PDF generation
├── requirements.txt            # Python dependencies
├── README.md                  # This file
├── .env.example               # Environment variables template
├── attendance.db              # SQLite database (auto-generated)
│
├── dataset/                   # Face images for training
├── trained_model/            # Trained AI models
├── static/
│      css/
│          style.css          # Custom styles
│      js/
│          main.js            # JavaScript functions
│      images/
│          company_logo.png   # Company logo
│
├── templates/
│      login.html             # Login page
│      dashboard.html         # Dashboard
│      add_employee.html      # Employee management
│      attendance.html         # Attendance tracking
│      payroll.html           # Payroll management
│      reports.html           # Reports
│      settings.html          # System settings
│
└── uploads/                  # Uploaded files (photos, payslips)
```

## Installation

### Prerequisites

- Python 3.12 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Step 1: Clone or Download the Project

```bash
cd c:/AI_Attendance_Payroll_System/attendance_ai
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** Installing dlib may take some time as it requires CMake and Visual Studio Build Tools on Windows.

### Step 5: Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
copy .env.example .env
```

Edit `.env` file with your settings:

```env
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development

# Database Configuration
DATABASE_URL=sqlite:///attendance.db

# Email Configuration (SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Company Settings
COMPANY_NAME=AI Attendance System
COMPANY_LOGO=static/images/company_logo.png

# Office Timing
OFFICE_START_TIME=09:00
OFFICE_END_TIME=18:00
GRACE_PERIOD_MINUTES=15

# Working Hours
WORKING_HOURS_PER_DAY=9.0

# Salary Calculation
LATE_DEDUCTION_ENABLED=false
LATE_DEDUCTION_PER_OCCURRENCE=0.0

# Overtime Calculation
OVERTIME_ENABLED=true
OVERTIME_RATE=1.5

# Face Recognition Settings
FACE_RECOGNITION_TOLERANCE=0.6
MIN_FACE_IMAGES_REQUIRED=20
```

### Step 6: Database Setup

The database will be automatically created when you run the application for the first time.

Default admin credentials:
- Username: `admin`
- Password: `admin123`

**Important:** Change the default password after first login!

### Step 7: Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

## How It Works

### AI Training

1. **Face Registration**: Add employee and capture 20+ face images using webcam
2. **Face Detection**: MediaPipe detects faces in captured images
3. **Feature Extraction**: face_recognition extracts 128-dimensional face encodings
4. **Model Training**: Encodings are saved to trained_model/face_model.pkl
5. **Automatic Training**: AI trains automatically after face registration

### Attendance System

1. **Face Recognition**: Webcam captures image and recognizes employee
2. **IN Punch**: Marks arrival time when employee is recognized
3. **OUT Punch**: Marks departure time when employee leaves
4. **Working Hours**: Automatically calculates total hours worked
5. **Late Detection**: Identifies late arrivals based on grace period
6. **Overtime Calculation**: Calculates overtime hours beyond working hours

### Payroll System

1. **Monthly Calculation**: Calculates payroll at month end
2. **Attendance Analysis**: Analyzes present, absent, half-day, late days
3. **Salary Calculation**:
   - Per Day Salary = Basic Salary / Working Days
   - Absent Deduction = Absent Days × Per Day Salary
   - Half Day Deduction = Half Days × (Per Day Salary / 2)
   - Late Deduction = Late Days × Late Deduction Amount
   - Overtime Bonus = Overtime Hours × Hourly Rate × Overtime Rate
   - Net Salary = Gross Salary - Deductions + Overtime Bonus
4. **Payslip Generation**: Creates professional PDF payslip with QR code
5. **Email Delivery**: Sends payslip to employee email automatically

### Email System

1. **SMTP Configuration**: Configure Gmail SMTP in .env file
2. **App Password**: Use Gmail App Password (not regular password)
3. **Automatic Sending**: Payslips sent automatically when generated
4. **HTML Emails**: Professional HTML email templates

### PDF Generation

1. **ReportLab**: Uses ReportLab for PDF generation
2. **Professional Layout**: Company logo, employee details, salary breakdown
3. **QR Code**: Includes QR code for verification
4. **Signature**: Placeholder for authorized signature
5. **Download**: Payslips available for download

## Usage Guide

### 1. Login

- Access the application at `http://localhost:5000`
- Login with default credentials (admin/admin123)
- Change password after first login

### 2. Add Employees

- Go to Employees → Add Employee
- Fill in employee details
- Upload profile photo (optional)
- Employee ID is auto-generated

### 3. Register Face for AI Recognition

- Go to Employees → Click camera icon for employee
- Set number of images (minimum 20 recommended)
- Click "Start Capture" to open webcam
- Ensure good lighting and face clearly visible
- System captures images automatically
- AI trains automatically after capture

### 4. Mark Attendance

- Go to Attendance page
- Click "Start Camera"
- Employee faces in front of webcam
- System recognizes employee automatically
- Click "Mark Attendance" to record IN/OUT
- System prevents duplicate IN punches
- OUT can only be marked after IN

### 5. Calculate Payroll

- Go to Payroll page
- Select month and year
- Click "Calculate Payroll"
- System calculates for all active employees
- View salary breakdown for each employee

### 6. Generate Payslips

- Go to Payroll page
- Click PDF icon for employee
- Payslip PDF downloads automatically
- Click email icon to send to employee
- Email sent with payslip attachment

### 7. Generate Reports

- Go to Reports page
- Select date range and employee
- Click "Generate Report"
- View attendance statistics
- Click "Export PDF" to download report

### 8. Configure Settings

- Go to Settings page
- Configure company details
- Set office timing and grace period
- Configure salary calculation rules
- Adjust face recognition tolerance
- Test email connection
- Retrain AI model if needed

## Database Configuration

### SQLite (Default)

No additional configuration needed. Database file: `attendance.db`

### MySQL

To use MySQL instead of SQLite:

1. Install MySQL server
2. Create database:
```sql
CREATE DATABASE attendance_db;
```

3. Update `.env` file:
```env
DATABASE_URL=mysql+pymysql://username:password@localhost/attendance_db
```

4. Install PyMySQL (already in requirements.txt)

## Troubleshooting

### Issue: dlib installation fails

**Solution:**
- Install CMake: `pip install cmake`
- Install Visual Studio Build Tools (Windows)
- Or use pre-compiled wheel: `pip install dlib-binary`

### Issue: Webcam not accessible

**Solution:**
- Check browser permissions
- Ensure no other application is using webcam
- Try different browser (Chrome recommended)

### Issue: Face recognition not working

**Solution:**
- Ensure good lighting
- Capture more face images (minimum 20)
- Retrain AI model from Settings
- Adjust face recognition tolerance in Settings

### Issue: Email not sending

**Solution:**
- Verify SMTP credentials in .env
- Use Gmail App Password (not regular password)
- Enable "Less Secure Apps" or use App Password
- Test email connection from Settings

### Issue: Database locked error

**Solution:**
- Close all database connections
- Delete `.db` file and restart application
- Check for multiple application instances

### Issue: Port 5000 already in use

**Solution:**
- Change port in app.py:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Issue: PDF generation fails

**Solution:**
- Ensure uploads folder exists
- Check write permissions
- Verify ReportLab installation

## Security Features

- **Password Hashing**: Using Werkzeug security functions
- **Session Management**: Secure session handling
- **CSRF Protection**: Built-in Flask-WTF CSRF protection
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **XSS Protection**: Jinja2 auto-escapes HTML
- **Session Timeout**: Configurable session lifetime
- **Input Validation**: Form validation on all inputs

## Performance Optimization

- **Database Indexing**: Automatic indexing on foreign keys
- **Lazy Loading**: SQLAlchemy lazy loading for relationships
- **Pagination**: Large datasets use pagination
- **Caching**: Face recognition model loaded once
- **Async Operations**: Email sending can be made async

## Deployment

### Production Deployment

1. **Set Environment Variables:**
```env
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
SESSION_COOKIE_SECURE=true
```

2. **Use Production WSGI Server:**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

3. **Configure Reverse Proxy:**
- Use Nginx or Apache as reverse proxy
- Configure SSL/HTTPS
- Set up static file serving

4. **Database:**
- Use MySQL or PostgreSQL for production
- Configure database backups
- Set up replication if needed

5. **Monitoring:**
- Set up application monitoring
- Configure error logging
- Monitor system resources

## Support and Contributing

For issues, questions, or contributions, please contact the development team.

## License

This project is proprietary software. All rights reserved.

## Version History

- **v1.0.0** (2024): Initial release
  - AI face recognition
  - Attendance tracking
  - Payroll management
  - PDF payslips
  - Email integration
  - Reports and analytics

## Screenshots

*Note: Screenshots will be added in future updates*

- Login Page
- Dashboard with charts
- Employee Management
- Face Registration
- Attendance Tracking
- Payroll Management
- Payslip PDF
- Reports
- Settings


**Built with ❤️ using Python, Flask, and AI**
