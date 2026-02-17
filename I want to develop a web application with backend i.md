from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
import openpyxl
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import secrets
import json
import traceback # Useful for the error handling in your code

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============================================================================
# Database Models
# ============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='employee')  # admin, manager, employee
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    progress = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    working_saturdays = db.Column(db.Text, default='[]')
    current_reschedule_number = db.Column(db.Integer, default=0)  # âœ… ADD THIS LINE    # Store as JSON array

class ProjectStage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    duration_days = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # ADD THIS LINE
    parallel_group_id = db.Column(db.String(50))  # For grouping parallel stages

class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'))
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='pending')  # pending, in-progress, completed
    deadline = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class ScheduleHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('project_stage.id'))
    reschedule_number = db.Column(db.Integer, default=1)  # âœ… ADD THIS
    original_date = db.Column(db.Date)
    new_date = db.Column(db.Date)
    reason = db.Column(db.Text)
    rescheduled_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    rescheduled_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class StageDailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stage_id = db.Column(db.Integer, db.ForeignKey('project_stage.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    scheduled_date = db.Column(db.Date, nullable=False)
    original_date = db.Column(db.Date)  # Track if rescheduled
    status = db.Column(db.String(20), default='pending')  # pending, completed, rescheduled
    completed_at = db.Column(db.DateTime)
    rescheduled_reason = db.Column(db.Text)
    reschedule_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailyTaskRescheduleHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('project_stage.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('stage_daily_task.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    reschedule_number = db.Column(db.Integer, default=1)  # âœ… ADD THIS
    original_date = db.Column(db.Date, nullable=False)
    new_date = db.Column(db.Date, nullable=False)
    days_shifted = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text)
    rescheduled_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    rescheduled_at = db.Column(db.DateTime, default=datetime.utcnow)


class HoldDate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('project_stage.id'), nullable=False)
    hold_date = db.Column(db.Date, nullable=False)  # The date that became HOLD
    reason = db.Column(db.Text)  # Why it's on hold
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================================
# Excel Generation Helper Function
# ============================================================================

def generate_excel_file(project_id, save_to_backend=True):
    """
    Generate Excel file for a project and optionally save to backend.
    
    Args:
        project_id: The project ID to generate Excel for
        save_to_backend: If True, saves the file to static/excel_exports/
    
    Returns:
        BytesIO object containing the Excel file, or None on error
    """
    try:
        project = Project.query.get(project_id)
        if not project:
            print(f"⚠️ Project {project_id} not found")
            return None
            
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        # Parse Working Saturdays
        try:
            working_saturdays = set(json.loads(project.working_saturdays) if project.working_saturdays else [])
        except:
            working_saturdays = set()

        # ==========================================
        # 1. PREPARE RESCHEDULE MAP (STAGE-WISE)
        # ==========================================
        stage_reschedule_map = {1: {}, 2: {}, 3: {}, 4: {}}
        
        for stage in stages:
            parts = stage.name.split('-')
            stage_abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            
            task_reschedules = DailyTaskRescheduleHistory.query.filter_by(
                project_id=project_id, 
                stage_id=stage.id
            ).all()
            
            unique_nums = sorted(list(set(r.reschedule_number for r in task_reschedules if r.reschedule_number)))
            
            for idx, r_num in enumerate(unique_nums):
                target_row = idx + 1
                if target_row > 4: continue
                
                event_tasks = [t for t in task_reschedules if t.reschedule_number == r_num]
                for t in event_tasks:
                    date_str = t.new_date.strftime('%Y-%m-%d')
                    if date_str not in stage_reschedule_map[target_row]:
                        stage_reschedule_map[target_row][date_str] = []
                    if stage_abbr not in stage_reschedule_map[target_row][date_str]:
                        stage_reschedule_map[target_row][date_str].append(stage_abbr)

        # ==========================================
        # 2. SETUP EXCEL & HEADERS
        # ==========================================
        wb = Workbook()
        ws = wb.active
        ws.title = "Schedule_Tracker"
        
        # Styles
        gray_header = PatternFill(start_color="C0C0C0", end_color="C0C0C0", fill_type="solid")
        light_blue_header = PatternFill(start_color="B4C7E7", end_color="B4C7E7", fill_type="solid")
        orange_header = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
        green_fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
        orange_fill = PatternFill(start_color="FFA500", end_color="FFA500", fill_type="solid")
        cyan_fill = PatternFill(start_color="00FFFF", end_color="00FFFF", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        light_gray = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        medium_border = Border(left=Side(style='medium'), right=Side(style='medium'), top=Side(style='medium'), bottom=Side(style='medium'))

        # Timeline
        project_start = project.start_date
        project_end = project.end_date
        
        if not project_start or not project_end:
            print(f"⚠️ Project {project_id} missing start/end dates")
            return None
            
        all_dates = []
        current_date = project_start
        while current_date <= project_end:
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        if not all_dates:
            print(f"⚠️ No dates in project range")
            return None

        current_row = 1

        # Set Widths
        ws.column_dimensions['A'].width = 28
        ws.column_dimensions['B'].width = 28
        ws.column_dimensions['C'].width = 28
        ws.column_dimensions['D'].width = 28
        ws.column_dimensions['E'].width = 28
        for i in range(6, len(all_dates) + 10):
            ws.column_dimensions[get_column_letter(i)].width = 15

        # ==========================================
        # STAGE DETAILS TABLE (TOP SECTION)
        # ==========================================
        stage_list = []
        for stage in stages:
            parts = stage.name.split('-')
            if len(parts) >= 2:
                category = '-'.join(parts[:-1]).strip()
                abbr = parts[-1].strip()
                stage_list.append(f"{category} -{abbr}")
            else:
                stage_list.append(stage.name)
        
        max_cols = 5
        table_row = current_row
        col_idx = 0
        
        for stage_text in stage_list:
            col = col_idx + 1
            
            cell = ws.cell(table_row, col, value=stage_text)
            cell.fill = white_fill
            cell.border = thin_border
            cell.font = Font(size=10, bold=True)
            cell.alignment = Alignment(horizontal='left', vertical='center')
            
            col_idx += 1
            if col_idx >= max_cols:
                col_idx = 0
                table_row += 1
        
        if col_idx > 0:
            table_row += 1
        
        current_row = table_row + 2

        # ==========================================
        # HEADER ROW 1: Month-Year header
        # ==========================================
        ws.cell(current_row, 1, value="")
        ws.cell(current_row, 1).border = thin_border
        
        ws.cell(current_row, 2, value="")
        ws.cell(current_row, 2).fill = gray_header
        ws.cell(current_row, 2).border = thin_border
        
        start_col = 3
        end_col = len(all_dates) + 2
        ws.merge_cells(start_row=current_row, start_column=start_col, end_row=current_row, end_column=end_col)
        
        month_year_text = all_dates[0].strftime('%b-%y')
        cell = ws.cell(current_row, start_col, value=month_year_text)
        cell.fill = orange_header
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.font = Font(bold=True, size=11)
        
        header_row_1 = current_row
        current_row += 1

        # ==========================================
        # HEADER ROW 2: Day numbers
        # ==========================================
        ws.cell(current_row, 1, value="")
        ws.cell(current_row, 1).border = thin_border
        
        ws.cell(current_row, 2, value="")
        ws.cell(current_row, 2).fill = gray_header
        ws.cell(current_row, 2).border = thin_border
        
        for i, d in enumerate(all_dates):
            cell = ws.cell(current_row, i+3, value=d.day)
            cell.fill = light_blue_header
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.font = Font(bold=True, size=11)
        
        header_row_2 = current_row
        current_row += 1

        # Merge A and B for Project Name and "Date"
        ws.merge_cells(start_row=header_row_1, start_column=1, end_row=header_row_2, end_column=1)
        ws.cell(header_row_1, 1, value=project.name)
        ws.cell(header_row_1, 1).fill = light_blue_header
        ws.cell(header_row_1, 1).border = thin_border
        ws.cell(header_row_1, 1).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(header_row_1, 1).font = Font(bold=True, size=12)

        ws.merge_cells(start_row=header_row_1, start_column=2, end_row=header_row_2, end_column=2)
        ws.cell(header_row_1, 2, value="Date")
        ws.cell(header_row_1, 2).fill = light_blue_header
        ws.cell(header_row_1, 2).border = thin_border
        ws.cell(header_row_1, 2).alignment = Alignment(horizontal='center', vertical='center')
        ws.cell(header_row_1, 2).font = Font(bold=True, size=11)

        # --- PLANNED ROW ---
        ws.cell(current_row, 1, value="").border = thin_border
        ws.cell(current_row, 2, value="Planned").border = thin_border
        ws.cell(current_row, 2).font = Font(bold=True)
        ws.cell(current_row, 2).alignment = Alignment(horizontal='center', vertical='center')
        
        planned_map = {}
        for stage in stages:
            if stage.start_date and stage.end_date:
                parts = stage.name.split('-')
                abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
                d = stage.start_date
                while d <= stage.end_date:
                    if is_working_day(d, False, working_saturdays):
                        ds = d.strftime('%Y-%m-%d')
                        if ds not in planned_map: 
                            planned_map[ds] = []
                        planned_map[ds].append(abbr)
                    d += timedelta(days=1)
        
        # ✅ ADD RESCHEDULE DATES TO PLANNED ROW
        # When a task is rescheduled to a new date, that date should appear in the Planned row
        for stage in stages:
            parts = stage.name.split('-')
            abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            
            task_reschedules = DailyTaskRescheduleHistory.query.filter_by(
                project_id=project_id, 
                stage_id=stage.id
            ).all()
            
            for reschedule in task_reschedules:
                # Add the NEW date to planned_map (where the task is now scheduled)
                new_ds = reschedule.new_date.strftime('%Y-%m-%d')
                if new_ds not in planned_map:
                    planned_map[new_ds] = []
                if abbr not in planned_map[new_ds]:
                    planned_map[new_ds].append(abbr)
                    
        for i, d in enumerate(all_dates):
            cell = ws.cell(current_row, i+3)
            ds = d.strftime('%Y-%m-%d')
            
            is_sunday = d.weekday() == 6
            is_non_working_saturday = d.weekday() == 5 and d not in working_saturdays
            
            if ds in planned_map:
                cell.value = ' , '.join(sorted(set(planned_map[ds])))
                cell.alignment = Alignment(text_rotation=0, horizontal='center', vertical='center')
                cell.font = Font(size=9, bold=True)
            
            if is_sunday or is_non_working_saturday:
                cell.fill = yellow_fill
            
            cell.border = thin_border
        
        ws.row_dimensions[current_row].height = 40
        current_row += 1

        # --- RESCHEDULE ROWS (1-4) ---
        for r_num in range(1, 5):
            ws.cell(current_row, 1, value="").border = thin_border
            ws.cell(current_row, 2, value=f"Reschedule -{r_num}").border = thin_border
            ws.cell(current_row, 2).font = Font(bold=True)
            ws.cell(current_row, 2).alignment = Alignment(horizontal='center', vertical='center')
            
            r_data = stage_reschedule_map.get(r_num, {})
            
            for i, d in enumerate(all_dates):
                cell = ws.cell(current_row, i+3)
                ds = d.strftime('%Y-%m-%d')
                
                is_sunday = d.weekday() == 6
                is_non_working_saturday = d.weekday() == 5 and d not in working_saturdays
                
                if ds in r_data:
                    cell.value = ' , '.join(sorted(set(r_data[ds])))
                    cell.alignment = Alignment(text_rotation=0, horizontal='center', vertical='center')
                    cell.font = Font(size=9, bold=True)
                
                if is_sunday or is_non_working_saturday:
                    cell.fill = yellow_fill
                
                cell.border = thin_border
            
            ws.row_dimensions[current_row].height = 30
            current_row += 1

        # --- ACTUAL ROW ---
        ws.cell(current_row, 1, value="").border = thin_border
        ws.cell(current_row, 2, value="Actual").border = thin_border
        ws.cell(current_row, 2).fill = PatternFill(start_color="C0C0C0", end_color="C0C0C0", fill_type="solid")
        ws.cell(current_row, 2).font = Font(bold=True)
        ws.cell(current_row, 2).alignment = Alignment(horizontal='center', vertical='center')

        actual_map = {}
        hold_dates_map = {}

        for stage in stages:
            parts = stage.name.split('-')
            abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            tasks = StageDailyTask.query.filter_by(stage_id=stage.id).all()
            
            for t in tasks:
                ds = t.scheduled_date.strftime('%Y-%m-%d')
                
                if t.status == 'hold':
                    if ds not in hold_dates_map:
                        hold_dates_map[ds] = []
                    if abbr not in hold_dates_map[ds]:
                        hold_dates_map[ds].append(abbr)
                else:
                    if ds not in actual_map: 
                        actual_map[ds] = []
                    actual_map[ds].append((abbr, t.status))
                
                if t.original_date and t.original_date != t.scheduled_date:
                    hds = t.original_date.strftime('%Y-%m-%d')
                    if hds not in hold_dates_map: 
                        hold_dates_map[hds] = []
                    if abbr not in hold_dates_map[hds]:
                        hold_dates_map[hds].append(abbr)
                        
        for i, d in enumerate(all_dates):
            cell = ws.cell(current_row, i+3)
            ds = d.strftime('%Y-%m-%d')
            
            active = actual_map.get(ds, [])
            active_abbrs = set(x[0] for x in active)
            hold_abbrs = set(hold_dates_map.get(ds, []))
            
            real_holds = hold_abbrs - active_abbrs
            
            parts = []
            if real_holds: 
                parts.append(f"{' , '.join(sorted(real_holds))}=HOLD")
            if active_abbrs: 
                parts.append(' , '.join(sorted(active_abbrs)))
            
            if parts:
                cell.value = ' , '.join(parts)
            
            cell.alignment = Alignment(text_rotation=0, horizontal='center', vertical='center')
            cell.font = Font(size=9, bold=True)
            cell.border = thin_border
            
            is_sunday = d.weekday() == 6
            is_non_working_saturday = d.weekday() == 5 and d not in working_saturdays
            
            if is_sunday or is_non_working_saturday:
                cell.fill = yellow_fill
            elif real_holds: 
                cell.fill = orange_fill
            elif active_abbrs:
                stats = set(x[1] for x in active)
                if 'completed' in stats: 
                    cell.fill = green_fill
                elif 'rescheduled' in stats: 
                    cell.fill = cyan_fill

        ws.row_dimensions[current_row].height = 40
        current_row += 1

        # ==========================================
        # REMARKS ROW
        # ==========================================
        ws.cell(current_row, 1, value="").border = thin_border

        ws.cell(current_row, 2, value="Remarks").border = thin_border
        ws.cell(current_row, 2).font = Font(size=10, italic=True, bold=True)
        ws.cell(current_row, 2).alignment = Alignment(vertical='center', horizontal='center')

        for i, d in enumerate(all_dates):
            ds = d.strftime('%Y-%m-%d')
            active = actual_map.get(ds, [])
            active_abbrs = set(x[0] for x in active)
            hold_abbrs = set(hold_dates_map.get(ds, []))
            real_holds = hold_abbrs - active_abbrs
            
            cell = ws.cell(current_row, i+3)
            
            is_sunday = d.weekday() == 6
            is_non_working_saturday = d.weekday() == 5 and d not in working_saturdays
            
            if real_holds:
                reason = "Waiting for issue tracker"
                for stage in stages:
                    parts = stage.name.split('-')
                    abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
                    if abbr in real_holds:
                        task = StageDailyTask.query.filter_by(stage_id=stage.id, scheduled_date=d, status='hold').first()
                        if not task:
                            task = StageDailyTask.query.filter_by(stage_id=stage.id, original_date=d).first()
                        
                        if task and task.rescheduled_reason:
                            reason = task.rescheduled_reason
                            break
                
                cell.value = reason
                cell.alignment = Alignment(text_rotation=0, horizontal='left', vertical='top', wrap_text=True)
                cell.font = Font(size=9)
            elif is_sunday or is_non_working_saturday:
                cell.fill = yellow_fill
            
            cell.border = thin_border

        ws.row_dimensions[current_row].height = 60
        current_row += 1
        current_row += 2
        
        # ==========================================
        # LEGEND TABLE
        # ==========================================
        cell_a1 = ws.cell(current_row, 1, value="")
        cell_a1.fill = orange_fill
        cell_a1.border = thin_border
        
        cell_b1 = ws.cell(current_row, 2, value="Hold")
        cell_b1.border = thin_border
        cell_b1.alignment = Alignment(horizontal='left', vertical='center')
        cell_b1.font = Font(size=10)
        
        ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=4)
        cell_c1 = ws.cell(current_row, 3, value="If project goes on hold from Customer")
        cell_c1.border = thin_border
        cell_c1.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        cell_c1.font = Font(size=10)
        ws.cell(current_row, 4).border = thin_border
        
        ws.row_dimensions[current_row].height = 25
        current_row += 1
        
        cell_a2 = ws.cell(current_row, 1, value="")
        cell_a2.border = thin_border
        
        cell_b2 = ws.cell(current_row, 2, value="Changes")
        cell_b2.border = thin_border
        cell_b2.alignment = Alignment(horizontal='left', vertical='center')
        cell_b2.font = Font(size=10)
        
        ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=4)
        cell_c2 = ws.cell(current_row, 3, value="")
        cell_c2.border = thin_border
        ws.cell(current_row, 4).border = thin_border
        
        ws.row_dimensions[current_row].height = 25
        current_row += 1
        
        cell_a3 = ws.cell(current_row, 1, value="")
        cell_a3.fill = yellow_fill
        cell_a3.border = thin_border
        
        cell_b3 = ws.cell(current_row, 2, value="Holidays")
        cell_b3.border = thin_border
        cell_b3.alignment = Alignment(horizontal='left', vertical='center')
        cell_b3.font = Font(size=10)
        
        ws.merge_cells(start_row=current_row, start_column=3, end_row=current_row, end_column=4)
        cell_c3 = ws.cell(current_row, 3, value="")
        cell_c3.border = thin_border
        ws.cell(current_row, 4).border = thin_border
        
        ws.row_dimensions[current_row].height = 25
        
        # Save to BytesIO
        excel_file = BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        # Save to backend if requested
        if save_to_backend:
            import os
            backend_dir = os.path.join(os.path.dirname(__file__), 'static', 'excel_exports')
            os.makedirs(backend_dir, exist_ok=True)
            
            backend_filepath = os.path.join(backend_dir, f"{project.name}_Tracker_{project_id}.xlsx")
            with open(backend_filepath, 'wb') as f:
                f.write(excel_file.getvalue())
            
            print(f"✅ Excel saved to backend: {backend_filepath}")
            excel_file.seek(0)  # Reset pointer after writing
        
        return excel_file
        
    except Exception as e:
        print(f"❌ Error generating Excel: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================================
# Default Stages Configuration
# ============================================================================

DEFAULT_STAGES = [
    {'name': 'Foot prints - library - FP-LIB', 'order': 1, 'duration_days': 3},
    {'name': 'Schematic - SCH', 'order': 2, 'duration_days': 7},
    {'name': 'Placement - PLC', 'order': 4, 'duration_days': 5},
    {'name': 'Placement - review - PLC-R', 'order': 5, 'duration_days': 3},
    {'name': 'Fan out - FNT', 'order': 6, 'duration_days': 3},
    {'name': 'Routing - RTNG', 'order': 7, 'duration_days': 2},
    {'name': 'Routing - Review - RTNG-R', 'order': 8, 'duration_days': 7},
    {'name': 'Length Matching - LM', 'order': 9, 'duration_days': 4},
    {'name': 'Post Screen - P-SI', 'order': 10, 'duration_days': 4},
    {'name': 'Silk Screen - SLK', 'order': 11, 'duration_days': 5},
    {'name': 'Deliverables - DLBS', 'order': 12, 'duration_days': 3},
    {'name': 'Approval - APRVL', 'order': 13, 'duration_days': 3},
    {'name': 'Fab setup - FB-STP', 'order': 14, 'duration_days': 5}
]
# ============================================================================
# Helper Functions
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def log_activity(action):
    user = get_current_user()
    if user:
        log = ActivityLog(user_id=user.id, action=action)
        db.session.add(log)
        db.session.commit()

def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()

def is_working_day(date, include_saturday=False, working_saturdays=None):
    """Check if a date is a working day"""
    if working_saturdays is None:
        working_saturdays = set()
        
    weekday = date.weekday()
    date_str = date.strftime('%Y-%m-%d')
    
    if weekday == 6:  # Sunday
        return False
    if weekday == 5:  # Saturday
        return date_str in working_saturdays
    return True

def add_working_days(start_date, days, include_saturday=False, working_saturdays=None):
    """Add working days to a date, properly handling working Saturdays"""
    if working_saturdays is None:
        working_saturdays = set()
        
    if days == 0:
        return start_date
        
    current_date = start_date
    direction = 1 if days > 0 else -1
    days_remaining = abs(days)
    
    while days_remaining > 0:
        current_date = current_date + timedelta(days=direction)
        if is_working_day(current_date, include_saturday, working_saturdays):
            days_remaining -= 1
    
    return current_date

def get_next_working_day(date, include_saturday=False, working_saturdays=None):
    """Get the next working day from a given date"""
    if working_saturdays is None:
        working_saturdays = set()
    check_date = date
    while not is_working_day(check_date, include_saturday, working_saturdays):
        check_date = check_date + timedelta(days=1)
    return check_date

def calculate_stage_dates(project_start_date, stages_data, include_saturday=False, working_saturdays=None):
    """Calculate start and end dates for each stage based on working days (excluding weekends)"""
    
    if working_saturdays is None:
        working_saturdays = set()
    
    calculated_stages = []
    current_date = get_next_working_day(project_start_date, False, working_saturdays)
    
    for stage_info in stages_data:
        stage_start = stage_info.get('start_date')
        
        if stage_start:
            # Custom start date provided
            custom_start = datetime.strptime(stage_start, '%Y-%m-%d').date()
            stage_start_date = get_next_working_day(custom_start, False, working_saturdays)
        else:
            # Use current date
            stage_start_date = current_date
        
        # Calculate end date based on duration
        duration = stage_info.get('duration_days', 1)
        if duration > 0:
            stage_end_date = add_working_days(stage_start_date, duration - 1, False, working_saturdays)
        else:
            stage_end_date = stage_start_date
        
        calculated_stages.append({
            'name': stage_info['name'],
            'order': stage_info['order'],
            'duration_days': duration,
            'start_date': stage_start_date,
            'end_date': stage_end_date,
            'manager_id': stage_info.get('manager_id'),
            'id': stage_info.get('id'),  # Preserve the ID for updates
            'parallel_group_id': stage_info.get('parallel_group_id')  # Preserve parallel_group_id
        })
        
        # Always advance current_date so sequential stages chain correctly
        # even if this stage used a custom start_date.
        current_date = add_working_days(stage_end_date, 1, False, working_saturdays)
    
    return calculated_stages

def generate_daily_tasks_for_project(project_id, working_saturdays=None):
    """Generate daily tasks for all stages in a project"""
    if working_saturdays is None:
        working_saturdays = set()
    
    project = Project.query.get(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")
    
    stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
    
    for stage in stages:
        if not stage.start_date or not stage.end_date:
            continue
        
        # Generate daily tasks
        current_date = stage.start_date
        day_number = 1
        
        while current_date <= stage.end_date:
            # Only create task for working days
            if is_working_day(current_date, False, working_saturdays):
                daily_task = StageDailyTask(
                    stage_id=stage.id,
                    project_id=project_id,
                    day_number=day_number,
                    scheduled_date=current_date,
                    status='pending'
                )
                db.session.add(daily_task)
                day_number += 1
            
            current_date = current_date + timedelta(days=1)
    
    # Don't commit here - let the caller handle the commit
    db.session.flush()

# ============================================================================
# Auto Gap-Filling Function
# ============================================================================

def auto_shift_tasks_to_fill_gaps(project_id):
    """
    Find gaps in the schedule and shift tasks AFTER the gap to fill it.
    Does NOT reorganize from start - only fills detected gaps.
    Preserves parallel stage structure.
    """
    project = Project.query.get(project_id)
    if not project:
        return {"success": False, "error": "Project not found"}
    
    # Get working Saturdays
    working_saturdays = json.loads(project.working_saturdays or '[]')
    working_saturdays = [datetime.strptime(d, '%Y-%m-%d').date() for d in working_saturdays]
    
    def is_working_day_check(date):
        """Check if a date is a working day (Mon-Fri or working Saturday)"""
        if date.weekday() < 5:  # Monday-Friday
            return True
        if date.weekday() == 5 and date in working_saturdays:  # Saturday
            return True
        return False
    
    # Get all hold dates for this project
    hold_dates = set(hd.hold_date for hd in HoldDate.query.filter_by(project_id=project_id).all())
    
    # Get all stages ordered by their actual dates (not by order field)
    stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.start_date).all()
    
    if not stages:
        return {"success": True, "message": "No stages to process", "shifts_made": 0}
    
    shifts_made = []
    
    # Process each stage independently to preserve parallel stages
    for stage in stages:
        # Get all tasks for this stage
        stage_tasks = StageDailyTask.query.filter_by(
            stage_id=stage.id
        ).filter(
            StageDailyTask.status.in_(['pending', 'rescheduled'])
        ).order_by(StageDailyTask.day_number).all()
        
        if not stage_tasks:
            continue
        
        # Find the expected start date for this stage
        expected_date = stage.start_date
        
        # Skip to first working day
        while not is_working_day_check(expected_date) or expected_date in hold_dates:
            expected_date += timedelta(days=1)
        
        # Check each task in this stage
        for task in stage_tasks:
            original_date = task.scheduled_date
            
            # Skip to next available working day
            while not is_working_day_check(expected_date) or expected_date in hold_dates:
                expected_date += timedelta(days=1)
            
            # If there's a gap (task is scheduled later than expected), shift it
            if task.scheduled_date > expected_date:
                days_shifted = (expected_date - task.scheduled_date).days
                
                # Update task
                task.original_date = task.original_date or task.scheduled_date
                task.scheduled_date = expected_date
                task.status = 'rescheduled'
                task.reschedule_count = (task.reschedule_count or 0) + 1
                task.rescheduled_reason = f"Auto-shifted to fill gap (moved {days_shifted} days)"
                
                # Log the shift
                history = DailyTaskRescheduleHistory(
                    project_id=project_id,
                    stage_id=task.stage_id,
                    task_id=task.id,
                    day_number=task.day_number,
                    reschedule_number=task.reschedule_count,
                    original_date=original_date,
                    new_date=expected_date,
                    days_shifted=abs(days_shifted),
                    reason=f"Auto-shifted to fill gap in schedule",
                    rescheduled_by=session.get('user_id'),
                    rescheduled_at=datetime.utcnow()
                )
                db.session.add(history)
                
                shifts_made.append({
                    'task_id': task.id,
                    'day_number': task.day_number,
                    'stage_id': task.stage_id,
                    'old_date': original_date.strftime('%Y-%m-%d'),
                    'new_date': expected_date.strftime('%Y-%m-%d'),
                    'days_shifted': days_shifted
                })
            
            # Move expected date to next working day for next task
            expected_date += timedelta(days=1)
        
        # Update stage end date based on last task
        if stage_tasks:
            stage.end_date = max(t.scheduled_date for t in stage_tasks)
    
    # Update project end date based on latest stage
    if stages:
        latest_end = max(s.end_date for s in stages if s.end_date)
        if latest_end and project.end_date != latest_end:
            project.end_date = latest_end
    
    # Commit all changes
    db.session.commit()
    
    # Regenerate Excel file
    try:
        generate_excel_file(project_id, save_to_backend=True)
    except Exception as e:
        print(f"Warning: Could not regenerate Excel file: {e}")
    
    return {
        "success": True,
        "shifts_made": len(shifts_made),
        "tasks_shifted": shifts_made,
        "new_project_end_date": project.end_date.strftime('%Y-%m-%d') if project.end_date else None,
        "project_end_date_changed": len(shifts_made) > 0
    }

# ============================================================================
# Routes
# ============================================================================

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    return render_template('index.html', current_user=user)

@app.route('/stage_popup.html')
def stage_popup():
    return render_template('stage_popup.html')

# ============================================================================
# API Endpoints
# ============================================================================

@app.route('/api/default-stages', methods=['GET'])
@login_required
def get_default_stages():
    """Return default stages for frontend"""
    return jsonify(DEFAULT_STAGES)

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status='active').count()
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(status='completed').count()
    total_employees = User.query.filter_by(role='employee').count()
    
    return jsonify({
        'total_projects': total_projects,
        'active_projects': active_projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'total_employees': total_employees
    })

@app.route('/api/projects', methods=['GET', 'POST'])
@login_required
def projects():
    if request.method == 'POST':
        data = request.get_json()
        user = get_current_user()
        
        try:
            project_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data.get('start_date') else datetime.now().date()

            include_saturday = data.get('include_saturday', False)
            working_saturdays = set(data.get('working_saturdays', []))
            
            # Calculate stage dates based on duration
            stages_data = data.get('stages', [])
            calculated_stages = calculate_stage_dates(project_start_date, stages_data, include_saturday, working_saturdays)

            # Calculate project end date from last stage
            project_end_date = calculated_stages[-1]['end_date'] if calculated_stages else project_start_date
            
            project = Project(
                name=data['name'],
                description=data.get('description', ''),
                start_date=project_start_date,
                end_date=project_end_date,
                created_by=user.id,
                working_saturdays=json.dumps(list(working_saturdays))
            )
            db.session.add(project)
            db.session.flush()


            
            # Add stages with calculated dates
            for stage_data in calculated_stages:
                stage = ProjectStage(
                    project_id=project.id,
                    name=stage_data['name'],
                    order=stage_data['order'],
                    duration_days=stage_data.get('duration_days', 0),
                    start_date=stage_data['start_date'],
                    end_date=stage_data['end_date'],
                    manager_id=stage_data.get('manager_id'),
                    parallel_group_id=stage_data.get('parallel_group_id')
                )
                db.session.add(stage)
                            
            # Add project members
            member_ids = data.get('members', [])
            for member_id in member_ids:
                member = ProjectMember(
                    project_id=project.id,
                    user_id=member_id
                )
                db.session.add(member)
                create_notification(member_id, f"You have been added to job: {project.name}")
            
            db.session.commit()
            
        # âœ… NEW: Generate daily tasks immediately after project creation
            try:
                generate_daily_tasks_for_project(project.id, working_saturdays)
                print(f"\u2714 Generated daily tasks for project {project.id}")
            except Exception as e:
                print(f"Warning: Could not generate daily tasks: {e}")            
            log_activity(f"Created job: {project.name}")
            
            return jsonify({'success': True, 'id': project.id}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error creating project: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 400
    
    # GET - Return list of all projects
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'status': p.status,
        'progress': p.progress,
        'start_date': p.start_date.isoformat() if p.start_date else None,
        'end_date': p.end_date.isoformat() if p.end_date else None
    } for p in projects])



from flask import make_response

@app.route('/api/projects/<int:project_id>/details', methods=['GET'])
@login_required
def project_details(project_id):
    project = Project.query.get_or_404(project_id)
    
    # ✅ Force fresh data from database (prevents ORM caching)
    db.session.refresh(project)
    
    stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
    tasks = Task.query.filter_by(project_id=project_id).all()
    schedule_history = ScheduleHistory.query.filter_by(project_id=project_id).order_by(ScheduleHistory.rescheduled_at.desc()).all()
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    
    # Parse working Saturdays
    try:
        if project.working_saturdays:
            working_saturdays = json.loads(project.working_saturdays)
        else:
            working_saturdays = []
    except:
        working_saturdays = []
    
    # Calculate task stats
    task_stats = {
        'pending': sum(1 for t in tasks if t.status == 'pending'),
        'in-progress': sum(1 for t in tasks if t.status == 'in-progress'),
        'completed': sum(1 for t in tasks if t.status == 'completed')
    }
    
    # Calculate stage completion
    completed_stages = sum(1 for s in stages if s.status == 'completed')
    
    # ✅ Build response data
    data = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'status': project.status,
        'progress': project.progress,
        'start_date': project.start_date.isoformat() if project.start_date else None,
        'end_date': project.end_date.isoformat() if project.end_date else None,
        'saturdayWorkingDays': working_saturdays,
        'stages': [{
            'id': s.id,
            'name': s.name,
            'order': s.order,
            'duration_days': s.duration_days,
            'status': s.status,
            'progress': s.progress,
            'start_date': s.start_date.isoformat() if s.start_date else None,
            'end_date': s.end_date.isoformat() if s.end_date else None,
            'manager_id': s.manager_id,
            'parallel_group_id': s.parallel_group_id if hasattr(s, 'parallel_group_id') else None  # ✅ ADD THIS
        } for s in stages],
        'members': [{
            'id': User.query.get(m.user_id).id,
            'username': User.query.get(m.user_id).username,
            'email': User.query.get(m.user_id).email
        } for m in members],
        'task_stats': task_stats,
        'stage_completion': {
            'completed': completed_stages,
            'total': len(stages)
        },
        'schedule_history': [{
            'original_date': h.original_date.isoformat() if h.original_date else None,
            'new_date': h.new_date.isoformat() if h.new_date else None,
            'reason': h.reason,
            'rescheduled_by': User.query.get(h.rescheduled_by).username if h.rescheduled_by else 'Unknown',
            'rescheduled_at': h.rescheduled_at.strftime('%Y-%m-%d %H:%M')
        } for h in schedule_history]
    }
    
    # ✅ Create response with anti-cache headers
    response = make_response(jsonify(data))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/api/projects/<int:project_id>/stage-status', methods=['GET'])
@login_required
def get_project_stage_status(project_id):
    """Get detailed status for each stage including reschedule info"""
    try:
        project = Project.query.get_or_404(project_id)
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        today = datetime.now().date()
        stage_statuses = []
        
        for stage in stages:
            # Check if stage has been rescheduled at stage level
            stage_reschedules = ScheduleHistory.query.filter_by(
                project_id=project_id,
                stage_id=stage.id
            ).order_by(ScheduleHistory.rescheduled_at.desc()).all()
            
            # Check if any daily tasks in this stage were rescheduled
            daily_task_reschedules = DailyTaskRescheduleHistory.query.filter_by(
                project_id=project_id,
                stage_id=stage.id
            ).all()
            
            # Consider stage rescheduled if EITHER stage-level or daily-task-level reschedules exist
            was_rescheduled = len(stage_reschedules) > 0 or len(daily_task_reschedules) > 0
            total_reschedules = len(stage_reschedules) + len(daily_task_reschedules)
            
            # Determine status
            if stage.progress == 100 or stage.status == 'completed':
                if was_rescheduled:
                    status = 'completed-rescheduled'
                    color = '#90EE90'  # Light green
                else:
                    status = 'completed'
                    color = '#006400'  # Dark green
            elif stage.start_date and stage.end_date:
                if today >= stage.start_date and today <= stage.end_date:
                    status = 'in-progress'
                    color = '#FFD700'  # Yellow
                elif today > stage.end_date and stage.status != 'completed':
                    status = 'overdue'
                    color = '#FF6B6B'  # Red
                else:
                    status = 'not-started'
                    color = '#dee2e6'  # Gray
            else:
                status = 'not-started'
                color = '#dee2e6'
            
            stage_statuses.append({
                'id': stage.id,
                'name': stage.name,
                'status': status,
                'color': color,
                'progress': stage.progress,
                'was_rescheduled': was_rescheduled,
                'reschedule_count': total_reschedules,
                'start_date': stage.start_date.isoformat() if stage.start_date else None,
                'end_date': stage.end_date.isoformat() if stage.end_date else None
            })
        
        return jsonify({
            'success': True,
            'stages': stage_statuses
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            task = Task(
                title=data['title'],
                description=data.get('description', ''),
                project_id=data.get('project_id'),
                assigned_to=data.get('assigned_to'),
                priority=data.get('priority', 'medium'),
                deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date() if data.get('deadline') else None
            )
            db.session.add(task)
            db.session.commit()
            
            log_activity(f"Created task: {task.title}")
            
            # Notify assigned user
            if task.assigned_to:
                create_notification(task.assigned_to, f"New task assigned: {task.title}")
            
            return jsonify({'success': True, 'id': task.id}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    # GET
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'description': t.description,
        'project': Project.query.get(t.project_id).name if t.project_id else None,
        'assigned_to': User.query.get(t.assigned_to).username if t.assigned_to else None,
        'priority': t.priority,
        'status': t.status,
        'deadline': t.deadline.isoformat() if t.deadline else None
    } for t in tasks])

