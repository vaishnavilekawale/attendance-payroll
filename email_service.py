import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = Config.MAIL_SERVER
        self.smtp_port = Config.MAIL_PORT
        self.smtp_username = Config.MAIL_USERNAME
        self.smtp_password = Config.MAIL_PASSWORD
        self.use_tls = Config.MAIL_USE_TLS
        self.default_sender = Config.MAIL_DEFAULT_SENDER
    
    def send_email(self, to_email, subject, body, attachments=None):
        """Send email with optional attachments"""
        if not self.smtp_username or not self.smtp_password:
            logger.error("SMTP credentials not configured")
            return {'success': False, 'message': 'SMTP credentials not configured'}
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.default_sender
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {os.path.basename(attachment_path)}'
                            )
                            msg.attach(part)
            
            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {to_email}")
            return {'success': True, 'message': 'Email sent successfully'}
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {'success': False, 'message': str(e)}
    
    def send_payslip(self, employee_email, employee_name, payslip_path, month, year):
        """Send payslip PDF to employee"""
        subject = f"Payslip for {month}/{year} - {Config.COMPANY_NAME}"
        
        body = f"""
        <html>
        <head></head>
        <body>
            <h2>Dear {employee_name},</h2>
            <p>Please find attached your payslip for {month}/{year}.</p>
            <p><strong>Company:</strong> {Config.COMPANY_NAME}</p>
            <p><strong>Period:</strong> {month}/{year}</p>
            <p>If you have any questions, please contact HR.</p>
            <br>
            <p>Best regards,</p>
            <p>{Config.COMPANY_NAME} HR Team</p>
        </body>
        </html>
        """
        
        return self.send_email(employee_email, subject, body, [payslip_path])
    
    def send_attendance_report(self, to_email, employee_name, report_path, start_date, end_date):
        """Send attendance report to employee"""
        subject = f"Attendance Report - {start_date} to {end_date}"
        
        body = f"""
        <html>
        <head></head>
        <body>
            <h2>Dear {employee_name},</h2>
            <p>Please find attached your attendance report from {start_date} to {end_date}.</p>
            <p><strong>Company:</strong> {Config.COMPANY_NAME}</p>
            <p>If you have any questions, please contact HR.</p>
            <br>
            <p>Best regards,</p>
            <p>{Config.COMPANY_NAME} HR Team</p>
        </body>
        </html>
        """
        
        return self.send_email(to_email, subject, body, [report_path])
    
    def test_email_connection(self):
        """Test email connection"""
        if not self.smtp_username or not self.smtp_password:
            return {'success': False, 'message': 'SMTP credentials not configured'}
        
        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            
            return {'success': True, 'message': 'Email connection successful'}
        
        except Exception as e:
            return {'success': False, 'message': str(e)}
