from datetime import datetime, date
from models import Payroll, Employee, Attendance, Settings
from database import db
from calendar import monthrange
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayrollCalculator:
    def __init__(self):
        self.settings = Settings.get_settings()
    
    def calculate_monthly_payroll(self, year, month, employee_id=None):
        """Calculate payroll for a specific month"""
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        working_days = self._get_working_days(start_date, end_date)
        
        if employee_id:
            employees = [Employee.query.get(employee_id)]
        else:
            employees = Employee.query.filter_by(status='active').all()
        
        payroll_records = []
        
        for employee in employees:
            if not employee:
                continue
            
            # Get attendance for the month
            attendances = Attendance.query.filter(
                Attendance.employee_id == employee.id,
                Attendance.date >= start_date,
                Attendance.date <= end_date
            ).all()
            
            # Calculate attendance stats
            present_days = len([a for a in attendances if a.status == 'present'])
            absent_days = len([a for a in attendances if a.status == 'absent'])
            half_days = len([a for a in attendances if a.status == 'half_day'])
            late_days = len([a for a in attendances if a.late_entry])
            
            # Calculate total hours worked
            total_hours_worked = sum([a.total_hours for a in attendances if a.total_hours])
            
            # Calculate overtime hours
            overtime_hours = sum([a.overtime_hours for a in attendances if a.overtime_hours])
            
            # Calculate salary
            basic_salary = employee.basic_salary
            per_day_salary = basic_salary / working_days if working_days > 0 else 0
            
            # Deductions
            absent_deduction = absent_days * per_day_salary
            half_day_deduction = half_days * (per_day_salary / 2)
            
            late_deduction = 0.0
            if self.settings.late_deduction_enabled:
                late_deduction = late_days * self.settings.late_deduction_per_occurrence
            
            # Overtime bonus
            overtime_bonus = 0.0
            if self.settings.overtime_enabled:
                hourly_rate = per_day_salary / self.settings.working_hours_per_day
                overtime_bonus = overtime_hours * hourly_rate * self.settings.overtime_rate
            
            # Calculate net salary
            gross_salary = basic_salary
            net_salary = gross_salary - absent_deduction - half_day_deduction - late_deduction + overtime_bonus
            
            # Check if payroll already exists
            payroll = Payroll.query.filter_by(
                employee_id=employee.id,
                month=month,
                year=year
            ).first()
            
            if payroll:
                # Update existing payroll
                payroll.working_days = working_days
                payroll.present_days = present_days
                payroll.absent_days = absent_days
                payroll.half_days = half_days
                payroll.late_days = late_days
                payroll.total_hours_worked = total_hours_worked
                payroll.overtime_hours = overtime_hours
                payroll.per_day_salary = per_day_salary
                payroll.absent_deduction = absent_deduction
                payroll.half_day_deduction = half_day_deduction
                payroll.late_deduction = late_deduction
                payroll.overtime_bonus = overtime_bonus
                payroll.gross_salary = gross_salary
                payroll.net_salary = net_salary
            else:
                # Create new payroll record
                payroll = Payroll(
                    employee_id=employee.id,
                    month=month,
                    year=year,
                    basic_salary=basic_salary,
                    working_days=working_days,
                    present_days=present_days,
                    absent_days=absent_days,
                    half_days=half_days,
                    late_days=late_days,
                    total_hours_worked=total_hours_worked,
                    overtime_hours=overtime_hours,
                    per_day_salary=per_day_salary,
                    absent_deduction=absent_deduction,
                    half_day_deduction=half_day_deduction,
                    late_deduction=late_deduction,
                    overtime_bonus=overtime_bonus,
                    gross_salary=gross_salary,
                    net_salary=net_salary
                )
                db.session.add(payroll)
            
            payroll_records.append(payroll)
        
        db.session.commit()
        logger.info(f"Calculated payroll for {len(payroll_records)} employees for {month}/{year}")
        
        return payroll_records
    
    def _get_working_days(self, start_date, end_date):
        """Calculate working days between two dates (excluding weekends)"""
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() < 5:  # Monday to Friday
                working_days += 1
            current_date += timedelta(days=1)
        
        return working_days
    
    def get_payroll(self, year, month, employee_id=None):
        """Get payroll records"""
        query = Payroll.query.filter_by(month=month, year=year)
        
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        
        return query.all()
    
    def get_payroll_summary(self, year, month):
        """Get payroll summary for a month"""
        payrolls = self.get_payroll(year, month)
        
        total_employees = len(payrolls)
        total_gross_salary = sum([p.gross_salary for p in payrolls])
        total_net_salary = sum([p.net_salary for p in payrolls])
        total_overtime_bonus = sum([p.overtime_bonus for p in payrolls])
        total_deductions = sum([p.absent_deduction + p.half_day_deduction + p.late_deduction for p in payrolls])
        
        return {
            'total_employees': total_employees,
            'total_gross_salary': total_gross_salary,
            'total_net_salary': total_net_salary,
            'total_overtime_bonus': total_overtime_bonus,
            'total_deductions': total_deductions
        }

from datetime import timedelta