@app.route('/api/tasks/<int:task_id>/status', methods=['PUT'])
@login_required
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    
    task.status = data['status']
    if data['status'] == 'completed':
        task.completed_at = datetime.utcnow()
    
    db.session.commit()
    log_activity(f"Updated task status: {task.title} to {task.status}")
    
    return jsonify({'success': True})

@app.route('/api/employees', methods=['GET'])
@login_required
def employees():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role
    } for u in users])

@app.route('/api/notifications', methods=['GET'])
@login_required
def notifications():
    user = get_current_user()
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify([{
        'id': n.id,
        'message': n.message,
        'is_read': n.is_read,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M')
    } for n in notifications])

@app.route('/api/notifications/<int:notification_id>/read', methods=['PUT'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/activity-logs', methods=['GET'])
@login_required
def activity_logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    
    return jsonify([{
        'user': User.query.get(l.user_id).username,
        'action': l.action,
        'timestamp': l.timestamp.strftime('%Y-%m-%d %H:%M')
    } for l in logs])

@app.route('/api/projects/<int:project_id>/stages/<int:stage_id>', methods=['PUT'])
@login_required
def update_stage_status(project_id, stage_id):
    """Update stage details and recalculate project schedule"""
    try:
        data = request.get_json()
        stage = ProjectStage.query.filter_by(
            id=stage_id,
            project_id=project_id
        ).first_or_404()
        
        project = Project.query.get_or_404(project_id)
        
        old_status = stage.status
        
        # Update stage fields
        if 'name' in data:
            stage.name = data['name']
        if 'duration_days' in data:
            stage.duration_days = data['duration_days']
        if 'status' in data:
            stage.status = data['status']
            # Update progress percentage based on status
            if stage.status == 'in-progress':
                stage.progress = 50
            elif stage.status == 'completed':
                stage.progress = 100
            else:
                stage.progress = 0
        if 'start_date' in data:
            stage.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data:
            stage.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        db.session.commit()
        
        # ✅ FIX: Only recalculate if duration or dates changed, not just status
        needs_recalculation = 'duration_days' in data or 'start_date' in data or 'end_date' in data
        
        # Skip recalculation if only status changed
        if not needs_recalculation and len(data) == 1 and 'status' in data:
            # Update project progress and return early
            update_project_progress(project_id)
            
            if old_status != stage.status:
                log_activity(f"Updated stage '{stage.name}' status from {old_status} to {stage.status}")
            
            return jsonify({'success': True, 'message': 'Stage updated successfully'})
        
        # Recalculate all stage dates and regenerate daily tasks
        working_saturdays_data = json.loads(project.working_saturdays) if project.working_saturdays else []
        working_saturdays = set(working_saturdays_data)
        
        # Get all stages for this project in order
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        # Recalculate dates starting from project start date
        current_date = get_next_working_day(project.start_date, False, working_saturdays)
        
        for s in stages:
            s.start_date = current_date
            s.end_date = add_working_days(current_date, s.duration_days - 1, False, working_saturdays)
            current_date = s.end_date + timedelta(days=1)
            current_date = get_next_working_day(current_date, False, working_saturdays)
        
        # Update project end date
        if stages:
            project.end_date = stages[-1].end_date
        
        db.session.commit()
        
        # Delete old daily tasks for this project
        StageDailyTask.query.filter_by(project_id=project_id).delete()
        
        # Regenerate daily tasks for all stages
        for s in stages:
            if s.duration_days > 0:
                task_date = s.start_date
                for day_num in range(1, s.duration_days + 1):
                    while not is_working_day(task_date, False, working_saturdays):
                        task_date += timedelta(days=1)
                    
                    daily_task = StageDailyTask(
                        stage_id=s.id,
                        project_id=project_id,
                        day_number=day_num,
                        scheduled_date=task_date,
                        original_date=task_date,
                        status='pending'
                    )
                    db.session.add(daily_task)
                    task_date += timedelta(days=1)
        
        db.session.commit()
        
        # Update project progress
        update_project_progress(project_id)
        
        if old_status != stage.status:
            log_activity(f"Updated stage '{stage.name}' status from {old_status} to {stage.status}")
        
        return jsonify({'success': True, 'message': 'Stage updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating stage: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def update_project_progress(project_id):
    """Calculate and update project progress based on stages"""
    stages = ProjectStage.query.filter_by(project_id=project_id).all()
    
    if not stages:
        return
    
    total_progress = sum(stage.progress for stage in stages)
    average_progress = total_progress // len(stages) if stages else 0
    
    project = Project.query.get(project_id)
    project.progress = average_progress
    
    # Auto-update project status
    completed_stages = sum(1 for s in stages if s.status == 'completed')
    if completed_stages == len(stages):
        project.status = 'completed'
    elif any(s.status == 'in-progress' for s in stages):
        project.status = 'active'
        
        
        

    
    db.session.commit()

@app.route('/api/projects/<int:project_id>/reschedule', methods=['POST'])
@login_required
def reschedule_stage(project_id):
    data = request.get_json()
    stage_id = data.get('stage_id')
    days = data.get('days', 0)
    reason = data.get('reason', '')
    working_saturdays = set(data.get('working_saturdays', []))
    
    try:
        project = Project.query.get_or_404(project_id)
        stage = ProjectStage.query.get_or_404(stage_id)
        
        # ✅ INCREMENT GLOBAL RESCHEDULE COUNTER
        project.current_reschedule_number += 1
        global_reschedule_num = project.current_reschedule_number
        
        print(f"\n📋 RESCHEDULE REQUEST:")
        print(f"   Stage: {stage.name}")
        print(f"   Global Reschedule Number: {global_reschedule_num}")
        
        # Store EXACT original dates BEFORE any modifications
        original_start_date = stage.start_date
        original_end_date = stage.end_date
        
        print(f"   Original dates: {original_start_date} to {original_end_date}")
        print(f"   Shift: {days} days")
        
        # Calculate which dates will become HOLD
        if days != 0 and original_start_date and original_end_date:
            # Get all original working dates
            original_dates = set()
            current = original_start_date
            while current <= original_end_date:
                if is_working_day(current, False, working_saturdays):
                    original_dates.add(current)
                current += timedelta(days=1)
            
            # Calculate new dates
            new_start = add_working_days(original_start_date, days, False, working_saturdays)
            new_end = add_working_days(original_end_date, days, False, working_saturdays)
            
            new_dates = set()
            current = new_start
            while current <= new_end:
                if is_working_day(current, False, working_saturdays):
                    new_dates.add(current)
                current += timedelta(days=1)
            
            # HOLD dates = dates that were in original but NOT in new schedule
            hold_dates = original_dates - new_dates
            
            print(f"   New dates: {new_start} to {new_end}")
            print(f"   HOLD dates: {sorted(hold_dates)}")
            
            # Store each HOLD date in database
            for hold_date in hold_dates:
                hold_record = HoldDate(
                    project_id=project_id,
                    stage_id=stage_id,
                    hold_date=hold_date,
                    reason=reason if reason else f"Stage rescheduled by {abs(days)} day(s)",
                    created_by=get_current_user().id
                )
                db.session.add(hold_record)
                print(f"   ✅ Stored HOLD: {hold_date}")
        
        # Update stage dates
        if days != 0:
            if stage.start_date:
                stage.start_date = add_working_days(stage.start_date, days, False, working_saturdays)
            if stage.end_date:
                stage.end_date = add_working_days(stage.end_date, days, False, working_saturdays)
            
            print(f"   ✅ Updated stage dates: {stage.start_date} to {stage.end_date}")
            
            # Move subsequent stages
            subsequent_stages = ProjectStage.query.filter(
                ProjectStage.project_id == project_id,
                ProjectStage.order > stage.order,
                ProjectStage.status != 'completed'
            ).order_by(ProjectStage.order).all()
            
            for subsequent_stage in subsequent_stages:
                if subsequent_stage.start_date:
                    subsequent_stage.start_date = add_working_days(
                        subsequent_stage.start_date, days, False, working_saturdays
                    )
                if subsequent_stage.end_date:
                    subsequent_stage.end_date = add_working_days(
                        subsequent_stage.end_date, days, False, working_saturdays
                    )
                print(f"   ↪️ Shifted subsequent stage: {subsequent_stage.name}")
        
        # ✅ CREATE HISTORY WITH GLOBAL RESCHEDULE NUMBER
        history = ScheduleHistory(
            project_id=project_id,
            stage_id=stage_id,
            reschedule_number=global_reschedule_num,  # ✅ Use global counter
            original_date=original_start_date,
            new_date=stage.start_date,
            reason=reason if reason else f"Reschedule #{global_reschedule_num}: Shifted {abs(days)} day(s)",
            rescheduled_by=get_current_user().id
        )
        db.session.add(history)
        
        print(f"   ✅ Created ScheduleHistory record: Reschedule #{global_reschedule_num}")
        print(f"      Original: {original_start_date} → New: {stage.start_date}")
        
        # Update project end date
        all_stages = ProjectStage.query.filter_by(project_id=project_id).all()
        if all_stages:
            latest_end = max(s.end_date for s in all_stages if s.end_date)
            project.end_date = latest_end
            project.working_saturdays = json.dumps(list(working_saturdays))
        
        # Delete old daily tasks before regenerating (critical for HOLD display)
        old_tasks_count = StageDailyTask.query.filter_by(project_id=project_id).count()
        StageDailyTask.query.filter_by(project_id=project_id).delete()
        print(f'   🗑️ Deleted {old_tasks_count} old daily tasks for project {project_id}')
        
        # Regenerate daily tasks
        generate_daily_tasks_for_project(project_id, working_saturdays)
        
        # ✅ COMMIT EVERYTHING
        db.session.commit()
        
        # 🔥 AUTO-REGENERATE EXCEL IN BACKEND
        try:
            generate_excel_file(project_id, save_to_backend=True)
            print(f"✅ Excel regenerated in backend for project {project_id}")
        except Exception as excel_error:
            print(f"⚠️ Excel regeneration failed: {excel_error}")
        
        # ✅ VERIFY the record was created
        verification = ScheduleHistory.query.filter_by(
            project_id=project_id,
            stage_id=stage_id,
            reschedule_number=global_reschedule_num
        ).first()
        
        if verification:
            print(f"   ✅ VERIFIED: ScheduleHistory record #{verification.id} exists in database")
            print(f"      Reschedule number: {verification.reschedule_number}")
        else:
            print(f"   ⚠️ WARNING: ScheduleHistory record not found after commit!")
        
        log_activity(f"Rescheduled stage '{stage.name}' (Global Reschedule #{global_reschedule_num})")
        
        return jsonify({
            'success': True,
            'reschedule_number': global_reschedule_num,
            'new_start': stage.start_date.isoformat() if stage.start_date else None,
            'new_end': stage.end_date.isoformat() if stage.end_date else None
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        
        # Delete associated records first (foreign key constraints)
        # ✅ CRITICAL FIX: Delete daily tasks (calendar events) first
        StageDailyTask.query.filter_by(project_id=project_id).delete()
        DailyTaskRescheduleHistory.query.filter_by(project_id=project_id).delete()
        HoldDate.query.filter_by(project_id=project_id).delete()
        
        # Delete other associated records
        ProjectStage.query.filter_by(project_id=project_id).delete()
        ProjectMember.query.filter_by(project_id=project_id).delete()
        Task.query.filter_by(project_id=project_id).delete()
        ScheduleHistory.query.filter_by(project_id=project_id).delete()
        
        # Delete the project
        db.session.delete(project)
        db.session.commit()
        
        log_activity(f"Deleted job: {project_name}")
        
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/projects/<int:project_id>/update-saturdays', methods=['POST'])
@login_required
def update_saturdays(project_id):
    """Update working Saturdays and recalculate all stage dates"""
    data = request.get_json()
    working_saturdays = set(data.get('working_saturdays', []))
    
    try:
        project = Project.query.get_or_404(project_id)
        
        # Save working Saturdays to database
        project.working_saturdays = json.dumps(list(working_saturdays))
        
        # Get all stages ordered by their order field
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        # Recalculate all stage dates from project start
        current_date = get_next_working_day(project.start_date, False, working_saturdays)
        
        for stage in stages:
            # Set start date
            stage.start_date = current_date
            
            # Calculate end date based on duration
            if stage.duration_days > 0:
                stage.end_date = add_working_days(current_date, stage.duration_days - 1, False, working_saturdays)
            else:
                stage.end_date = current_date
            
            # Next stage starts the next working day after THIS stage ends
            current_date = add_working_days(stage.end_date, 1, False, working_saturdays)
        
        # Update project end date
        if stages:
            latest_end = max(s.end_date for s in stages if s.end_date)
            project.end_date = latest_end
        
        db.session.commit()
        
        log_activity(f"Updated working Saturdays for project '{project.name}'")
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating Saturdays: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/projects/<int:project_id>/stages/<int:stage_id>/daily-tasks', methods=['GET'])
@login_required
def get_stage_daily_tasks(project_id, stage_id):
    """Get all daily tasks for a stage"""
    try:
        tasks = StageDailyTask.query.filter_by(
            project_id=project_id,
            stage_id=stage_id
        ).order_by(StageDailyTask.day_number).all()
        
        return jsonify([{
            'id': t.id,
            'day_number': t.day_number,
            'scheduled_date': t.scheduled_date.isoformat(),
            'original_date': t.original_date.isoformat() if t.original_date else None,
            'status': t.status,
            'completed_at': t.completed_at.strftime('%Y-%m-%d %H:%M') if t.completed_at else None,
            'rescheduled_reason': t.rescheduled_reason,
            'is_rescheduled': t.original_date is not None
        } for t in tasks])
    except Exception as e:
        print(f"Error loading daily tasks: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/projects/<int:project_id>/stages/<int:stage_id>/daily-tasks/<int:task_id>/complete', methods=['PUT'])
@login_required
def complete_daily_task(project_id, stage_id, task_id):
    """Mark a daily task as completed"""
    task = StageDailyTask.query.get_or_404(task_id)
    
    # ✅ VALIDATION: Don't allow completing future tasks
    today = datetime.now().date()
    task_date = task.scheduled_date
    
    if task_date > today:
        return jsonify({
            'success': False, 
            'error': f'Cannot complete future task scheduled for {task_date.strftime("%B %d, %Y")}. Today is {today.strftime("%B %d, %Y")}.'
        }), 400
    
    task.status = 'completed'
    task.completed_at = datetime.utcnow()
    db.session.commit()
    
    # 🔥 AUTO-REGENERATE EXCEL IN BACKEND
    try:
        generate_excel_file(project_id, save_to_backend=True)
        print(f"✅ Excel regenerated in backend for project {project_id}")
    except Exception as excel_error:
        print(f"⚠️ Excel regeneration failed: {excel_error}")
    
    # ✅ AUTO-COMPLETE STAGE: Check if all tasks in this stage are completed
    all_tasks = StageDailyTask.query.filter_by(
        stage_id=stage_id,
        project_id=project_id
    ).all()
    
    completed_tasks = [t for t in all_tasks if t.status == 'completed']
    all_completed = len(completed_tasks) == len(all_tasks) and len(all_tasks) > 0
    
    # If all tasks are completed, mark stage as completed
    if all_completed:
        stage = ProjectStage.query.get(stage_id)
        if stage and stage.status != 'completed':
            stage.status = 'completed'
            stage.progress = 100
            db.session.commit()
            log_activity(f"Stage '{stage.name}' automatically completed - all daily tasks done")
    
    log_activity(f"Completed day {task.day_number} of stage")
    
    return jsonify({
        'success': True,
        'stage_completed': all_completed,
        'completed_tasks': len(completed_tasks),
        'total_tasks': len(all_tasks)
    })


@app.route('/api/projects/<int:project_id>/stages/<int:stage_id>/daily-tasks/<int:task_id>/reschedule', methods=['POST'])
@login_required
def reschedule_daily_task(project_id, stage_id, task_id):
    data = request.get_json()
    days_to_shift = data.get('days', 0)
    reason = data.get('reason', '')
    working_saturdays = set(data.get('working_saturdays', []))
    
    try:
        task = StageDailyTask.query.get_or_404(task_id)
        stage = ProjectStage.query.get_or_404(stage_id)
        project = Project.query.get_or_404(project_id)
        
        # PREVENT RESCHEDULING COMPLETED TASKS
        if task.status == 'completed':
            return jsonify({'error': 'Cannot reschedule a completed task'}), 400
        
        # ✅ INCREMENT GLOBAL RESCHEDULE COUNTER
        project.current_reschedule_number += 1
        global_reschedule_num = project.current_reschedule_number
        
        # ✅ INCREMENT TASK-LEVEL RESCHEDULE COUNT (for tracking)
        task.reschedule_count = (task.reschedule_count or 0) + 1
        
        # ✅ FIX: Store CURRENT scheduled_date as original_date for THIS reschedule
        # This is the date the task is being moved FROM (not the very first original date)
        current_location = task.scheduled_date  # This is where the task is NOW
        
        # Keep track of the very first original date (for reference only)
        if not task.original_date:
            task.original_date = task.scheduled_date
        
        # Calculate new date
        new_date = add_working_days(task.scheduled_date, days_to_shift, False, working_saturdays)
        
        task.scheduled_date = new_date
        task.status = 'rescheduled'
        task.rescheduled_reason = reason
        
        print(f"\n📋 DAILY TASK RESCHEDULE:")
        print(f"   Stage: {stage.name}, Day {task.day_number}")
        print(f"   Global Reschedule Number: {global_reschedule_num}")
        print(f"   Current Location: {current_location} → New: {new_date}")
        print(f"   Task Reschedule count: {task.reschedule_count}")
        
        # ✅ CREATE DAILY TASK HISTORY WITH CURRENT LOCATION (not original_date)
        task_history = DailyTaskRescheduleHistory(
            project_id=project_id,
            stage_id=stage_id,
            task_id=task.id,
            day_number=task.day_number,
            reschedule_number=global_reschedule_num,
            original_date=current_location,  # ✅ USE CURRENT LOCATION, not task.original_date
            new_date=new_date,
            days_shifted=abs(days_to_shift),
            reason=reason if reason else f"Reschedule #{global_reschedule_num}: Shifted {abs(days_to_shift)} day(s)",
            rescheduled_by=get_current_user().id
        )
        db.session.add(task_history)
        
        # ✅ REMOVED STAGE-LEVEL HISTORY - IT WAS CREATING DUPLICATE GHOST EVENTS!
        # Only daily task history should be created for daily task reschedules
        
        print(f"   ✅ Created daily task history with global reschedule #{global_reschedule_num}")        
        # UPDATE SUBSEQUENT NON-COMPLETED TASKS
        all_stage_tasks = StageDailyTask.query.filter_by(
            stage_id=stage_id
        ).filter(
            StageDailyTask.day_number > task.day_number,
            StageDailyTask.status != 'completed'
        ).order_by(StageDailyTask.day_number).all()
        
        for subsequent_task in all_stage_tasks:
            subsequent_task.reschedule_count = (subsequent_task.reschedule_count or 0) + 1
            
            # ✅ FIX: Use CURRENT scheduled_date as the "from" location
            subsequent_current_location = subsequent_task.scheduled_date
            
            if not subsequent_task.original_date:
                subsequent_task.original_date = subsequent_task.scheduled_date
            
            subsequent_new_date = add_working_days(
                subsequent_task.scheduled_date, 
                days_to_shift, 
                False, 
                working_saturdays
            )
            
            subsequent_task.scheduled_date = subsequent_new_date
            subsequent_task.status = 'rescheduled'
            if not subsequent_task.rescheduled_reason:
                subsequent_task.rescheduled_reason = f"Auto-shifted due to Day {task.day_number} reschedule"
            
            subsequent_history = DailyTaskRescheduleHistory(
                project_id=project_id,
                stage_id=stage_id,
                task_id=subsequent_task.id,
                day_number=subsequent_task.day_number,
                reschedule_number=global_reschedule_num,
                original_date=subsequent_current_location,  # ✅ USE CURRENT LOCATION
                new_date=subsequent_new_date,
                days_shifted=abs(days_to_shift),
                reason=f"Auto-reschedule due to Day {task.day_number}",
                rescheduled_by=get_current_user().id
            )
            db.session.add(subsequent_history)
        
        # Update stage dates based on actual task dates
        all_tasks_in_stage = StageDailyTask.query.filter_by(stage_id=stage_id).order_by(
            StageDailyTask.day_number
        ).all()
        
        if all_tasks_in_stage:
            stage.start_date = min(t.scheduled_date for t in all_tasks_in_stage)
            stage.end_date = max(t.scheduled_date for t in all_tasks_in_stage)
            print(f"   ✅ Updated stage dates: {stage.start_date} to {stage.end_date}")        
        # ✅ COMMIT
        db.session.commit()
        
        # 🔥 AUTO-REGENERATE EXCEL IN BACKEND
        try:
            generate_excel_file(project_id, save_to_backend=True)
            print(f"✅ Excel regenerated in backend for project {project_id}")
        except Exception as excel_error:
            print(f"⚠️ Excel regeneration failed: {excel_error}")
        
        # ✅ VERIFY
        verification = DailyTaskRescheduleHistory.query.filter_by(
            project_id=project_id,
            task_id=task_id,
            reschedule_number=global_reschedule_num
        ).first()
        
        if verification:
            print(f"   ✅ VERIFIED: Daily task history record exists")
        else:
            print(f"   ⚠️ WARNING: History record not found!")
        
        log_activity(f"Rescheduled day {task.day_number} of stage '{stage.name}' (Global Reschedule #{global_reschedule_num})")
        
        return jsonify({
            'success': True,
            'new_date': new_date.isoformat(),
            'reschedule_count': task.reschedule_count,
            'global_reschedule_number': global_reschedule_num
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/projects/<int:project_id>/stages/<int:stage_id>/daily-tasks/<int:task_id>/hold', methods=['POST'])
@login_required
def hold_daily_task(project_id, stage_id, task_id):
    """Mark a daily task as HOLD without affecting subsequent days"""
    data = request.get_json()
    reason = data.get('reason', 'Put on hold')
    working_saturdays = set(data.get('working_saturdays', []))
    
    try:
        task = StageDailyTask.query.get_or_404(task_id)
        stage = ProjectStage.query.get_or_404(stage_id)
        project = Project.query.get_or_404(project_id)
        
        # PREVENT HOLDING COMPLETED TASKS
        if task.status == 'completed':
            return jsonify({'error': 'Cannot hold a completed task'}), 400
        
        # Store original date if not already stored
        if not task.original_date:
            task.original_date = task.scheduled_date
        
        original_date = task.scheduled_date
        
        # Mark task as HOLD
        task.status = 'hold'
        task.rescheduled_reason = reason
        
        # Create HoldDate record
        hold_record = HoldDate(
            project_id=project_id,
            stage_id=stage_id,
            hold_date=original_date,
            reason=reason,
            created_by=get_current_user().id
        )
        db.session.add(hold_record)
        
        print(f"\n🔒 DAILY TASK HOLD:")
        print(f"   Stage: {stage.name}, Day {task.day_number}")
        print(f"   Date: {original_date}")
        print(f"   Reason: {reason}")
        
        # Commit changes
        db.session.commit()
        
        # 🔥 AUTO-REGENERATE EXCEL IN BACKEND
        try:
            generate_excel_file(project_id, save_to_backend=True)
            print(f"✅ Excel regenerated in backend for project {project_id}")
        except Exception as excel_error:
            print(f"⚠️ Excel regeneration failed: {excel_error}")
        
        log_activity(f"Put day {task.day_number} of stage '{stage.name}' on HOLD")
        
        return jsonify({
            'success': True,
            'hold_date': original_date.isoformat(),
            'message': f'Day {task.day_number} marked as HOLD'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500   


@app.route('/api/projects/<int:project_id>/generate-daily-tasks', methods=['POST'])
@login_required
def generate_daily_tasks(project_id):
    """Generate daily tasks for all stages in a project"""
    try:
        project = Project.query.get_or_404(project_id)
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        working_saturdays = set(json.loads(project.working_saturdays) if project.working_saturdays else [])
        
        for stage in stages:
            # Delete existing daily tasks for this stage
            StageDailyTask.query.filter_by(stage_id=stage.id).delete()
            
            if not stage.start_date or not stage.end_date:
                continue
            
            # Generate daily tasks
            current_date = stage.start_date
            day_number = 1
            
            while current_date <= stage.end_date:
                # Only create task for working days
                if is_working_day(current_date, False, working_saturdays):
                    daily_task = StageDailyTask(
                        stage_id=stage.id,
                        project_id=project_id,
                        day_number=day_number,
                        scheduled_date=current_date,
                        status='pending'
                    )
                    db.session.add(daily_task)
                    day_number += 1
                
                current_date = current_date + timedelta(days=1)
        
        db.session.commit()
        log_activity(f"Generated daily tasks for project '{project.name}'")
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@app.route('/api/projects/<int:project_id>/daily-tasks', methods=['GET'])
@login_required
def get_all_project_daily_tasks(project_id):
    """Get all daily tasks for a project (across all stages)"""
    try:
        daily_tasks = StageDailyTask.query.filter_by(
            project_id=project_id
        ).order_by(
            StageDailyTask.stage_id,
            StageDailyTask.day_number
        ).all()
        
        return jsonify([{
            'id': task.id,
            'stage_id': task.stage_id,
            'day_number': task.day_number,
            'scheduled_date': task.scheduled_date.isoformat() if task.scheduled_date else None,
            'original_date': task.original_date.isoformat() if task.original_date else None,
            'status': task.status,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'reschedule_count': task.reschedule_count or 0
        } for task in daily_tasks]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/reschedule-history', methods=['GET'])
@login_required
def get_reschedule_history(project_id):
    """Get reschedule history for a project"""
    history = ScheduleHistory.query.filter_by(project_id=project_id).order_by(
        ScheduleHistory.rescheduled_at.desc()
    ).all()
    
    return jsonify([{
        'stage_id': h.stage_id,
        'stage_name': ProjectStage.query.get(h.stage_id).name if h.stage_id else 'Unknown',
        'original_date': h.original_date.isoformat() if h.original_date else None,
        'new_date': h.new_date.isoformat() if h.new_date else None,
        'days_shifted': (h.new_date - h.original_date).days if h.new_date and h.original_date else 0,
        'direction': 'forward' if (h.new_date and h.original_date and h.new_date > h.original_date) else 'backward',
        'reason': h.reason,
        'rescheduled_by': User.query.get(h.rescheduled_by).username if h.rescheduled_by else 'Unknown',
        'rescheduled_at': h.rescheduled_at.strftime('%Y-%m-%d %H:%M')
    } for h in history])

@app.route('/api/projects/<int:project_id>/complete-reschedule-history', methods=['GET'])
@login_required
def get_complete_reschedule_history(project_id):
    """Get ALL reschedule history - both stage-level and daily task reschedules"""
    
    # Force a database commit to ensure all records are visible
    db.session.commit()
    
    # Stage-level reschedules
    stage_history = ScheduleHistory.query.filter_by(
        project_id=project_id
    ).order_by(ScheduleHistory.rescheduled_at.desc()).all()
    
    # Daily task reschedules
    task_history = DailyTaskRescheduleHistory.query.filter_by(
        project_id=project_id
    ).order_by(DailyTaskRescheduleHistory.rescheduled_at.desc()).all()
    
    print(f"\n=== Complete Reschedule History for Project {project_id} ===")
    print(f"Stage-level reschedules: {len(stage_history)}")
    print(f"Daily task reschedules: {len(task_history)}")
    
    combined = []
    
    # Add stage reschedules
    for h in stage_history:
        stage = ProjectStage.query.get(h.stage_id) if h.stage_id else None
        record = {
            'type': 'stage',
            'stage_id': h.stage_id,
            'stage_name': stage.name if stage else 'Unknown',
            'day_number': None,
            'original_date': h.original_date.isoformat() if h.original_date else None,
            'new_date': h.new_date.isoformat() if h.new_date else None,
            'days_shifted': abs((h.new_date - h.original_date).days) if h.new_date and h.original_date else 0,
            'direction': 'forward' if (h.new_date and h.original_date and h.new_date > h.original_date) else 'backward',
            'reason': h.reason or 'No reason provided',
            'rescheduled_by': User.query.get(h.rescheduled_by).username if h.rescheduled_by else 'Unknown',
            'rescheduled_at': h.rescheduled_at.strftime('%Y-%m-%d %H:%M') if h.rescheduled_at else None
        }
        combined.append(record)
        print(f"  ✔️ Stage: {record['stage_name']}, {record['original_date']} → {record['new_date']}")
    
    # Add daily task reschedules
    for h in task_history:
        stage = ProjectStage.query.get(h.stage_id) if h.stage_id else None
        record = {
            'type': 'daily_task',
            'stage_id': h.stage_id,
            'stage_name': stage.name if stage else 'Unknown',
            'day_number': h.day_number,
            'reschedule_number': h.reschedule_number if hasattr(h, 'reschedule_number') else 1,
            'original_date': h.original_date.isoformat() if h.original_date else None,
            'new_date': h.new_date.isoformat() if h.new_date else None,
            'days_shifted': abs(h.days_shifted),
            'direction': 'forward' if h.days_shifted > 0 else 'backward',
            'reason': h.reason or 'No reason provided',
            'rescheduled_by': User.query.get(h.rescheduled_by).username if h.rescheduled_by else 'Unknown',
            'rescheduled_at': h.rescheduled_at.strftime('%Y-%m-%d %H:%M') if h.rescheduled_at else None
        }
        combined.append(record)
        print(f"  ✔️ Daily Task: {record['stage_name']} Day {record['day_number']}, Reschedule #{record['reschedule_number']}, {record['original_date']} → {record['new_date']}")
    
    # Sort by reschedule time (most recent first)
    combined.sort(key=lambda x: x['rescheduled_at'] if x['rescheduled_at'] else '', reverse=True)
    
    print(f"Total records returned: {len(combined)}")
    print("=" * 60 + "\n")
    
    return jsonify(combined)

@app.route('/api/projects/<int:project_id>/export-excel', methods=['GET'])
@login_required
def export_project_to_excel(project_id):
    """
    Generate Excel with stage-specific reschedule rows, clean weekly timeline, and correct Hold coloring.
    
    This uses the generate_excel_file() helper which saves to backend automatically.
    """
    try:
        excel_file = generate_excel_file(project_id, save_to_backend=True)
        
        if not excel_file:
            return jsonify({'error': 'Failed to generate Excel file'}), 500
        
        project = Project.query.get_or_404(project_id)
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{project.name}_Tracker.xlsx"
        )
        
    except Exception as e:
        print(f"Export Error: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/hold-dates', methods=['GET'])
@login_required
def get_hold_dates(project_id):
    """Get all HOLD dates for a project"""
    hold_dates = HoldDate.query.filter_by(project_id=project_id).order_by(
        HoldDate.hold_date
    ).all()
    
    return jsonify([{
        'id': h.id,
        'stage_id': h.stage_id,
        'stage_name': ProjectStage.query.get(h.stage_id).name if h.stage_id else 'Unknown',
        'hold_date': h.hold_date.isoformat(),
        'reason': h.reason,
        'created_by': User.query.get(h.created_by).username if h.created_by else 'Unknown',
        'created_at': h.created_at.strftime('%Y-%m-%d %H:%M')
    } for h in hold_dates]) 


@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    try:
        # ✅ GET THE EXISTING PROJECT FROM DATABASE
        project = Project.query.get_or_404(project_id)
        data = request.get_json()
        
        # ✅ COMPLETELY REPLACE THE OLD DATA WITH NEW DATA
        # This is the correct approach - overwrite the original
        project.name = data.get('name', project.name)
        project.description = data.get('description', project.description)
        
        # Update working Saturdays - REPLACES old data
        working_saturdays = set(data.get('working_saturdays', []))
        project.working_saturdays = json.dumps(list(working_saturdays))
        
        # Update start date - REPLACES old data
        if data.get('start_date'):
            new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            project.start_date = new_start_date
        
        # Handle stage updates - REPLACES old stages
        calculated_stages = []  # ✅ Initialize outside if block
        if 'stages' in data:
            stages_data = data['stages']
            
            # Calculate new dates
            calculated_stages = calculate_stage_dates(
                project.start_date, 
                stages_data, 
                data.get('include_saturday', False),
                working_saturdays
            )
            
            
            # ✅ CRITICAL FIX: Delete stages that were unchecked (not in the update)
            # Get IDs of stages that are being kept/updated
            kept_stage_ids = set()
            for stage_data in calculated_stages:
                if 'id' in stage_data and stage_data['id']:
                    kept_stage_ids.add(stage_data['id'])
            
            # Delete stages that aren't in the update (i.e., were unchecked)
            existing_stages = ProjectStage.query.filter_by(project_id=project.id).all()
            for existing_stage in existing_stages:
                if existing_stage.id not in kept_stage_ids:
                    # This stage was unchecked - delete it and its related data
                    print(f"🗑️ Deleting unchecked stage: {existing_stage.name} (ID: {existing_stage.id})")
                    
                    # Delete related daily tasks
                    StageDailyTask.query.filter_by(stage_id=existing_stage.id).delete()
                    
                    # Delete related schedule history
                    ScheduleHistory.query.filter_by(stage_id=existing_stage.id).delete()
                    
                    # Delete related reschedule history
                    DailyTaskRescheduleHistory.query.filter_by(stage_id=existing_stage.id).delete()
                    
                    # Delete related hold dates
                    HoldDate.query.filter_by(stage_id=existing_stage.id).delete()
                    
                    # Delete the stage itself
                    db.session.delete(existing_stage)
            # Update or create stages - THIS REPLACES THE OLD STAGE DATA
            for stage_data in calculated_stages:
                if 'id' in stage_data and stage_data['id']:
                    # ✅ UPDATE EXISTING STAGE - REPLACES ALL FIELDS
                    stage = ProjectStage.query.get(stage_data['id'])
                    if stage:
                        stage.name = stage_data['name']  # NEW name replaces old
                        stage.order = stage_data['order']  # NEW order replaces old
                        stage.duration_days = stage_data['duration_days']  # NEW duration replaces old
                        stage.start_date = stage_data['start_date']  # NEW start_date replaces old
                        stage.end_date = stage_data['end_date']  # NEW end_date replaces old
                        stage.manager_id = stage_data.get('manager_id')  # NEW manager replaces old
                        stage.parallel_group_id = stage_data.get('parallel_group_id')  # NEW parallel group
                else:
                    # ✅ CREATE NEW STAGE
                    stage = ProjectStage(
                        project_id=project.id,
                        name=stage_data['name'],
                        order=stage_data['order'],
                        duration_days=stage_data['duration_days'],
                        start_date=stage_data['start_date'],
                        end_date=stage_data['end_date'],
                        manager_id=stage_data.get('manager_id'),
                        parallel_group_id=stage_data.get('parallel_group_id')
                    )
                    db.session.add(stage)
        
        # ✅ UPDATE PROJECT END DATE based on last stage
        if calculated_stages:
            project.end_date = calculated_stages[-1]['end_date']
        
        # ✅ DELETE old daily tasks and regenerate them with new dates
        deleted_count = StageDailyTask.query.filter_by(project_id=project.id).delete()
        db.session.flush()  # Ensure delete completes before regeneration
        print(f"🗑️ Deleted {deleted_count} old daily tasks for project {project.id}")
        
        generate_daily_tasks_for_project(project.id, working_saturdays)
        print(f"✨ Generated new daily tasks for project {project.id}")
        
        # ✅ SAVE ALL CHANGES TO DATABASE
        # This commits all the replaced/updated data
        db.session.commit()
        
        # ✅ AUTOMATICALLY SHIFT TASKS TO FILL GAPS AFTER UPDATE
        print(f"[AUTO-SHIFT] Triggering gap fill for project {project_id}...")
        shift_result = auto_shift_tasks_to_fill_gaps(project_id)
        print(f"[AUTO-SHIFT] Result: {shift_result}")
        
        # Regenerate Excel
        try:
            generate_excel_file(project_id, save_to_backend=True)
        except Exception as e:
            print(f"Warning: Excel generation failed: {e}")
        
        # The edited data is now the NEW ORIGINAL data
        return jsonify({
            'success': True,
            'id': project.id,
            'auto_shift_result': shift_result  # Include shift info in response
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/projects/<int:project_id>/excel-preview-html', methods=['GET'])
@login_required
def get_excel_preview_html(project_id):
    """Generate HTML preview that exactly matches the Excel export"""
    try:
        project = Project.query.get_or_404(project_id)
        stages = ProjectStage.query.filter_by(project_id=project_id).order_by(ProjectStage.order).all()
        
        # Parse Working Saturdays
        try:
            working_saturdays = set(json.loads(project.working_saturdays) if project.working_saturdays else [])
        except:
            working_saturdays = set()

        # Generate all dates (same as Excel)
        project_start = project.start_date
        project_end = project.end_date
        all_dates = []
        current_date = project_start
        while current_date <= project_end:
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        if not all_dates:
            return jsonify({'error': 'No dates in project range'}), 400

        # Get stage abbreviations
        stage_abbrs = {}
        for stage in stages:
            parts = stage.name.split('-')
            abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            stage_abbrs[stage.id] = abbr

        # Build PLANNED row data (exact same logic as Excel)
        planned_map = {}
        for stage in stages:
            if stage.start_date and stage.end_date:
                parts = stage.name.split('-')
                abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
                d = stage.start_date
                while d <= stage.end_date:
                    ds = d.strftime('%Y-%m-%d')
                    if ds not in planned_map:
                        planned_map[ds] = []
                    if is_working_day(d, False, working_saturdays):
                        planned_map[ds].append(abbr)
                    d += timedelta(days=1)

        # Build RESCHEDULE row data (exact same logic as Excel)
        stage_reschedule_map = {1: {}, 2: {}, 3: {}, 4: {}}
        
        for stage in stages:
            parts = stage.name.split('-')
            stage_abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            
            task_reschedules = DailyTaskRescheduleHistory.query.filter_by(
                project_id=project_id, 
                stage_id=stage.id
            ).all()
            
            unique_nums = sorted(list(set(r.reschedule_number for r in task_reschedules if r.reschedule_number)))
            
            for idx, r_num in enumerate(unique_nums):
                target_row = idx + 1
                if target_row > 4: 
                    continue
                
                event_tasks = [t for t in task_reschedules if t.reschedule_number == r_num]
                for t in event_tasks:
                    date_str = t.new_date.strftime('%Y-%m-%d')
                    if date_str not in stage_reschedule_map[target_row]:
                        stage_reschedule_map[target_row][date_str] = []
                    if stage_abbr not in stage_reschedule_map[target_row][date_str]:
                        stage_reschedule_map[target_row][date_str].append(stage_abbr)

        # Build ACTUAL row data (exact same logic as Excel)
        actual_map = {}
        hold_dates_map = {}
        
        for stage in stages:
            parts = stage.name.split('-')
            abbr = parts[-1].strip() if len(parts) > 1 else stage.name[:6]
            
            tasks = StageDailyTask.query.filter_by(stage_id=stage.id).all()
            task_map = {t.scheduled_date.strftime('%Y-%m-%d'): t for t in tasks}
            
            if stage.start_date and stage.end_date:
                d = stage.start_date
                while d <= stage.end_date:
                    if is_working_day(d, False, working_saturdays):
                        ds = d.strftime('%Y-%m-%d')
                        
                        if ds in task_map:
                            task = task_map[ds]
                            
                            if task.status == 'hold':
                                if ds not in hold_dates_map:
                                    hold_dates_map[ds] = []
                                if abbr not in hold_dates_map[ds]:
                                    hold_dates_map[ds].append(abbr)
                            elif task.status in ['pending', 'completed']:
                                if ds not in actual_map:
                                    actual_map[ds] = []
                                actual_map[ds].append((abbr, task.status))
                        else:
                            if ds not in actual_map:
                                actual_map[ds] = []
                            actual_map[ds].append((abbr, 'pending'))
                    
                    d += timedelta(days=1)

        # Organize into weeks for display
        weeks = []
        current_week = []
        
        for date in all_dates:
            if date.weekday() == 0 and current_week:  # Monday
                weeks.append(current_week)
                current_week = [date]
            else:
                current_week.append(date)
        
        if current_week:
            weeks.append(current_week)

        # Convert data to week-based format for frontend
        planned_by_week = {}
        actual_by_week = {}
        reschedule_by_week = {1: {}, 2: {}, 3: {}, 4: {}}
        
        for w_idx, week in enumerate(weeks):
            week_planned = set()
            week_actual = set()
            week_reschedules = {1: set(), 2: set(), 3: set(), 4: set()}
            
            for date in week:
                ds = date.strftime('%Y-%m-%d')
                
                # Planned
                if ds in planned_map:
                    week_planned.update(planned_map[ds])
                
                # Actual
                if ds in actual_map:
                    week_actual.update([x[0] for x in actual_map[ds]])
                
                # Reschedules
                for r_num in range(1, 5):
                    if ds in stage_reschedule_map[r_num]:
                        week_reschedules[r_num].update(stage_reschedule_map[r_num][ds])
            
            if week_planned:
                planned_by_week[w_idx] = ' , '.join(sorted(week_planned))
            if week_actual:
                actual_by_week[w_idx] = ' , '.join(sorted(week_actual))
            for r_num in range(1, 5):
                if week_reschedules[r_num]:
                    reschedule_by_week[r_num][w_idx] = ' , '.join(sorted(week_reschedules[r_num]))

        return jsonify({
            'success': True,
            'project_name': project.name,
            'stages': [{'name': s.name} for s in stages],
            'weeks': [[d.strftime('%Y-%m-%d') for d in week] for week in weeks],
            'planned_data': {str(k): v for k, v in planned_by_week.items()},
            'reschedule_data': {
                str(r_num): {str(k): v for k, v in r_data.items()}
                for r_num, r_data in reschedule_by_week.items()
            },
            'actual_data': {str(k): v for k, v in actual_by_week.items()}
        })
        
    except Exception as e:
        print(f"Error generating preview: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/project/<int:project_id>/auto-shift-tasks', methods=['POST'])
@login_required
def auto_shift_project_tasks(project_id):
    """API endpoint to trigger automatic task shifting"""
    try:
        result = auto_shift_tasks_to_fill_gaps(project_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

# ============================================================================
# Initialize Database & Create Default User
# ============================================================================

def init_db():
    with app.app_context():
        db.create_all()
        
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)


            # ==========================================
            # ADD GLOBAL RESCHEDULE COUNTER TO PROJECT
            # ==========================================
            project_columns = [col['name'] for col in inspector.get_columns('project')]
            if 'current_reschedule_number' not in project_columns:
                print("[INFO] Adding current_reschedule_number to project table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE project ADD COLUMN current_reschedule_number INTEGER DEFAULT 0"))
                    conn.commit()
                print("[SUCCESS] Added current_reschedule_number column")

            
            # ==========================================
            # 1. SCHEDULE_HISTORY TABLE (Stage-level reschedules)
            # ==========================================
            schedule_history_columns = [col['name'] for col in inspector.get_columns('schedule_history')]
            if 'reschedule_number' not in schedule_history_columns:
                print("[WARNING] Adding reschedule_number column to schedule_history...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE schedule_history ADD COLUMN reschedule_number INTEGER DEFAULT 1"))
                    conn.commit()
                print("[SUCCESS] Added reschedule_number column to schedule_history")
            
            # CRITICAL: Backfill existing records with sequential numbers
            existing_records = ScheduleHistory.query.all()
            if existing_records:
                print(f"[INFO] Checking {len(existing_records)} existing reschedule records...")
                
                # Group by project_id and stage_id
                from collections import defaultdict
                grouped = defaultdict(list)
                
                for record in existing_records:
                    key = (record.project_id, record.stage_id)
                    grouped[key].append(record)
                
                # Number them sequentially per stage
                for (proj_id, stage_id), records in grouped.items():
                    records.sort(key=lambda r: r.rescheduled_at)
                    for idx, record in enumerate(records, 1):
                        if not record.reschedule_number or record.reschedule_number == 0:
                            record.reschedule_number = idx
                            print(f"  [UPDATE] Record ID {record.id} set to reschedule #{idx}")
                
                db.session.commit()
                print("[SUCCESS] Backfilled reschedule numbers for stage-level reschedules")
            
            # ==========================================
            # 2. STAGE_DAILY_TASK TABLE (Add reschedule_count)
            # ==========================================
            if inspector.has_table('stage_daily_task'):
                task_columns = [col['name'] for col in inspector.get_columns('stage_daily_task')]
                if 'reschedule_count' not in task_columns:
                    print("[WARNING] Adding reschedule_count column to stage_daily_task...")
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE stage_daily_task ADD COLUMN reschedule_count INTEGER DEFAULT 0"))
                        conn.commit()
                    print("[SUCCESS] Added reschedule_count column to stage_daily_task")
            else:
                db.create_all()
                print("✅ Created stage_daily_task table")
            
            # ==========================================
            # 3. DAILY_TASK_RESCHEDULE_HISTORY TABLE (Add reschedule_number)
            # ==========================================
            if inspector.has_table('daily_task_reschedule_history'):
                history_columns = [col['name'] for col in inspector.get_columns('daily_task_reschedule_history')]
                if 'reschedule_number' not in history_columns:
                    print("[WARNING] Adding reschedule_number column to daily_task_reschedule_history...")
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE daily_task_reschedule_history ADD COLUMN reschedule_number INTEGER DEFAULT 1"))
                        conn.commit()
                    print("[SUCCESS] Added reschedule_number column to daily_task_reschedule_history")
                
                # Backfill existing daily task reschedule records
                existing_task_history = DailyTaskRescheduleHistory.query.all()
                if existing_task_history:
                    print(f"[INFO] Backfilling {len(existing_task_history)} daily task reschedule records...")
                    
                    from collections import defaultdict
                    task_grouped = defaultdict(list)
                    
                    for record in existing_task_history:
                        key = (record.project_id, record.task_id)
                        task_grouped[key].append(record)
                    
                    for (proj_id, task_id), records in task_grouped.items():
                        records.sort(key=lambda r: r.rescheduled_at)
                        for idx, record in enumerate(records, 1):
                            if not hasattr(record, 'reschedule_number') or not record.reschedule_number or record.reschedule_number == 0:
                                record.reschedule_number = idx
                                print(f"  [UPDATE] Task history ID {record.id} set to reschedule #{idx}")
                    
                    db.session.commit()
                    print("[SUCCESS] Backfilled reschedule numbers for daily task reschedules")
            else:
                print("⚠️  daily_task_reschedule_history table missing, creating...")
                db.create_all()
                print("✅ Created daily_task_reschedule_history table")
            
            # ==========================================
            # 4. PROJECT TABLE (working_saturdays)
            # ==========================================
            columns = [col['name'] for col in inspector.get_columns('project')]
            if 'working_saturdays' not in columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE project ADD COLUMN working_saturdays TEXT DEFAULT '[]'"))
                    conn.commit()
                print("✅ Added working_saturdays column to project")
            
            # ==========================================
            # 5. PROJECT_STAGE TABLE (manager_id)
            # ==========================================
            stage_columns = [col['name'] for col in inspector.get_columns('project_stage')]
            if 'manager_id' not in stage_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE project_stage ADD COLUMN manager_id INTEGER"))
                    conn.commit()
                print("✅ Added manager_id column to project_stage")
            
            # ==========================================
            # 5.5 PROJECT_STAGE TABLE (parallel_group_id)
            # ==========================================
            stage_columns = [col['name'] for col in inspector.get_columns('project_stage')]
            if 'parallel_group_id' not in stage_columns:
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE project_stage ADD COLUMN parallel_group_id VARCHAR(50)"))
                    conn.commit()
                print("✅ Added parallel_group_id column to project_stage")
            
            # ==========================================
            # 6. HOLD_DATE TABLE
            # ==========================================
            if not inspector.has_table('hold_date'):
                print("⚠️  hold_date table missing, creating...")
                db.create_all()
                print("✅ Created hold_date table")
            
            print("\n" + "="*60)
            print("✅ DATABASE INITIALIZATION COMPLETE")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ Error during database initialization: {e}")
            import traceback
            traceback.print_exc()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created (username: admin, password: admin123)")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)





    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Management Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.css' rel='stylesheet' />
    <!-- Add this in the <head> section of index.html -->
    <style>
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
}

body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.stat-card {
    background: white;
    border-radius: 15px;
    padding: 25px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.3s;
    height: 100%;
}

.stat-card:hover { 
    transform: translateY(-5px);
}

.stat-card .icon {
    width: 60px;
    height: 60px;
    border-radius: 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    margin-bottom: 15px;
}

.stat-card h3 { 
    font-size: 2rem; font-weight: 700; margin: 10px 0; 
}

.card-custom {
    background: white;
    border-radius: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}

.card-custom .card-header {
    background: transparent;
    border-bottom: 2px solid #f1f3f5;
    padding: 20px;
    font-weight: 600;
    font-size: 1.2rem;
}

.btn-primary-custom {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    color: white;
    font-weight: 600;
}

.btn-primary-custom:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(95, 116, 206, 0.4);
    color: white;
}

/* Delete Button Styling - Modern & Attractive */
.btn-delete-project {
    background: white;
    border: 2px solid #dc3545;
    color: #dc3545;
    border-radius: 8px;
    font-weight: 600;
    padding: 8px 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.btn-delete-project:hover {
    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
    color: white;
    border-color: #dc3545;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
}

.btn-delete-project:active {
    transform: translateY(0);
    box-shadow: 0 2px 6px rgba(220, 53, 69, 0.2);
}

.top-bar-custom {
    background: white;
    padding: 15px 30px;
    border-radius: 15px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

.notification-badge {
    position: absolute;
    top: -5px;
    right: -5px;
    background: #dc3545;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
}

.modal-header {
    background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
    color: white;
    border-bottom: none;
}

.modal-content {
    border-radius: 8px;
    border: 1px solid #dee2e6;
}

.modal-body {
    padding: 25px 30px;
    background: white;
}

/* Main container with top padding to accommodate parallel badge */
.progress-steps {
    position: relative;
    display: flex;
    flex-direction: row;
    margin: 30px 0;
    align-items: flex-start;
    overflow-x: auto;
    padding-bottom: 10px;
    padding-top: 40px; /* Push all content down to make room for parallel badge */
}

/* Progress line positioned at exact circle center - ENHANCED */
.progress-line {
    position: absolute;
    top: 65px; /* Align with circle centers after adjustment */
    left: 20px;
    right: 20px;
    height: 3px;
    background: linear-gradient(to right, #e9ecef 0%, #dee2e6 100%);
    z-index: 1;
    min-width: calc(100% - 40px);
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.progress-line-fill {
    position: absolute;
    height: 100%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    position: relative;
}

/* Add animated shimmer effect */
.progress-line-fill::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(255, 255, 255, 0.3) 50%, 
        transparent 100%);
    animation: shimmer 2s infinite;
    border-radius: 10px;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}
/* All progress steps have consistent structure */
.progress-step {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.3s;
}

.progress-step.normal-spacing {
    flex: 1;
    padding: 0 15px;
}

.progress-step.tight-spacing {
    flex: 0 0 140px;
    margin: 0 5px;
}

.progress-step.medium-spacing {
    flex: 0 0 140px;
    margin: 0 5px;
}

/* Parallel container using grid for perfect alignment */
.stage-group-container {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: 180px;
    gap: 30px;
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.12) 0%, rgba(118, 75, 162, 0.12) 100%);
    border: 2px solid #667eea;
    border-radius: 15px;
    padding: 30px 30px 40px 30px;  /* Changed top padding from 10px to 30px */
    margin: -10px 10px 0 10px;
    position: relative;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15);
    align-items: start;
}
/* Parallel badge above container */
.stage-group-container::before {
    content: '⚡ Parallel';
    position: absolute;
    top: -25px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 4px 16px;
    font-size: 0.7rem;
    font-weight: 700;
    border-radius: 20px;
    box-shadow: 0 2px 6px rgba(102, 126, 234, 0.4);
    z-index: 10;
    white-space: nowrap;
    margin-top: 0;
    padding-top: 0px;

}

/* Enhanced circle styling with status colors */
.step-circle {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: white;
    border: 4px solid #dee2e6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1rem;
    color: #495057;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    z-index: 3;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    flex-shrink: 0;
    margin: 0; /* ✅ Ensure no margins by default */
}

/* Status-based circle colors */
.step-circle.not-started {
    background: white;
    border-color: #dee2e6;
    color: #6c757d;
}

.step-circle.in-progress {
    background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
    border-color: #FFD700;
    color: white;
    animation: pulse 2s infinite;
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
}

.step-circle.completed {
    background: linear-gradient(135deg, #006400 0%, #228B22 100%);
    border-color: #006400;
    color: white;
    box-shadow: 0 4px 12px rgba(0, 100, 0, 0.3);
}

.step-circle.completed-rescheduled {
    background: linear-gradient(135deg, #90EE90 0%, #98FB98 100%);
    border-color: #90EE90;
    color: #006400;
    box-shadow: 0 4px 12px rgba(144, 238, 144, 0.3);
}

.step-circle.overdue {
    background: linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%);
    border-color: #FF6B6B;
    color: white;
    animation: shake 0.5s infinite;
    box-shadow: 0 0 20px rgba(255, 107, 107, 0.5);
}

/* Legacy active class for backward compatibility */
.step-circle.active {
    background: #17a2b8;
    border-color: #17a2b8;
    color: white;
    box-shadow: 0 0 0 4px rgba(23,162,184,0.2);
}

/* Hover effect for circles - shows they're interactive */
.step-circle[style*="cursor: pointer"]:hover {
    transform: scale(1.1);
    transition: transform 0.2s ease;
    filter: brightness(1.1);
}

/* Pulse animation for in-progress */
@keyframes pulse {
    0%, 100% {
        transform: scale(1);
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
    }
    50% {
        transform: scale(1.05);
        box-shadow: 0 0 30px rgba(255, 215, 0, 0.8);
    }
}

/* Shake animation for overdue */
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-2px); }
    75% { transform: translateX(2px); }
}

/* Status badge on circle */
.step-circle::after {
    content: '';
    position: absolute;
    top: -5px;
    right: -5px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2px solid white;
    display: none;
}

.step-circle.completed::after,
.step-circle.completed-rescheduled::after {
    content: '✓';
    display: flex;
    align-items: center;
    justify-content: center;
    background: #28a745;
    color: white;
    font-size: 10px;
    font-weight: bold;
}

.step-circle.completed-rescheduled::after {
    content: '↻';
    background: #90EE90;
    color: #006400;
}


/* Label styling with consistent spacing */
.step-label {
    margin-top: 10px;
    padding: 8px 12px;
    background: white;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
    max-width: 140px;
    min-width: 100px;
    word-wrap: break-word;
    line-height: 1.3;
    display: flex;
    flex-direction: column; /* Stack name and badge vertically */
    gap: 4px;
}

.step-label.completed {
    background: linear-gradient(135deg, #e8eef9 0%, #f0e8f5 100%);
    color: #667eea;
}

.step-label.active {
    background: #17a2b8;
    color: white;
}

.duration-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2px 6px;
    border-radius: 8px;
    font-size: 0.6rem;
    font-weight: 600;
    align-self: center; /* Center the badge */
    margin: 0; /* Remove margin */
}

/* Date text styling */
.progress-step small {
    display: block;
    margin-top: 8px;
    font-size: 0.65rem;
    line-height: 1.4;
    text-align: center;
    white-space: normal;
    max-width: 120px;
    color: #6c757d;
    background: rgba(255, 255, 255, 0.9);
    padding: 3px 6px;
    border-radius: 4px;
}

/* Parallel stage specific styling */
.stage-group-container .progress-step {
    display: grid !important; /* ✅ Ensure grid overrides any flex */
    grid-template-rows: 58px auto auto !important; /* ✅ Fixed height for circle row (50px circle + 8px buffer) */
    justify-items: center;
    align-items: start !important; /* ✅ Force top alignment */
    align-content: start !important; /* ✅ NEW: Force grid content to start at top */
    gap: 10px;
}

/* ✅ Control ALL direct children positioning */
.stage-group-container .progress-step > * {
    margin: 0 !important; /* Remove all margins from children */
}

.stage-group-container .step-circle {
    grid-row: 1 !important; /* Force circle to first row */
    margin: 0 !important; /* ✅ Remove ALL margins */
    margin-top: -10px !important; /* ✅ Compensate for container's 10px top padding */
    padding: 0 !important; /* ✅ Remove padding that might affect position */
    align-self: start !important; /* ✅ Ensure circles align at the top */
    justify-self: center !important; /* ✅ Center horizontally */
}

.stage-group-container .step-label {
    grid-row: 2 !important; /* Force label to second row */
    margin: 0 !important; /* ✅ Remove ALL margins including inherited margin-top */
    margin-top: 0 !important; /* ✅ Explicitly override label's default margin-top */
}

/* ✅ Control the dates wrapper div */
.stage-group-container .step-label + div,
.stage-group-container > div > div:nth-child(3) {
    grid-row: 3 !important; /* Force dates wrapper to third row */
    margin-top: 0 !important; /* Override inline style margin-top: 5px */
}

.stage-group-container small {
    grid-row: 3; /* Force dates to third row */
    font-size: 0.65rem;
    padding: 3px 6px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 4px;
}
    /* ===== CALENDAR MODAL ===== */
    .calendar-modal .modal-dialog {
        max-width: 1200px;
        width: 95%;
        margin: 1.75rem auto;
    }

    .calendar-modal .modal-content {
        border-radius: 15px;
    }

    #calendar {
        width: 100%;
        min-height: 450px;
    }

    .fc {
        font-family: inherit !important;
        font-size: 0.75rem;
        background: white;
        border-radius: 10px;
        padding: 10px;
    }

    .fc-toolbar-title {
        font-size: 1rem !important;
        font-weight: 700 !important;
    }

    .fc-button {
        padding: 5px 10px !important;
        font-size: 0.75rem !important;
        border-radius: 6px !important;
    }

    .fc-event {
        padding: 2px 4px;
        margin: 1px;
        font-size: 0.7rem;
        border-radius: 4px;
    }

    /* ===== LEGEND ===== */
    .calendar-legend {
        background: transparent;
        padding: 0;
    }

    .legend-item {
        padding: 6px 8px;
        margin-bottom: 4px;
        background: #f8f9fa;
        border-radius: 6px;
        font-size: 0.7rem;
        border-left: 3px solid;
        transition: all 0.2s;
    }

    .legend-item:hover {
        background: #e9ecef;
        transform: translateX(2px);
    }

/* ================================================
   CLEAN PROFESSIONAL CALENDAR DESIGN
   Optimized for Clarity and Readability
   
   ✅ IMPROVEMENTS APPLIED (v2.1 - Final Optimization):
   - Day cell height: 110px (optimal for 7-8 stages)
   - Event height: 24px for clearer text
   - Font size: 0.74rem with better line-height
   - Hover tooltip: Full stage names visible on hover
   - Better spacing: Optimized margins between stages
   - Duration badges: Larger and better positioned
   - Event limit: Shows up to 8 events before "+more" link
   - Text overflow: Smart ellipsis with full text on hover
   - Enhanced shadows and borders for better depth
   - Improved mobile responsiveness (80px cells)
   ================================================ */

/* ===== CALENDAR CONTAINER ===== */
#calendar {
    background: white;
    border-radius: 12px;
    padding: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    max-width: 100%;
}

/* ===== CALENDAR HEADER ===== */
.fc-header-toolbar {
    padding-bottom: 12px !important;
    margin-bottom: 12px !important;
    border-bottom: 2px solid #f0f0f0 !important;
}

.fc-toolbar-title {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    color: #2c3e50 !important;
    letter-spacing: -0.5px !important;
}

/* ===== CALENDAR BUTTONS ===== */
.fc-button {
    padding: 8px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
}

.fc-button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.5) !important;
}

.fc-button:active,
.fc-button:focus {
    background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%) !important;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4) !important;
}

.fc-button-active {
    background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%) !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.2) !important;
}

