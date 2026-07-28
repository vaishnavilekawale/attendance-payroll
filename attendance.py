import logging
from datetime import datetime, time, timedelta

from database import db
from models import Attendance, Employee, Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttendanceManager:
    def __init__(self):
        self.settings = Settings.get_settings()
    
    def mark_attendance(self, employee_id, confidence=None):
        """Mark attendance for employee (IN or OUT)"""
        today = datetime.now().date()
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return {'success': False, 'message': 'Employee not found'}
        
        # Check if attendance already exists for today
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        if attendance:
            # Check if OUT can be marked
            if attendance.in_time and not attendance.out_time:
                return self.mark_out(attendance, confidence)
            elif attendance.in_time and attendance.out_time:
                return {'success': False, 'message': 'Attendance already marked for today'}
            else:
                return {'success': False, 'message': 'Invalid attendance state'}
        else:
            # Mark IN
            return self.mark_in(employee, confidence)
    
    def mark_in(self, employee, confidence=None):
        """Mark IN attendance"""
        today = datetime.now().date()
        now = datetime.now()
        
        # ✅ Fix 1: Properly handle time + timedelta using datetime.combine
        office_start = self._parse_time(self.settings.office_start_time)
        office_start_datetime = datetime.combine(now.date(), office_start)
        grace_period = timedelta(minutes=self.settings.grace_period_minutes)
        late_threshold = office_start_datetime + grace_period
        
        is_late = now > late_threshold
        
        attendance = Attendance(
            employee_id=employee.id,
            date=today,
            in_time=now,
            status='present' if not is_late else 'late',
            late_entry=is_late,
            confidence=confidence
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        logger.info(f"IN marked for {employee.name} at {now}")
        
        return {
            'success': True,
            'message': f'IN marked successfully for {employee.name}',
            'attendance_id': attendance.id,
            'in_time': now.strftime('%H:%M:%S'),
            'is_late': is_late
        }
    
    def mark_out(self, attendance, confidence=None):
        """Mark OUT attendance"""
        now = datetime.now()
        
        # Check office end time
        office_end = self._parse_time(self.settings.office_end_time)
        is_early_exit = now.time() < office_end
        
        # Calculate total hours
        if attendance.in_time:
            total_hours = (now - attendance.in_time).total_seconds() / 3600
            attendance.total_hours = round(total_hours, 2)
        
        # Calculate overtime
        working_hours = self.settings.working_hours_per_day
        if attendance.total_hours and attendance.total_hours > working_hours:
            attendance.overtime_hours = round(attendance.total_hours - working_hours, 2)
        else:
            attendance.overtime_hours = 0.0
        
        attendance.out_time = now
        attendance.early_exit = is_early_exit
        attendance.confidence = confidence
        
        # Update status based on hours
        if attendance.total_hours < (working_hours / 2):
            attendance.status = 'absent'
        elif attendance.total_hours < working_hours:
            attendance.status = 'half_day'
        
        db.session.commit()
        
        logger.info(f"OUT marked for attendance ID {attendance.id} at {now}")
        
        return {
            'success': True,
            'message': 'OUT marked successfully',
            'out_time': now.strftime('%H:%M:%S'),
            'total_hours': attendance.total_hours,
            'overtime_hours': attendance.overtime_hours,
            'is_early_exit': is_early_exit
        }
    
    def get_today_attendance(self, employee_id=None):
        """Get today's attendance"""
        today = datetime.now().date()
        
        if employee_id:
            attendance = Attendance.query.filter_by(
                employee_id=employee_id,
                date=today
            ).first()
            return attendance
        else:
            attendances = Attendance.query.filter_by(date=today).all()
            return attendances
    
    def get_attendance_by_date_range(self, start_date, end_date, employee_id=None):
        """Get attendance by date range"""
        query = Attendance.query.filter(
            Attendance.date >= start_date,
            Attendance.date <= end_date
        )
        
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
        
        return query.all()
    
    def get_monthly_attendance(self, year, month, employee_id=None):
        """Get monthly attendance"""
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        return self.get_attendance_by_date_range(start_date, end_date, employee_id)
    
    def get_attendance_stats(self, start_date, end_date):
        """Get attendance statistics for date range"""
        attendances = self.get_attendance_by_date_range(start_date, end_date)
        
        total_employees = Employee.query.filter_by(status='active').count()
        present = len([a for a in attendances if a.status == 'present'])
        absent = len([a for a in attendances if a.status == 'absent'])
        half_day = len([a for a in attendances if a.status == 'half_day'])
        late = len([a for a in attendances if a.late_entry])
        
        return {
            'total_employees': total_employees,
            'present': present,
            'absent': absent,
            'half_day': half_day,
            'late': late
        }
    
    def get_department_stats(self, start_date, end_date):
        """Get department-wise attendance statistics"""
        attendances = self.get_attendance_by_date_range(start_date, end_date)
        
        dept_stats = {}
        for attendance in attendances:
            dept = attendance.employee.department if attendance.employee else "Unknown"
            if dept not in dept_stats:
                dept_stats[dept] = {
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0
                }
            
            dept_stats[dept]['total'] += 1
            if attendance.status == 'present':
                dept_stats[dept]['present'] += 1
            elif attendance.status == 'absent':
                dept_stats[dept]['absent'] += 1
            if attendance.late_entry:
                dept_stats[dept]['late'] += 1
        
        return dept_stats
    
    def _parse_time(self, time_str):
        """Parse time string to time object"""
        hours, minutes = map(int, time_str.split(':'))
        return time(hours, minutes)
    
    def can_mark_in(self, employee_id):
        """Check if employee can mark IN"""
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        return attendance is None
    
    def can_mark_out(self, employee_id):
        """Check if employee can mark OUT"""
        today = datetime.now().date()
        attendance = Attendance.query.filter_by(
            employee_id=employee_id,
            date=today
        ).first()
        
        return attendance and attendance.in_time and not attendance.out_time


class WorkingHoursCalculator:
    def __init__(self):
        self.settings = Settings.get_settings()
    
    def calculate_working_hours(self, attendance):
        """Calculate working hours for attendance record"""
        if attendance.in_time and attendance.out_time:
            total_hours = (attendance.out_time - attendance.in_time).total_seconds() / 3600
            attendance.total_hours = round(total_hours, 2)
            
            # ✅ Fix 2: Properly handle time + timedelta for WorkingHoursCalculator
            office_start = self._parse_time(self.settings.office_start_time)
            office_start_datetime = datetime.combine(attendance.in_time.date(), office_start)
            grace_period = timedelta(minutes=self.settings.grace_period_minutes)
            late_threshold = office_start_datetime + grace_period
            
            if attendance.in_time > late_threshold:
                attendance.late_entry = True
            
            # Check for early exit
            office_end = self._parse_time(self.settings.office_end_time)
            if attendance.out_time.time() < office_end:
                attendance.early_exit = True
            
            # Calculate overtime
            working_hours = self.settings.working_hours_per_day
            if attendance.total_hours > working_hours:
                attendance.overtime_hours = round(attendance.total_hours - working_hours, 2)
            else:
                attendance.overtime_hours = 0.0
            
            return attendance.total_hours
        return 0.0
    
    def _parse_time(self, time_str):
        """Parse time string to time object"""
        hours, minutes = map(int, time_str.split(':'))
        return time(hours, minutes)