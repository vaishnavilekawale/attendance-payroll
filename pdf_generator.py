try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    reportlab_available = True
except ImportError:
    reportlab_available = False

try:
    import qrcode
    qrcode_available = True
except ImportError:
    qrcode_available = False

import os
from datetime import datetime
from config import Config
import io

class PDFGenerator:
    def __init__(self):
        if not reportlab_available:
            raise ImportError("ReportLab is not installed. PDF generation will not work.")
        self.styles = getSampleStyleSheet()
        self.company_name = Config.COMPANY_NAME
        self.company_logo = Config.COMPANY_LOGO
    
    def generate_payslip(self, payroll, employee, output_path):
        """Generate professional payslip PDF"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=12
        )
        
        # Company Header
        if os.path.exists(self.company_logo):
            try:
                logo = Image(self.company_logo, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.2*inch))
            except:
                pass
        
        story.append(Paragraph(self.company_name, title_style))
        story.append(Paragraph("PAYSLIP", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Period
        month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                      'July', 'August', 'September', 'October', 'November', 'December']
        period = f"{month_names[payroll.month - 1]} {payroll.year}"
        story.append(Paragraph(f"<b>Period:</b> {period}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Employee Details
        story.append(Paragraph("Employee Details", header_style))
        employee_data = [
            ['Employee ID:', employee.employee_id],
            ['Name:', employee.name],
            ['Department:', employee.department],
            ['Designation:', employee.designation],
            ['Email:', employee.email],
            ['Phone:', employee.phone]
        ]
        
        employee_table = Table(employee_data, colWidths=[2*inch, 4*inch])
        employee_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(employee_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Attendance Summary
        story.append(Paragraph("Attendance Summary", header_style))
        attendance_data = [
            ['Working Days:', str(payroll.working_days)],
            ['Present Days:', str(payroll.present_days)],
            ['Absent Days:', str(payroll.absent_days)],
            ['Half Days:', str(payroll.half_days)],
            ['Late Days:', str(payroll.late_days)],
            ['Total Hours Worked:', f"{payroll.total_hours_worked:.2f}"],
            ['Overtime Hours:', f"{payroll.overtime_hours:.2f}"]
        ]
        
        attendance_table = Table(attendance_data, colWidths=[2*inch, 4*inch])
        attendance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(attendance_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Salary Breakdown
        story.append(Paragraph("Salary Breakdown", header_style))
        salary_data = [
            ['Basic Salary:', f"${payroll.basic_salary:.2f}"],
            ['Per Day Salary:', f"${payroll.per_day_salary:.2f}"],
            ['', ''],
            ['Deductions:', ''],
            ['Absent Deduction:', f"-${payroll.absent_deduction:.2f}"],
            ['Half Day Deduction:', f"-${payroll.half_day_deduction:.2f}"],
            ['Late Deduction:', f"-${payroll.late_deduction:.2f}"],
            ['Total Deductions:', f"-${(payroll.absent_deduction + payroll.half_day_deduction + payroll.late_deduction):.2f}"],
            ['', ''],
            ['Additions:', ''],
            ['Overtime Bonus:', f"+${payroll.overtime_bonus:.2f}"],
            ['', ''],
            ['Gross Salary:', f"${payroll.gross_salary:.2f}"],
            ['Net Salary:', f"${payroll.net_salary:.2f}"]
        ]
        
        salary_table = Table(salary_data, colWidths=[2*inch, 4*inch])
        salary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TEXTCOLOR', (-1, -1), (-1, -1), colors.darkgreen),
            ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (-1, -1), (-1, -1), 12)
        ]))
        story.append(salary_table)
        story.append(Spacer(1, 0.5*inch))
        
        # QR Code
        if qrcode_available:
            qr_data = f"{self.company_name}|{employee.employee_id}|{employee.name}|{period}|{payroll.net_salary:.2f}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            qr_buffer = io.BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
            qr_image.hAlign = 'CENTER'
            story.append(qr_image)
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("Scan to verify payslip authenticity", self.styles['Normal']))
        story.append(Spacer(1, 0.5*inch))
        
        # Signature
        story.append(Paragraph("_________________________", self.styles['Normal']))
        story.append(Paragraph("Authorized Signature", self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def generate_attendance_report(self, attendances, employee, start_date, end_date, output_path):
        """Generate attendance report PDF
        
        Args:
            attendances: List of attendance records
            employee: Employee object (None for All Employees report)
            start_date: Start date string
            end_date: End date string
            output_path: Output PDF file path
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.darkblue,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12
        )
        
        # Header
        story.append(Paragraph(self.company_name, title_style))
        story.append(Paragraph("Attendance Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Check if this is an All Employees report or Single Employee report
        if employee is None:
            # All Employees report
            story.append(Paragraph("<b>Employee:</b> All Employees", self.styles['Normal']))
            story.append(Paragraph("<b>Department:</b> All Departments", self.styles['Normal']))
        else:
            # Single Employee report
            story.append(Paragraph(f"<b>Employee:</b> {employee.name}", self.styles['Normal']))
            story.append(Paragraph(f"<b>Employee ID:</b> {employee.employee_id}", self.styles['Normal']))
            story.append(Paragraph(f"<b>Department:</b> {employee.department}", self.styles['Normal']))
        
        story.append(Paragraph(f"<b>Period:</b> {start_date} to {end_date}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Attendance Table
        if attendances:
            # For All Employees report, include Employee ID, Name, Department columns
            if employee is None:
                data = [['Employee ID', 'Employee Name', 'Department', 'Date', 'IN Time', 'OUT Time', 'Total Hours', 'Status', 'Late', 'Overtime']]
                
                for att in attendances:
                    data.append([
                        att.employee.employee_id,
                        att.employee.name,
                        att.employee.department,
                        att.date.strftime('%Y-%m-%d'),
                        att.in_time.strftime('%H:%M') if att.in_time else '-',
                        att.out_time.strftime('%H:%M') if att.out_time else '-',
                        f"{att.total_hours:.2f}" if att.total_hours else '-',
                        att.status.upper(),
                        'Yes' if att.late_entry else 'No',
                        f"{att.overtime_hours:.2f}" if att.overtime_hours else '-'
                    ])
                
                table = Table(data, colWidths=[1*inch, 1.5*inch, 1.2*inch, 1*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch, 0.8*inch])
            else:
                # Single Employee report - keep existing format
                data = [['Date', 'IN Time', 'OUT Time', 'Total Hours', 'Status', 'Late', 'Overtime']]
                
                for att in attendances:
                    data.append([
                        att.date.strftime('%Y-%m-%d'),
                        att.in_time.strftime('%H:%M') if att.in_time else '-',
                        att.out_time.strftime('%H:%M') if att.out_time else '-',
                        f"{att.total_hours:.2f}" if att.total_hours else '-',
                        att.status.upper(),
                        'Yes' if att.late_entry else 'No',
                        f"{att.overtime_hours:.2f}" if att.overtime_hours else '-'
                    ])
                
                table = Table(data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1*inch])
            
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9)
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No attendance records found for this period.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Summary - works for both report types
        present = len([a for a in attendances if a.status == 'present'])
        absent = len([a for a in attendances if a.status == 'absent'])
        half_day = len([a for a in attendances if a.status == 'half_day'])
        late = len([a for a in attendances if a.late_entry])
        
        summary_data = [
            ['Total Records:', str(len(attendances))],
            ['Present:', str(present)],
            ['Absent:', str(absent)],
            ['Half Days:', str(half_day)],
            ['Late Arrivals:', str(late)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        
        # Build PDF
        doc.build(story)
        
        return output_path