.fc-prev-button,
.fc-next-button {
    padding: 8px 12px !important;
    font-size: 1.1rem !important;
}

.fc-today-button {
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
}

.fc-today-button:hover {
    background: linear-gradient(135deg, #218838 0%, #1ba881 100%) !important;
}

/* ===== DAY HEADERS ===== */
.fc-col-header-cell {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
    border-color: #dee2e6 !important;
    padding: 8px 4px !important;
}

.fc-col-header-cell-cushion {
    color: #495057 !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ===== CALENDAR GRID ===== */
.fc-daygrid-day {
    border-color: #e9ecef !important;
    transition: background 0.2s ease !important;
}

.fc-daygrid-day:hover {
    background: rgba(102, 126, 234, 0.02) !important;
}

.fc-daygrid-day-number {
    color: #495057 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    padding: 4px !important;
}

.fc-day-today {
    background: rgba(102, 126, 234, 0.05) !important;
}

.fc-day-today .fc-daygrid-day-number {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border-radius: 50% !important;
    width: 26px !important;
    height: 26px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-weight: 700 !important;
}

/* ===== WEEKEND STYLING ===== */
.fc-day-sun {
    background: linear-gradient(135deg, #fff5f5 0%, #ffe9e9 100%) !important;
}

.fc-day-sat {
    background: linear-gradient(135deg, #fffbf0 0%, #fff3d9 100%) !important;
}

/* ===== DAY CELLS - OPTIMIZED VERTICAL SPACE ===== */
.fc-daygrid-day-frame {
    min-height: 180px !important; /* Increased from 110px to accommodate more parallel events */
    padding: 2px !important;
}

/* Force events to render within their start date's cell */
.fc-daygrid-event {
    position: relative !important;
}

/* Prevent FullCalendar from pushing events to wrong week rows */
.fc-daygrid-body {
    position: relative !important;
}

.fc-daygrid-body .fc-row {
    position: relative !important;
    overflow: visible !important;
    min-height: 180px !important;
}

/* Ensure event stacking happens within the correct day cell */
.fc-daygrid-day-events {
    margin-top: 2px !important;
    position: relative !important;
    min-height: 150px !important; /* Room for all parallel events */
}

.fc-daygrid-event-harness {
    margin-bottom: 1px !important;
}

/* ================================================
   EVENT STYLING - CLEAN & COMPACT
   ================================================ */

.fc-event {
    padding: 3px 8px !important;
    margin: 1px 0px !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    border-radius: 5px !important;
    border: none !important;
    border-left: 3px solid rgba(0,0,0,0.3) !important;
    line-height: 1.5 !important;
    min-height: 24px !important;
    max-height: 24px !important;
    overflow: hidden !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
    background: linear-gradient(135deg, var(--event-color) 0%, var(--event-color) 100%) !important;
    position: relative !important;
}

.fc-event:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.15) !important;
    z-index: 100 !important;
    max-height: auto !important;
    min-height: 24px !important;
    overflow: visible !important;
}

/* Better text handling - NO CUTOFF */
.fc-event-main {
    overflow: hidden !important;
    padding-right: 22px !important;
}

.fc-event-title {
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    display: block !important;
    font-weight: 700 !important;
    color: white !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
    font-size: 0.74rem !important;
    padding-right: 2px !important;
}

/* Show full text on hover */
.fc-event:hover .fc-event-title {
    white-space: normal !important;
    overflow: visible !important;
}

.fc-event-title-container {
    overflow: hidden !important;
}

/* ===== TOOLTIP EFFECT FOR FULL TEXT ===== */
.fc-event:hover {
    z-index: 1000 !important;
    white-space: normal !important;
}

.fc-event:hover .fc-event-main {
    overflow: visible !important;
    background: inherit !important;
    padding-right: 22px !important;
}

.fc-event:hover .fc-event-title-container {
    overflow: visible !important;
    background: inherit !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    border-radius: 5px !important;
    padding: 2px !important;
}

/* ===== DURATION BADGE - COMPACT ===== */
.parallel-stage-indicator {
    position: absolute !important;
    top: 3px !important;
    right: 4px !important;
    background: rgba(255, 255, 255, 0.95) !important;
    color: #333 !important;
    border-radius: 10px !important;
    padding: 1px 5px !important;
    font-size: 0.64rem !important;
    font-weight: 700 !important;
    z-index: 10 !important;
    border: 1px solid rgba(0,0,0,0.15) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
    line-height: 1.4 !important;
    letter-spacing: 0.2px !important;
}

.fc-event.event-completed .parallel-stage-indicator {
    right: auto !important;
    left: 3px !important;
}

/* ===== COMPLETION INDICATOR - COMPACT ===== */
.fc-event.event-completed::after {
    content: '✓';
    position: absolute !important;
    top: 2px !important;
    right: 3px !important;
    width: 15px !important;
    height: 15px !important;
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%) !important;
    color: white !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    z-index: 15 !important;
    box-shadow: 0 1px 4px rgba(40, 167, 69, 0.4) !important;
    border: 1.5px solid white !important;
}

.fc-event.event-completed {
    opacity: 0.92 !important;
    border-left-color: #28a745 !important;
}

/* ===== RESCHEDULE INDICATOR - COMPACT ===== */
.fc-event.event-rescheduled::before {
    content: '↻';
    position: absolute;
    top: 2px;
    left: 3px;
    width: 15px;
    height: 15px;
    background: linear-gradient(135deg, #ff9800 0%, #ff6f00 100%);
    border-radius: 50%;
    z-index: 15;
    box-shadow: 0 1px 4px rgba(255, 152, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 10px;
    font-weight: 700;
    border: 1.5px solid white;
    animation: gentle-pulse 2.5s infinite;
}

@keyframes gentle-pulse {
    0%, 100% {
        transform: scale(1);
        box-shadow: 0 1px 4px rgba(255, 152, 0, 0.4);
    }
    50% {
        transform: scale(1.06);
        box-shadow: 0 2px 6px rgba(255, 152, 0, 0.5);
    }
}

.fc-event.event-rescheduled {
    border-left-color: #ff9800 !important;
    padding-left: 24px !important;
}

/* ===== STAGE RESCHEDULED - SUBTLE ===== */
.fc-event.stage-rescheduled {
    border-left-width: 3px !important;
    border-left-color: #17a2b8 !important;
}

.fc-event.stage-rescheduled::after {
    content: '⟲';
    position: absolute;
    bottom: 2px;
    right: 3px;
    font-size: 10px;
    color: rgba(255,255,255,0.9);
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    z-index: 5;
}

.fc-event.event-completed.stage-rescheduled::after {
    content: '✓';
    bottom: auto;
    top: 2px;
    right: 3px;
}

/* ===== PARALLEL JOBS COUNTER - COMPACT ===== */
.parallel-jobs-badge {
    position: absolute !important;
    top: 2px !important;
    right: 3px !important;
    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%) !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 0px 5px !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    z-index: 999 !important;
    border: 1.5px solid white !important;
    box-shadow: 0 1px 4px rgba(220, 53, 69, 0.4) !important;
    pointer-events: none !important;
    display: block !important;
    line-height: 1.3 !important;
    letter-spacing: 0.2px !important;
}

/* ===== ACTIVE STAGE ===== */
.fc-event.stage-event-active {
    box-shadow: 0 0 0 2px #ffc107, 0 2px 8px rgba(255, 193, 7, 0.3) !important;
    animation: active-glow 2s infinite !important;
}

@keyframes active-glow {
    0%, 100% {
        box-shadow: 0 0 0 2px #ffc107, 0 2px 8px rgba(255, 193, 7, 0.3);
    }
    50% {
        box-shadow: 0 0 0 3px #ffc107, 0 3px 12px rgba(255, 193, 7, 0.5);
    }
}

/* ===== GHOST EVENTS ===== */
.fc-event.ghost-event {
    opacity: 0.5 !important;
    background: repeating-linear-gradient(
        45deg,
        var(--event-color),
        var(--event-color) 8px,
        rgba(255,255,255,0.2) 8px,
        rgba(255,255,255,0.2) 16px
    ) !important;
    border-style: dashed !important;
    border-width: 2px !important;
    cursor: help !important;
}

.fc-event.ghost-event:hover {
    opacity: 0.7 !important;
}

/* ================================================
   TOOLTIPS - PROFESSIONAL
   ================================================ */

.fc-event {
    position: relative !important;
}

.fc-event[data-tooltip]:hover::after {
    content: attr(data-tooltip);
    position: fixed !important;
    background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    white-space: pre-line;
    font-size: 0.75rem;
    line-height: 1.6;
    z-index: 999999 !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    min-width: 180px;
    max-width: 300px;
    pointer-events: none;
    display: block !important;
    animation: tooltipSlideIn 0.2s ease-out;
    border: 2px solid rgba(255,255,255,0.1);
    font-weight: 500;
}

@keyframes tooltipSlideIn {
    from {
        opacity: 0;
        transform: translate(-50%, -90%) scale(0.96);
    }
    to {
        opacity: 1;
        transform: translate(-50%, -100%) scale(1);
    }
}

.fc-event.ghost-event[data-tooltip]:hover::after {
    background: linear-gradient(135deg, #ff9800 0%, #ff6f00 100%) !important;
}

/* Ensure calendar containers don't clip tooltips */
.calendar-modal .modal-body,
#calendar, 
.fc, 
.fc-view-harness,
.fc-daygrid-body, 
.fc-scrollgrid,
.fc-scrollgrid-sync-table {
    overflow: visible !important;
}

/* ===== MORE EVENTS LINK STYLING ===== */
.fc-daygrid-more-link {
    color: #667eea !important;
    font-weight: 600 !important;
    font-size: 0.7rem !important;
    padding: 2px 6px !important;
    background: rgba(102, 126, 234, 0.1) !important;
    border-radius: 4px !important;
    margin-top: 2px !important;
    display: inline-block !important;
}

.fc-daygrid-more-link:hover {
    background: rgba(102, 126, 234, 0.2) !important;
    text-decoration: none !important;
}

/* Ensure popover shows all events properly */
.fc-more-popover {
    z-index: 10000 !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15) !important;
    border-radius: 8px !important;
}

.fc-more-popover .fc-popover-body {
    max-height: 400px !important;
    overflow-y: auto !important;
}

/* ================================================
   LEGEND - CLEAN & ORGANIZED
   ================================================ */

.calendar-legend {
    background: #f8f9fa;
    padding: 14px;
    border-radius: 10px;
    max-height: 500px;
    overflow-y: auto;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.calendar-legend h6 {
    font-size: 0.85rem;
    font-weight: 700;
    color: #2c3e50;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.legend-item {
    padding: 8px 10px;
    margin-bottom: 5px;
    background: white;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 500;
    border-left: 3px solid;
    transition: all 0.2s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.legend-item:hover {
    background: #fff;
    transform: translateX(3px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

/* ===== SCROLLBAR ===== */
.calendar-legend::-webkit-scrollbar {
    width: 6px;
}

.calendar-legend::-webkit-scrollbar-track {
    background: #e9ecef;
    border-radius: 10px;
}

.calendar-legend::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}

.calendar-legend::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
}

/* ================================================
   RESPONSIVE DESIGN
   ================================================ */

@media (max-width: 768px) {
    .fc-toolbar-title {
        font-size: 1rem !important;
    }
    
    .fc-button {
        padding: 5px 10px !important;
        font-size: 0.7rem !important;
    }
    
    .fc-daygrid-day-frame {
        min-height: 80px !important;
    }
    
    .fc-event {
        font-size: 0.68rem !important;
        padding: 2px 6px !important;
        min-height: 20px !important;
        max-height: 20px !important;
    }
    
    .fc-event-title {
        font-size: 0.68rem !important;
    }
    
    .parallel-stage-indicator {
        font-size: 0.55rem !important;
        padding: 0px 3px !important;
    }
    
    .fc-daygrid-day-number {
        font-size: 0.7rem !important;
        padding: 3px !important;
    }
    
    #calendar {
        padding: 8px;
    }
}

/* ================================================
   END OF CLEAN PROFESSIONAL CALENDAR DESIGN
   ================================================ */


/* ===== DAY RESCHEDULE BUTTON ===== */
.day-reschedule-btn {
    position: absolute;
    top: 5px;
    right: 5px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: none;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    cursor: pointer;
    z-index: 150;
    transition: all 0.3s;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
}

.fc-daygrid-day:hover .day-reschedule-btn {
    display: flex;
}

.day-reschedule-btn:hover {
    transform: scale(1.15);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

/* ===== MINI RESCHEDULE POPUP ===== */
.mini-reschedule-popup {
    position: fixed;
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    padding: 15px;
    z-index: 9999;
    min-width: 280px;
    display: none;
    border: 2px solid #667eea;
}

.mini-reschedule-popup.active {
    display: block;
    animation: popIn 0.3s ease-out;
}

@keyframes popIn {
    from {
        opacity: 0;
        transform: scale(0.8) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

.mini-reschedule-popup h6 {
    margin: 0 0 10px 0;
    color: #667eea;
    font-weight: 700;
    font-size: 0.9rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.mini-reschedule-popup .stage-chip {
    background: #f8f9fa;
    border-radius: 6px;
    padding: 6px 10px;
    margin: 4px 0;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    transition: all 0.2s;
    border: 2px solid transparent;
}

.mini-reschedule-popup .stage-chip:hover {
    border-color: #667eea;
    background: #e8eef9;
}

/* ===== DAILY TASK MODAL ===== */
.daily-task-item {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 15px;
    transition: all 0.3s;
    border: 2px solid transparent;
}

.daily-task-item:hover {
    border-color: #667eea;
    background: #e8eef9;
}

.daily-task-item.completed {
    opacity: 0.7;
    background: #e8f5e9;
    border-left: 4px solid #10b981;
}

.daily-task-item.rescheduled {
    border-left: 4px solid #f59e0b;
    background: #fffbeb;
}

.task-day-number {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1.1rem;
}

.task-day-number.completed {
    background: #28a745;
}

.task-status-badge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-pending {
    background: #6c757d;
    color: white;
}

.badge-completed {
    background: #28a745;
    color: white;
}

.badge-rescheduled {
    background: #ffc107;
    color: #000;
}

/* ===== ANIMATIONS ===== */
@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

@keyframes slideOutRight {
    from {
        transform: translateX(0);
        opacity: 1;
    }
    to {
        transform: translateX(100%);
        opacity: 0;
    }
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* ===== RESPONSIVE ===== */
@media (max-width: 992px) {
    .calendar-legend {
        max-height: 250px;  /* Changed from 300px */
    }
    
    .fc {
        font-size: 0.7rem;
        padding: 8px;
    }
    
    #calendar {
        min-height: 400px;
    }
}

/* ===== SCROLLBAR ===== */
.calendar-legend::-webkit-scrollbar {
    width: 6px;
}

.calendar-legend::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 10px;
}

.calendar-legend::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}
/* Ghost Events - Show original locations */
.fc-event.ghost-event {
    opacity: 0.5 !important;
    border: 2px dashed rgba(220, 53, 69, 0.6) !important;
    background: repeating-linear-gradient(
        45deg,
        rgba(255, 255, 255, 0.8),
        rgba(255, 255, 255, 0.8) 8px,
        rgba(220, 53, 69, 0.15) 8px,
        rgba(220, 53, 69, 0.15) 16px
    ) !important;
    cursor: help !important;
    pointer-events: auto !important;
}
.fc-event.ghost-event .fc-event-main {
    color: #ff9800 !important;
    font-weight: 600 !important;
    text-decoration: line-through !important;
}
.fc-event.ghost-event::before {
    display: none !important;
}
/* Date cell reschedule indicator */
.date-reschedule-badge {
    position: absolute;
    bottom: 3px;
    left: 3px;
    background: #ff9800;
    color: white;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: bold;
    z-index: 100;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Enhanced tooltip for ghost events */
.fc-event.ghost-event {
    opacity: 0.6 !important;
    border: 2px dashed rgba(255, 152, 0, 0.8) !important;
    background: repeating-linear-gradient(
        45deg,
        rgba(255, 255, 255, 0.9),
        rgba(255, 255, 255, 0.9) 8px,
        rgba(255, 152, 0, 0.2) 8px,
        rgba(255, 152, 0, 0.2) 16px
    ) !important;
    cursor: help !important;
    pointer-events: auto !important;
    position: relative !important;
}

.fc-event.ghost-event::after {
    content: 'MOVED';
    position: absolute !important;
    top: 2px !important;
    right: 2px !important;
    background: #ff9800 !important;
    color: white !important;
    border-radius: 4px !important;
    padding: 2px 5px !important;
    font-size: 8px !important;
    font-weight: bold !important;
    z-index: 999 !important;
    display: block !important;
}


/* Enhanced reschedule indicator */
.reschedule-indicator {
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-10px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.daily-task-item.rescheduled {
    border-left: 4px solid #ff9800 !important;
    background: linear-gradient(135deg, #fffbf0 0%, #fff8e8 100%) !important;
}

.daily-task-item {
    transition: all 0.3s ease;
}

.task-info {
    min-width: 0; /* Allow flex shrinking */
}

.card.mb-2 {
    border-radius: 12px !important;
    border: 2px solid #e9ecef !important;
    transition: all 0.3s ease;
    background: white !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.card.mb-2:hover {
    border-color: #667eea !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    transform: translateY(-2px);
}
.card.mb-2[style*="border-left: 3px solid rgb(102, 126, 234)"] {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.03) 0%, rgba(118, 75, 162, 0.03) 100%) !important;
}
/* ===== FORM CONTROLS - BETTER STYLING ===== */
.modal-body .form-control,
.modal-body .form-select {
    border: 2px solid #e9ecef;
    border-radius: 8px;
    transition: all 0.3s ease;
    background: white;
}

.modal-body .form-control:focus,
.modal-body .form-select:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.modal-body .form-label {
    font-weight: 600;
    color: #495057;
    margin-bottom: 8px;
}

/* ===== STAGE CONTAINER - BETTER SCROLLBAR ===== */
#stagesContainer {
    background: white;
    border-radius: 12px;
    padding: 15px;
    max-height: 50vh;
    overflow-y: auto;
}

#stagesContainer::-webkit-scrollbar {
    width: 8px;
}

#stagesContainer::-webkit-scrollbar-track {
    background: #f1f3f5;
    border-radius: 10px;
}

#stagesContainer::-webkit-scrollbar-thumb {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 10px;
}

/* ===== CHECKBOX STYLING ===== */
.form-check-input {
    width: 20px;
    height: 20px;
    border: 2px solid #dee2e6;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.form-check-input:checked {
    background-color: #667eea;
    border-color: #667eea;
}

.form-check-input:focus {
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.25);
}

/* ===== PROJECTED END DATE - ENHANCED ===== */
.alert-info {
    background: linear-gradient(135deg, #e8f4fd 0%, #f3e8fd 100%) !important;
    border: 2px solid #667eea !important;
    border-radius: 12px !important;
    color: #495057 !important;
}

/* ===== MANAGER DROPDOWN - BETTER VISIBILITY ===== */
.form-select {
    font-weight: 500;
    color: #495057;
}

.form-select option {
    padding: 10px;
}

/* ===== DELETE BUTTON - SUBTLE ===== */
.btn-outline-danger {
    border-radius: 8px !important;
    opacity: 0.7;
    transition: all 0.2s ease;
}

.btn-outline-danger:hover {
    opacity: 1;
    transform: scale(1.05);
}

/* ===== ADD CUSTOM / RESET BUTTONS ===== */
.btn-success, .btn-outline-secondary {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}

.btn-success:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
}

/* ===== CREATE JOB BUTTON - ENHANCED ===== */
.btn-primary-custom.w-100 {
    padding: 15px !important;
    font-size: 1.1rem !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.btn-primary-custom.w-100:hover {
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    transform: translateY(-2px);
}

/* ===== MODAL BACKDROP - BETTER BLUR ===== */
.modal-backdrop {
    backdrop-filter: blur(3px);
}

/* ===== RESPONSIVE ADJUSTMENTS ===== */
@media (max-width: 768px) {
    .modal-body {
        padding: 15px;
    }
    
    .card.mb-2 .card-body {
        padding: 12px !important;
    }
}

/* ===== STAGE CONTENT OPACITY FIX ===== */
#stageContent-1, #stageContent-2, #stageContent-3,
#stageContent-4, #stageContent-5, #stageContent-6,
#stageContent-7, #stageContent-8, #stageContent-9,
#stageContent-10, #stageContent-11, #stageContent-12,
#stageContent-13, #stageContent-14 {
    transition: opacity 0.3s ease;
}

/* Small, subtle duration badges */
.duration-badge {
    background: #667eea;
    color: white;
    padding: 1px 5px; /* Smaller padding */
    border-radius: 6px; /* Smaller radius */
    font-size: 0.55rem; /* Smaller font */
    margin-left: 4px;
    font-weight: 600;
    vertical-align: middle;
    display: inline-block;
}

/* For parallel stages - even smaller */
.stage-group-container .duration-badge {
    font-size: 0.5rem;
    padding: 1px 4px;
    
}/* ===== WORKING DAYS BADGE ===== */
span[style*="background: rgb(102, 126, 234)"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border-radius: 8px !important;
    padding: 4px 10px !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
}
/* Hide ALL number badges in calendar */
.fc-daygrid-day-bottom {
    display: none !important;
}

.date-reschedule-badge,
.parallel-jobs-badge {
    display: none !important;
}
/* Search and Filter Bar */
.search-filter-bar {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 10px;
}

.search-box {
    position: relative;
    margin-bottom: 12px;
}

.search-icon {
    position: absolute;
    left: 15px;
    top: 50%;
    transform: translateY(-50%);
    color: #6c757d;
    font-size: 1rem;
    z-index: 1;
}

.search-input {
    width: 100%;
    padding: 12px 45px 12px 45px;
    border: 2px solid #dee2e6;
    border-radius: 10px;
    font-size: 0.95rem;
    transition: all 0.3s;
}

.search-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.clear-search {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    color: #6c757d;
    cursor: pointer;
    padding: 5px 10px;
    border-radius: 5px;
    transition: all 0.2s;
}

.clear-search:hover {
    background: #e9ecef;
    color: #dc3545;
}

.filter-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
}

.filter-select {
    padding: 8px 12px;
    border: 2px solid #dee2e6;
    border-radius: 8px;
    font-size: 0.85rem;
    background: white;
    cursor: pointer;
    transition: all 0.3s;
}

.filter-select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.results-count {
    margin-left: auto;
    font-size: 0.85rem;
    color: #6c757d;
    font-weight: 600;
}

/* Pagination */
.pagination-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    margin-top: 20px;
    padding: 15px;
}

.pagination-btn {
    padding: 8px 16px;
    border: 2px solid #667eea;
    background: white;
    color: #667eea;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s;
}

.pagination-btn:hover:not(:disabled) {
    background: #667eea;
    color: white;
    transform: translateY(-2px);
}

.pagination-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

.pagination-info {
    font-size: 0.9rem;
    color: #495057;
    font-weight: 600;
}

/* Loading Spinner */
.loading-spinner {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 40px;
}

.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #667eea;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* No Results */
.no-results {
    text-align: center;
    padding: 60px 20px;
}

.no-results i {
    font-size: 4rem;
    color: #dee2e6;
    margin-bottom: 20px;
}

.no-results h5 {
    color: #6c757d;
    margin-bottom: 10px;
}

.no-results p {
    color: #adb5bd;
    font-size: 0.9rem;
}
/* Fix projects section scroll */
#allProjectsSection {
    overflow: visible !important;
    max-height: none !important;
}

/* Improve card layout */
.project-progress-container {
    margin-bottom: 30px;
    padding: 25px;
    background: #f8f9fa;
    border-radius: 15px;
    overflow: visible !important;
}

/* Better spacing for the entire projects card */
.card-custom .card-body {
    padding: 20px;
    overflow: visible !important;
}
/* HOLD Event Styling */
.fc-event.event-hold {
    background: linear-gradient(135deg, #ff0000 0%, #cc0000 100%) !important;
    border-left: 4px solid #990000 !important;
    opacity: 0.85;
}

.fc-event.event-hold::before {
    content: '🔒';
    position: absolute;
    top: 2px;
    left: 2px;
    font-size: 14px;
    z-index: 10;
}

.fc-event.event-hold .fc-event-title {
    font-weight: bold;
    text-decoration: line-through;
}
</style>
</head>
<body>
    <div class="container-fluid" style="max-width: 1400px;">
        <div class="top-bar-custom d-flex justify-content-between align-items-center">
            <div>
                <h4 class="mb-0">Welcome, {{ current_user.username }}!</h4>
                <small class="text-muted">Have a productive day</small>
            </div>
            <div class="d-flex align-items-center gap-3">
                <div class="position-relative">
                    <button class="btn btn-link text-dark" onclick="toggleNotifications()">
                        <i class="fas fa-bell fa-lg"></i>
                        <span class="notification-badge" id="notifBadge">0</span>
                    </button>
                </div>
                <a href="/logout" class="btn btn-outline-danger">
                    <i class="fas fa-sign-out-alt me-2"></i> Logout
                </a>
            </div>
        </div>

        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="stat-card">
                    <div class="icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <i class="fas fa-briefcase"></i>
                    </div>
                    <p>Total Jobs</p>
                    <h3 id="totalProjects">0</h3>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card">
                    <div class="icon" style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white;">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <p>Active Jobs</p>
                    <h3 id="activeProjects">0</h3>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card">
                    <div class="icon" style="background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); color: white;">
                        <i class="fas fa-tasks"></i>
                    </div>
                    <p>Total Tasks</p>
                    <h3 id="totalTasks">0</h3>
                </div>
            </div>
            <div class="col-md-3 mb-3">
                <div class="stat-card">
                    <div class="icon" style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: white;">
                        <i class="fas fa-users"></i>
                    </div>
                    <p>Team Members</p>
                    <h3 id="totalEmployees">0</h3>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="card-custom">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <span>All Jobs</span>
                        <button class="btn btn-sm btn-primary-custom" onclick="openProjectModal()">
                            <i class="fas fa-plus me-1"></i> New Job
                        </button>
                    </div>
                    
                    <!-- Search and Filter Bar -->
                    <div class="search-filter-bar">
                        <div class="search-box">
                            <i class="fas fa-search search-icon"></i>
                            <input type="text" 
                                id="projectSearchInput" 
                                class="search-input" 
                                placeholder="Search by job number, name, or date..."
                                oninput="handleProjectSearch()">
                            <button class="clear-search" id="clearSearchBtn" onclick="clearProjectSearch()" style="display: none;">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        
                        <div class="filter-controls">
                            <select id="statusFilter" class="filter-select" onchange="handleProjectSearch()">
                                <option value="">All Status</option>
                                <option value="active">Active</option>
                                <option value="completed">Completed</option>
                            </select>
                            
                            <select id="sortBy" class="filter-select" onchange="handleProjectSearch()">
                                <option value="newest">Newest First</option>
                                <option value="oldest">Oldest First</option>
                                <option value="name">Name (A-Z)</option>
                                <option value="progress">Progress</option>
                            </select>
                            
                            <span class="results-count" id="resultsCount">Showing 0 jobs</span>
                        </div>
                    </div>
                </div>                   
                 <div class="card-body">
                        <!-- Helpful Hint Banner -->
                        <div id="allProjectsSection"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

<div class="modal fade" id="projectModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-xl">
    <div class="modal-content">            
    <div class="modal-header">                
    <h5 class="modal-title">Create New Job</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
             <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">            
                <form id="projectForm">
            <div class="row">
                <!-- Left Column -->
                <div class="col-md-6">
                    <div class="mb-3">
                        <label class="form-label">Job Number</label>
                        <input type="text" class="form-control form-control-sm" id="projectName" required placeholder="Enter job number">
                    </div>
                    <!-- REMOVED DESCRIPTION FIELD -->
                    <div class="mb-3">
                        <label class="form-label">Start Date</label>
                        <input type="date" class="form-control form-control-sm" id="projectStartDate" required onchange="updateProjectEndDate()">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Team Members</label>
                        <select class="form-select form-select-sm" id="memberSelect" onchange="addMember()">
                            <option value="">Select member to add...</option>
                        </select>
                        <div id="selectedMembers" class="mt-2"></div>
                    </div>
                    <div class="alert alert-info py-2 mb-0">
                        <small>
                            <i class="fas fa-info-circle me-1"></i>
                            <strong>Projected End Date:</strong> <span id="projectedEndDate">Not calculated</span>
                        </small>
                    </div>
                </div>
                
                <!-- Right Column -->
                <div class="col-md-6">
                    <div class="mb-2">
                        <label class="form-label d-flex justify-content-between align-items-center mb-2">
                            <span>Tasks</span>
                            <div>
                                <button type="button" class="btn btn-sm btn-success py-1 px-2 me-1" onclick="addCustomTask()" style="font-size: 0.75rem;">
                                    <i class="fas fa-plus"></i> Add Custom
                                </button>
                                <button type="button" class="btn btn-sm btn-outline-secondary py-1 px-2" onclick="loadDefaultStages()" style="font-size: 0.75rem;">
                                    <i class="fas fa-redo"></i> Reset
                                </button>
                            </div>
                        </label>
                        <div id="stagesContainer" style="max-height: 50vh; overflow-y: auto; padding-right: 5px;"></div>
                    </div>
                </div>
            </div>
             <div class="mt-3">
            <button type="submit" class="btn btn-primary-custom w-100">Create Job</button>
        </div>
    </form>
 </div>       
 </div>
</div>
</div>
<!-- Task Popup Modal (ADD THIS IF YOU DON'T HAVE IT) -->
     <div id="taskPopup" style="display: none;">
        <div class="popup-overlay" onclick="closePopup()"></div>
        <div class="popup-container">
            <div id="popupContent"></div>
        </div>
    </div>
<div class="modal fade calendar-modal" id="calendarModal" tabindex="-1">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h5 class="modal-title mb-1" id="calendarProjectTitle">Job Calendar View</h5>
                    <small class="text-white-50" id="calendarProjectDates"></small>
                </div>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-3">
                <div class="row g-2">
                    <!-- Calendar Section - Full Width -->
                    <div class="col-12">
                        <div style="background: white; padding: 10px; border-radius: 10px;">
                            <div id="calendar"></div>
                        </div>
                    </div>
                    
                    <!-- Compact Legend Below Calendar -->
                    <div class="col-12">
                        <div class="d-flex gap-2 flex-wrap">
                            <!-- Stages Legend - Compact Horizontal -->
                            <div class="flex-grow-1" style="background: white; padding: 10px; border-radius: 10px;">
                                <h6 style="font-size: 0.8rem; margin-bottom: 8px; font-weight: 700;">
                                    <i class="fas fa-palette me-1"></i>Stages
                                </h6>
                                <div id="calendarLegend" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px; max-height: 150px; overflow-y: auto;"></div>
                            </div>
                            
                            <!-- Status Indicators - Compact -->
                            <div style="background: white; padding: 10px; border-radius: 10px; min-width: 200px;">
                                <h6 style="font-size: 0.8rem; margin-bottom: 8px; font-weight: 700;">
                                    <i class="fas fa-info-circle me-1"></i>Legend
                                </h6>
                                <div style="font-size: 0.7rem; line-height: 1.5;">
                                    <div style="margin-bottom: 4px;">
                                        <span style="display: inline-block; width: 8px; height: 8px; background: #dc3545; border-radius: 2px; margin-right: 4px;"></span>
                                        Parallel
                                    </div>
                                    <div style="margin-bottom: 4px;">
                                        <span style="display: inline-block; width: 8px; height: 8px; background: #ffc107; border-radius: 2px; margin-right: 4px;"></span>
                                        Active
                                    </div>
                                    <div style="margin-bottom: 4px;">
                                        <span style="display: inline-block; width: 8px; height: 8px; background: #28a745; border-radius: 2px; margin-right: 4px;"></span>
                                        Done
                                    </div>
                                    <div>
                                        <span style="display: inline-block; width: 8px; height: 8px; background: #ff9800; border-radius: 2px; margin-right: 4px;"></span>
                                        Moved
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
<!-- Mini Reschedule Popup -->
<div class="mini-reschedule-popup" id="miniReschedulePopup">
    <h6>
        <span><i class="fas fa-calendar-alt me-2"></i>Stages on <span id="popupDate"></span></span>
        <button class="close-popup" onclick="closeMiniPopup()">✖</button>
    </h6>
    <div id="popupStagesList"></div>
</div>
<!-- Compact Reschedule Modal -->
<div class="modal fade reschedule-modal-compact" id="rescheduleModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title text-white">
                    <i class="fas fa-calendar-plus me-2"></i>Reschedule Stage
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <!-- Stage Info Card -->
                <div class="card mb-3" style="background: linear-gradient(135deg, #f5f7fa 0%, #e8eef9 100%);">
                    <div class="card-body p-3">
                        <div class="d-flex align-items-start">
                            <div class="flex-grow-1">
                                <div class="mb-2">
                                    <strong style="color: #667eea; font-size: 1.1rem;" id="rescheduleStageInfo"></strong>
                                </div>
                                <div class="mb-2">
                                    <small class="text-muted">Current:</small><br>
                                    <span id="rescheduleCurrentDates" class="badge bg-dark"></span>
                                </div>
                                <div id="rescheduleNewDatesPreview" style="display: none;">
                                    <small class="text-muted">New:</small><br>
                                    <span id="rescheduleNewDatesValue" class="badge bg-success"></span>
                                </div>
                            </div>
                            <div id="rescheduleStageColor" style="width: 40px; height: 40px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Reschedule Form -->
                <form id="rescheduleForm">
                    <div class="mb-3">
                        <label class="form-label fw-bold" style="font-size: 0.9rem;">
                            <i class="fas fa-arrows-alt-h me-2"></i>Shift by days
                        </label>
                        <div class="input-group">
                            <button class="btn btn-outline-secondary" type="button" onclick="adjustRescheduleDays(-1)">
                                <i class="fas fa-minus"></i>
                            </button>
                            <input type="number" class="form-control text-center fw-bold" id="rescheduleDays" required 
                                   placeholder="0" style="font-size: 1.1rem;" oninput="updateReschedulePreview()">
                            <button class="btn btn-outline-secondary" type="button" onclick="adjustRescheduleDays(1)">
                                <i class="fas fa-plus"></i>
                            </button>
                            <span class="input-group-text">days</span>
                        </div>
                        <small class="text-muted">
                            <i class="fas fa-lightbulb me-1"></i>
                            Positive = forward, Negative = backward
                        </small>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label fw-bold" style="font-size: 0.9rem;">
                            <i class="fas fa-comment-dots me-2"></i>Reason (optional)
                        </label>
                        <textarea class="form-control" id="rescheduleReason" rows="2" 
                                  placeholder="e.g., Resource availability..."></textarea>
                    </div>
                    
                    <!-- Impact Warning -->
                    <div class="alert alert-warning py-2" id="rescheduleImpactWarning" style="display: none; font-size: 0.85rem;">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <span id="rescheduleImpactText"></span>
                    </div>
                    
                    <input type="hidden" id="rescheduleProjectId">
                    <input type="hidden" id="rescheduleStageId">
                    <input type="hidden" id="rescheduleStageStartDate">
                    <input type="hidden" id="rescheduleStageEndDate">
                    
                <div class="d-grid gap-2">
                    <button class="btn btn-primary-custom" onclick="confirmDayReschedule()">
                        <i class="fas fa-check-circle me-2"></i>Confirm Reschedule
                    </button>
                    <button class="btn btn-warning" onclick="holdDayTask()">
                        <i class="fas fa-lock me-2"></i>Put on Hold
                    </button>
                    <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                </div>               
            </div>
        </div>
    </div>
</div>
<!-- Daily Task Management Modal -->
<div class="modal fade" id="dailyTaskModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h5 class="modal-title text-white" id="dailyTaskModalTitle">Manage Daily Tasks</h5>
                    <small class="text-white-50" id="dailyTaskStageName"></small>
                </div>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div id="dailyTasksList"></div>
            </div>
        </div>
    </div>
</div>

<!-- Reschedule Single Day Modal -->
<div class="modal fade" id="rescheduleDayModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title text-white">Reschedule Day</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="alert alert-info" id="dayRescheduleInfo"></div>
                
                <div class="mb-3">
                    <label class="form-label fw-bold">Shift by working days:</label>
                    <div class="input-group">
                        <button class="btn btn-outline-secondary" type="button" onclick="adjustDayShift(-1)">
                            <i class="fas fa-minus"></i>
                        </button>
                        <input type="number" class="form-control text-center fw-bold" id="dayShiftAmount" value="0">
                        <button class="btn btn-outline-secondary" type="button" onclick="adjustDayShift(1)">
                            <i class="fas fa-plus"></i>
                        </button>
                        <span class="input-group-text">days</span>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label fw-bold">Reason:</label>
                    <textarea class="form-control" id="dayRescheduleReason" rows="2" placeholder="Why is this day being rescheduled?"></textarea>
                </div>
                
                <div id="dayReschedulePreview" style="display: none;" class="alert alert-success"></div>
                
                <input type="hidden" id="rescheduleTaskId">
                <input type="hidden" id="rescheduleTaskProjectId">
                <input type="hidden" id="rescheduleTaskStageId">
                
                <div class="d-grid gap-2">
                    <button class="btn btn-primary-custom" onclick="confirmDayReschedule()">
                        <i class="fas fa-check-circle me-2"></i>Confirm Reschedule
                    </button>
                    <button class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                </div>
            </div>
        </div>
    </div>
</div>  


<!-- Add this right before the opening <script> tag -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
<script>
    let projects = [];
    let employees = [];
    let projectModal;
    let stageCounter = 0;
    let selectedMembers = [];
    let defaultStages = [];
    let calendar;
    let calendarModal;
    let rescheduleModal;
    let currentProjectForCalendar = null;
    let currentProjectData = null;
    let includeSaturdayAsWorkingDay = false;
    let workingSaturdays = new Set();
    let dailyTaskModal;
    
    // ✅ ADD DEBOUNCE TO PREVENT DOUBLE-CLICK ISSUES
    let lastClickTime = 0;
    const CLICK_DEBOUNCE = 300; // milliseconds
    let rescheduleDayModal;
    let currentStageForDailyTasks = null; // Track individual working Saturdays
    let allProjectsCache = [];
    let filteredProjects = [];
    let currentPage = 1;
    const projectsPerPage = 10;
    let searchTimeout = null;    
    const STAGE_COLORS = [
        '#667eea', '#764ba2', '#f093fb', '#4facfe', 
        '#43e97b', '#fa709a', '#fee140', '#30cfd0', 
        '#a8edea', '#ff6a88', '#feca57', '#48dbfb'
    ];

    // Add this near the top of your script section
    async function handleApiResponse(response) {
        if (response.status === 401) {
            alert('Your session has expired. Please log in again.');
            window.location.href = '/login';
            throw new Error('Session expired');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }    

    document.addEventListener('DOMContentLoaded', function() {
        projectModal = new bootstrap.Modal(document.getElementById('projectModal'));
        calendarModal = new bootstrap.Modal(document.getElementById('calendarModal'));
        rescheduleModal = new bootstrap.Modal(document.getElementById('rescheduleModal'));
        
        // Reset form when modal is hidden
        document.getElementById('projectModal').addEventListener('hidden.bs.modal', function() {
            console.log('Modal hidden - resetting form');
            resetProjectForm();
        });
        
        // Clean up calendar when calendar modal is closed
        document.getElementById('calendarModal').addEventListener('hidden.bs.modal', function() {
            console.log('Calendar modal hidden - cleaning up');
            if (calendar) {
                calendar.destroy();
                calendar = null;
                console.log('✅ Calendar destroyed on modal close');
            }
            // Clear current project data
            currentProjectData = null;
            currentProjectForCalendar = null;
            // Stop auto-refresh
            stopAllProgressLineAutoRefresh();
        });
        
        document.getElementById('projectForm').addEventListener('submit', handleProjectSubmit);
        document.getElementById('rescheduleForm').addEventListener('submit', handleReschedule);
        
        // Add event listener for start date change
        document.getElementById('projectStartDate').addEventListener('change', checkStartDateWeekend);
        document.getElementById('projectStartDate').valueAsDate = new Date();
        dailyTaskModal = new bootstrap.Modal(document.getElementById('dailyTaskModal'));
        rescheduleDayModal = new bootstrap.Modal(document.getElementById('rescheduleDayModal'));
        
        const saturdayCheckbox = document.getElementById('includeSaturday');
        if (saturdayCheckbox) {
            saturdayCheckbox.addEventListener('change', (e) => {
                includeSaturdayAsWorkingDay = e.target.checked;
                updateProjectEndDate();
                if (currentProjectForCalendar && calendar) {
                    openCalendarView(currentProjectForCalendar);
                }
                loadProjects();
            });
        }
        
        // ✅ ADD EVENT DELEGATION FOR CIRCLE CLICKS (LEFT AND RIGHT CLICK)
            document.addEventListener('click', function(e) {
                const circle = e.target.closest('.step-circle');
                if (circle) {
                    e.stopPropagation();
                    
                    const now = Date.now();
                    const timeSinceLastClick = now - lastClickTime;
                    
                    // Detect double-click (within 400ms)
                    if (timeSinceLastClick < 400) {
                        console.log('🔄 Double-click detected - undoing last action');
                        const step = circle.closest('.progress-step');
                        if (step) {
                            const projectId = step.dataset.projectId;
                            const stageId = step.dataset.stageId;
                            const currentStatus = step.dataset.stageStatus;
                            
                            if (projectId && stageId && currentStatus !== 'pending') {
                                const prevStatus = currentStatus === 'completed' ? 'in-progress' : 'pending';
                                undoStageStatus(parseInt(projectId), parseInt(stageId), prevStatus);
                            }
                        }
                        lastClickTime = 0; // Reset to prevent triple-click issues
                        return;
                    }
                    
                    lastClickTime = now;
                    
                    const step = circle.closest('.progress-step');
                    if (step) {
                        const projectId = step.dataset.projectId;
                        const stageId = step.dataset.stageId;
                        const currentStatus = step.dataset.stageStatus;
                        
                        if (projectId && stageId && currentStatus) {
                            updateStageStatus(parseInt(projectId), parseInt(stageId), currentStatus);
                        }
                    }
                }
            });        
        // ✅ ADD EVENT DELEGATION FOR RIGHT-CLICK (UNDO)
        document.addEventListener('contextmenu', function(e) {
            const circle = e.target.closest('.step-circle');
            if (circle) {
                e.preventDefault();
                e.stopPropagation();
                
                const step = circle.closest('.progress-step');
                if (step) {
                    const projectId = step.dataset.projectId;
                    const stageId = step.dataset.stageId;
                    const currentStatus = step.dataset.stageStatus;
                    
                    if (projectId && stageId && currentStatus) {
                        if (currentStatus !== 'pending') {
                            const prevStatus = currentStatus === 'completed' ? 'in-progress' : 'pending';
                            undoStageStatus(parseInt(projectId), parseInt(stageId), prevStatus);
                        } else {
                            showNotification('Already at initial status', 'info');
                        }
                    }
                }
            }
        });
        
        init();
    });

    // NEW FUNCTION: Check if start date is weekend
    function checkStartDateWeekend() {
        const startDateInput = document.getElementById('projectStartDate');
        if (!startDateInput.value) return;
        
        const selectedDate = new Date(startDateInput.value);
        const dayOfWeek = selectedDate.getDay();
        
        // Check if Sunday (0)
                if (dayOfWeek === 0) {
            showPopup(
                'âš ï¸ Sunday is a Holiday',                       
                'The selected start date falls on Sunday, which is a holiday. Please select a working day (Monday-Friday).',
                        [
                            {
                                text: 'Choose Another Date',
                                className: 'btn-primary',
                                onClick: () => {
                                    startDateInput.value = '';
                                    startDateInput.focus();
                                    closePopup();
                                }
                            }
                        ]
                    );
                    return;
                }        
        // Check if Saturday (6)
        if (dayOfWeek === 6) {
            const dateStr = selectedDate.toISOString().split('T')[0];
            
        showPopup(
                'ðŸ“… Saturday Detected',
                `The selected start date is Saturday (${selectedDate.toLocaleDateString()}). Do you want to consider this Saturday as a working day?`,
                [
                    {
                        text: '\u2714 Yes, Working Day',
                        className: 'btn-success',
                        onClick: () => {
                            workingSaturdays.add(dateStr);
                            updateProjectEndDate();
                            closePopup();
                            showNotification('Saturday marked as working day', 'success');
                        }
                    },               
                       {
                        text: '\u274C No, Holiday',
                        className: 'btn-secondary',
                        onClick: () => {
                            workingSaturdays.delete(dateStr);
                            // Move to next Monday
                            const nextMonday = new Date(selectedDate);
                            nextMonday.setDate(nextMonday.getDate() + 2);
                            startDateInput.valueAsDate = nextMonday;
                            updateProjectEndDate();
                            closePopup();
                            showNotification('Start date moved to Monday', 'info');
                        }
                    }              
                ]
            );
        }
    }

    // NEW FUNCTION: Show popup dialog
    function showPopup(title, message, buttons) {
        const popup = document.getElementById('taskPopup');
        const content = document.getElementById('popupContent');
        
        const buttonsHtml = buttons.map((btn, index) => 
            `<button class="btn ${btn.className}" id="popupBtn${index}">${btn.text}</button>`
        ).join('');
        
        content.innerHTML = `
            <h5 style="margin-bottom: 15px; color: #667eea;">${title}</h5>
            <p style="margin-bottom: 20px; line-height: 1.6;">${message}</p>
            <div class="popup-buttons">
                ${buttonsHtml}
            </div>
        `;
        
        // Attach click handlers after rendering
        buttons.forEach((btn, index) => {
            document.getElementById(`popupBtn${index}`).onclick = btn.onClick;
        });
        
        popup.style.display = 'block';
    }

    // NEW FUNCTION: Close popup
    function closePopup() {
        document.getElementById('taskPopup').style.display = 'none';
    }

    // UPDATED FUNCTION: Calculate working days excluding weekends
    function addWorkingDays(startDate, days) {
        if (days === 0) return startDate;
        
        let currentDate = new Date(startDate);
        let direction = days > 0 ? 1 : -1;
        let daysRemaining = Math.abs(days);
        
        while (daysRemaining > 0) {
            currentDate.setDate(currentDate.getDate() + direction);
            
            const dayOfWeek = currentDate.getDay();
            const dateStr = currentDate.toISOString().split('T')[0];
            
            // Skip Sundays (0)
            if (dayOfWeek === 0) continue;
            
            // For Saturdays (6), check if it's a working Saturday
            if (dayOfWeek === 6) {
                if (workingSaturdays.has(dateStr) || includeSaturdayAsWorkingDay) {
                    daysRemaining--;
                }
                continue;
            }
            
            // Monday-Friday are working days
            daysRemaining--;
        }
        
        return currentDate;
    }

    // UPDATED FUNCTION: Get next working day
    function getNextWorkingDay(date) {
        let checkDate = new Date(date);
        
        while (true) {
            const dayOfWeek = checkDate.getDay();
            const dateStr = checkDate.toISOString().split('T')[0];
            
            // Sunday - skip
            if (dayOfWeek === 0) {
                checkDate.setDate(checkDate.getDate() + 1);
                continue;
            }
            
            // Saturday - check if working
            if (dayOfWeek === 6) {
                if (workingSaturdays.has(dateStr) || includeSaturdayAsWorkingDay) {
                    return checkDate;
                }
                checkDate.setDate(checkDate.getDate() + 1);
                continue;
            }
            
            // Monday-Friday
            return checkDate;
        }
    }

    async function init() {
        await loadDefaultStagesFromAPI();
        await loadEmployees();
        await loadStats();
        await loadProjects();
    }

    async function loadDefaultStagesFromAPI() {
        const response = await fetch('/api/default-stages');
        defaultStages = await response.json();
    }

    function loadDefaultStages() {
            document.getElementById('stagesContainer').innerHTML = '';
            stageCounter = 0;
            defaultStages.forEach(stage => addTaskCheckbox(stage.name, stage.duration_days, true));
            updateProjectEndDate();
        }

        function addTaskCheckbox(name, duration, isChecked = false, managerId = null) {
            stageCounter++;
            const html = `
                <div class="card mb-2" id="stage-${stageCounter}" style="background: #f8f9fa; border-left: 3px solid ${isChecked ? '#667eea' : '#dee2e6'};">
                    <div class="card-body p-2">
                        <div class="d-flex align-items-start gap-2">
                            <input type="checkbox" class="form-check-input mt-1" id="stageCheck-${stageCounter}" 
                                ${isChecked ? 'checked' : ''} onchange="toggleStageSelection(${stageCounter})" 
                                style="width: 18px; height: 18px; cursor: pointer;">
                            <div class="flex-grow-1" id="stageContent-${stageCounter}" style="opacity: ${isChecked ? '1' : '0.5'};">
                                <div class="mb-2">
                                    <strong style="color: #495057; font-size: 0.85rem;">${name}</strong>
                                    <input type="hidden" id="stageName-${stageCounter}" value="${name}">
                                </div>
                                <div class="row mb-2">
                                    <div class="col-4">
                                        <label class="form-label mb-1" style="font-size: 0.75rem;">Duration (days):</label>
                                        <input type="number" class="form-control form-control-sm" placeholder="Days" 
                                            id="stageDuration-${stageCounter}" min="1" value="${duration}" 
                                            onchange="updateProjectEndDate()" style="font-size: 0.85rem;" ${!isChecked ? 'disabled' : ''}>
                                    </div>
                                    <div class="col-4">
                                        <label class="form-label mb-1" style="font-size: 0.75rem;">Manager:</label>
                                        <select class="form-select form-select-sm" id="stageManager-${stageCounter}" 
                                            style="font-size: 0.85rem;" ${!isChecked ? 'disabled' : ''}>
                                            <option value="">Select Manager...</option>
                                        </select>
                                    </div>
                                    <div class="col-4">
                                        <label class="form-label mb-1" style="font-size: 0.75rem;">Custom Start:</label>
                                        <input type="date" class="form-control form-control-sm" 
                                            id="stageStartDate-${stageCounter}" 
                                            data-is-custom="false"
                                            onchange="this.setAttribute('data-is-custom','true'); updateProjectEndDate();" style="font-size: 0.85rem;" ${!isChecked ? 'disabled' : ''}>
                                    </div>
                                </div>
                                <div>
                                    <small class="text-muted" style="font-size: 0.65rem;">
                                        <i class="fas fa-calendar me-1"></i>
                                        <span id="stagePreview-${stageCounter}">Calculating...</span>
                                    </small>
                                </div>
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1" onclick="removeStage(${stageCounter})" 
                                    style="font-size: 0.7rem; ${isChecked ? 'display: none;' : ''}" id="deleteBtn-${stageCounter}">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.getElementById('stagesContainer').insertAdjacentHTML('beforeend', html);
            
            // Populate manager dropdown
            populateManagerDropdown(stageCounter, managerId);
        }

        function populateManagerDropdown(stageId, selectedManagerId = null) {
            const managerSelect = document.getElementById(`stageManager-${stageId}`);
            if (!managerSelect) return;
            
            managerSelect.innerHTML = '<option value="">Select Manager...</option>' + 
                employees.map(e => `<option value="${e.id}" ${e.id === selectedManagerId ? 'selected' : ''}>${e.username}</option>`).join('');
        }

        function toggleStageSelection(id) {
            const checkbox = document.getElementById(`stageCheck-${id}`);
            const content = document.getElementById(`stageContent-${id}`);
            const card = document.getElementById(`stage-${id}`);
            const durationInput = document.getElementById(`stageDuration-${id}`);
            const managerSelect = document.getElementById(`stageManager-${id}`);  // ADD THIS
            const startDateInput = document.getElementById(`stageStartDate-${id}`);
            const deleteBtn = document.getElementById(`deleteBtn-${id}`);
            
            if (checkbox.checked) {
                content.style.opacity = '1';
                card.style.borderLeftColor = '#667eea';
                durationInput.disabled = false;
                managerSelect.disabled = false;  // ADD THIS
                startDateInput.disabled = false;
                if (deleteBtn) deleteBtn.style.display = 'none';
            } else {
                content.style.opacity = '0.5';
                card.style.borderLeftColor = '#dee2e6';
                durationInput.disabled = true;
                managerSelect.disabled = true;  // ADD THIS
                startDateInput.disabled = true;
                if (deleteBtn) deleteBtn.style.display = 'block';
            }
            
            updateProjectEndDate();
        }

        function addCustomTask() {
            const taskName = prompt('Enter custom task name:');
            if (!taskName || taskName.trim() === '') return;
            
            const duration = prompt('Enter duration in days:', '1');
            if (!duration || isNaN(duration) || parseInt(duration) < 1) return;
            
            addTaskCheckbox(taskName.trim(), parseInt(duration), true);
            updateProjectEndDate();
            showNotification('Custom task added!', 'success');
        }

        function addStageWithData(name, duration) {
            addTaskCheckbox(name, duration, true);
        }
        function removeStage(id) {
            document.getElementById(`stage-${id}`)?.remove();
            updateProjectEndDate();
        }

    // UPDATED FUNCTION: Update project end date with working days calculation
    function updateProjectEndDate() {
        const startDateInput = document.getElementById('projectStartDate');
        if (!startDateInput.value) return;
        
        const projectStartDate = new Date(startDateInput.value);
        let currentDate = getNextWorkingDay(projectStartDate);
        const stageElements = document.querySelectorAll('[id^="stage-"]');
        
        const stageDates = [];
        
        stageElements.forEach((element, idx) => {
            const id = element.id.split('-')[1];
            const checkbox = document.getElementById(`stageCheck-${id}`);
            
            // Skip unchecked tasks
            if (!checkbox || !checkbox.checked) return;
            
            const duration = parseInt(document.getElementById(`stageDuration-${id}`)?.value) || 1;
            const customStartDateInput = document.getElementById(`stageStartDate-${id}`);
            const customStartDate = customStartDateInput?.value;
            const isCustom = customStartDateInput?.getAttribute('data-is-custom') === 'true';
            
            let stageStart;
            if (customStartDate && isCustom) {
                stageStart = getNextWorkingDay(new Date(customStartDate));
            } else {
                stageStart = new Date(currentDate);
            }
            
            // Calculate end date using working days
            const stageEnd = addWorkingDays(stageStart, duration - 1);
            
            stageDates.push({ 
                id: id,
                index: idx,
                start: stageStart, 
                end: stageEnd,
                hasCustomDate: !!(customStartDate && isCustom),
                duration: duration
            });
            
            // Always advance so subsequent sequential stages chain correctly
            currentDate = addWorkingDays(stageEnd, 1);
        });
        
        // Detect overlapping stages
        const overlapGroups = [];
        stageDates.forEach((stage, idx) => {
            const overlappingIndices = [idx];
            
            stageDates.forEach((otherStage, otherIdx) => {
                if (idx === otherIdx) return;
                const hasOverlap = (stage.start <= otherStage.end && stage.end >= otherStage.start);
                if (hasOverlap && !overlappingIndices.includes(otherIdx)) {
                    overlappingIndices.push(otherIdx);
                }
            });
            
            if (overlappingIndices.length > 1) {
                overlappingIndices.sort((a, b) => a - b);
                const groupExists = overlapGroups.some(group => 
                    JSON.stringify(group.stages.sort()) === JSON.stringify(overlappingIndices.sort())
                );
                if (!groupExists) {
                    overlapGroups.push({ stages: overlappingIndices });
                }
            }
        });
    
    // Update previews
    stageDates.forEach((stageData, idx) => {
        const preview = document.getElementById(`stagePreview-${stageData.id}`);
        if (!preview) return;
        
        let previewHTML = `${stageData.start.toLocaleDateString()} - ${stageData.end.toLocaleDateString()}`;
        previewHTML += ` <span class="duration-badge">${stageData.duration} working days</span>`;
        
        if (stageData.hasCustomDate) {
            previewHTML += ' <span class="badge bg-primary" style="font-size: 0.65rem;">Custom</span>';
        }
        
        const overlapGroup = overlapGroups.find(group => group.stages.includes(idx));
        if (overlapGroup) {
            const position = overlapGroup.stages.indexOf(idx) + 1;
            const total = overlapGroup.stages.length;
            previewHTML += ` <span class="badge bg-warning" style="font-size: 0.65rem;">Overlap ${position}/${total}</span>`;
        }
        
        preview.innerHTML = previewHTML;
    });
    
    // Update projected end date with proper messaging
    if (stageDates.length > 0) {
        const latestEndDate = stageDates.reduce((latest, stage) => {
            return stage.end > latest ? stage.end : latest;
        }, stageDates[0].end);
        
        document.getElementById('projectedEndDate').textContent = latestEndDate.toLocaleDateString();
    } else {
        document.getElementById('projectedEndDate').textContent = 'No tasks selected';
    }
}
    function addMember() {
        const select = document.getElementById('memberSelect');
        const memberId = parseInt(select.value);
        if (!memberId || selectedMembers.includes(memberId)) return;
        selectedMembers.push(memberId);
        renderSelectedMembers();
        select.value = '';
    }

    function removeMember(memberId) {
        selectedMembers = selectedMembers.filter(id => id !== memberId);
        renderSelectedMembers();
    }

    function renderSelectedMembers() {
        const container = document.getElementById('selectedMembers');
        container.innerHTML = selectedMembers.map(memberId => {
            const member = employees.find(e => e.id === memberId);
            return `<div class="member-chip"><i class="fas fa-user-circle me-1"></i>${member.username}<i class="fas fa-times" onclick="removeMember(${memberId})"></i></div>`;
        }).join('');
    }

    async function loadStats() {
        const response = await fetch('/api/stats');
        const data = await response.json();
        document.getElementById('totalProjects').textContent = data.total_projects;
        document.getElementById('activeProjects').textContent = data.active_projects;
        document.getElementById('totalTasks').textContent = data.total_tasks;
        document.getElementById('totalEmployees').textContent = data.total_employees;
    }

async function loadProjects() {
    try {
        console.log('📦 Loading projects...');
        const response = await fetch(`/api/projects?_t=${Date.now()}`, {
            cache: 'no-store',
            headers: {'Cache-Control': 'no-cache'}
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        projects = await response.json();
        console.log('📦 Projects loaded:', projects.length, projects);
        
        if (projects.length === 0) {
            const container = document.getElementById('allProjectsSection');
            container.innerHTML = '<p class="text-muted text-center py-4">No jobs yet. Create your first job!</p>';
            return;
        }
        
        // Fetch details for each project
        const projectsWithDetails = await Promise.all(
            projects.map(async (project) => {
                try {
                    console.log(`📋 Fetching details for project ${project.id}: "${project.name}"...`);
                    const detailsResponse = await fetch(`/api/projects/${project.id}/details?_t=${Date.now()}`, {
                        cache: 'no-store',
                        headers: {'Cache-Control': 'no-cache'}
                    });
                    
                    if (!detailsResponse.ok) {
                        console.error(`❌ Failed to fetch details for project ${project.id}`);
                        return null;
                    }
                    
                    const details = await detailsResponse.json();
                    console.log(`✅ Details loaded for project ${project.id}:`, {
                        name: details.name,
                        stages: details.stages.length,
                        stagesData: details.stages
                    });
                    return details;
                } catch (error) {
                    console.error(`❌ Error fetching project ${project.id}:`, error);
                    return null;
                }
            })
        );
        
        // Filter out null values
        const validProjects = projectsWithDetails.filter(p => p !== null);
        console.log('✅ Valid projects to render:', validProjects.length);
        
        if (validProjects.length === 0) {
            const container = document.getElementById('allProjectsSection');
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Jobs exist but couldn't load details. Please refresh the page.
                </div>
            `;
            return;
        }
        
        // Force clear and re-render
        const container = document.getElementById('allProjectsSection');
        container.innerHTML = '';
        renderProjectsWithStages(validProjects);
    } catch (error) {
        console.error('Error loading projects:', error);
        const container = document.getElementById('allProjectsSection');
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error loading jobs: ${error.message}
                <button class="btn btn-sm btn-outline-danger ms-3" onclick="loadProjects()">
                    <i class="fas fa-redo me-1"></i> Retry
                </button>
            </div>
        `;
    }
}    

function renderProjectsWithStages(projectsData) {
        const container = document.getElementById('allProjectsSection');
        
        if (!projectsData.length) {
            container.innerHTML = '<p class="text-muted text-center py-4">No jobs yet. Create your first job!</p>';
            return;
        }
            
        container.innerHTML = '';
        
        container.innerHTML = projectsData.map(project => {
            const stages = project.stages || [];
            const totalStages = stages.length;
            const completedStages = stages.filter(s => s.status === 'completed').length;
            const progress = totalStages > 0 ? Math.round((completedStages / totalStages) * 100) : 0;
            
            console.log(`🎨 Rendering project "${project.name}" with ${stages.length} stages`);
            
            const startDateGroups = new Map();
            
            stages.forEach((stage, idx) => {
                if (!stage.start_date) {
                    console.log(`  ⚠️ Stage ${idx} "${stage.name}" has NO start_date`);
                    return;
                }
                const startDateKey = stage.start_date;
                if (!startDateGroups.has(startDateKey)) {
                    startDateGroups.set(startDateKey, []);
                }
                startDateGroups.get(startDateKey).push(idx);
                console.log(`  ✅ Stage ${idx} "${stage.name}" start_date: ${stage.start_date}`);
            });
            
            console.log(`  📊 Start date groups found:`, startDateGroups.size);
            startDateGroups.forEach((indices, startDate) => {
                if (indices.length > 1) {
                    console.log(`    🔵 PARALLEL GROUP on ${startDate}: ${indices.length} stages`, indices);
                }
            });
            
            const stageGroupMap = new Map();
            startDateGroups.forEach((indices, startDate) => {
                if (indices.length > 1) {
                    indices.sort((a, b) => a - b);
                    indices.forEach(i => stageGroupMap.set(i, indices));
                }
            });
            
            const orderedStages = [];
            const processedIndices = new Set();
            
            stages.forEach((stage, idx) => {
                if (processedIndices.has(idx)) return;
                
                const sameStartGroup = stageGroupMap.get(idx);
                
                if (sameStartGroup && sameStartGroup.length > 1) {
                    sameStartGroup.forEach(groupIdx => {
                        if (!processedIndices.has(groupIdx)) {
                            orderedStages.push({ stage: stages[groupIdx], originalIndex: groupIdx, group: sameStartGroup });
                            processedIndices.add(groupIdx);
                        }
                    });
                } else {
                    orderedStages.push({ stage: stages[idx], originalIndex: idx, group: null });
                    processedIndices.add(idx);
                }
            });
            
            let stagesHTML = '';
            let previousGroup = null;
            let groupHTML = '';
            let isInGroup = false;
            
            orderedStages.forEach((stageData, displayIndex) => {
                const stage = stageData.stage;
                const index = stageData.originalIndex;
                const currentGroup = stageData.group;
                
                const isCompleted = stage.status === 'completed';
                const isActive = stage.status === 'in-progress';
                
                const hasSameStart = currentGroup && currentGroup.length > 1;
                const isFirstInGroup = hasSameStart && currentGroup.indexOf(index) === 0;
                const isLastInGroup = hasSameStart && currentGroup.indexOf(index) === currentGroup.length - 1;
                
                if (isFirstInGroup) {
                    isInGroup = true;
                    groupHTML = '<div class="stage-group-container">';
                }
                
                let spacingClass = 'normal-spacing';
                if (hasSameStart) {
                    spacingClass = currentGroup.length >= 3 ? 'tight-spacing' : 'medium-spacing';
                }

                let groupBadge = '';
                if (hasSameStart) {
                    const position = currentGroup.indexOf(index) + 1;
                    const total = currentGroup.length;
                    // groupBadge = `<span class="parallel-badge">${position}/${total}</span>`;  // ← COMMENTED OUT
                }
                                
                    let circleContent;
                    if (isCompleted) {
                        circleContent = '<i class="fas fa-check"></i>';
                    } else {
                    circleContent = '';                    
                    }                
                    const stageElement = `
                        <div class="progress-step ${spacingClass}" data-stage-id="${stage.id}" 
                            data-project-id="${project.id}" 
                            data-in-parallel="${hasSameStart ? 'true' : 'false'}"
                            data-stage-status="${stage.status}">
                            <div class="step-circle ${isCompleted ? 'completed' : ''} ${isActive ? 'in-progress' : ''}" 
                                 style="cursor: pointer;"
                                 title="Left-click: Advance status | Right-click: Undo status">
                                ${circleContent}
                            </div>
                        <div class="step-label ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}">
                            ${stage.name}
                            <span class="duration-badge">${stage.duration_days}d</span>
                            ${groupBadge}
                        </div>
                ${stage.start_date ? `
                    <div style="margin-top: 5px; text-align: center;">
                        <small class="text-muted" style="font-size: 0.7rem; display: block; line-height: 1.4;">
                            ${new Date(stage.start_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}
                            ${stage.end_date ? '<br>' + new Date(stage.end_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'}) : ''}
                        </small>
                    </div>
                ` : ''}                   
                </div>
                `;
                
                if (isInGroup) {
                    groupHTML += stageElement;
                } else {
                    stagesHTML += stageElement;
                }
                
                if (isLastInGroup) {
                    groupHTML += '</div>';
                    stagesHTML += groupHTML;
                    groupHTML = '';
                    isInGroup = false;
                }
                
                previousGroup = currentGroup;
            });
            
            const membersHTML = project.members && project.members.length > 0 
                ? project.members.slice(0, 3).map(m => `<span class="badge bg-info me-1"><i class="fas fa-user me-1"></i>${m.username}</span>`).join('') + 
                (project.members.length > 3 ? `<span class="badge bg-secondary">+${project.members.length - 3}</span>` : '')
                : '<span class="text-muted small">No members</span>';
            
            return `
                <div class="project-progress-container">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <div class="d-flex align-items-center gap-2 mb-2">
                                <h5 class="mb-0">${project.name}</h5>
                                <span class="project-status-badge status-${project.status}">
                                    ${project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                                </span>
                            </div>
                            <div class="mt-1">${membersHTML}</div>
                        </div>
                        <div class="project-actions">
                            <button class="btn btn-outline-success" onclick="showExcelPreview(${project.id})"                                   
                            style="border-radius: 8px; font-weight: 600; padding: 8px 16px;">
                                <i class="fas fa-file-excel me-2"></i> Export to Excel
                            </button>                            
                            <button class="btn btn-outline-primary" onclick="openCalendarView(${project.id})" 
                                    style="border-radius: 8px; font-weight: 600; padding: 8px 16px;">
                                <i class="fas fa-calendar-alt me-2"></i> View Calendar
                            </button>
                            <button class="btn btn-outline-warning" onclick="openEditProjectModal(${project.id}, event)" 
                                    style="border-radius: 8px; font-weight: 600; padding: 8px 16px;">
                                <i class="fas fa-edit me-2"></i> Edit
                            </button>
                            <button class="btn-delete-project" onclick="deleteProject(${project.id}, event)">
                                <i class="fas fa-trash-alt me-2"></i> Delete
                            </button>
                        </div>                        
                    </div>
                    
                    <p class="text-muted small">${project.description || 'No description'}</p>
                    
                    <div class="progress-steps">
                        <div class="progress-line">
                            <div class="progress-line-fill" style="width: ${progress}%"></div>
                        </div>
                        ${stagesHTML}
                    </div>
                    
                    <div class="d-flex justify-content-between align-items-center mt-3">
                        <small class="text-muted">
                            <i class="fas fa-calendar-alt me-1"></i>
                            ${project.start_date ? new Date(project.start_date).toLocaleDateString() : 'Not set'} - 
                            ${project.end_date ? new Date(project.end_date).toLocaleDateString() : 'Not set'}
                        </small>
                        <strong style="color: #667eea; font-size: 1.1rem;">${progress}% Complete (${completedStages}/${totalStages})</strong>
                    </div>
                </div>
            `;
        }).join('');
        
setTimeout(() => {
    document.querySelectorAll('.progress-steps').forEach(progressContainer => {
        const line = progressContainer.querySelector('.progress-line');
        
        // Get all top-level steps (including group containers)
        const directChildren = Array.from(progressContainer.children).filter(
            child => child.classList.contains('progress-step') || 
                     child.classList.contains('stage-group-container')
        );
        
        if (line && directChildren.length > 0) {
            const firstChild = directChildren[0];
            const lastChild = directChildren[directChildren.length - 1];
            
            // For group containers, get the first circle inside
            const firstCircle = firstChild.classList.contains('stage-group-container') 
                ? firstChild.querySelector('.step-circle')
                : firstChild.querySelector('.step-circle');
                
            const lastCircle = lastChild.classList.contains('stage-group-container')
                ? lastChild.querySelector('.step-circle')
                : lastChild.querySelector('.step-circle');
            
            if (firstCircle && lastCircle) {
                const firstRect = firstCircle.getBoundingClientRect();
                const lastRect = lastCircle.getBoundingClientRect();
                const containerRect = progressContainer.getBoundingClientRect();
                
                const lineLeft = firstRect.left - containerRect.left + 25;
                const lineRight = lastRect.left - containerRect.left + 25;
                const lineWidth = lineRight - lineLeft;
                
                line.style.left = `${lineLeft}px`;
                line.style.width = `${lineWidth}px`;
                line.style.right = 'auto';
            }
        }
    });
}, 100);
    
    // Update progress line status for each project
// Update progress line status for each project
    projectsData.forEach(project => {
        startProgressLineAutoRefresh(project.id);
    });
    
    // ✅ Setup parallel stage click handlers - DISABLED (circles now have direct onclick)
    // setTimeout(() => {
    //     setupParallelStageClickHandlers();
    // }, 100);

}
    async function loadEmployees() {
        const response = await fetch('/api/employees');
        employees = await response.json();
        const select = document.getElementById('memberSelect');
        select.innerHTML = '<option value="">Select member to add...</option>' + 
            employees.map(e => `<option value="${e.id}">${e.username} (${e.role})</option>`).join('');
    }

    // UPDATED FUNCTION: Handle project submit with working Saturdays
async function handleProjectSubmit(e) {
    e.preventDefault();
    
    // ✅ STEP 1: Collect current form data
    const stages = [];
    const stageElements = document.querySelectorAll('[id^="stage-"]');
    
    stageElements.forEach((element, index) => {
        const id = element.id.split('-')[1];
        const checkbox = document.getElementById(`stageCheck-${id}`);
        
        if (!checkbox || !checkbox.checked) return;
        
        const name = document.getElementById(`stageName-${id}`)?.value;
        const duration = parseInt(document.getElementById(`stageDuration-${id}`)?.value) || 1;
        const managerId = parseInt(document.getElementById(`stageManager-${id}`)?.value) || null;
        const startDateInput = document.getElementById(`stageStartDate-${id}`);
        const customStartDate = startDateInput?.value || null;
        const isCustomDate = startDateInput?.getAttribute('data-is-custom') === 'true';
        
        if (name) {
            const stageData = { 
                name,  // This will REPLACE the old name
                order: stages.length + 1,
                duration_days: duration,  // This will REPLACE the old duration
                manager_id: managerId  // This will REPLACE the old manager
            };
            
            // ✅ Include custom start date if user set one
            if (isCustomDate && customStartDate) {
                stageData.start_date = customStartDate;
            }
            
            // ✅ Include the database ID so backend knows to UPDATE (not create new)
            const dbId = element.getAttribute('data-db-id');
            if (dbId) {
                stageData.id = parseInt(dbId);  // This tells backend "update this record"
            }
            
            stages.push(stageData);
        }
    });
    
    // ✅ STEP 2: Determine if editing or creating
    const wasEditMode = isEditMode;
    const projectIdBeingEdited = editingProjectId;
    
    // ✅ STEP 3: Prepare data to send
    const data = {
        name: document.getElementById('projectName').value,
        start_date: document.getElementById('projectStartDate').value,
        stages,  // This REPLACES all the old stages
        members: selectedMembers,
        include_saturday: includeSaturdayAsWorkingDay,
        working_saturdays: Array.from(workingSaturdays),
        is_direct_edit: wasEditMode
    };
    
    // ✅ STEP 4: Send to backend - PUT for update, POST for create
    const url = wasEditMode ? `/api/projects/${projectIdBeingEdited}` : '/api/projects';
    const method = wasEditMode ? 'PUT' : 'POST';  // PUT = update existing
    
    console.log('🚀 Sending request:', { url, method, data });
    
    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)  // Send the new data
    });
    
    console.log('📡 Response status:', response.status);
    
    if (response.ok) {
        const result = await response.json();
        console.log('✅ Server response:', result);
        
        // ✅ CLOSE THE MODAL
        projectModal.hide();
        
        // ✅ RESET THE FORM
        resetProjectForm();
        
        showNotification(wasEditMode ? '✅ Job updated successfully!' : '✅ Job created successfully!', 'success');
        
        // Check if calendar modal is open BEFORE clearing data
        const calendarModalEl = document.getElementById('calendarModal');
        const wasCalendarOpen = calendarModalEl && calendarModalEl.classList.contains('show');
        const projectIdForRefresh = wasCalendarOpen ? currentProjectForCalendar : null;
        
        // Wait for modal to close
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Reload to show updated data
        await loadProjects();
        await loadStats();
        
        // ✅ REFRESH CALENDAR VIEW IF IT WAS OPEN - IMPROVED VERSION
        if (wasCalendarOpen && projectIdForRefresh) {
            console.log('🔄 Calendar was open - forcing complete refresh for project:', projectIdForRefresh);
            
            // Wait a bit more to ensure database is updated
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Force complete calendar rebuild
            currentProjectForCalendar = projectIdForRefresh;
            
            // Destroy existing calendar if it exists
            if (calendar) {
                try {
                    calendar.destroy();
                    calendar = null;
                    console.log('🗑️ Destroyed old calendar');
                } catch (e) {
                    console.warn('Could not destroy calendar:', e);
                }
            }
            
            // Clear the calendar container COMPLETELY
            const calendarEl = document.getElementById('calendar');
            if (calendarEl) {
                // Remove all content and classes
                calendarEl.innerHTML = '';
                calendarEl.className = '';
                // Force browser to recalculate layout
                calendarEl.offsetHeight; // Trigger reflow
                console.log('🧹 Cleared calendar DOM');
            }
            
            // Extra wait to ensure DOM is clean
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Reopen calendar view with fresh data
            await openCalendarView(projectIdForRefresh);
            
            console.log('✅ Calendar refreshed with updated data');
        }
        
        // Clear cached data AFTER calendar refresh
        window.originalProjectData = null;
        currentProjectData = null;
    } else {
        // ✅ SHOW ACTUAL ERROR
        const errorData = await response.json();
        console.error('❌ Server error:', errorData);
        showNotification('❌ Error: ' + (errorData.error || 'Failed to save changes'), 'error');
    }
}

async function updateStageStatus(projectId, stageId, currentStatus) {
    try {
        // Determine next status
        const newStatus = currentStatus === 'pending' ? 'in-progress' : 
                         currentStatus === 'in-progress' ? 'completed' : 'pending';
        
        // Update the status on the server
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update stage status');
        }
        
        // ✅ FIX: Find and update the specific stage (works for both regular and parallel)
        const stageElement = document.querySelector(`[data-stage-id="${stageId}"]`);
        
        if (stageElement) {
            const circle = stageElement.querySelector('.step-circle');
            const label = stageElement.querySelector('.step-label');
            
            // ✅ UPDATE THE DATA ATTRIBUTE SO RIGHT-CLICK WORKS
            stageElement.setAttribute('data-stage-status', newStatus);
            
            // ✅ SAVE original content BEFORE any changes
            if (!circle.dataset.originalNumber) {
                const circleText = circle.textContent.trim();
                if (circleText && !isNaN(circleText)) {
                    circle.dataset.originalNumber = circleText;
                }
            }
            
            // Remove all status classes
            circle.classList.remove('completed', 'active', 'not-started', 'in-progress', 'overdue', 'completed-rescheduled');
            label.classList.remove('completed', 'active');
            
            // Apply new status
            if (newStatus === 'completed') {
                circle.classList.add('completed');
                label.classList.add('completed');
                circle.innerHTML = '<i class="fas fa-check"></i>';
            } else if (newStatus === 'in-progress') {
                circle.classList.add('in-progress');
                label.classList.add('active');
                // ✅ Restore from saved original number
                circle.textContent = circle.dataset.originalNumber || '';
            } else {
                // Reset to pending
                circle.classList.add('not-started');
                // ✅ Restore from saved original number
                circle.textContent = circle.dataset.originalNumber || '';
            }
        }
        
        // Update progress line and percentage
        updateProgressLineFill(projectId);
        
        // Refresh progress line status with new colors
        await updateProgressLineStatus(projectId);
        
        // Only update stats (lightweight)
        await loadStats();
        
    } catch (error) {
        console.error('Error updating stage status:', error);
        // Only reload if there's an error
        await loadProjects();
        await loadStats();
    }
}
// ✅ NEW FUNCTION: Undo stage status (right-click support)
async function undoStageStatus(projectId, stageId, previousStatus) {
    try {
        console.log(`Undoing stage ${stageId} to status: ${previousStatus}`);
        
        // Update the status on the server to previous state
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: previousStatus })
        });
        
        if (!response.ok) {
            throw new Error('Failed to undo stage status');
        }
        
        // Find and update the specific stage
        const stageElement = document.querySelector(`[data-stage-id="${stageId}"]`);
        
        if (stageElement) {
            const circle = stageElement.querySelector('.step-circle');
            const label = stageElement.querySelector('.step-label');
            
            // ✅ UPDATE THE DATA ATTRIBUTE SO RIGHT-CLICK CONTINUES TO WORK
            stageElement.setAttribute('data-stage-status', previousStatus);
            
            // ✅ SAVE original content BEFORE any changes
            if (!circle.dataset.originalNumber) {
                const circleText = circle.textContent.trim();
                if (circleText && !isNaN(circleText)) {
                    circle.dataset.originalNumber = circleText;
                }
            }
            
            // Remove all status classes
            circle.classList.remove('completed', 'active', 'not-started', 'in-progress', 'overdue', 'completed-rescheduled');
            label.classList.remove('completed', 'active');
            
            // Apply previous status
            if (previousStatus === 'completed') {
                circle.classList.add('completed');
                label.classList.add('completed');
                circle.innerHTML = '<i class="fas fa-check"></i>';
            } else if (previousStatus === 'in-progress') {
                circle.classList.add('in-progress');
                label.classList.add('active');
                // ✅ Restore from saved original number
                circle.textContent = circle.dataset.originalNumber || '';
            } else {
                // Reset to pending
                circle.classList.add('not-started');
                // ✅ Restore from saved original number
                circle.textContent = circle.dataset.originalNumber || '';
            }
        }
        
        // Update progress line and percentage
        updateProgressLineFill(projectId);
        
        // Refresh progress line status with new colors
        await updateProgressLineStatus(projectId);
        
        // Update stats
        await loadStats();
        
        showNotification('Status reverted successfully', 'success');
        
    } catch (error) {
        console.error('Error undoing stage status:', error);
        showNotification('Error undoing status: ' + error.message, 'error');
        // Reload on error
        await loadProjects();
        await loadStats();
    }
}
// ✅ ADD THIS NEW HELPER FUNCTION (add it right after updateStageStatus)
function updateProgressLineFill(projectId) {
    const projectContainers = document.querySelectorAll('.project-progress-container');
    
    projectContainers.forEach(container => {
        const editBtn = container.querySelector(`[onclick*="openEditProjectModal(${projectId}"]`);
        if (editBtn) {
            const steps = container.querySelectorAll('.progress-step');
            const completedSteps = container.querySelectorAll('.step-circle.completed').length;
            const totalSteps = steps.length;
            const progress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;
            
            // Update progress line fill
            const progressFill = container.querySelector('.progress-line-fill');
            if (progressFill) {
                progressFill.style.width = `${progress}%`;
            }
            
            // Update progress percentage text
            const progressText = container.querySelector('strong[style*="color: #667eea"]');
            if (progressText) {
                progressText.textContent = `${Math.round(progress)}% Complete (${completedSteps}/${totalSteps})`;
            }
        }
    });
}
function openProjectModal() {
    document.getElementById('projectForm').reset();
    document.getElementById('projectStartDate').valueAsDate = new Date();
    workingSaturdays.clear();
    loadDefaultStages();
    projectModal.show();
}

function toggleNotifications() {
    alert('Notifications feature');
}

async function deleteProject(projectId, event) {
    event.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/projects/${projectId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('✅ Job deleted successfully!', 'success');
            await loadProjects();
            await loadStats();
        } else {
            const error = await response.json();
            showNotification('❌ Error: ' + (error.error || 'Failed to delete job'), 'error');
        }
    } catch (error) {
        console.error('Error deleting job:', error);
        showNotification('❌ Error deleting job: ' + error.message, 'error');
    }
}

function getStageColor(index) {
    return STAGE_COLORS[index % STAGE_COLORS.length];
}

let miniPopupData = null;

// ✅ NEW FUNCTION - Dynamic Layout Calculator
function calculateOptimalCalendarLayout(stages) {
    console.log('📐 Calculating optimal calendar layout...');
    
    // Step 1: Build a map of dates to stage counts
    const dateStageMap = new Map();
    let maxStagesPerDay = 0;
    
    stages.forEach((stage, idx) => {
        if (!stage.start_date || !stage.end_date) return;
        
        const start = new Date(stage.start_date);
        const end = new Date(stage.end_date);
        
        // Count stages for each date
        for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
            const dateKey = d.toISOString().split('T')[0];
            const count = (dateStageMap.get(dateKey) || 0) + 1;
            dateStageMap.set(dateKey, count);
            maxStagesPerDay = Math.max(maxStagesPerDay, count);
        }
    });
    
    console.log(`📊 Max stages per day: ${maxStagesPerDay}`);
    
    // Step 2: Calculate optimal heights
    const baseEventHeight = 24; // pixels per event
    const cellPadding = 20; // top/bottom padding
    const minCellHeight = 80; // minimum cell height
    
    const optimalCellHeight = Math.max(
        minCellHeight,
        (maxStagesPerDay * baseEventHeight) + cellPadding
    );
    
    console.log(`✅ Optimal cell height: ${optimalCellHeight}px`);
    
    return {
        maxStagesPerDay,
        optimalCellHeight,
        dateStageMap
    };
}

// ✅ NEW FUNCTION - Apply Dynamic Styles
function applyDynamicCalendarStyles(layoutInfo) {
    const { optimalCellHeight, maxStagesPerDay } = layoutInfo;
    
    // Remove existing dynamic styles
    const existingStyle = document.getElementById('dynamic-calendar-styles');
    if (existingStyle) {
        existingStyle.remove();
    }
    
    // Create new style element
    const style = document.createElement('style');
    style.id = 'dynamic-calendar-styles';
    
    // Dynamic CSS based on layout analysis
    style.textContent = `
        /* Dynamic cell height based on stage count */
        .fc-daygrid-day-frame {
            min-height: ${optimalCellHeight}px !important;
        }
        
        /* Adjust event spacing for dense layouts */
        .fc-daygrid-event-harness {
            margin-bottom: ${maxStagesPerDay > 5 ? '2px' : '4px'} !important;
        }
        
        /* Event font size adjustment for dense layouts */
        .fc-event-title {
            font-size: ${maxStagesPerDay > 7 ? '0.7rem' : '0.75rem'} !important;
            line-height: 1.2 !important;
        }
        
        /* Compact padding for dense layouts */
        .fc-daygrid-event {
            padding: ${maxStagesPerDay > 5 ? '1px 3px' : '2px 4px'} !important;
        }
        
        /* Adjust day number position for better visibility */
        .fc-daygrid-day-number {
            font-size: ${maxStagesPerDay > 7 ? '0.8rem' : '0.9rem'} !important;
            padding: 4px !important;
        }
    `;
    
    document.head.appendChild(style);
    console.log('✅ Applied dynamic calendar styles');
}



async function openCalendarView(projectId) {
    currentProjectForCalendar = projectId;
    
    // Clean up any existing calendar first
    if (calendar) {
        console.log('🗑️ Destroying existing calendar before opening new one');
        calendar.destroy();
        calendar = null;
    }
    
    // Stop any existing auto-refresh
    stopAllProgressLineAutoRefresh();
    
    try {
        // Fetch project details
        const response = await fetch(`/api/projects/${projectId}/details?_t=${Date.now()}`, {
            cache: 'no-store',
            headers: {'Cache-Control': 'no-cache'}
        });
        currentProjectData = await response.json();
        
        // ✅ CRITICAL: ALWAYS fetch complete reschedule history (including daily tasks)
        const timestamp = Date.now();
        const historyResponse = await fetch(`/api/projects/${projectId}/complete-reschedule-history?_t=${timestamp}`);
        if (historyResponse.ok) {
            const historyData = await historyResponse.json();
            currentProjectData.rescheduleHistory = historyData;
            console.log('✅ Loaded complete reschedule history:', historyData.length, 'records');
            console.log('History details:', historyData);
        } else {
            console.warn('⚠️ Failed to load reschedule history');
            currentProjectData.rescheduleHistory = [];
        }  
              
        // Initialize saturdayWorkingDays
        if (!currentProjectData.saturdayWorkingDays) {
            currentProjectData.saturdayWorkingDays = new Set();
        } else if (Array.isArray(currentProjectData.saturdayWorkingDays)) {
            currentProjectData.saturdayWorkingDays = new Set(currentProjectData.saturdayWorkingDays);
        }
        
        console.log('Working Saturdays loaded:', Array.from(currentProjectData.saturdayWorkingDays));
        console.log('Reschedule History loaded:', currentProjectData.rescheduleHistory);
        
        // ✅ STEP 1: Analyze layout BEFORE creating calendar
        const layoutInfo = calculateOptimalCalendarLayout(currentProjectData.stages);
        
        // ✅ STEP 2: Apply dynamic styles
        applyDynamicCalendarStyles(layoutInfo);
        
        document.getElementById('calendarProjectTitle').textContent = `${currentProjectData.name}`;
        document.getElementById('calendarProjectDates').textContent = 
            `${new Date(currentProjectData.start_date).toLocaleDateString()} - ${new Date(currentProjectData.end_date).toLocaleDateString()}`;
        
        // Show modal first
        calendarModal.show();
        
        // Update progress line status
        updateProgressLineStatus(projectId);
        startProgressLineAutoRefresh(projectId);
        
        // Wait for modal to be fully shown
        setTimeout(async () => {
            const calendarEl = document.getElementById('calendar');
            
            // Clear any existing calendar thoroughly
            if (calendar) {
                calendar.destroy();
                calendar = null;
                console.log('🗑️ Previous calendar destroyed');
            }
            
            // Clear the calendar element's innerHTML to ensure clean slate
            calendarEl.innerHTML = '';
            
            // ✅ Generate events with ghost events
            const calendarEvents = await generateEnhancedCalendarEvents(currentProjectData.stages);
            
            console.log('📊 Total calendar events generated:', calendarEvents.length);
            console.log('👻 Ghost events:', calendarEvents.filter(e => e.classNames?.includes('ghost-event')).length);
            
            // Create new calendar
            calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'dayGridMonth',
                initialDate: currentProjectData.start_date,
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,listMonth'
                },                
                height: 'auto',
                contentHeight: 'auto',  // Let it expand as needed for all events
                // ✅ CRITICAL FIX: Use function instead of static array so refetchEvents() works
                events: async function(fetchInfo, successCallback, failureCallback) {
                    try {
                        console.log('🔄 Fetching fresh calendar events...');
                        const freshEvents = await generateEnhancedCalendarEvents(currentProjectData.stages);
                        console.log('✅ Generated', freshEvents.length, 'events');
                        successCallback(freshEvents);
                    } catch (error) {
                        console.error('❌ Error generating events:', error);
                        failureCallback(error);
                    }
                },
                eventOrder: 'start,-duration,title',  // Order by start date FIRST, then by duration (longer first), then by title
                eventMaxStack: layoutInfo.maxStagesPerDay + 2,  // ✅ DYNAMIC: Adjust based on layout complexity
                dayMaxEvents: false,  // Show ALL events without "+more" links - THIS IS KEY
                dayMaxEventRows: false,  // Don't limit the number of event rows per day
                showNonCurrentDates: false,  // Hide dates from other months
                fixedWeekCount: false,  // Don't show 6 weeks if month is shorter
                editable: true,  // Enable drag and drop editing
                eventClick: function(info) {
                    // ✅ Don't allow clicking ghost events
                    if (info.event.extendedProps.isGhost) {
                        const props = info.event.extendedProps;
                        let message = `Original Location\n\n`;
                        
                        if (props.type === 'daily_task') {
                            message += `Stage: ${props.stageName}\n`;
                            message += `Day: ${props.dayNumber}\n`;
                        } else {
                            message += `Stage: ${props.stageName}\n`;
                        }
                        
                        message += `Moved ${props.daysShifted} day(s) ${props.direction}\n`;
                        message += `New location: ${new Date(props.movedTo).toLocaleDateString()}`;
                        
                        alert(message);
                        return;
                    }
                    handleStageClickReschedule(info, currentProjectData);
                },
                // ✅ FIX: Handle event drag/drop - refresh calendar layout
                eventDrop: async function(info) {
                    console.log('📌 Event dropped, updating layout...');
                    try {
                        // Update backend if needed (you can add your API call here)
                        // await fetch(...);
                        
                        // ✅ Reload fresh project data
                        const response = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${Date.now()}`, {
                            cache: 'no-store',
                            headers: {'Cache-Control': 'no-cache'}
                        });
                        if (response.ok) {
                            const freshData = await response.json();
                            // Update stages with fresh data
                            currentProjectData.stages = freshData.stages;
                            
                            // ✅ RECALCULATE AND REAPPLY LAYOUT
                            const newLayoutInfo = calculateOptimalCalendarLayout(freshData.stages);
                            applyDynamicCalendarStyles(newLayoutInfo);
                            
                            console.log('✅ Loaded fresh project data');
                        }
                        
                        // ✅ CRITICAL: Refresh the calendar to fix layout
                        setTimeout(() => {
                            if (calendar) {
                                calendar.refetchEvents();
                                calendar.updateSize();
                                calendar.render();
                                console.log('✅ Calendar layout refreshed after drop');
                            }
                        }, 100);
                    } catch (error) {
                        console.error('Error updating event:', error);
                        info.revert(); // Revert if error
                    }
                },
                // ✅ FIX: Handle event resize - refresh calendar layout
                eventResize: async function(info) {
                    console.log('📏 Event resized, updating layout...');
                    try {
                        // Update backend if needed (you can add your API call here)
                        // await fetch(...);
                        
                        // ✅ Reload fresh project data
                        const response = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${Date.now()}`, {
                            cache: 'no-store',
                            headers: {'Cache-Control': 'no-cache'}
                        });
                        if (response.ok) {
                            const freshData = await response.json();
                            // Update stages with fresh data
                            currentProjectData.stages = freshData.stages;
                            
                            // ✅ RECALCULATE AND REAPPLY LAYOUT
                            const newLayoutInfo = calculateOptimalCalendarLayout(freshData.stages);
                            applyDynamicCalendarStyles(newLayoutInfo);
                            
                            console.log('✅ Loaded fresh project data');
                        }
                        
                        // ✅ CRITICAL: Refresh the calendar to fix layout
                        setTimeout(() => {
                            if (calendar) {
                                calendar.refetchEvents();
                                calendar.updateSize();
                                calendar.render();
                                console.log('✅ Calendar layout refreshed after resize');
                            }
                        }, 100);
                    } catch (error) {
                        console.error('Error updating event:', error);
                        info.revert(); // Revert if error
                    }
                },
                dayCellDidMount: function(info) {
                    addDayRescheduleButton(info, currentProjectData);
                },
                eventDisplay: 'block',
                displayEventTime: false,
                eventDidMount: function(info) {
                    enhanceEventDisplay(info);
                },
                datesSet: function() {
                    // ✅ When month changes, refresh badges
                    setTimeout(() => {
                        refreshParallelBadges();
                    }, 200);
                }
            });
            
            calendar.render();
            
            // ✅ FORCE LAYOUT RECALCULATION - Critical for fixing messy overlaps
            setTimeout(() => {
                if (calendar) {
                    // Force FullCalendar to recalculate dimensions and event positions
                    calendar.updateSize();
                    // Force re-render to recalculate event layout
                    calendar.render();
                    console.log('🔄 Forced layout recalculation');
                }
            }, 150);
            
            // ✅ Apply enhancements after render INCLUDING badge refresh
            setTimeout(() => {
                enhanceCalendarWithWeekends();
                generateEnhancedLegend(currentProjectData.stages);
                refreshParallelBadges(); // ✅ ADDED: Refresh badges on initial load
            }, 500); // ✅ Increased timeout from 300ms to 500ms
        }, 300);
        
    } catch (error) {
        console.error('Error loading calendar:', error);
        showNotification('❌ Failed to open calendar: ' + error.message, 'error');
        // Close the modal if it was opened
        if (typeof calendarModal !== 'undefined' && calendarModal) {
            try {
                calendarModal.hide();
            } catch (e) {
                console.warn('Could not hide calendar modal:', e);
            }
        }
    }
}

async function generateEnhancedCalendarEvents(stages) {
    const events = [];
    const dateStageMap = new Map();
    
    // Ensure saturdayWorkingDays is always a Set
    if (!currentProjectData.saturdayWorkingDays) {
        currentProjectData.saturdayWorkingDays = new Set();
    } else if (Array.isArray(currentProjectData.saturdayWorkingDays)) {
        currentProjectData.saturdayWorkingDays = new Set(currentProjectData.saturdayWorkingDays);
    } else if (!(currentProjectData.saturdayWorkingDays instanceof Set)) {
        try {
            currentProjectData.saturdayWorkingDays = new Set(JSON.parse(currentProjectData.saturdayWorkingDays));
        } catch (e) {
            currentProjectData.saturdayWorkingDays = new Set();
        }
    }
    
    
        console.log('=== Generating Calendar Events ===');
        console.log('Working Saturdays:', Array.from(currentProjectData.saturdayWorkingDays));
        console.log('Reschedule History:', currentProjectData.rescheduleHistory?.length || 0, 'records');    
    // Helper function to check if date is working day
    function isWorkingDay(date) {
        const day = date.getDay();
        const dateStr = date.toISOString().split('T')[0];
        
        if (day === 0) return false;
        if (day === 6) {
            const isWorking = currentProjectData.saturdayWorkingDays.has(dateStr);
            return isWorking;
        }
        return true;
    }
    
if (currentProjectData.rescheduleHistory && currentProjectData.rescheduleHistory.length > 0) {
    console.log('\n=== Adding Ghost Events ===');
    console.log('Total history records:', currentProjectData.rescheduleHistory.length);
    
try {
        currentProjectData.rescheduleHistory.forEach(history => {
            const stage = stages.find(s => s.id === history.stage_id);
            if (!stage) {
                console.warn('⚠️ Stage not found for history:', history);
                return;
            }
            
            const index = stages.indexOf(stage);
            const color = getStageColor(index);
            
            // ✅ Determine ghost event title based on type
            let ghostTitle = '';
            let tooltipText = '';
            
            if (history.type === 'daily_task') {
                // For daily tasks, show "Stage Name - Day X"
                ghostTitle = `⇢ ${history.stage_name} - Day ${history.day_number}`;
                
                tooltipText = `📍 Original Location\n`;
                tooltipText += `━━━━━━━━━━━━━\n`;
                tooltipText += `Stage: ${history.stage_name}\n`;
                tooltipText += `Day: ${history.day_number}\n`;
                tooltipText += `Moved ${history.days_shifted} day(s) ${history.direction}\n`;
                tooltipText += `➡️ New date: ${new Date(history.new_date).toLocaleDateString()}`;
                if (history.reason) {
                    tooltipText += `\n💬 Reason: ${history.reason}`;
                }
                
                console.log(`  ✔️ Daily task ghost: ${history.stage_name} Day ${history.day_number} at ${history.original_date} → ${history.new_date}`);
            } else {
                // For stage-level reschedules
                ghostTitle = `⇢ ${history.stage_name}`;
                
                tooltipText = `📍 Original Location\n`;
                tooltipText += `━━━━━━━━━━━━━\n`;
                tooltipText += `Stage: ${history.stage_name}\n`;
                tooltipText += `Moved ${history.days_shifted} day(s) ${history.direction}\n`;
                tooltipText += `➡️ New date: ${new Date(history.new_date).toLocaleDateString()}`;
                if (history.reason) {
                    tooltipText += `\n💬 Reason: ${history.reason}`;
                }
                
                console.log(`  ✔️ Stage ghost: ${history.stage_name} at ${history.original_date} → ${history.new_date}`);
            }            
            // ✅ Create ghost event at ORIGINAL location
            const ghostEvent = {
                title: ghostTitle,
                start: history.original_date,
                end: history.original_date, // Single day indicator
                backgroundColor: color,
                borderColor: color,
                classNames: ['ghost-event'],
                extendedProps: {
                    isGhost: true,
                    type: history.type,
                    stageId: history.stage_id,
                    stageName: history.stage_name,
                    dayNumber: history.day_number || null,
                    movedTo: history.new_date,
                    daysShifted: history.days_shifted,
                    direction: history.direction,
                    reason: history.reason,
                    rescheduledBy: history.rescheduled_by,
                    rescheduledAt: history.rescheduled_at,
                    tooltip: tooltipText
                }
            };
            
            events.push(ghostEvent);
        });
        
console.log(`=== Total ghost events created: ${currentProjectData.rescheduleHistory.length} ===\n`);
    } catch (error) {
        console.error('❌ Error creating ghost events:', error);
        // Continue anyway - don't let ghost event errors break the whole calendar
    }
}
    // ✅ STEP 2 - Process actual stage events (with daily tasks if available)
    for (const stage of stages) {
        const index = stages.indexOf(stage);
        
        try {
            const response = await fetch(`/api/projects/${currentProjectData.id}/stages/${stage.id}/daily-tasks`);
            
            if (response.ok) {
                const dailyTasks = await response.json();
                
                if (dailyTasks && dailyTasks.length > 0) {
                    console.log(`\n✔️ Using daily tasks for stage: "${stage.name}" (${dailyTasks.length} tasks)`);
                    
                    const color = getStageColor(index);
                    let segmentStart = null;
                    let lastDate = null;
                    let segmentTasks = [];
                    
                    dailyTasks.sort((a, b) => new Date(a.scheduled_date) - new Date(b.scheduled_date));
                    
                    const hasAnyRescheduled = dailyTasks.some(t => t.is_rescheduled);
                    
                    // ✅ Check if THIS stage was rescheduled (entire stage)
                    const stageRescheduleHistory = currentProjectData.rescheduleHistory?.find(h => h.stage_id === stage.id);
                    
                    dailyTasks.forEach((task, taskIdx) => {
                        const taskDate = new Date(task.scheduled_date + 'T12:00:00');
                        
                        const dateKey = taskDate.toISOString().split('T')[0];
                        if (!dateStageMap.has(dateKey)) {
                            dateStageMap.set(dateKey, []);
                        }
                        dateStageMap.get(dateKey).push({ stage, index });
                        
                        // ✅ NEW: If task is on HOLD, create a separate single-day event
                        if (task.status === 'hold') {
                            const holdStart = new Date(taskDate);
                            const holdEnd = new Date(taskDate);
                            holdEnd.setDate(holdEnd.getDate() + 1);
                            
                            events.push({
                                title: `🔒 ${stage.name} - Day ${task.day_number}`,
                                start: holdStart.toISOString().split('T')[0],
                                end: holdEnd.toISOString().split('T')[0],
                                backgroundColor: '#dc3545', // Red color
                                borderColor: '#dc3545',
                                classNames: ['event-hold'],
                                extendedProps: {
                                    stageId: stage.id,
                                    stageIndex: index,
                                    stageName: stage.name,
                                    status: 'hold',
                                    dayNumber: task.day_number,
                                    reason: task.rescheduled_reason || 'On hold'
                                }
                            });
                            
                            console.log(`  🔒 HOLD day created: ${stage.name} Day ${task.day_number} on ${dateKey}`);
                            return; // Skip adding to segment
                        }
                        
                        // Normal segment logic for non-HOLD tasks
                        if (!segmentStart) {
                            segmentStart = new Date(taskDate);
                            lastDate = new Date(taskDate);
                            segmentTasks = [task];
                        } else {
                            const nextDay = new Date(lastDate);
                            nextDay.setDate(nextDay.getDate() + 1);
                            
                            if (taskDate.getTime() !== nextDay.getTime()) {
                                const segmentEnd = new Date(lastDate);
                                segmentEnd.setDate(segmentEnd.getDate() + 1);
                                
                                console.log(`  ✔️ Daily task segment: ${segmentStart.toISOString().split('T')[0]} to ${segmentEnd.toISOString().split('T')[0]}`);
                                
                                events.push(createStageEventWithStatus(
                                    stage, 
                                    index, 
                                    segmentStart, 
                                    segmentEnd, 
                                    color, 
                                    dateStageMap,
                                    segmentTasks,
                                    hasAnyRescheduled,
                                    stageRescheduleHistory
                                ));
                                
                                segmentStart = new Date(taskDate);
                                segmentTasks = [task];
                            } else {
                                segmentTasks.push(task);
                            }
                            lastDate = new Date(taskDate);
                        }
                        
                        if (taskIdx === dailyTasks.length - 1 && segmentStart) {
                            const segmentEnd = new Date(lastDate);
                            segmentEnd.setDate(segmentEnd.getDate() + 1);
                            console.log(`  ✔️ Final daily task segment: ${segmentStart.toISOString().split('T')[0]} to ${segmentEnd.toISOString().split('T')[0]}`);
                            
                            events.push(createStageEventWithStatus(
                                stage, 
                                index, 
                                segmentStart, 
                                segmentEnd, 
                                color, 
                                dateStageMap,
                                segmentTasks,
                                hasAnyRescheduled,
                                stageRescheduleHistory
                            ));
                        }
                    })                    
                    continue;
                }
            }
        } catch (error) {
            console.log(`  ℹ️ No daily tasks for stage "${stage.name}", using default dates`);
        }
        
        // Fallback: Use original logic if no daily tasks
        if (!stage.start_date || !stage.end_date) {
            console.warn(`Stage "${stage.name}" missing dates`);
            continue;
        }
        
        const stageStart = new Date(stage.start_date);
        const stageEnd = new Date(stage.end_date);
        const color = getStageColor(index);
        
        // ✅ Check if THIS stage was rescheduled
        const stageRescheduleHistory = currentProjectData.rescheduleHistory?.find(h => h.stage_id === stage.id);
        
        console.log(`\nProcessing Stage: "${stage.name}" (using default dates)`);
        
        for (let d = new Date(stageStart); d <= stageEnd; d.setDate(d.getDate() + 1)) {
            const dateKey = d.toISOString().split('T')[0];
            if (!dateStageMap.has(dateKey)) {
                dateStageMap.set(dateKey, []);
            }
            dateStageMap.get(dateKey).push({ stage, index });
        }
        
        let segmentStart = null;
        let lastWorkingDate = null;
        
        for (let d = new Date(stageStart); d <= stageEnd; d.setDate(d.getDate() + 1)) {
            const currentDate = new Date(d);
            const isWorking = isWorkingDay(currentDate);
            
            if (isWorking) {
                if (!segmentStart) {
                    segmentStart = new Date(currentDate);
                }
                lastWorkingDate = new Date(currentDate);
            } else {
                if (segmentStart && lastWorkingDate) {
                    const segmentEnd = new Date(lastWorkingDate);
                    segmentEnd.setDate(segmentEnd.getDate() + 1);
                    
                    events.push(createStageEvent(
                        stage, 
                        index, 
                        segmentStart, 
                        segmentEnd, 
                        color, 
                        dateStageMap,
                        stageRescheduleHistory // ✅ Pass reschedule info
                    ));
                    
                    segmentStart = null;
                    lastWorkingDate = null;
                }
            }
        }
        
        if (segmentStart && lastWorkingDate) {
            const segmentEnd = new Date(lastWorkingDate);
            segmentEnd.setDate(segmentEnd.getDate() + 1);
            events.push(createStageEvent(
                stage, 
                index, 
                segmentStart, 
                segmentEnd, 
                color, 
                dateStageMap,
                stageRescheduleHistory // ✅ Pass reschedule info
            ));
        }
    }
    
    console.log(`\nGenerated ${events.length} total calendar events (including ghosts)`);
    console.log('=== Event Generation Complete ===\n');
    return events;
}


function createStageEvent(stage, index, start, end, color, dateStageMap, stageRescheduleHistory = null) {
    // Check for parallel stages
    let hasParallel = false;
    let parallelCount = 0;
    
    for (let d = new Date(start); d < end; d.setDate(d.getDate() + 1)) {
        const dateKey = d.toISOString().split('T')[0];
        const stagesOnDate = dateStageMap.get(dateKey) || [];
        if (stagesOnDate.length > 1) {
            hasParallel = true;
            parallelCount = Math.max(parallelCount, stagesOnDate.length);
        }
    }
    
    // Check entire project for overlaps
    if (currentProjectData && currentProjectData.stages) {
        const stageStart = new Date(stage.start_date);
        const stageEnd = new Date(stage.end_date);
        
        let overlapCount = 1;
        
        currentProjectData.stages.forEach((otherStage, otherIdx) => {
            if (otherStage.id === stage.id || !otherStage.start_date || !otherStage.end_date) return;
            
            const otherStart = new Date(otherStage.start_date);
            const otherEnd = new Date(otherStage.end_date);
            
            if (stageStart <= otherEnd && stageEnd >= otherStart) {
                hasParallel = true;
                overlapCount++;
            }
        });
        
        parallelCount = Math.max(parallelCount, overlapCount);
    }
    
    let title = stage.name;
    
    if (hasParallel) {
        title = `⚡ ${stage.name}`;
    }      
    const classNames = [];
    if (stage.status === 'completed') classNames.push('stage-event-completed');
    if (stage.status === 'in-progress') classNames.push('stage-event-active');
    
    // ✅ Build extended props with reschedule info
    const extendedProps = {
        stageId: stage.id,
        stageIndex: index,
        duration: stage.duration_days,
        status: stage.status,
        hasParallel: hasParallel,
        parallelCount: parallelCount,
        startDate: stage.start_date,
        endDate: stage.end_date,
        stageName: stage.name
    };
    
    // ✅ Add reschedule information if available
    if (stageRescheduleHistory) {
        extendedProps.wasRescheduled = true;
        extendedProps.daysShifted = stageRescheduleHistory.days_shifted || 
            Math.abs(Math.round((new Date(stageRescheduleHistory.new_date) - new Date(stageRescheduleHistory.original_date)) / (1000 * 60 * 60 * 24)));
        extendedProps.rescheduleDirection = stageRescheduleHistory.direction || 
            (new Date(stageRescheduleHistory.new_date) > new Date(stageRescheduleHistory.original_date) ? 'forward' : 'backward');
        extendedProps.rescheduleBadge = `${extendedProps.rescheduleDirection === 'forward' ? '+' : '-'}${extendedProps.daysShifted}d`;
        extendedProps.originalDate = stageRescheduleHistory.original_date;
    }

    return {
        title: title,
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0],
        backgroundColor: color,
        borderColor: color,
        extendedProps: extendedProps,
        classNames: classNames
    };
}
// Create tooltip element once (add this BEFORE enhanceEventDisplay function)
let tooltipElement = null;

function createTooltipElement() {
    if (!tooltipElement) {
        tooltipElement = document.createElement('div');
        tooltipElement.className = 'event-tooltip';
        tooltipElement.style.cssText = `
            position: fixed;
            background: rgba(44, 62, 80, 0.98);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            white-space: pre-line;
            font-size: 11.5px;
            line-height: 1.6;
            z-index: 999999;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            min-width: 180px;
            max-width: 300px;
            pointer-events: none;
            border: 1px solid rgba(255,255,255,0.1);
            display: none;
        `;
        document.body.appendChild(tooltipElement);
    }
    return tooltipElement;
}

function enhanceEventDisplay(info) {
    const props = info.event.extendedProps;
    
    info.el.style.setProperty('--event-color', info.event.backgroundColor);
    
    // Build tooltip content
    let tooltipText = '';
    let isGhost = false;
    
    // Ghost event handling
    if (props.isGhost) {
        isGhost = true;
        
        // ✅ Use pre-built tooltip if available, otherwise construct
        if (props.tooltip) {
            tooltipText = props.tooltip;
        } else {
                    tooltipText = `👻 Original Location\n`;
                    tooltipText += `━━━━━━━━━━━━━\n`;
                    
                    // ✅ Check if it's a daily task or stage-level reschedule
                    if (props.type === 'daily_task' && props.dayNumber) {
                        tooltipText += `Stage: ${props.stageName}\n`;
                        tooltipText += `Day: ${props.dayNumber}\n`;
                    } else {
                        tooltipText += `Stage: ${props.stageName}\n`;
                    }
                    
                    tooltipText += `Moved ${props.daysShifted} day(s) ${props.direction}\n`;
                    tooltipText += `➡️ New date: ${new Date(props.movedTo).toLocaleDateString()}`;
                    
                    if (props.reason) {
                        tooltipText += `\n💬 Reason: ${props.reason}`;
                    }
                }        
        info.el.style.cursor = 'help';
    } else {
        // Build tooltip for real events
        tooltipText = `${props.stageName}\n━━━━━━━━━━━━━\n`;
                tooltipText += `📅 ${props.duration} days\n`;
                
                if (props.completedCount > 0) {
                    tooltipText += `✅ ${props.completedCount}/${props.totalTasks} completed\n`;
                }
                
                if (props.rescheduledCount > 0) {
                    tooltipText += `🔄 ${props.rescheduledCount} day(s) rescheduled\n`;
                }
                
                // ✅ ADD: Show if entire stage was rescheduled
                if (props.wasRescheduled) {
                    tooltipText += `🔄 Stage shifted ${props.rescheduleBadge}\n`;
                }
                
                tooltipText += `📊 ${props.status}`;
            }    
    // Add hover events to show tooltip
    info.el.addEventListener('mouseenter', function(e) {
        const tooltip = createTooltipElement();
        tooltip.textContent = tooltipText;
        
        // Set background color based on type
        if (isGhost) {
            tooltip.style.background = 'rgba(255, 152, 0, 0.98)';
        } else {
            tooltip.style.background = 'rgba(44, 62, 80, 0.98)';
        }
        
        // Calculate position
        const rect = info.el.getBoundingClientRect();
        const tooltipX = rect.left + (rect.width / 2);
        
        // Show tooltip immediately
        tooltip.style.display = 'block';
        tooltip.style.left = tooltipX + 'px';
        tooltip.style.transform = 'translateX(-50%)';
        
        // Wait for next frame to position vertically
        setTimeout(() => {
            const tooltipHeight = tooltip.offsetHeight;
            let tooltipY;
            
            // Check if tooltip would go off top of screen
            if (rect.top - tooltipHeight - 20 < 10) {
                // Position below the event
                tooltipY = rect.bottom + 12;
            } else {
                // Position above the event
                tooltipY = rect.top - tooltipHeight - 12;
            }
            
            tooltip.style.top = tooltipY + 'px';
        }, 10);
    });
    
    // Hide tooltip on mouse leave
    info.el.addEventListener('mouseleave', function(e) {
        const tooltip = createTooltipElement();
        tooltip.style.display = 'none';
    });
    
    // Add duration badge (only for non-ghost events)
    if (!isGhost && props.duration) {
        const durationBadge = document.createElement('span');
        durationBadge.className = 'parallel-stage-indicator';
        durationBadge.textContent = `${props.duration}d`;
        info.el.appendChild(durationBadge);
    }
}
function addDayRescheduleButton(info, projectData) {
    const dateStr = info.date.toISOString().split('T')[0];
    const checkDate = new Date(dateStr + 'T12:00:00');
    const dayOfWeek = checkDate.getDay();
    
    // Don't show anything on Sundays (always holiday)
    if (dayOfWeek === 0) {
        return;
    }
    
    // Don't show anything on Saturdays that are holidays
    if (dayOfWeek === 6) {
        const isWorkingDay = projectData.saturdayWorkingDays && 
                            projectData.saturdayWorkingDays.has(dateStr);
        if (!isWorkingDay) {
            return;
        }
    }
    
    const stagesOnDay = projectData.stages.filter(stage => {
        if (!stage.start_date || !stage.end_date) return false;
        
        const stageStart = new Date(stage.start_date + 'T12:00:00');
        const stageEnd = new Date(stage.end_date + 'T12:00:00');
        
        return checkDate >= stageStart && checkDate <= stageEnd;
    });
    
    const dayFrame = info.el.querySelector('.fc-daygrid-day-frame');
    
    if (!dayFrame) {
        return;
    }
    
    // Add reschedule button only if there are stages
}

function showMiniReschedulePopup(date, stages, projectData, event) {
        const popup = document.getElementById('miniReschedulePopup');
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        
        document.getElementById('popupDate').textContent = dateStr;
        
        const stagesList = document.getElementById('popupStagesList');
        stagesList.innerHTML = stages.map((stage, idx) => {
            const color = getStageColor(projectData.stages.indexOf(stage));
            const isCompleted = stage.status === 'completed';
            const statusIcon = isCompleted ? '<i class="fas fa-check-circle text-success"></i>' : 
                              stage.status === 'in-progress' ? '<i class="fas fa-spinner text-warning"></i>' : '';
            
            return `
                <div class="stage-chip ${isCompleted ? 'opacity-50' : ''}" 
                     ${!isCompleted ? `onclick="handleStageRescheduleFromPopup(${projectData.id}, ${stage.id}, '${stage.name.replace(/'/g, "\\'")}', '${stage.start_date}', '${stage.end_date}')"` : ''}>
                    <div class="stage-chip-color" style="background: ${color};"></div>
                    <div class="stage-chip-name">${stage.name} ${statusIcon}</div>
                    ${!isCompleted ? `<button class="stage-chip-btn" onclick="event.stopPropagation(); handleStageRescheduleFromPopup(${projectData.id}, ${stage.id}, '${stage.name.replace(/'/g, "\\'")}', '${stage.start_date}', '${stage.end_date}');">Reschedule</button>` : ''}
                </div>
            `;
        }).join('');
        
        const rect = event.target.getBoundingClientRect();
        popup.style.left = `${Math.min(rect.left, window.innerWidth - 320)}px`;
        popup.style.top = `${rect.bottom + 10}px`;
        
        setTimeout(() => {
            const popupRect = popup.getBoundingClientRect();
            if (popupRect.bottom > window.innerHeight) {
                popup.style.top = `${rect.top - popupRect.height - 10}px`;
            }
        }, 10);
        
        popup.classList.add('active');
        
        setTimeout(() => {
            document.addEventListener('click', closeMiniPopupOutside);
        }, 100);
    }

    function closeMiniPopup() {
        const popup = document.getElementById('miniReschedulePopup');
        popup.classList.remove('active');
        document.removeEventListener('click', closeMiniPopupOutside);
    }

    function closeMiniPopupOutside(e) {
        const popup = document.getElementById('miniReschedulePopup');
        if (!popup.contains(e.target)) {
            closeMiniPopup();
        }
    }

    function handleStageRescheduleFromPopup(projectId, stageId, stageName, startDate, endDate) {
        closeMiniPopup();
        
        const color = getStageColor(currentProjectData.stages.findIndex(s => s.id === stageId));
        
        document.getElementById('rescheduleStageInfo').textContent = stageName;
        document.getElementById('rescheduleCurrentDates').textContent = 
            `${new Date(startDate).toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})} - ${new Date(endDate).toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})}`;
        document.getElementById('rescheduleStageColor').style.background = color;
        document.getElementById('rescheduleProjectId').value = projectId;
        document.getElementById('rescheduleStageId').value = stageId;
        document.getElementById('rescheduleStageStartDate').value = startDate;
        document.getElementById('rescheduleStageEndDate').value = endDate;
        document.getElementById('rescheduleDays').value = '';
        document.getElementById('rescheduleReason').value = '';
        document.getElementById('rescheduleNewDatesPreview').style.display = 'none';
        document.getElementById('rescheduleImpactWarning').style.display = 'none';
        
        rescheduleModal.show();
    }


function handleStageClickReschedule(info, project) {
    const stage = project.stages.find(s => s.id === info.event.extendedProps.stageId);
    
    if (!stage) return;
    
    // Show options: Reschedule entire stage OR manage daily tasks
    const choice = confirm(
        `Stage: ${stage.name}\n\n` +
        `Click OK to manage individual days\n` +
        `Click Cancel to reschedule entire stage`
    );
    
    if (choice) {
        // Open daily task manager
        openDailyTaskManager(project.id, stage.id, stage.name);
    } else {
        // Original behavior - reschedule entire stage
        if (stage.status === 'completed') {
            alert('Cannot reschedule a completed stage. Update its status first.');
            return;
        }
        
        handleStageRescheduleFromPopup(
            project.id, 
            stage.id, 
            stage.name, 
            stage.start_date, 
            stage.end_date
        );
    }
}

function generateEnhancedLegend(stages) {
    const legendContainer = document.getElementById('calendarLegend');
    
    const legendHTML = stages.map((stage, index) => {
        const color = getStageColor(index);
        
        let statusBadge = '';
        if (stage.status === 'completed') {
            statusBadge = '<span class="badge bg-success" style="font-size: 0.6rem; padding: 2px 4px;">✓</span>';
        } else if (stage.status === 'in-progress') {
            statusBadge = '<span class="badge bg-warning" style="font-size: 0.6rem; padding: 2px 4px;">⏱</span>';
        }        
        return `
            <div class="legend-item" style="border-left-color: ${color};">
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 4px;">
                    <div style="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <strong style="font-size: 0.75rem;">${stage.name}</strong>
                    </div>
                    ${statusBadge}
                </div>
                   <small style="font-size: 0.65rem; color: #6c757d;">
                    ${stage.duration_days}d • ${new Date(stage.start_date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}
                   </small>            
                </div>
        `;
    }).join('');
    
    legendContainer.innerHTML = legendHTML;
}

// ✅ UPDATED: handleReschedule - Add forced refresh
async function handleReschedule(e) {
    e.preventDefault();
    
    const projectId = document.getElementById('rescheduleProjectId').value;
    const stageId = parseInt(document.getElementById('rescheduleStageId').value);
    const days = parseInt(document.getElementById('rescheduleDays').value);
    const reason = document.getElementById('rescheduleReason').value;
    
    if (!days || days === 0) {
        alert('Please enter a valid number of days (not zero)');
        return;
    }
    
    const startDate = new Date(document.getElementById('rescheduleStageStartDate').value);
    const testDate = addWorkingDays(startDate, days);
    const testDay = testDate.getDay();
    
    if (testDay === 0) {
        alert('⚠️ Cannot reschedule to Sunday (holiday)');
        return;
    }
    
    if (testDay === 6 && !includeSaturdayAsWorkingDay) {
        alert('⚠️ Cannot reschedule to Saturday (holiday).\n\nEnable "Include Saturday as Working Day" if needed.');
        return;
    }
    
    const stageIndex = currentProjectData.stages.findIndex(s => s.id === stageId);
    const hasCompletedBefore = currentProjectData.stages
        .slice(0, stageIndex)
        .some(s => s.status === 'completed');
    
    let confirmMsg = `Are you sure you want to shift this stage by ${days} working days?\n\n`;
    
    if (hasCompletedBefore) {
        confirmMsg += '✅ Completed stages will remain unchanged\n';
    }
    confirmMsg += '✅ This stage and subsequent stages will be shifted\n';
    confirmMsg += '✅ Weekends will be excluded from calculation';
    
    if (!confirm(confirmMsg)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/projects/${projectId}/reschedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stage_id: stageId,
                days: days,
                reason: reason,
                include_saturday: includeSaturdayAsWorkingDay,
                working_saturdays: Array.from(currentProjectData.saturdayWorkingDays || [])
            })
        });
        
        if (response.ok) {
            showNotification('Stage rescheduled successfully!', 'success');
            rescheduleModal.hide();
            
            // ✅ CRITICAL: Wait for database transaction to fully commit
            console.log('⏳ Waiting for database commit (3 seconds)...');
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            // ✅ Force complete calendar rebuild with verified data
            console.log('🔨 Starting COMPLETE calendar rebuild...');
            await forceCompleteCalendarRebuild(parseInt(projectId));
            
            // ✅ Refresh main project view
            await loadProjects();
            await loadStats();
            
            // ✅ FORCE CALENDAR REFRESH TO FIX LAYOUT
            console.log('🔄 Forcing calendar refresh after reschedule...');
            if (calendar) {
                try {
                    calendar.destroy();
                    calendar = null;
                    const calendarEl = document.getElementById('calendar');
                    if (calendarEl) {
                        calendarEl.innerHTML = '';
                        calendarEl.className = '';
                        calendarEl.offsetHeight; // Force reflow
                    }
                    await new Promise(resolve => setTimeout(resolve, 150));
                    await openCalendarView(parseInt(projectId));
                    console.log('✅ Calendar rebuilt successfully');
                } catch (e) {
                    console.error('Error rebuilding calendar:', e);
                }
            }
            
            showNotification('✅ Calendar updated successfully!', 'success');
            
        } else {
            const error = await response.json();
            alert('Error: ' + (error.error || 'Failed to reschedule'));
        }
    } catch (error) {
        console.error('❌ Reschedule error:', error);
        alert('Error rescheduling: ' + error.message);
    }
}
// ✅ NEW FUNCTION: Complete calendar rebuild with verification
async function forceCompleteCalendarRebuild(projectId) {
    console.log('🔨 Starting COMPLETE calendar rebuild...');
    
    // Step 1: Clear ALL badges
    document.querySelectorAll('.parallel-jobs-badge').forEach(badge => badge.remove());
    console.log('🧹 Cleared all badges');
    
    // Step 2: Wait for database
    await new Promise(resolve => setTimeout(resolve, 2000));
    console.log('✅ Database wait complete');
    
    // Step 3: Fetch FRESH data - MULTIPLE ATTEMPTS
    let freshData = null;
    let attempts = 0;
    const maxAttempts = 3;
    
    while (attempts < maxAttempts && !freshData) {
        attempts++;
        console.log(`📡 Fetch attempt ${attempts}/${maxAttempts}...`);
        
        try {
            const timestamp = Date.now();
            const response = await fetch(`/api/projects/${projectId}/details?_bust=${timestamp}`, {
                method: 'GET',
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            
            if (response.ok) {
                freshData = await response.json();
                console.log(`✅ Got fresh data (attempt ${attempts})`);
                break;
            }
        } catch (error) {
            console.error(`❌ Fetch attempt ${attempts} failed:`, error);
        }
        
        if (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 500));
        }
    }
    
    if (!freshData) {
        alert('Failed to refresh calendar data');
        return;
    }
    
    // Step 4: Log what we received
    console.log('📊 Fresh stage dates from backend:');
    freshData.stages.forEach((s, idx) => {
        console.log(`  ${idx + 1}. ${s.name}: ${s.start_date} → ${s.end_date}`);
    });
    
    // Step 5: Fetch COMPLETE reschedule history (both stage and daily task)
    try {
        const historyResponse = await fetch(`/api/projects/${projectId}/complete-reschedule-history?_t=${timestamp}`);
        if (historyResponse.ok) {
            freshData.rescheduleHistory = await historyResponse.json();
            console.log(`✅ Loaded ${freshData.rescheduleHistory.length} history records`);
        } else {
            freshData.rescheduleHistory = [];
        }
    } catch (error) {
        console.error('Failed to load history:', error);
        freshData.rescheduleHistory = [];
    }    
    // Step 6: Process saturdayWorkingDays
    if (Array.isArray(freshData.saturdayWorkingDays)) {
        freshData.saturdayWorkingDays = new Set(freshData.saturdayWorkingDays);
    } else {
        freshData.saturdayWorkingDays = new Set();
    }
    
    // Step 7: ✅ CRITICAL - Completely replace currentProjectData
    if (!currentProjectData.rescheduleHistory || currentProjectData.rescheduleHistory.length === 0) {
        console.warn('⚠️ WARNING: No reschedule history in currentProjectData!');
        console.log('Attempting to reload history...');
        
        try {
            const historyResponse = await fetch(`/api/projects/${projectId}/complete-reschedule-history?_t=${Date.now()}`);
            if (historyResponse.ok) {
                currentProjectData.rescheduleHistory = await historyResponse.json();
                console.log(`✅ Reloaded ${currentProjectData.rescheduleHistory.length} history records`);
            }
        } catch (e) {
            console.error('❌ Failed to reload history:', e);
        }
    } else {
        console.log(`✅ History verified: ${currentProjectData.rescheduleHistory.length} records`);
    }    
    
    // ✅ NEW: RECALCULATE LAYOUT with fresh data
    console.log('📐 Recalculating layout with fresh data...');
    const layoutInfo = calculateOptimalCalendarLayout(freshData.stages);
    applyDynamicCalendarStyles(layoutInfo);
    console.log('✅ Recalculated and applied new layout');
    
    // Step 8: Regenerate calendar events
    console.log('🎨 Generating new calendar events...');
    const newEvents = await generateEnhancedCalendarEvents(currentProjectData.stages);
    console.log(`✅ Generated ${newEvents.length} events`);
    
    // Step 9: Destroy old calendar
    if (calendar) {
        calendar.destroy();
        console.log('🗑️ Old calendar destroyed');
    }
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Step 10: Create NEW calendar
    const calendarEl = document.getElementById('calendar');
    
    calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        initialDate: currentProjectData.start_date,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listMonth'
        },
        height: 'auto',
        contentHeight: 'auto',
        eventMaxStack: layoutInfo.maxStagesPerDay + 2,  // ✅ DYNAMIC: Adjust based on layout complexity
        dayMaxEvents: false,
        dayMaxEventRows: false,
        // ✅ CRITICAL FIX: Use function instead of static array so refetchEvents() works
        events: async function(fetchInfo, successCallback, failureCallback) {
            try {
                console.log('🔄 Fetching fresh calendar events...');
                const freshEvents = await generateEnhancedCalendarEvents(currentProjectData.stages);
                console.log('✅ Generated', freshEvents.length, 'events');
                successCallback(freshEvents);
            } catch (error) {
                console.error('❌ Error generating events:', error);
                failureCallback(error);
            }
        },
        editable: true,  // Enable drag and drop editing
        eventClick: function(info) {
            if (info.event.extendedProps.isGhost) {
                const props = info.event.extendedProps;
                alert(
                    `Original Location\n\n` +
                    `Stage: ${props.stageName}\n` +
                    `Moved ${props.daysShifted} day(s) ${props.direction}\n` +
                    `New location: ${new Date(props.movedTo).toLocaleDateString()}`
                );
                return;
            }
            handleStageClickReschedule(info, currentProjectData);
        },
        // ✅ FIX: Handle event drag/drop - refresh calendar layout
        eventDrop: async function(info) {
            console.log('📌 Event dropped, updating layout...');
            try {
                // ✅ Reload fresh project data
                const response = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${Date.now()}`, {
                    cache: 'no-store',
                    headers: {'Cache-Control': 'no-cache'}
                });
                if (response.ok) {
                    const freshData = await response.json();
                    currentProjectData.stages = freshData.stages;
                    
                    // ✅ RECALCULATE AND REAPPLY LAYOUT
                    const newLayoutInfo = calculateOptimalCalendarLayout(freshData.stages);
                    applyDynamicCalendarStyles(newLayoutInfo);
                    
                    console.log('✅ Loaded fresh project data');
                }
                
                // ✅ CRITICAL: Refresh the calendar to fix layout
                setTimeout(() => {
                    if (calendar) {
                        calendar.refetchEvents();
                        calendar.updateSize();
                        calendar.render();
                        console.log('✅ Calendar layout refreshed after drop');
                    }
                }, 100);
            } catch (error) {
                console.error('Error updating event:', error);
                info.revert();
            }
        },
        // ✅ FIX: Handle event resize - refresh calendar layout
        eventResize: async function(info) {
            console.log('📏 Event resized, updating layout...');
            try {
                // ✅ Reload fresh project data
                const response = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${Date.now()}`, {
                    cache: 'no-store',
                    headers: {'Cache-Control': 'no-cache'}
                });
                if (response.ok) {
                    const freshData = await response.json();
                    currentProjectData.stages = freshData.stages;
                    
                    // ✅ RECALCULATE AND REAPPLY LAYOUT
                    const newLayoutInfo = calculateOptimalCalendarLayout(freshData.stages);
                    applyDynamicCalendarStyles(newLayoutInfo);
                    
                    console.log('✅ Loaded fresh project data');
                }
                
                // ✅ CRITICAL: Refresh the calendar to fix layout
                setTimeout(() => {
                    if (calendar) {
                        calendar.refetchEvents();
                        calendar.updateSize();
                        calendar.render();
                        console.log('✅ Calendar layout refreshed after resize');
                    }
                }, 100);
            } catch (error) {
                console.error('Error updating event:', error);
                info.revert();
            }
        },
        dayCellDidMount: function(info) {
            addDayRescheduleButton(info, currentProjectData);
        },
        eventDisplay: 'block',
        displayEventTime: false,
        eventDidMount: function(info) {
            enhanceEventDisplay(info);
        }
    });
    
    calendar.render();
    console.log('🎬 New calendar rendered');
    
    // Step 12: Wait for DOM
    await new Promise(resolve => setTimeout(resolve, 1000));

    console.log('🎉 Calendar rebuild COMPLETE!');
}

function adjustRescheduleDays(delta) {
        const input = document.getElementById('rescheduleDays');
        const currentValue = parseInt(input.value) || 0;
        input.value = currentValue + delta;
        updateReschedulePreview();
    }

    function updateReschedulePreview() {
        const days = parseInt(document.getElementById('rescheduleDays').value);
        
        if (!days || days === 0) {
            document.getElementById('rescheduleNewDatesPreview').style.display = 'none';
            document.getElementById('rescheduleImpactWarning').style.display = 'none';
            return;
        }
        
        const startDate = new Date(document.getElementById('rescheduleStageStartDate').value);
        const endDate = new Date(document.getElementById('rescheduleStageEndDate').value);
        
        const newStart = addWorkingDays(startDate, days);
        const newEnd = addWorkingDays(endDate, days);
        
        document.getElementById('rescheduleNewDatesValue').textContent = 
            `${newStart.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})} - ${newEnd.toLocaleDateString('en-US', {month: 'short', day: 'numeric', year: 'numeric'})}`;
        document.getElementById('rescheduleNewDatesPreview').style.display = 'block';
        
        const impactText = days > 0 
            ? `All subsequent stages will be pushed forward by ${days} working day(s)`
            : `All subsequent stages will be pulled backward by ${Math.abs(days)} working day(s)`;
        document.getElementById('rescheduleImpactText').textContent = impactText;
        document.getElementById('rescheduleImpactWarning').style.display = 'block';
    }

function enhanceCalendarWithWeekends() {
    if (!calendar) return;
    
    // Ensure working Saturdays is initialized
    if (!currentProjectData.saturdayWorkingDays) {
        currentProjectData.saturdayWorkingDays = new Set();
    }
    
    // Get the current dayCellDidMount handler
    const oldDayCellDidMount = calendar.getOption('dayCellDidMount');
    
    // Override with enhanced version
    calendar.setOption('dayCellDidMount', function(info) {
        const day = info.date.getDay();
        const dateKey = info.date.toISOString().split('T')[0];
        
        // Handle Sundays (day 0)
        if (day === 0) {
            info.el.style.background = 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)';
            info.el.style.opacity = '0.7';
            info.el.title = 'Sunday - Holiday';
        }
        
        // Handle Saturdays (day 6) - always holiday, no toggle
        if (day === 6) {
            info.el.style.background = 'linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%)';
            info.el.style.opacity = '0.7';
            info.el.title = 'Saturday - Holiday';
        }
        
        // Call original handler if it exists
        if (oldDayCellDidMount) {
            oldDayCellDidMount(info);
        }
        
        // Add reschedule button
        addDayRescheduleButton(info, currentProjectData);
    });
    
    // Force calendar to re-render with new dayCellDidMount
    calendar.render();
}
    // UPDATED FUNCTION: Toggle Saturday working status with recalculation
async function recalculateProjectWithSaturdays() {
    if (!currentProjectData) return;
    
    try {
        // Send update to backend
        const response = await fetch(`/api/projects/${currentProjectData.id}/update-saturdays`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                working_saturdays: Array.from(currentProjectData.saturdayWorkingDays || [])
            })
        });
        
        if (response.ok) {
            // Wait for DB to update
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // Fetch fresh data
            const detailsResponse = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${Date.now()}`, {
                cache: 'no-store',
                headers: {'Cache-Control': 'no-cache'}
            });
            const freshData = await detailsResponse.json();
            
            // Update current data
            currentProjectData = freshData;
            
            // Ensure Set conversion
            if (Array.isArray(freshData.saturdayWorkingDays)) {
                currentProjectData.saturdayWorkingDays = new Set(freshData.saturdayWorkingDays);
            }
            
            // COMPLETE calendar regeneration
            const calendarEl = document.getElementById('calendar');
            calendarEl.innerHTML = '';
            
            calendar = new FullCalendar.Calendar(calendarEl, {
                initialView: 'dayGridMonth',
                initialDate: currentProjectData.start_date,
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,timeGridWeek,listMonth'
                },
                events: generateEnhancedCalendarEvents(currentProjectData.stages),
                eventClick: function(info) {
                    handleStageClickReschedule(info, currentProjectData);
                },
                dayCellDidMount: function(info) {
                    addDayRescheduleButton(info, currentProjectData);
                },
                height: 'auto',
                eventDisplay: 'block',
                displayEventTime: false,
                eventDidMount: function(info) {
                    enhanceEventDisplay(info);
                }
            });
            
            calendar.render();
            enhanceCalendarWithWeekends(); // CRITICAL: Call after render
            generateEnhancedLegend(currentProjectData.stages);
            
            await loadProjects(); // Refresh main view
            
            showNotification('Schedule recalculated!', 'success');
        }
    } catch (error) {
        console.error('Recalculation error:', error);
        showNotification('Failed to update: ' + error.message, 'error');
    }
}

// Helper function to show notifications
    function showNotification(message, type = 'success') {
        const bgColors = {
            success: '#28a745',
            info: '#17a2b8',
            warning: '#ffc107',
            error: '#dc3545'
        };
        
        const bgColor = bgColors[type] || bgColors.success;
        
        const notification = document.createElement('div');
        notification.className = 'alert alert-dismissible fade show position-fixed';
        notification.style.cssText = `top: 20px; right: 20px; z-index: 9999; min-width: 300px; background: ${bgColor}; color: white; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.3);`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

async function openDailyTaskManager(projectId, stageId, stageName) {
    currentStageForDailyTasks = { projectId, stageId };
    
    document.getElementById('dailyTaskModalTitle').textContent = 'Manage Daily Tasks';
    document.getElementById('dailyTaskStageName').textContent = `Stage: ${stageName}`;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks`);
        const tasks = await handleApiResponse(response);  // ✅ CHANGED THIS LINE
        
        if (tasks.length === 0) {
            console.log('No tasks found, generating...');
            await generateDailyTasks(projectId);
            
            const retryResponse = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks`);
            const retryTasks = await handleApiResponse(retryResponse);  // ✅ CHANGED THIS LINE
            renderDailyTasks(retryTasks);
        } else {
            renderDailyTasks(tasks);
        }
        
        dailyTaskModal.show();
    } catch (error) {
        console.error('Error loading daily tasks:', error);
        if (error.message !== 'Session expired') {
            alert(`Error loading daily tasks: ${error.message}`);
        }
    }
}
// Generate daily tasks for project
async function generateDailyTasks(projectId) {
    const response = await fetch(`/api/projects/${projectId}/generate-daily-tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
        throw new Error('Failed to generate daily tasks');
    }
}


// Helper function to check if task date is today or in the past
function isTaskDateInPast(scheduledDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const taskDate = new Date(scheduledDate);
    taskDate.setHours(0, 0, 0, 0);
    
    return taskDate <= today;
}

// Render daily tasks
function renderDailyTasks(tasks) {
    const container = document.getElementById('dailyTasksList');
    
    if (tasks.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">No daily tasks available</p>';
        return;
    }
    
    container.innerHTML = tasks.map(task => {
        const statusClass = task.status === 'completed' ? 'completed' : task.is_rescheduled ? 'rescheduled' : '';
        const statusBadge = task.status === 'completed' ? 'badge-completed' : 
                           task.status === 'rescheduled' ? 'badge-rescheduled' : 'badge-pending';
        
        let dateDisplay = new Date(task.scheduled_date).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        
        let rescheduleInfo = '';
        if (task.is_rescheduled) {
            const originalDate = new Date(task.original_date).toLocaleDateString('en-US', { 
                weekday: 'short',
                month: 'short', 
                day: 'numeric',
                year: 'numeric'
            });
            const currentDate = new Date(task.scheduled_date);
            const origDate = new Date(task.original_date);
            const daysDiff = Math.round((currentDate - origDate) / (1000 * 60 * 60 * 24));
            const direction = daysDiff > 0 ? 'forward' : 'backward';
            
            rescheduleInfo = `
                <div class="reschedule-indicator mt-2 p-2" style="background: #fff3cd; border-left: 4px solid #ff9800; border-radius: 6px;">
                    <div class="d-flex align-items-start">
                        <i class="fas fa-exchange-alt me-2 mt-1" style="color: #ff9800;"></i>
                        <div style="flex: 1;">
                            <div class="mb-1">
                                <strong style="color: #ff6b00;">Rescheduled</strong>
                                <span class="badge bg-warning text-dark ms-2">${Math.abs(daysDiff)} day(s) ${direction}</span>
                            </div>
                            <small class="text-muted d-block">Original: ${originalDate}</small>
                            ${task.rescheduled_reason ? `
                                <small class="d-block mt-1" style="color: #495057;">
                                    <i class="fas fa-comment-dots me-1"></i>
                                    <strong>Reason:</strong> ${task.rescheduled_reason}
                                </small>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="daily-task-item ${statusClass}">
                <div class="task-day-number ${task.status === 'completed' ? 'completed' : ''}">
                    ${task.status === 'completed' ? '<i class="fas fa-check"></i>' : `Day ${task.day_number}`}
                </div>
                <div class="task-info flex-grow-1">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <div class="task-date-display fw-bold">${dateDisplay}</div>
                        <span class="task-status-badge ${statusBadge}">${task.status.toUpperCase()}</span>
                    </div>
                    ${rescheduleInfo}
                </div>
            <div class="d-flex gap-2 align-items-start">
                    ${task.status !== 'completed' && task.status !== 'hold' ? `
                        ${isTaskDateInPast(task.scheduled_date) ? `
                            <button class="btn btn-sm btn-success" onclick="completeDailyTask(${task.id}, ${currentStageForDailyTasks.projectId}, ${currentStageForDailyTasks.stageId})" title="Mark as complete">
                                <i class="fas fa-check me-1"></i>Complete
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-secondary" disabled title="Cannot complete future tasks">
                                <i class="fas fa-lock me-1"></i>Future Task
                            </button>
                        `}
                        <button class="btn btn-sm btn-primary-custom" onclick="openRescheduleDayModal(${task.id}, ${task.day_number}, '${task.scheduled_date}')" title="Change schedule">
                            <i class="fas fa-calendar-alt me-1"></i>Reschedule
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="holdDailyTask(${task.id}, ${currentStageForDailyTasks.projectId}, ${currentStageForDailyTasks.stageId})" title="Put on hold">
                            <i class="fas fa-lock me-1"></i>Hold
                        </button>
                    ` : task.status === 'hold' ? `
                        <div class="text-center">
                            <span class="text-warning d-block">
                                <i class="fas fa-lock me-1"></i>
                                ON HOLD
                            </span>
                        </div>
                    ` : `
                        <div class="text-center">
                            <span class="text-success d-block">
                                <i class="fas fa-check-circle me-1"></i>
                                Completed
                            </span>
                            ${task.completed_at ? `
                                <small class="text-muted">${new Date(task.completed_at).toLocaleDateString('en-US', {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</small>
                            ` : ''}
                        </div>
                    `}
                </div>            
             </div>
        `;
    }).join('');
}
// Complete a daily task
async function completeDailyTask(taskId, projectId, stageId) {
    if (!confirm('Mark this day as completed?')) return;
    
    try {
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks/${taskId}/complete`, {
            method: 'PUT'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showNotification('Day marked as completed!', 'success');
            
            // Show if stage was automatically completed
            if (data.stage_completed) {
                showNotification(`🎉 All daily tasks completed! Stage marked as complete (${data.completed_tasks}/${data.total_tasks})`, 'success');
            }
            
            // ✅ Wait for database commit
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Reload tasks in modal
            const tasksResponse = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks`);
            const tasks = await tasksResponse.json();
            renderDailyTasks(tasks);
            
            // ✅ Refresh calendar in background
            if (calendar && currentProjectForCalendar === projectId) {
                await refreshCalendarEvents();
            }
            
            // ✅ Update progress line status
            await updateProgressLineStatus(projectId);
        } else {
            // Show error message from server
            showNotification(data.error || 'Failed to complete task', 'error');
        }
    } catch (error) {
        console.error('Error completing task:', error);
        showNotification('Error: ' + error.message, 'error');
    }
}
// Open reschedule day modal
function openRescheduleDayModal(taskId, dayNumber, currentDate) {
    document.getElementById('rescheduleTaskId').value = taskId;
    document.getElementById('rescheduleTaskProjectId').value = currentStageForDailyTasks.projectId;
    document.getElementById('rescheduleTaskStageId').value = currentStageForDailyTasks.stageId;
    document.getElementById('dayShiftAmount').value = 0;
    document.getElementById('dayRescheduleReason').value = '';
    document.getElementById('dayReschedulePreview').style.display = 'none';
    
    const dateStr = new Date(currentDate).toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
    });
    
    document.getElementById('dayRescheduleInfo').innerHTML = `
        <strong>Day ${dayNumber}</strong><br>
        Current date: ${dateStr}
    `;
    
    rescheduleDayModal.show();
}

// Adjust day shift
function adjustDayShift(delta) {
    const input = document.getElementById('dayShiftAmount');
    input.value = parseInt(input.value || 0) + delta;
    updateDayReschedulePreview();
}

// Update preview
function updateDayReschedulePreview() {
    const days = parseInt(document.getElementById('dayShiftAmount').value || 0);
    const preview = document.getElementById('dayReschedulePreview');
    
    if (days === 0) {
        preview.style.display = 'none';
        return;
    }
    
    preview.style.display = 'block';
    preview.textContent = `This day will be shifted ${Math.abs(days)} working day(s) ${days > 0 ? 'forward' : 'backward'}`;
}


// Confirm day reschedule
async function confirmDayReschedule() {
    const taskId = document.getElementById('rescheduleTaskId').value;
    const projectId = document.getElementById('rescheduleTaskProjectId').value;
    const stageId = document.getElementById('rescheduleTaskStageId').value;
    const days = parseInt(document.getElementById('dayShiftAmount').value || 0);
    const reason = document.getElementById('dayRescheduleReason').value;
    
    if (days === 0) {
        alert('Please enter a number of days to shift');
        return;
    }
    
    try {
        console.log('🔄 Rescheduling daily task...');
        
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks/${taskId}/reschedule`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                days: days,
                reason: reason,
                working_saturdays: Array.from(currentProjectData?.saturdayWorkingDays || [])
            })
        });
        
        if (response.ok) {
            showNotification('✅ Day rescheduled successfully!', 'success');
            
            // Close the reschedule day modal
            rescheduleDayModal.hide();
            
            // ✅ CRITICAL: Wait LONGER for database transaction to FULLY commit
            console.log('⏳ Waiting for database commit (4 seconds)...');
            await new Promise(resolve => setTimeout(resolve, 4000));
            
            console.log('🔥 Fetching updated task list...');
            
            // Reload tasks in the daily task modal
            const tasksResponse = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks?_t=${Date.now()}`, {
                cache: 'no-store',
                headers: { 'Cache-Control': 'no-cache' }
            });
            const tasks = await tasksResponse.json();
            renderDailyTasks(tasks);
            
            console.log('✅ Task list updated');
            
            // ✅ Close the daily task modal so user can see the calendar
            console.log('📊 Closing daily task modal...');
            dailyTaskModal.hide();
            
            // ✅ Additional wait before calendar rebuild
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // ✅ Force COMPLETE calendar rebuild with ALL history
            if (calendar && currentProjectForCalendar === parseInt(projectId)) {
                showNotification('🔄 Rebuilding calendar with ghost events...', 'info');
                
                console.log('🔨 Starting calendar rebuild...');
                
                // ✅ CRITICAL: Fetch history FIRST before rebuild
                try {
                    const timestamp = Date.now();
                    const historyResponse = await fetch(`/api/projects/${projectId}/complete-reschedule-history?_t=${timestamp}`, {
                        cache: 'no-store',
                        headers: { 
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache'
                        }
                    });
                    
                    if (historyResponse.ok) {
                        const historyData = await historyResponse.json();
                        console.log(`📜 Loaded ${historyData.length} history records (including daily tasks)`);
                        
                        // Update currentProjectData with fresh history
                        if (!currentProjectData) {
                            console.error('❌ currentProjectData is null!');
                        } else {
                            currentProjectData.rescheduleHistory = historyData;
                            console.log('✅ Updated currentProjectData.rescheduleHistory');
                        }
                    } else {
                        console.warn('⚠️ Failed to fetch history:', historyResponse.status);
                    }
                } catch (error) {
                    console.error('❌ Error fetching history:', error);
                }
                
                // Now rebuild calendar with updated history
                await forceCompleteCalendarRebuild(parseInt(projectId));
                
                // ✅ FORCE CALENDAR REFRESH TO FIX LAYOUT
                console.log('🔄 Forcing calendar refresh after day reschedule...');
                if (calendar) {
                    try {
                        calendar.destroy();
                        calendar = null;
                        const calendarEl = document.getElementById('calendar');
                        if (calendarEl) {
                            calendarEl.innerHTML = '';
                            calendarEl.className = '';
                            calendarEl.offsetHeight; // Force reflow
                        }
                        await new Promise(resolve => setTimeout(resolve, 150));
                        await openCalendarView(parseInt(projectId));
                        console.log('✅ Calendar rebuilt successfully');
                    } catch (e) {
                        console.error('Error rebuilding calendar:', e);
                    }
                }
                
                showNotification('✅ Calendar updated! Ghost event shows original location.', 'success');
            } else {
                console.warn('⚠️ Calendar not available for rebuild');
            }
        } else {
            const error = await response.json();
            alert('Error: ' + error.error);
        }
    } catch (error) {
        console.error('❌ Reschedule error:', error);
        alert('Error: ' + error.message);
    }
}


// Hold a daily task
async function holdDailyTask(taskId, projectId, stageId) {
    const reason = prompt('Reason for putting this day on hold:');
    if (reason === null) return; // User cancelled
    
    if (!confirm('Are you sure you want to put this day on HOLD? Other days will continue as scheduled.')) {
        return;
    }
    
    try {
        console.log('🔒 Putting daily task on HOLD...');
        
        const response = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks/${taskId}/hold`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                reason: reason || 'Put on hold',
                working_saturdays: Array.from(currentProjectData?.saturdayWorkingDays || [])
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Day marked as HOLD successfully', 'success');
            
            // Wait for database commit
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Reload tasks in the daily task modal
            const tasksResponse = await fetch(`/api/projects/${projectId}/stages/${stageId}/daily-tasks?_t=${Date.now()}`, {
                cache: 'no-store',
                headers: { 'Cache-Control': 'no-cache' }
            });
            const tasks = await tasksResponse.json();
            renderDailyTasks(tasks);
            
            // Rebuild calendar
            if (calendar && currentProjectForCalendar === projectId) {
                showNotification('🔄 Updating calendar...', 'info');
                await refreshCalendarEvents();
                showNotification('✅ Calendar updated!', 'success');
            }
        } else {
            alert('Error: ' + (result.error || 'Failed to hold day'));
        }
    } catch (error) {
        console.error('❌ Hold error:', error);
        alert('Error: ' + error.message);
    }
}

// ✅ NEW FUNCTION: Refresh calendar events without closing/reopening modal
async function refreshCalendarEvents() {
    if (!calendar || !currentProjectData) {
        console.log('⚠️ Cannot refresh calendar: calendar or data missing');
        return;
    }
    
    try {
        console.log('🔄 Refreshing calendar events...');
        
        // ✅ CRITICAL: Fetch COMPLETE reschedule history
        const timestamp = Date.now();
        const historyResponse = await fetch(`/api/projects/${currentProjectData.id}/complete-reschedule-history?_t=${timestamp}`, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        
        if (historyResponse.ok) {
            currentProjectData.rescheduleHistory = await historyResponse.json();
            console.log('✅ Loaded reschedule history:', currentProjectData.rescheduleHistory.length, 'records');
        } else {
            console.warn('⚠️ Failed to load history');
            currentProjectData.rescheduleHistory = [];
        }
        
        // Fetch fresh project data
        const response = await fetch(`/api/projects/${currentProjectData.id}/details?_t=${timestamp}`, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        const freshData = await response.json();
        
        // Update saturdayWorkingDays
        if (Array.isArray(freshData.saturdayWorkingDays)) {
            freshData.saturdayWorkingDays = new Set(freshData.saturdayWorkingDays);
        }
        
        // ✅ PRESERVE reschedule history
        freshData.rescheduleHistory = currentProjectData.rescheduleHistory;
        
        currentProjectData = freshData;
        
        // Generate new events from fresh data (including ghost events)
        const newEvents = await generateEnhancedCalendarEvents(freshData.stages);
        
        console.log('📊 Generated events:', newEvents.length, 'total');
        console.log('👻 Ghost events:', newEvents.filter(e => e.classNames?.includes('ghost-event')).length);
        
        // Remove all old events
        calendar.removeAllEvents();
        
        // Wait a tick
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // Add new events
        newEvents.forEach(event => {
            calendar.addEvent(event);
        });
        
        // Refresh display
        calendar.render();
                
        console.log('✅ Calendar refreshed successfully');
        
    } catch (error) {
        console.error('Error refreshing calendar:', error);
    }
}

// Complete calendar refresh with FORCED data reload
async function refreshCalendarWithBadges() {
    if (!calendar || !currentProjectData) {
        console.log('⚠️ Cannot refresh calendar: calendar or data missing');
        return;
    }
    
    try {
        console.log('🔄 Starting calendar refresh...');
        
        const projectId = currentProjectData.id;
        
        // ✅ Wait for database commit
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // ✅ Fetch fresh data with cache busting
        const timestamp = Date.now();
        const detailsUrl = `/api/projects/${projectId}/details?_t=${timestamp}&_bustCache=${Math.random()}`;
        
        const response = await fetch(detailsUrl, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        const freshData = await response.json();
        console.log('✅ Fresh data received:', freshData.stages.length, 'stages');
        
        // Fetch reschedule history
        const historyUrl = `/api/projects/${projectId}/reschedule-history?_t=${timestamp}`;
        const historyResponse = await fetch(historyUrl, {
            cache: 'no-store',
            headers: { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' }
        });
        
        if (historyResponse.ok) {
            freshData.rescheduleHistory = await historyResponse.json();
        } else {
            freshData.rescheduleHistory = [];
        }
        
        // Convert saturdayWorkingDays
        if (Array.isArray(freshData.saturdayWorkingDays)) {
            freshData.saturdayWorkingDays = new Set(freshData.saturdayWorkingDays);
        } else {
            freshData.saturdayWorkingDays = new Set();
        }
        
        // ✅ Update currentProjectData
        currentProjectData = freshData;
        
        // ✅ CRITICAL FIX: Clear ALL badges BEFORE any calendar operations
        document.querySelectorAll('.parallel-jobs-badge').forEach(badge => badge.remove());
        
        // ✅ Regenerate events
        const newEvents = await generateEnhancedCalendarEvents(currentProjectData.stages);
        console.log('🎯 Generated', newEvents.length, 'events');
        
        // ✅ Remove old events
        calendar.removeAllEvents();
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // ✅ Add new events
        newEvents.forEach(event => calendar.addEvent(event));
        
        // ✅ CRITICAL: Force calendar to fully re-render
        calendar.render();
        
        // ✅ Wait for render to complete
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // ✅ NOW recalculate badges with fresh DOM
        console.log('🏷️ Recalculating badges with updated stage positions...');
        
        // Clear again just to be safe
        document.querySelectorAll('.parallel-jobs-badge').forEach(badge => badge.remove());
        
        // ✅ IMPROVED: Recalculate badges with the UPDATED stage data
        recalculateBadgesWithFreshData();
        
        // ✅ Do additional refreshes to ensure accuracy
        
        console.log('✅ Calendar refresh complete');
        
    } catch (error) {
        console.error('❌ Error:', error);
        showNotification('Failed to refresh: ' + error.message, 'error');
    }
}

function createStageEventWithStatus(stage, index, start, end, color, dateStageMap, tasks, stageHasRescheduled, stageRescheduleHistory = null) {
    // Check for parallel stages
    let hasParallel = false;
    let parallelCount = 0;
    
    for (let d = new Date(start); d < end; d.setDate(d.getDate() + 1)) {
        const dateKey = d.toISOString().split('T')[0];
        const stagesOnDate = dateStageMap.get(dateKey) || [];
        if (stagesOnDate.length > 1) {
            hasParallel = true;
            parallelCount = Math.max(parallelCount, stagesOnDate.length);
        }
    }
    
    // Analyze task statuses
    const allCompleted = tasks.every(t => t.status === 'completed');
    const someCompleted = tasks.some(t => t.status === 'completed');
    const hasRescheduled = tasks.some(t => t.reschedule_count && t.reschedule_count > 0);
    const completedCount = tasks.filter(t => t.status === 'completed').length;
    const rescheduledCount = tasks.filter(t => t.reschedule_count && t.reschedule_count > 0).length;
    
    let title = stage.name;
    
    // Build clean tooltip
    let tooltip = `${stage.name}\n`;
    tooltip += `━━━━━━━━━━━━━━━\n`;
    tooltip += `📅 Duration: ${stage.duration_days} days\n`;
    tooltip += `📊 Status: ${stage.status}\n`;    

    if (completedCount > 0) {
        tooltip += `✅ Completed: ${completedCount}/${tasks.length} days\n`;
    }
    
    if (rescheduledCount > 0) {
        tooltip += `🔄 Rescheduled: ${rescheduledCount} day(s)\n`;
    }
    
    if (hasParallel) {
        tooltip += `⚡️ Parallel with ${parallelCount - 1} other stage(s)`;
    }
    
    const classNames = [];
    
    if (allCompleted) {
        classNames.push('event-completed');
    } else if (hasRescheduled) {
        classNames.push('event-rescheduled');
    }
    
    if (stageHasRescheduled) {
        classNames.push('stage-rescheduled');
    }
    
    if (stage.status === 'in-progress') {
        classNames.push('stage-event-active');
    }
    // ✅ Check if any task in this stage is on HOLD
    const hasHoldTask = tasks.some(t => t.status === 'hold');
    if (hasHoldTask) {
        classNames.push('event-hold');
    }

    
    // ✅ Build extended props with reschedule info
    const extendedProps = {
        stageId: stage.id,
        stageIndex: index,
        duration: stage.duration_days,
        status: stage.status,
        hasParallel: hasParallel,
        parallelCount: parallelCount,
        stageName: stage.name,
        allCompleted: allCompleted,
        hasRescheduled: hasRescheduled,
        completedCount: completedCount,
        rescheduledCount: rescheduledCount,
        totalTasks: tasks.length
    };
    
    // ✅ Add reschedule information if available
    if (stageRescheduleHistory) {
        extendedProps.wasRescheduled = true;
        extendedProps.daysShifted = stageRescheduleHistory.days_shifted || 
            Math.abs(Math.round((new Date(stageRescheduleHistory.new_date) - new Date(stageRescheduleHistory.original_date)) / (1000 * 60 * 60 * 24)));
        extendedProps.rescheduleDirection = stageRescheduleHistory.direction || 
            (new Date(stageRescheduleHistory.new_date) > new Date(stageRescheduleHistory.original_date) ? 'forward' : 'backward');
        extendedProps.rescheduleBadge = `${extendedProps.rescheduleDirection === 'forward' ? '+' : '-'}${extendedProps.daysShifted}d`;
        extendedProps.originalDate = stageRescheduleHistory.original_date;
    }
    
    return {
        title: title,
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0],
        backgroundColor: color,
        borderColor: color,
        extendedProps: extendedProps,
        classNames: classNames
    };
}

// UPDATED showExcelPreview function - EXACTLY matches Excel export
async function showExcelPreview(projectId) {
    try {
        // ✅ REMOVE ANY EXISTING MODALS FIRST
        document.querySelectorAll('#exportPreviewModal').forEach(m => m.remove());
        
        showNotification('Loading Excel preview...', 'info');
        
        // ✅ Fetch project details with cache-busting
        const timestamp = new Date().getTime();
        const projResponse = await fetch(`/api/projects/${projectId}/details?_=${timestamp}`, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        const projData = await projResponse.json();
        
        if (!projData || !projData.id) {
            throw new Error('Project not found');
        }
        
        console.log('✅ Project data loaded:', projData);
        console.log('✅ Stages found:', projData.stages?.length || 0);
        
        // ✅ Fetch reschedule history
        let rescheduleHistory = [];
        try {
            const historyResponse = await fetch(`/api/projects/${projectId}/complete-reschedule-history?_=${timestamp}`);
            rescheduleHistory = historyResponse.ok ? await historyResponse.json() : [];
            console.log('✅ Reschedule history loaded:', rescheduleHistory.length, 'records');
        } catch (error) {
            console.warn('⚠️ Could not load reschedule history:', error);
        }
        
        // ✅ Fetch daily tasks (for actual completion data) - MATCHING BACKEND
        let dailyTasks = [];
        try {
            const dailyTasksResponse = await fetch(`/api/projects/${projectId}/daily-tasks?_=${timestamp}`);
            dailyTasks = dailyTasksResponse.ok ? await dailyTasksResponse.json() : [];
            console.log('✅ Daily tasks loaded:', dailyTasks.length, 'tasks');
        } catch (error) {
            console.warn('⚠️ Could not load daily tasks:', error);
        }
        
        // ✅ Fetch hold dates from database
        let holdDates = [];
        try {
            const holdDatesResponse = await fetch(`/api/projects/${projectId}/hold-dates?_=${timestamp}`);
            holdDates = holdDatesResponse.ok ? await holdDatesResponse.json() : [];
            console.log('✅ Hold dates loaded:', holdDates.length, 'hold records');
        } catch (error) {
            console.warn('⚠️ Could not load hold dates:', error);
        }
        
        // ✅ CALCULATE ACTUAL END DATE FROM STAGES (safety check)
        const stages = projData.stages || [];
        let calculatedEndDate = new Date(projData.start_date);
        
        console.log('🔍 DEBUG - Number of stages:', stages.length);
        stages.forEach((stage, idx) => {
            console.log(`🔍 Stage ${idx + 1}: ${stage.name}`);
            console.log(`   Start: ${stage.start_date}, End: ${stage.end_date}`);
            if (stage.end_date) {
                const stageEnd = new Date(stage.end_date);
                if (stageEnd > calculatedEndDate) {
                    calculatedEndDate = stageEnd;
                    console.log(`   ✅ This is now the latest end date: ${stageEnd.toISOString().split('T')[0]}`);
                }
            }
        });
        
        // Use the minimum of stored end_date and calculated end_date
        const storedEndDate = new Date(projData.end_date);
        const actualEndDate = calculatedEndDate < storedEndDate ? calculatedEndDate : storedEndDate;
        
        console.log('🔍 DEBUG - Stored End Date:', projData.end_date, storedEndDate.toISOString().split('T')[0]);
        console.log('🔍 DEBUG - Calculated End Date from Stages:', calculatedEndDate.toISOString().split('T')[0]);
        console.log('🔍 DEBUG - Using End Date (minimum):', actualEndDate.toISOString().split('T')[0]);
        
        const startDate = new Date(projData.start_date);
        const endDate = actualEndDate;  // ✅ USE CALCULATED END DATE
        const allDates = [];
        
        let currentDate = new Date(startDate);
        while (currentDate <= endDate) {
            allDates.push(new Date(currentDate));
            currentDate.setDate(currentDate.getDate() + 1);
        }
        
        console.log('🔍 DEBUG - Total dates generated:', allDates.length);
        console.log('🔍 DEBUG - First date:', allDates[0]?.toISOString().split('T')[0]);
        console.log('🔍 DEBUG - Last date:', allDates[allDates.length - 1]?.toISOString().split('T')[0]);
        console.log('🔍 DEBUG - Date range:', allDates[0]?.getDate(), 'to', allDates[allDates.length - 1]?.getDate());
        
        // stages already declared above on line 5894
        const workingSaturdays = new Set(projData.saturdayWorkingDays || []);
        console.log('Working Saturdays:', workingSaturdays);
        
        // Build Excel-like preview
        let html = '<div style="overflow: auto; max-height: 75vh; background: white; padding: 15px; font-family: Calibri, Arial, sans-serif;">';
        html += '<!-- 🔥 FIXED VERSION - Check console for debug logs -->';
        html += '<table style="border-collapse: collapse; font-size: 11px; table-layout: auto;">';
        
        // ==========================================
        // STAGE DETAILS SECTION (5-column table at top)
        // ==========================================
        if (stages.length > 0) {
            const stageNames = stages.map(s => {
                const parts = s.name.split('-');
                if (parts.length >= 2) {
                    const category = parts.slice(0, -1).join('-').trim();
                    const abbr = parts[parts.length - 1].trim();
                    return `${category} -${abbr}`;
                }
                return s.name;
            });
            
            let stageIdx = 0;
            while (stageIdx < stageNames.length) {
                html += '<tr>';
                for (let col = 0; col < 5; col++) {
                    if (stageIdx < stageNames.length) {
                        html += `<td style="border: 1px solid #000; padding: 8px; background: white; font-weight: bold; font-size: 10px; min-width: 180px;">${stageNames[stageIdx]}</td>`;
                        stageIdx++;
                    } else {
                        html += '<td style="border: 1px solid #000; padding: 8px; background: white; min-width: 180px;"></td>';
                    }
                }
                html += '</tr>';
            }
            
            html += '<tr><td colspan="5" style="border: none; height: 20px;"></td></tr>';
        }
        
        // ==========================================
        // MAIN SCHEDULE TABLE
        // ==========================================
        
        // Headers
        html += '<tr>';
        html += `<td rowspan="2" style="border: 1px solid #000; padding: 8px; background: #B4C7E7; font-weight: bold; font-size: 12px; text-align: center; vertical-align: middle; min-width: 180px;">${projData.name}</td>`;
        html += '<td rowspan="2" style="border: 1px solid #000; padding: 8px; background: #B4C7E7; font-weight: bold; font-size: 11px; text-align: center; vertical-align: middle; min-width: 150px;">Date</td>';
        
        const monthYear = startDate.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
        html += `<td colspan="${allDates.length}" style="border: 1px solid #000; padding: 8px; background: #FFA500; font-weight: bold; font-size: 11px; text-align: center;">${monthYear}</td>`;
        html += '</tr>';
        
        // Day numbers
        html += '<tr>';
        allDates.forEach(date => {
            html += `<td style="border: 1px solid #000; padding: 6px; background: #B4C7E7; font-weight: bold; font-size: 11px; text-align: center; min-width: 50px;">${date.getDate()}</td>`;
        });
        html += '</tr>';
        
        // ==========================================
        // PLANNED ROW - Build from stage dates
        // ==========================================
        html += '<tr style="height: 40px;">';
        html += '<td style="border: 1px solid #000; padding: 8px;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px; font-weight: bold; text-align: center;">Planned</td>';
        
        const plannedMap = {};
        
        stages.forEach(stage => {
            if (stage.start_date && stage.end_date) {
                const parts = stage.name.split('-');
                const abbr = parts.length > 1 ? parts[parts.length - 1].trim() : stage.name.substring(0, 6);
                
                let d = new Date(stage.start_date);
                const endD = new Date(stage.end_date);
                
                while (d <= endD) {
                    const dayOfWeek = d.getDay();
                    const dateStr = d.toISOString().split('T')[0];
                    const isSaturday = dayOfWeek === 6;
                    const isWorkingSaturday = isSaturday && workingSaturdays.has(dateStr);
                    
                    // Include if it's a weekday OR a working Saturday
                    if (dayOfWeek !== 0 && (!isSaturday || isWorkingSaturday)) {
                        if (!plannedMap[dateStr]) plannedMap[dateStr] = [];
                        if (!plannedMap[dateStr].includes(abbr)) {
                            plannedMap[dateStr].push(abbr);
                        }
                    }
                    d.setDate(d.getDate() + 1);
                }
            }
        });
        
        allDates.forEach(date => {
            const dayOfWeek = date.getDay();
            const dateStr = date.toISOString().split('T')[0];
            const isSunday = dayOfWeek === 0;
            const isSaturday = dayOfWeek === 6;
            const isWorkingSaturday = isSaturday && workingSaturdays.has(dateStr);
            const isWeekend = isSunday || (isSaturday && !isWorkingSaturday);
            
            const bgColor = isWeekend ? '#FFFF00' : 'white';
            const value = plannedMap[dateStr] ? plannedMap[dateStr].sort().join(' , ') : '';
            
            html += `<td style="border: 1px solid #000; padding: 6px; background: ${bgColor}; text-align: center; font-weight: bold; font-size: 9px; min-width: 50px; vertical-align: middle;">${value}</td>`;
        });
        html += '</tr>';
        
        // ==========================================
        // RESCHEDULE ROWS (1-4) - MATCHING BACKEND LOGIC
        // ==========================================
        const stageRescheduleMap = {1: {}, 2: {}, 3: {}, 4: {}};
        
        // Build reschedule map matching backend logic
        stages.forEach(stage => {
            const parts = stage.name.split('-');
            const stageAbbr = parts.length > 1 ? parts[parts.length - 1].trim() : stage.name.substring(0, 6);
            
            const taskReschedules = rescheduleHistory.filter(r => r.stage_id === stage.id);
            const uniqueNums = [...new Set(taskReschedules.map(r => r.reschedule_number).filter(n => n))].sort((a, b) => a - b);
            
            uniqueNums.forEach((rNum, idx) => {
                const targetRow = idx + 1;
                if (targetRow > 4) return;
                
                const eventTasks = taskReschedules.filter(t => t.reschedule_number === rNum);
                eventTasks.forEach(t => {
                    const dateStr = t.new_date.split('T')[0];
                    if (!stageRescheduleMap[targetRow][dateStr]) {
                        stageRescheduleMap[targetRow][dateStr] = [];
                    }
                    if (!stageRescheduleMap[targetRow][dateStr].includes(stageAbbr)) {
                        stageRescheduleMap[targetRow][dateStr].push(stageAbbr);
                    }
                });
            });
        });
        
        // Render reschedule rows
        for (let rNum = 1; rNum <= 4; rNum++) {
            html += '<tr style="height: 30px;">';
            html += '<td style="border: 1px solid #000; padding: 8px;"></td>';
            html += `<td style="border: 1px solid #000; padding: 8px; font-weight: bold; text-align: center;">Reschedule -${rNum}</td>`;
            
            const rData = stageRescheduleMap[rNum] || {};
            
            allDates.forEach(date => {
                const dayOfWeek = date.getDay();
                const dateStr = date.toISOString().split('T')[0];
                const isSunday = dayOfWeek === 0;
                const isSaturday = dayOfWeek === 6;
                const isWorkingSaturday = isSaturday && workingSaturdays.has(dateStr);
                const isWeekend = isSunday || (isSaturday && !isWorkingSaturday);
                
                const bgColor = isWeekend ? '#FFFF00' : 'white';
                const value = rData[dateStr] ? rData[dateStr].sort().join(' , ') : '';
                
                html += `<td style="border: 1px solid #000; padding: 6px; background: ${bgColor}; text-align: center; font-weight: bold; font-size: 9px; min-width: 50px; vertical-align: middle;">${value}</td>`;
            });
            html += '</tr>';
        }
        
        // ==========================================
        // ACTUAL ROW - MATCHING BACKEND LOGIC
        // ==========================================
        html += '<tr style="height: 40px;">';
        html += '<td style="border: 1px solid #000; padding: 8px;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px; background: #C0C0C0; font-weight: bold; text-align: center;">Actual</td>';
        
        const actualMap = {};
        const holdDatesMap = {};
        
        // Step 1: Build holdDatesMap from database HoldDate records
        holdDates.forEach(holdRecord => {
            const dateStr = holdRecord.hold_date; // Already in YYYY-MM-DD format
            const stageName = holdRecord.stage_name;
            const parts = stageName.split('-');
            const abbr = parts.length > 1 ? parts[parts.length - 1].trim() : stageName.substring(0, 6);
            
            if (!holdDatesMap[dateStr]) holdDatesMap[dateStr] = [];
            if (!holdDatesMap[dateStr].includes(abbr)) {
                holdDatesMap[dateStr].push(abbr);
                console.log(`📌 HOLD: ${dateStr} -> ${abbr} (${stageName})`);
            }
        });
        
        // Step 2: Build actualMap from real daily task records
        stages.forEach(stage => {
            const parts = stage.name.split('-');
            const abbr = parts.length > 1 ? parts[parts.length - 1].trim() : stage.name.substring(0, 6);
            const tasks = dailyTasks.filter(t => t.stage_id === stage.id);

            tasks.forEach(t => {
                const ds = t.scheduled_date.split('T')[0];

                if (t.status === 'hold') {
                    // HOLD task: add to holdDatesMap on its scheduled_date (backup in case not in HoldDate table)
                    if (!holdDatesMap[ds]) holdDatesMap[ds] = [];
                    if (!holdDatesMap[ds].includes(abbr)) holdDatesMap[ds].push(abbr);
                } else {
                    // All other statuses (pending/completed/rescheduled): add to actualMap
                    if (!actualMap[ds]) actualMap[ds] = [];
                    actualMap[ds].push({abbr, status: t.status});
                }
                
                // CRITICAL: If task was rescheduled, add original_date to holdDatesMap
                // This matches backend logic (app.py lines 439-444)
                if (t.original_date && t.original_date !== t.scheduled_date) {
                    const hds = t.original_date.split('T')[0];
                    if (!holdDatesMap[hds]) holdDatesMap[hds] = [];
                    if (!holdDatesMap[hds].includes(abbr)) {
                        holdDatesMap[hds].push(abbr);
                        console.log(`📌 HOLD from reschedule: ${hds} -> ${abbr} (original date)`);
                    }
                }
            });
        });

        // Step 3: Fallback for planned stages with no task record yet (e.g. DLBS on day 12)
        // Only add if NOT already in actualMap AND NOT already in holdDatesMap
        Object.keys(plannedMap).forEach(ds => {
            plannedMap[ds].forEach(abbr => {
                const inActual = (actualMap[ds] || []).some(x => x.abbr === abbr);
                const inHold   = (holdDatesMap[ds] || []).includes(abbr);
                if (!inActual && !inHold) {
                    if (!actualMap[ds]) actualMap[ds] = [];
                    actualMap[ds].push({abbr, status: 'pending'});
                }
            });
        });

        
        allDates.forEach(date => {
            const dayOfWeek = date.getDay();
            const dateStr = date.toISOString().split('T')[0];
            const isSunday = dayOfWeek === 0;
            const isSaturday = dayOfWeek === 6;
            const isWorkingSaturday = isSaturday && workingSaturdays.has(dateStr);
            const isWeekend = isSunday || (isSaturday && !isWorkingSaturday);
            
            const active = actualMap[dateStr] || [];
            const activeAbbrs = new Set(active.map(x => x.abbr));
            const holdAbbrs = new Set(holdDatesMap[dateStr] || []);
            
            // Filter out holds that overlap with active tasks (matches backend app.py line 454)
            const realHolds = [...holdAbbrs].filter(h => !activeAbbrs.has(h));
            
            const parts = [];
            if (realHolds.length > 0) {
                parts.push(`${realHolds.sort().join(' , ')}=HOLD`);
            }
            if (activeAbbrs.size > 0) {
                parts.push([...activeAbbrs].sort().join(' , '));
            }
            
            const value = parts.join(' , ');
            
            // Determine background color
            // Priority: Weekend > Hold > Completed > Rescheduled > Default
            let bgColor = 'white';
            
            if (isWeekend) {
                bgColor = '#FFFF00'; // Yellow for weekends (highest priority)
            } else if (holdAbbrs.size > 0) {
                bgColor = '#FFA500'; // Orange for hold (second priority - ANY hold dates make it orange)
            } else if (activeAbbrs.size > 0) {
                const stats = new Set(active.map(x => x.status));
                if (stats.has('completed')) {
                    bgColor = '#00FF00'; // Green for completed
                } else if (stats.has('rescheduled')) {
                    bgColor = '#00FFFF'; // Cyan for rescheduled
                }
            }
            
            html += `<td style="border: 1px solid #000; padding: 6px; background: ${bgColor}; text-align: center; font-weight: bold; font-size: 9px; min-width: 50px; vertical-align: middle;">${value}</td>`;
        });
        html += '</tr>';
        
        // ==========================================
        // REMARKS ROW - NEW ADDITION TO MATCH EXCEL
        // ==========================================
        html += '<tr style="height: 60px;">';
        html += '<td style="border: 1px solid #000; padding: 8px;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px; font-weight: bold; font-style: italic; text-align: center;">Remarks</td>';
        
        allDates.forEach(date => {
            const dayOfWeek = date.getDay();
            const dateStr = date.toISOString().split('T')[0];
            const isSunday = dayOfWeek === 0;
            const isSaturday = dayOfWeek === 6;
            const isWorkingSaturday = isSaturday && workingSaturdays.has(dateStr);
            const isWeekend = isSunday || (isSaturday && !isWorkingSaturday);
            
            const active = actualMap[dateStr] || [];
            const activeAbbrs = new Set(active.map(x => x.abbr));
            const holdAbbrs = new Set(holdDatesMap[dateStr] || []);
            const realHolds = [...holdAbbrs].filter(h => !activeAbbrs.has(h));
            
            let remark = '';
            let bgColor = 'white';
            
            if (realHolds.length > 0) {
                remark = "Waiting for issue tracker";
                
                // Try to find the actual reason from tasks
                for (const stage of stages) {
                    const parts = stage.name.split('-');
                    const abbr = parts.length > 1 ? parts[parts.length - 1].trim() : stage.name.substring(0, 6);
                    
                    if (realHolds.includes(abbr)) {
                        // Check for manual hold
                        const task = dailyTasks.find(t => 
                            t.stage_id === stage.id && 
                            t.scheduled_date.split('T')[0] === dateStr && 
                            t.status === 'hold'
                        );
                        
                        // If not found, check for rescheduled hold
                        const rescheduleTask = task || dailyTasks.find(t => 
                            t.stage_id === stage.id && 
                            t.original_date && 
                            t.original_date.split('T')[0] === dateStr
                        );
                        
                        if (rescheduleTask && rescheduleTask.rescheduled_reason) {
                            remark = rescheduleTask.rescheduled_reason;
                            break;
                        }
                    }
                }
            } else if (isWeekend) {
                bgColor = '#FFFF00';
            }
            
            html += `<td style="border: 1px solid #000; padding: 6px; background: ${bgColor}; text-align: left; vertical-align: top; font-size: 9px; min-width: 50px; word-wrap: break-word;">${remark}</td>`;
        });
        html += '</tr>';
        
        // ==========================================
        // SPACING BEFORE LEGEND
        // ==========================================
        html += `<tr><td colspan="${allDates.length + 2}" style="border: none; height: 20px;"></td></tr>`;
        
        // ==========================================
        // LEGEND SECTION - MATCHING EXCEL EXACTLY
        // ==========================================
        html += '<tr style="height: 25px;">';
        html += '<td style="border: 1px solid #000; padding: 8px; background: #FFA500; min-width: 180px;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px; min-width: 150px;">Hold</td>';
        html += '<td colspan="2" style="border: 1px solid #000; padding: 8px;">If project goes on hold from Customer</td>';
        html += '</tr>';
        
        html += '<tr style="height: 25px;">';
        html += '<td style="border: 1px solid #000; padding: 8px; background: white;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px;">Changes</td>';
        html += '<td colspan="2" style="border: 1px solid #000; padding: 8px;"></td>';
        html += '</tr>';
        
        html += '<tr style="height: 25px;">';
        html += '<td style="border: 1px solid #000; padding: 8px; background: #FFFF00;"></td>';
        html += '<td style="border: 1px solid #000; padding: 8px;">Holidays</td>';
        html += '<td colspan="2" style="border: 1px solid #000; padding: 8px;"></td>';
        html += '</tr>';
        
        html += '</table></div>';
        
        // ==========================================
        // CREATE MODAL
        // ==========================================
        const completedTasksCount = dailyTasks.filter(t => t.status === 'completed').length;
        
        const modalHTML = `
            <div class="modal fade" id="exportPreviewModal" tabindex="-1">
                <div class="modal-dialog modal-fullscreen">
                    <div class="modal-content">
                        <div class="modal-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                            <h5 class="modal-title">📊 Excel Preview - ${projData.name} <span style="font-size: 0.8em; opacity: 0.8;">[FIXED v2 - Days ${allDates[0]?.getDate()}-${allDates[allDates.length-1]?.getDate()}]</span></h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" style="background: #f5f5f5; padding: 20px;">
                            <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin-bottom: 15px; border-radius: 5px;">
                                <strong>🔧 Debug Info:</strong> Showing ${allDates.length} days from ${allDates[0]?.toLocaleDateString()} to ${allDates[allDates.length-1]?.toLocaleDateString()} 
                                | Check browser console (F12) for detailed logs
                            </div>
                            ${html}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="fas fa-times me-2"></i>Close Preview
                            </button>
                            <button class="btn btn-success btn-lg" onclick="downloadExcelFromPreview(${projectId})">
                                <i class="fas fa-file-excel me-2"></i> Download Excel File
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const existingModal = document.getElementById('exportPreviewModal');
        if (existingModal) existingModal.remove();
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        const modal = new bootstrap.Modal(document.getElementById('exportPreviewModal'));
        modal.show();
        
        document.getElementById('exportPreviewModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
        
        showNotification(`✅ Preview loaded with ${stages.length} stages!`, 'success');
        
    } catch (error) {
        console.error('Preview error:', error);
        showNotification('❌ Preview error: ' + error.message, 'error');
    }
}

// Keep these at the end
window.showExportPreview = showExcelPreview;
console.log('✅ Excel Preview with stage data loaded!');

async function downloadExcelFromPreview(projectId) {
    try {
        showNotification('📥 Generating Excel file...', 'info');
        
        const response = await fetch(`/api/projects/${projectId}/export-excel`);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `Project_${projectId}_Tracker.xlsx`;
        
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?(.+)"?/i);
            if (match) filename = match[1];
        }
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        }, 100);
        
        showNotification('✅ Excel file downloaded: ' + filename, 'success');
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('exportPreviewModal'));
        if (modal) modal.hide();
        
    } catch (error) {
        console.error('Download error:', error);
        showNotification('❌ Download failed: ' + error.message, 'error');
    }
}

window.showExportPreview = showExcelPreview;
console.log('✅ Excel Preview with stage data loaded!');


// Override just the export function to work with the current preview
window.exportCurrentProject = async function(projectId) {
    try {
        console.log('Export button clicked for project:', projectId);
        showNotification('Preparing Excel export...', 'info');
        
        const response = await fetch(`/api/projects/${projectId}/export-excel`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `Project_${projectId}_${new Date().toISOString().split('T')[0]}.xlsx`;
        
        document.body.appendChild(a);
        a.click();
        
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('Excel file downloaded successfully!', 'success');
        
    } catch (error) {
        console.error('Export error:', error);
        showNotification('Export failed: ' + error.message, 'error');
    }
};

console.log('✅ Export function fixed!');


// Load projects with caching
async function loadProjects() {
    try {
        const response = await fetch(`/api/projects?_t=${Date.now()}`, {
            cache: 'no-store',
            headers: {'Cache-Control': 'no-cache'}
        });
        projects = await response.json();
        allProjectsCache = projects;
        
        // Initial filter and display
        handleProjectSearch();
        
    } catch (error) {
        console.error('Error loading projects:', error);
        const container = document.getElementById('allProjectsSection');
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Error loading jobs: ${error.message}
                <button class="btn btn-sm btn-outline-danger ms-3" onclick="loadProjects()">
                    <i class="fas fa-redo me-1"></i> Retry
                </button>
            </div>
        `;
    }
}
// ✅ NEW FUNCTION: Handle clicks on parallel stages
function setupParallelStageClickHandlers() {
    document.querySelectorAll('.stage-group-container').forEach(container => {
        // Add click event to the container
        container.addEventListener('click', function(e) {
            const stageStep = e.target.closest('.progress-step');
            
            if (stageStep && stageStep.getAttribute('data-in-parallel') === 'true') {
                const stageId = parseInt(stageStep.getAttribute('data-stage-id'));
                const projectId = parseInt(stageStep.getAttribute('data-project-id'));
                
                // Get current status from circle classes
                const circle = stageStep.querySelector('.step-circle');
                let currentStatus = 'pending';
                
                if (circle.classList.contains('completed')) {
                    currentStatus = 'completed';
                } else if (circle.classList.contains('active')) {
                    currentStatus = 'in-progress';
                }
                
                // Update the stage
                updateStageStatus(projectId, stageId, currentStatus);
            }
        });
        
        // Make parallel stages look clickable
        container.querySelectorAll('.progress-step[data-in-parallel="true"]').forEach(step => {
            step.style.cursor = 'pointer';
        });
    });
}

// Handle search with debouncing
function handleProjectSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        performSearch();
    }, 300); // Wait 300ms after user stops typing
}

// Perform the actual search and filter
function performSearch() {
    const searchTerm = document.getElementById('projectSearchInput').value.toLowerCase().trim();
    const statusFilter = document.getElementById('statusFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    
    // Show/hide clear button
    document.getElementById('clearSearchBtn').style.display = searchTerm ? 'block' : 'none';
    
    // Filter projects
    filteredProjects = allProjectsCache.filter(project => {
        const matchesSearch = searchTerm === '' || 
            project.name.toLowerCase().includes(searchTerm) ||
            (project.description && project.description.toLowerCase().includes(searchTerm)) ||
            (project.start_date && project.start_date.includes(searchTerm)) ||
            (project.end_date && project.end_date.includes(searchTerm));
        
        const matchesStatus = statusFilter === '' || project.status === statusFilter;
        
        return matchesSearch && matchesStatus;
    });
    
    // Sort projects
    filteredProjects.sort((a, b) => {
        switch(sortBy) {
            case 'newest':
                return new Date(b.created_at || 0) - new Date(a.created_at || 0);
            case 'oldest':
                return new Date(a.created_at || 0) - new Date(b.created_at || 0);
            case 'name':
                return a.name.localeCompare(b.name);
            case 'progress':
                return (b.progress || 0) - (a.progress || 0);
            default:
                return 0;
        }
    });
    
    // Update results count
    document.getElementById('resultsCount').textContent = 
        `Showing ${filteredProjects.length} job${filteredProjects.length !== 1 ? 's' : ''}`;
    
    // Reset to first page
    currentPage = 1;
    
    // Display results
    displayPaginatedProjects();
}

// Display projects with pagination
async function displayPaginatedProjects() {
    const container = document.getElementById('allProjectsSection');
    
    if (filteredProjects.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <i class="fas fa-search"></i>
                <h5>No jobs found</h5>
                <p>Try adjusting your search or filters</p>
            </div>
        `;
        updatePaginationControls();
        return;
    }
    
    // Show loading spinner
    container.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    
    // Calculate pagination
    const startIndex = (currentPage - 1) * projectsPerPage;
    const endIndex = startIndex + projectsPerPage;
    const projectsToDisplay = filteredProjects.slice(startIndex, endIndex);
    
    // Fetch details for visible projects only
    const projectsWithDetails = await Promise.all(
        projectsToDisplay.map(async (project) => {
            try {
                const response = await fetch(`/api/projects/${project.id}/details`);
                return await response.json();
            } catch (error) {
                console.error(`Error loading project ${project.id}:`, error);
                return null;
            }
        })
    );
    
    // Filter out failed requests
    const validProjects = projectsWithDetails.filter(p => p !== null);
    
    // Render projects
    renderProjectsWithStages(validProjects);
    
    // Update pagination controls
    updatePaginationControls();
}

// Update pagination controls
function updatePaginationControls() {
    const totalPages = Math.ceil(filteredProjects.length / projectsPerPage);
    const container = document.getElementById('allProjectsSection');
    
    let paginationHTML = '';
    
    if (totalPages > 1) {
        paginationHTML = `
            <div class="pagination-container">
                <button class="pagination-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i> Previous
                </button>
                
                <span class="pagination-info">
                    Page ${currentPage} of ${totalPages}
                </span>
                
                <button class="pagination-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                    Next <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
    }
    
    container.insertAdjacentHTML('beforeend', paginationHTML);
}

// Navigate to specific page
function goToPage(page) {
    const totalPages = Math.ceil(filteredProjects.length / projectsPerPage);
    
    if (page < 1 || page > totalPages) return;
    
    currentPage = page;
    displayPaginatedProjects();
    
    // Scroll to top of projects section
    document.getElementById('allProjectsSection').scrollIntoView({ behavior: 'smooth' });
}

// Clear search
function clearProjectSearch() {
    document.getElementById('projectSearchInput').value = '';
    document.getElementById('statusFilter').value = '';
    document.getElementById('sortBy').value = 'newest';
    handleProjectSearch();
}




// ============================================================================
// EDIT PROJECT FUNCTIONALITY
// ============================================================================

let isEditMode = false;
let editingProjectId = null;

async function openEditProjectModal(projectId, event) {
    if (event) event.stopPropagation();
    
    try {
        // ⭐ Clear any old cached data first ⭐
        window.originalProjectData = null;
        
        console.log('=== OPENING EDIT MODAL ===');
        console.log('Project ID:', projectId);
        
        showNotification('Loading job details...', 'info');
        
        // Fetch project details
        const response = await fetch(`/api/projects/${projectId}/details`);
        const project = await response.json();

        // ⭐ Store fresh original data ⭐
        window.originalProjectData = project;

        console.log('Loaded project:', project);
        
        // Set edit mode
        isEditMode = true;
        editingProjectId = projectId;
        
        console.log('Set isEditMode to:', isEditMode);
        console.log('Set editingProjectId to:', editingProjectId);
        
        // Update modal title
        document.querySelector('#projectModal .modal-title').textContent = 'Edit Job';
        
        // Update submit button text
        document.querySelector('#projectForm button[type="submit"]').textContent = 'Update Job';
        
        // Fill in basic project info
        document.getElementById('projectName').value = project.name;
        document.getElementById('projectStartDate').value = project.start_date;
        
        // Load working Saturdays
        workingSaturdays.clear();
        if (project.saturdayWorkingDays) {
            project.saturdayWorkingDays.forEach(date => workingSaturdays.add(date));
        }
        
        // Load employees first
        await loadEmployees();
        
        // Fill in members
        selectedMembers = project.members.map(m => m.id);
        const membersContainer = document.getElementById('selectedMembers');
        membersContainer.innerHTML = '';
        project.members.forEach(member => {
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary me-2 mb-2';
            badge.innerHTML = `
                ${member.username}
                <i class="fas fa-times ms-2" style="cursor: pointer;" onclick="removeMember(${member.id})"></i>
            `;
            membersContainer.appendChild(badge);
        });
        
        // Clear stages container
        stageCounter = 0;
        document.getElementById('stagesContainer').innerHTML = '';
        
        // Load stages
        for (const stage of project.stages) {
            addEditStage(stage);
        }
        
        // Update projected end date
        if (typeof updateProjectEndDate === 'function') {
            updateProjectEndDate();
        }
        
        // Show modal
        projectModal.show();
        
        showNotification('Job loaded successfully', 'success');
        
    } catch (error) {
        console.error('Error loading project for edit:', error);
        showNotification('Error loading job details: ' + error.message, 'error');
    }
}

// Add stage for editing
function addEditStage(stageData) {
    const stageId = stageCounter++;
    const container = document.getElementById('stagesContainer');
    
    const stageDiv = document.createElement('div');
    stageDiv.id = `stage-${stageId}`;
    stageDiv.className = 'stage-item p-2 mb-2 border rounded';
    stageDiv.style.backgroundColor = '#f8f9fa';
    
    // ✅ Store database ID for updates
    if (stageData.id) {
        stageDiv.setAttribute('data-db-id', stageData.id);
    }
    
    // ✅ NEW: Store original values for change detection
    if (stageData.name) {
        stageDiv.setAttribute('data-original-name', stageData.name);
    }
    if (stageData.duration_days) {
        stageDiv.setAttribute('data-original-duration', stageData.duration_days);
    }
    
    stageDiv.innerHTML = `
        <div class="d-flex align-items-start gap-2">
            <div style="min-width: 30px;">
                <input type="checkbox" class="form-check-input mt-1" id="stageCheck-${stageId}" checked>
            </div>
            <div class="flex-grow-1">
                <div class="row g-2">
                    <div class="col-md-6">
                        <input type="text" class="form-control form-control-sm" id="stageName-${stageId}" 
                               placeholder="Stage name" value="${stageData.name || ''}" style="font-size: 0.85rem;">
                    </div>
                    <div class="col-md-3">
                        <div class="input-group input-group-sm">
                            <input type="number" class="form-control" id="stageDuration-${stageId}" 
                                   value="${stageData.duration_days || 1}" min="1" onchange="updateProjectEndDate()" style="font-size: 0.85rem;">
                            <span class="input-group-text" style="font-size: 0.75rem;">days</span>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <select class="form-select form-select-sm" id="stageManager-${stageId}" style="font-size: 0.85rem;">
                            <option value="">No manager</option>
                        </select>
                    </div>
                </div>
                <div class="row g-2 mt-1">
                    <div class="col-md-6">
                        <input type="date" class="form-control form-control-sm" id="stageStartDate-${stageId}" 
                               value="${stageData.start_date || ''}"
                               data-is-custom="${stageData.start_date ? 'true' : 'false'}"
                               onchange="this.setAttribute('data-is-custom','true'); updateProjectEndDate();" style="font-size: 0.85rem;">
                        <small class="text-muted" style="font-size: 0.7rem;">Custom start (optional)</small>
                    </div>
                </div>
            </div>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeStage(${stageId})" style="font-size: 0.75rem;">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    container.appendChild(stageDiv);
    
    // Populate manager dropdown
    const managerSelect = document.getElementById(`stageManager-${stageId}`);
    if (typeof employees !== 'undefined' && employees && employees.length > 0) {
        employees.forEach(emp => {
            const option = document.createElement('option');
            option.value = emp.id;
            option.textContent = `${emp.username} (${emp.role})`;
            if (stageData.manager_id && emp.id === stageData.manager_id) {
                option.selected = true;
            }
            managerSelect.appendChild(option);
        });
    }
}

// ============================================================================
// PROGRESS LINE STATUS UPDATE FUNCTIONALITY
// ============================================================================

// Update progress line with calendar status
async function updateProgressLineStatus(projectId) {
    try {
        console.log(`[Progress Line] Fetching status for project ${projectId}...`);
        const response = await fetch(`/api/projects/${projectId}/stage-status`);
        const data = await response.json();
        
        if (data.success) {
            console.log(`[Progress Line] Received ${data.stages.length} stages:`, data.stages);
            
            let updatedCount = 0;
            data.stages.forEach(stage => {
                // Find the circle element for this stage
                const stepElement = document.querySelector(`[data-stage-id="${stage.id}"]`);
                const circleElement = stepElement ? stepElement.querySelector('.step-circle') : null;
                
                if (circleElement) {
                    // Remove all status classes
                    circleElement.classList.remove(
                        'not-started', 
                        'in-progress', 
                        'completed', 
                        'completed-rescheduled',
                        'overdue',
                        'active'  // Remove legacy class
                    );
                    
                    // Add new status class
                    circleElement.classList.add(stage.status);
                    updatedCount++;
                    
                    console.log(`[Progress Line] ✓ Updated stage "${stage.name}" (ID: ${stage.id}) to ${stage.status} (rescheduled: ${stage.was_rescheduled})`);
                    
                    // Optional: Add tooltip with details
                    let tooltipText = `${stage.name}\nStatus: ${stage.status}\nProgress: ${stage.progress}%`;
                    if (stage.was_rescheduled) {
                        tooltipText += `\nRescheduled ${stage.reschedule_count} time(s)`;
                    }
                    circleElement.title = tooltipText;
                } else {
                    console.warn(`[Progress Line] ⚠️ Could not find element for stage "${stage.name}" (ID: ${stage.id})`);
                }
            });
            
            console.log(`[Progress Line] ✅ Updated ${updatedCount}/${data.stages.length} circles`);
        } else {
            console.error('[Progress Line] API returned success: false', data);
        }
    } catch (error) {
        console.error('[Progress Line] Error updating progress line status:', error);
    }
}

// Auto-refresh progress line every 30 seconds
let progressRefreshIntervals = {};

function startProgressLineAutoRefresh(projectId) {
    // Clear existing interval for this project
    if (progressRefreshIntervals[projectId]) {
        clearInterval(progressRefreshIntervals[projectId]);
    }
    
    // Initial update
    updateProgressLineStatus(projectId);
    
    // Set up auto-refresh
    progressRefreshIntervals[projectId] = setInterval(() => {
        updateProgressLineStatus(projectId);
    }, 30000); // Refresh every 30 seconds
}

// Stop auto-refresh when needed
function stopProgressLineAutoRefresh(projectId) {
    if (progressRefreshIntervals[projectId]) {
        clearInterval(progressRefreshIntervals[projectId]);
        delete progressRefreshIntervals[projectId];
    }
}

// Stop all auto-refresh intervals
function stopAllProgressLineAutoRefresh() {
    Object.keys(progressRefreshIntervals).forEach(projectId => {
        stopProgressLineAutoRefresh(projectId);
    });
}


// Helper function to reset form
function resetProjectForm() {
    document.getElementById('projectForm').reset();
    document.getElementById('stagesContainer').innerHTML = '';
    document.getElementById('selectedMembers').innerHTML = '';
    document.querySelector('#projectModal .modal-title').textContent = 'Create New Job';
    document.querySelector('#projectForm button[type="submit"]').textContent = 'Create Job';
    stageCounter = 0;
    selectedMembers = [];
    workingSaturdays.clear();
    isEditMode = false;
    editingProjectId = null;
}
</script>
</body>
</html>
