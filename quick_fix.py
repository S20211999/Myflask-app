# UPDATED ADMIN APP - With Email Notifications & Live Monitoring

import sys
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QComboBox, QCheckBox, QDateTimeEdit,
    QSpinBox, QTabWidget, QListWidget, QListWidgetItem, QScrollArea,
    QGridLayout, QHeaderView, QFrame, QProgressBar, QStatusBar,
    QMenuBar, QMenu, QInputDialog, QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt, QDateTime, QSize, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# ============================================================================
# EMAIL CONFIGURATION - Add your SMTP settings
# ============================================================================
EMAIL_ENABLED = True  # Set to True when you configure email settings
SMTP_SERVER = "smtp.gmail.com"  # e.g., Gmail SMTP server
SMTP_PORT = 587
SENDER_EMAIL = "sciary@gmail.com"  # Your email
SENDER_PASSWORD = ""  # Gmail App Password (not regular password)

# ============================================================================
# CONFIGURATION
# ============================================================================
CREDENTIALS_FILE = "online-exam-477315-6c00539fc553.json"
SPREADSHEET_ID = "1Ahx7MKPuTDxzPBqsV5UHTnjSkE7e0NVz9EYHfQ4USKc"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ============================================================================
# GOOGLE SHEETS MANAGER
# ============================================================================
class GoogleSheetsManager:
    """Manages all Google Sheets operations"""
    def __init__(self, credentials_file, spreadsheet_id):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self.connect()

    def connect(self):
        """Connect to Google Sheets using Sheet ID"""
        try:
            import os
            if not os.path.exists(self.credentials_file):
                raise FileNotFoundError(
                    f"❌ {self.credentials_file} not found!\n\n"
                    f"Download from Google Cloud Console and place in this folder"
                )

            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            print(f"🔑 Connecting with Sheet ID: {self.spreadsheet_id}")
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"✅ Connected! Sheet: {self.spreadsheet.title}")
            self.setup_sheets()

        except FileNotFoundError as e:
            raise Exception(str(e))
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(
                f"❌ Sheet ID not found: {self.spreadsheet_id}\n\n"
                f"Make sure:\n"
                f"1. Sheet ID is correct\n"
                f"2. Sheet is shared with service account\n"
                f"3. Google Drive API is enabled"
            )
        except Exception as e:
            raise Exception(f"Connection failed: {str(e)}")

    def setup_sheets(self):
        """Create required worksheets with headers"""
        # Students sheet
        try:
            students_sheet = self.spreadsheet.worksheet("Students")
        except:
            students_sheet = self.spreadsheet.add_worksheet("Students", 1000, 10)
            students_sheet.append_row([
                "id", "name", "username", "password", "email", "roll_number", "group_name", "created_at"
            ])

        # Questions sheet
        try:
            questions_sheet = self.spreadsheet.worksheet("Questions")
        except:
            questions_sheet = self.spreadsheet.add_worksheet("Questions", 1000, 10)
            questions_sheet.append_row([
                "id", "question", "option1", "option2", "option3", "option4",
                "correct_answer", "subject", "marks", "created_at"
            ])

        # Exams sheet
        try:
            exams_sheet = self.spreadsheet.worksheet("Exams")
        except:
            exams_sheet = self.spreadsheet.add_worksheet("Exams", 1000, 15)
            exams_sheet.append_row([
                "exam_id", "exam_name", "description", "start_datetime", "duration_minutes",
                "passing_percentage", "camera_required", "tab_switch_limit", "total_marks",
                "question_ids", "student_ids", "created_at"
            ])

        # Results sheet
        try:
            results_sheet = self.spreadsheet.worksheet("Results")
        except:
            results_sheet = self.spreadsheet.add_worksheet("Results", 1000, 12)
            results_sheet.append_row([
                "id", "exam_id", "student_id", "score", "total_marks", "percentage",
                "time_taken", "answers_json", "submitted_at"
            ])

        # SecurityLog sheet for live monitoring
        try:
            security_sheet = self.spreadsheet.worksheet("SecurityLog")
        except:
            security_sheet = self.spreadsheet.add_worksheet("SecurityLog", 1000, 6)
            security_sheet.append_row([
                "id", "student_id", "exam_id", "event_type", "details", "timestamp"
            ])

        print("✓ All worksheets ready!")

    # Students operations
    def add_student(self, data):
        """Add new student"""
        sheet = self.spreadsheet.worksheet("Students")
        records = sheet.get_all_records()
        new_id = len(records) + 1
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        # Fix datetime format: Use proper ISO format
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            new_id,
            data['name'],
            data['username'],
            password_hash,
            data['email'],
            data['roll_number'],
            data['group_name'],
            created_at
        ]
        sheet.append_row(row)
        return new_id

    def get_all_students(self):
        """Get all students"""
        sheet = self.spreadsheet.worksheet("Students")
        return sheet.get_all_records()

    def get_student_by_id(self, student_id):
        """Get student details by ID"""
        sheet = self.spreadsheet.worksheet("Students")
        records = sheet.get_all_records()
        for student in records:
            if int(student['id']) == student_id:
                return student
        return None

    def delete_student(self, student_id):
        """Delete student by ID"""
        sheet = self.spreadsheet.worksheet("Students")
        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record['id']) == student_id:
                sheet.delete_rows(i)
                return True
        return False

    # Questions operations
    def add_question(self, data):
        """Add new question"""
        sheet = self.spreadsheet.worksheet("Questions")
        records = sheet.get_all_records()
        new_id = len(records) + 1
        
        # Fix datetime format
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            new_id,
            data['question'],
            data['option1'],
            data['option2'],
            data['option3'],
            data['option4'],
            data['correct_answer'],
            data['subject'],
            data['marks'],
            created_at
        ]
        sheet.append_row(row)
        return new_id

    def get_all_questions(self):
        """Get all questions"""
        sheet = self.spreadsheet.worksheet("Questions")
        return sheet.get_all_records()

    def delete_question(self, question_id):
        """Delete question by ID"""
        sheet = self.spreadsheet.worksheet("Questions")
        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record['id']) == question_id:
                sheet.delete_rows(i)
                return True
        return False

    # Exams operations
    def add_exam(self, data):
        """Add new exam"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        new_id = len(records) + 1
        
        # Fix datetime format
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            new_id,
            data['exam_name'],
            data['description'],
            data['start_datetime'],
            data['duration_minutes'],
            data['passing_percentage'],
            data['camera_required'],
            data['tab_switch_limit'],
            data['total_marks'],
            json.dumps(data['question_ids']),
            json.dumps(data['student_ids']),
            created_at
        ]
        sheet.append_row(row)
        return new_id

    def get_all_exams(self):
        """Get all exams"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        for record in records:
            record['question_ids'] = json.loads(record['question_ids']) if record['question_ids'] else []
            record['student_ids'] = json.loads(record['student_ids']) if record['student_ids'] else []
        return records

    def get_exam_by_id(self, exam_id):
        """Get exam details by ID"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        for exam in records:
            if int(exam['exam_id']) == exam_id:
                exam['question_ids'] = json.loads(exam['question_ids']) if exam['question_ids'] else []
                exam['student_ids'] = json.loads(exam['student_ids']) if exam['student_ids'] else []
                return exam
        return None

    def delete_exam(self, exam_id):
        """Delete exam by ID"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record['exam_id']) == exam_id:
                sheet.delete_rows(i)
                return True
        return False

    def update_exam_students(self, exam_id, student_ids):
        """Update student list for an exam (for kickout functionality)"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record['exam_id']) == exam_id:
                # Update student_ids column
                sheet.update_cell(i, 11, json.dumps(student_ids))  # Column 11 is student_ids
                return True
        return False

    # Security logs for live monitoring
    def get_security_logs(self, exam_id=None, student_id=None):
        """Get security logs with optional filters"""
        try:
            sheet = self.spreadsheet.worksheet("SecurityLog")
            records = sheet.get_all_records()
            
            filtered = []
            for record in records:
                if exam_id and int(record.get('exam_id', 0)) != exam_id:
                    continue
                if student_id and int(record.get('student_id', 0)) != student_id:
                    continue
                filtered.append(record)
            
            return filtered
        except:
            return []

    def get_violation_count(self, exam_id, student_id):
        """Get violation count for a specific student in an exam"""
        logs = self.get_security_logs(exam_id=exam_id, student_id=student_id)
        return len(logs)

    # Results operations
    def get_all_results(self):
        """Get all results"""
        sheet = self.spreadsheet.worksheet("Results")
        return sheet.get_all_records()

# Global sheets manager
sheets_manager = None

# ============================================================================
# EMAIL SENDER
# ============================================================================
def send_credentials_email(student_email, student_name, username, password, exam_name, exam_start):
    """Send login credentials via email"""
    if not EMAIL_ENABLED:
        print(f"⚠️ Email disabled. Would send to {student_email}")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = student_email
        msg['Subject'] = f"Exam Credentials: {exam_name}"

        body = f"""
Dear {student_name},

You have been assigned to the following exam:

📝 Exam: {exam_name}
📅 Start Time: {exam_start}

Your login credentials:
👤 Username: {username}
🔒 Password: {password}

Please login to the Student Exam Portal to take your exam.

Important:
- Login before the exam start time
- Ensure stable internet connection
- Keep your webcam enabled during the exam
- Do not switch tabs during the exam

Good luck!

Regards,
Exam Administration Team
        """

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, student_email, text)
        server.quit()

        print(f"✅ Email sent to {student_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email to {student_email}: {str(e)}")
        return False

# ============================================================================
# STYLES
# ============================================================================
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
    color: #e0e0e0;
}
QWidget {
    background-color: #1e1e2e;
    color: #e0e0e0;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
    color: white;
    padding: 12px 25px;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    font-size: 12px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5568d3, stop:1 #6a3f8f);
}
QLineEdit, QTextEdit {
    background-color: #2d2d44;
    color: #e0e0e0;
    border: 2px solid #3d3d54;
    border-radius: 6px;
    padding: 8px 12px;
}
QTableWidget {
    background-color: #2d2d44;
    gridline-color: #3d3d54;
    border: 1px solid #3d3d54;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d3d54, stop:1 #2d2d44);
    color: #e0e0e0;
    padding: 6px;
    border: none;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #3d3d54;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #2d2d44;
    color: #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #667eea;
}
"""

# ============================================================================
# DIALOGS - Same as before but add email notification checkbox
# ============================================================================
class AddStudentDialog(QDialog):
    """Add new student dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("➕ Add New Student")
        self.setGeometry(300, 300, 500, 600)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Add New Student")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        self.name_input = self.create_input_field("📝 Full Name", "John Doe")
        layout.addLayout(self.name_input[1])

        self.username_input = self.create_input_field("👤 Username", "johndoe")
        layout.addLayout(self.username_input[1])

        self.password_input = self.create_input_field("🔒 Password", "password")
        self.password_input[0].setEchoMode(QLineEdit.EchoMode.Password)
        layout.addLayout(self.password_input[1])

        self.email_input = self.create_input_field("📧 Email", "john@example.com")
        layout.addLayout(self.email_input[1])

        self.roll_input = self.create_input_field("📌 Roll Number", "001")
        layout.addLayout(self.roll_input[1])

        self.group_input = self.create_input_field("👥 Group", "A")
        layout.addLayout(self.group_input[1])

        layout.addStretch()

        button_layout = QHBoxLayout()
        save_btn = QPushButton("✓ Save Student")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_input_field(self, label_text, placeholder):
        """Create labeled input field"""
        layout = QVBoxLayout()
        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(label)

        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setMinimumHeight(40)
        layout.addWidget(input_field)

        return (input_field, layout)

    def get_data(self):
        """Get form data"""
        return {
            "name": self.name_input[0].text(),
            "username": self.username_input[0].text(),
            "password": self.password_input[0].text(),
            "email": self.email_input[0].text(),
            "roll_number": self.roll_input[0].text(),
            "group_name": self.group_input[0].text()
        }

class AddQuestionDialog(QDialog):
    """Add new question dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("➕ Add New Question")
        self.setGeometry(300, 300, 600, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Add New Question")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        q_label = QLabel("❓ Question Text")
        q_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(q_label)

        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("Enter the question...")
        self.question_input.setMinimumHeight(100)
        layout.addWidget(self.question_input)

        opt_label = QLabel("🎯 Answer Options")
        opt_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(opt_label)

        self.options = []
        for i in range(4):
            opt = QLineEdit()
            opt.setPlaceholderText(f"Option {i+1}")
            opt.setMinimumHeight(40)
            self.options.append(opt)
            layout.addWidget(opt)

        ans_layout = QHBoxLayout()
        ans_label = QLabel("✓ Correct Answer:")
        ans_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        ans_layout.addWidget(ans_label)

        self.correct_answer = QComboBox()
        self.correct_answer.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])
        ans_layout.addWidget(self.correct_answer)
        ans_layout.addStretch()
        layout.addLayout(ans_layout)

        meta_layout = QHBoxLayout()
        subject_label = QLabel("📚 Subject:")
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g., Math")
        meta_layout.addWidget(subject_label)
        meta_layout.addWidget(self.subject_input)

        marks_label = QLabel("⭐ Marks:")
        self.marks_input = QSpinBox()
        self.marks_input.setValue(1)
        self.marks_input.setMinimum(1)
        meta_layout.addWidget(marks_label)
        meta_layout.addWidget(self.marks_input)

        layout.addLayout(meta_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()
        save_btn = QPushButton("✓ Save Question")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        """Get form data"""
        return {
            "question": self.question_input.toPlainText(),
            "option1": self.options[0].text(),
            "option2": self.options[1].text(),
            "option3": self.options[2].text(),
            "option4": self.options[3].text(),
            "correct_answer": self.correct_answer.currentIndex(),
            "subject": self.subject_input.text(),
            "marks": self.marks_input.value()
        }

class CreateExamDialog(QDialog):
    """Create new exam dialog - WITH EMAIL NOTIFICATION OPTION"""
    def __init__(self, parent=None, students=None, questions=None):
        super().__init__(parent)
        self.students = students or []
        self.questions = questions or []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📝 Create New Exam")
        self.setFixedSize(900, 780)
        self.setStyleSheet(DARK_STYLESHEET)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Create New Exam")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        main_layout.addWidget(title)

        # Basic info
        name_label = QLabel("Exam Name:")
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.exam_name = QLineEdit()
        self.exam_name.setPlaceholderText("e.g., Physics Final Exam")
        self.exam_name.setMinimumHeight(40)
        main_layout.addWidget(name_label)
        main_layout.addWidget(self.exam_name)

        desc_label = QLabel("Description:")
        desc_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.description = QTextEdit()
        self.description.setPlaceholderText("Enter exam description...")
        self.description.setMinimumHeight(80)
        main_layout.addWidget(desc_label)
        main_layout.addWidget(self.description)

        # Settings
        settings_layout = QGridLayout()

        start_label = QLabel("Start DateTime:")
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setDateTime(QDateTime.currentDateTime())
        settings_layout.addWidget(start_label, 0, 0)
        settings_layout.addWidget(self.start_datetime, 0, 1)

        duration_label = QLabel("Duration (min):")
        self.duration = QSpinBox()
        self.duration.setValue(60)
        self.duration.setMinimum(10)
        self.duration.setMaximum(600)
        settings_layout.addWidget(duration_label, 0, 2)
        settings_layout.addWidget(self.duration, 0, 3)

        passing_label = QLabel("Passing %:")
        self.passing = QSpinBox()
        self.passing.setValue(40)
        self.passing.setMinimum(0)
        self.passing.setMaximum(100)
        settings_layout.addWidget(passing_label, 1, 0)
        settings_layout.addWidget(self.passing, 1, 1)

        marks_label = QLabel("Total Marks:")
        self.total_marks = QSpinBox()
        self.total_marks.setValue(100)
        self.total_marks.setMinimum(1)
        self.total_marks.setMaximum(1000)
        settings_layout.addWidget(marks_label, 1, 2)
        settings_layout.addWidget(self.total_marks, 1, 3)

        tab_label = QLabel("Tab Switch Limit:")
        self.tab_limit = QSpinBox()
        self.tab_limit.setValue(3)
        self.tab_limit.setMinimum(0)
        settings_layout.addWidget(tab_label, 2, 0)
        settings_layout.addWidget(self.tab_limit, 2, 1)

        self.camera_required = QCheckBox("📷 Require Webcam")
        self.camera_required.setChecked(True)
        settings_layout.addWidget(self.camera_required, 2, 2)

        # NEW: Email notification checkbox
        self.send_email = QCheckBox("📧 Send Credentials via Email")
        self.send_email.setChecked(EMAIL_ENABLED)
        self.send_email.setEnabled(EMAIL_ENABLED)
        settings_layout.addWidget(self.send_email, 2, 3)

        main_layout.addLayout(settings_layout)

        # Students and Questions
        content_layout = QHBoxLayout()

        # Students
        students_layout = QVBoxLayout()
        students_label = QLabel("👥 Select Students")
        students_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        students_layout.addWidget(students_label)

        self.students_list = QListWidget()
        self.students_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for student in self.students:
            item = QListWidgetItem(f"{student['name']} ({student['username']})")
            item.setData(Qt.ItemDataRole.UserRole, student['id'])
            self.students_list.addItem(item)
        students_layout.addWidget(self.students_list)

        select_all_students = QPushButton("✓ Select All")
        select_all_students.clicked.connect(lambda: self.students_list.selectAll())
        students_layout.addWidget(select_all_students)

        content_layout.addLayout(students_layout)

        # Questions
        questions_layout = QVBoxLayout()
        questions_label = QLabel("❓ Select Questions")
        questions_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        questions_layout.addWidget(questions_label)

        self.questions_list = QListWidget()
        self.questions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for question in self.questions:
            q_text = question['question'][:50]
            item = QListWidgetItem(f"{q_text}... [{question['subject']}]")
            item.setData(Qt.ItemDataRole.UserRole, question['id'])
            self.questions_list.addItem(item)
        questions_layout.addWidget(self.questions_list)

        select_all_questions = QPushButton("✓ Select All")
        select_all_questions.clicked.connect(lambda: self.questions_list.selectAll())
        questions_layout.addWidget(select_all_questions)

        content_layout.addLayout(questions_layout)
        main_layout.addLayout(content_layout)

        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("✓ Create Exam")
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_data(self):
        """Get form data"""
        selected_students = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.students_list.selectedItems()
        ]

        selected_questions = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.questions_list.selectedItems()
        ]

        if not self.exam_name.text().strip():
            QMessageBox.warning(self, "Error", "Please enter exam name")
            return None

        if not selected_students:
            QMessageBox.warning(self, "Error", "Please select at least one student")
            return None

        if not selected_questions:
            QMessageBox.warning(self, "Error", "Please select at least one question")
            return None

        return {
            "exam_name": self.exam_name.text().strip(),
            "description": self.description.toPlainText().strip(),
            "start_datetime": self.start_datetime.dateTime().toString("yyyy-MM-dd HH:mm"),
            "duration_minutes": self.duration.value(),
            "passing_percentage": self.passing.value(),
            "camera_required": 1 if self.camera_required.isChecked() else 0,
            "tab_switch_limit": self.tab_limit.value(),
            "total_marks": self.total_marks.value(),
            "question_ids": selected_questions,
            "student_ids": selected_students,
            "send_email": self.send_email.isChecked()
        }

# ============================================================================
# LIVE MONITORING TAB
# ============================================================================
class LiveMonitoringTab(QWidget):
    """Live monitoring tab for a specific exam"""
    def __init__(self, exam, parent=None):
        super().__init__(parent)
        self.exam = exam
        self.init_ui()
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Exam info header
        header = QLabel(f"📝 {self.exam['exam_name']} - Live Monitoring")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #667eea;")
        layout.addWidget(header)

        exam_info = QLabel(
            f"Start: {self.exam['start_datetime']} | "
            f"Duration: {self.exam['duration_minutes']} min | "
            f"Total Students: {len(self.exam['student_ids'])}"
        )
        exam_info.setFont(QFont("Segoe UI", 10))
        exam_info.setStyleSheet("color: #a0a0b0;")
        layout.addWidget(exam_info)

        # Refresh button
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Students table
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(6)
        self.students_table.setHorizontalHeaderLabels([
            "Student ID", "Name", "Email", "Violations", "Status", "Action"
        ])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.students_table)

        self.setLayout(layout)
        self.refresh_data()

    def refresh_data(self):
        """Refresh student data and violation counts"""
        try:
            # Get current exam data (in case students were kicked out)
            exam = sheets_manager.get_exam_by_id(self.exam['exam_id'])
            if not exam:
                return

            self.exam = exam
            student_ids = exam['student_ids']

            self.students_table.setRowCount(len(student_ids))

            for i, student_id in enumerate(student_ids):
                # Get student details
                student = sheets_manager.get_student_by_id(student_id)
                if not student:
                    continue

                # Get violation count
                violation_count = sheets_manager.get_violation_count(
                    self.exam['exam_id'],
                    student_id
                )

                # Populate table
                self.students_table.setItem(i, 0, QTableWidgetItem(str(student_id)))
                self.students_table.setItem(i, 1, QTableWidgetItem(student['name']))
                self.students_table.setItem(i, 2, QTableWidgetItem(student['email']))

                # Violation count with color coding
                violation_item = QTableWidgetItem(str(violation_count))
                if violation_count > 5:
                    violation_item.setForeground(QColor("#ff6b6b"))  # Red
                elif violation_count > 2:
                    violation_item.setForeground(QColor("#ffa500"))  # Orange
                else:
                    violation_item.setForeground(QColor("#52c41a"))  # Green
                self.students_table.setItem(i, 3, violation_item)

                # Status
                status = "🟢 Active"
                self.students_table.setItem(i, 4, QTableWidgetItem(status))

                # Kickout button
                kickout_btn = QPushButton("⛔ Kickout")
                kickout_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b6b, stop:1 #ff5252);
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5555, stop:1 #ff4444);
                    }
                """)
                kickout_btn.clicked.connect(lambda checked, sid=student_id: self.kickout_student(sid))
                self.students_table.setCellWidget(i, 5, kickout_btn)

        except Exception as e:
            print(f"Error refreshing monitoring data: {str(e)}")

    def kickout_student(self, student_id):
        """Remove student from exam (live kickout)"""
        reply = QMessageBox.question(
            self,
            "Confirm Kickout",
            f"Are you sure you want to remove student ID {student_id} from this exam?\n\n"
            "The student will be immediately kicked out and cannot rejoin.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Remove student from exam's student list
                current_students = self.exam['student_ids']
                if student_id in current_students:
                    current_students.remove(student_id)
                    
                    # Update in Google Sheets
                    success = sheets_manager.update_exam_students(
                        self.exam['exam_id'],
                        current_students
                    )

                    if success:
                        # Log the kickout event
                        sheets_manager.log_security_event(
                            student_id,
                            self.exam['exam_id'],
                            "kickout",
                            "Student kicked out by admin"
                        )

                        QMessageBox.information(
                            self,
                            "Success",
                            f"Student ID {student_id} has been kicked out"
                        )
                        self.refresh_data()
                    else:
                        QMessageBox.warning(self, "Error", "Failed to kickout student")
                else:
                    QMessageBox.warning(self, "Error", "Student not found in exam")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to kickout student: {str(e)}")

    def closeEvent(self, event):
        """Stop refresh timer when tab is closed"""
        self.refresh_timer.stop()
        event.accept()

# ============================================================================
# ADMIN LOGIN
# ============================================================================
class AdminLoginWindow(QMainWindow):
    """Admin login window"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)

    def init_ui(self):
        self.setWindowTitle("🔐 Admin Login")
        self.setFixedSize(600, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(30)

        emoji = QLabel("🔑")
        emoji.setFont(QFont("Segoe UI Emoji", 80))
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(emoji)

        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        user_label = QLabel("👤 Username")
        user_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(user_label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter admin username")
        self.username.setMinimumHeight(50)
        layout.addWidget(self.username)

        pass_label = QLabel("🔒 Password")
        pass_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(pass_label)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(50)
        self.password.returnPressed.connect(self.login)
        layout.addWidget(self.password)

        login_btn = QPushButton("🚀 Login")
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setMinimumHeight(60)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        self.status = QLabel("Default: admin / admin123")
        self.status.setFont(QFont("Segoe UI", 10))
        self.status.setStyleSheet("color: #a0a0b0;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        layout.addStretch()
        central_widget.setLayout(layout)

    def login(self):
        """Login to admin panel"""
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Enter username and password")
            return

        # Simple auth for demo
        if username == "admin" and password == "admin123":
            try:
                # Initialize Google Sheets connection
                global sheets_manager
                sheets_manager = GoogleSheetsManager(CREDENTIALS_FILE, SPREADSHEET_ID)

                self.admin_panel = AdminPanel(username)
                self.admin_panel.show()
                self.close()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to connect to Google Sheets:\n{str(e)}")
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
            self.password.clear()

# ============================================================================
# ADMIN PANEL - WITH LIVE MONITORING TABS
# ============================================================================
class AdminPanel(QMainWindow):
    """Main admin panel"""
    def __init__(self, admin_username):
        super().__init__()
        self.admin_username = admin_username
        self.students = []
        self.questions = []
        self.exams = []
        self.results = []
        self.monitoring_tabs = {}  # Track monitoring tabs
        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)
        self.load_all_data()

    def init_ui(self):
        self.setWindowTitle(f"Admin Dashboard - {self.admin_username}")
        self.setGeometry(50, 50, 1600, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 11))
        self.tabs.addTab(self.create_students_tab(), "👥 Students")
        self.tabs.addTab(self.create_questions_tab(), "❓ Questions")
        self.tabs.addTab(self.create_exams_tab(), "📝 Exams")
        self.tabs.addTab(self.create_results_tab(), "📊 Results")
        main_layout.addWidget(self.tabs)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage(f"Ready | Google Sheets: {SPREADSHEET_ID}")

        central_widget.setLayout(main_layout)

    def create_header(self):
        """Create header"""
        header = QFrame()
        header.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
            padding: 20px;
        }
        """)

        layout = QHBoxLayout()

        title = QLabel(f"👤 Welcome, {self.admin_username}!")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        layout.addStretch()

        header.setLayout(layout)
        return header

    def create_students_tab(self):
        """Create students tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Student")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_student)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_students)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.students_table = QTableWidget()
        self.students_table.setColumnCount(7)
        self.students_table.setHorizontalHeaderLabels([
            "ID", "Name", "Username", "Email", "Roll #", "Group", "Action"
        ])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.students_table)

        widget.setLayout(layout)
        return widget

    def create_questions_tab(self):
        """Create questions tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Question")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_question)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_questions)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.questions_table = QTableWidget()
        self.questions_table.setColumnCount(7)
        self.questions_table.setHorizontalHeaderLabels([
            "ID", "Question", "Subject", "Marks", "Correct", "Options", "Action"
        ])
        self.questions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.questions_table)

        widget.setLayout(layout)
        return widget

    def create_exams_tab(self):
        """Create exams tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Create Exam")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.create_exam)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_exams)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.exams_table = QTableWidget()
        self.exams_table.setColumnCount(8)
        self.exams_table.setHorizontalHeaderLabels([
            "ID", "Exam Name", "Start", "Duration", "Students", "Questions", "Monitor", "Action"
        ])
        self.exams_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.exams_table)

        widget.setLayout(layout)
        return widget

    def create_results_tab(self):
        """Create results tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_results)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Student ID", "Exam ID", "Score", "Total", "Percentage", "Time", "Date"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.results_table)

        widget.setLayout(layout)
        return widget

    def load_all_data(self):
        """Load all data from Google Sheets"""
        self.load_students()
        self.load_questions()
        self.load_exams()
        self.load_results()

    def load_students(self):
        """Load students from Google Sheets"""
        try:
            self.students = sheets_manager.get_all_students()
            self.students_table.setRowCount(len(self.students))

            for i, student in enumerate(self.students):
                self.students_table.setItem(i, 0, QTableWidgetItem(str(student['id'])))
                self.students_table.setItem(i, 1, QTableWidgetItem(student['name']))
                self.students_table.setItem(i, 2, QTableWidgetItem(student['username']))
                self.students_table.setItem(i, 3, QTableWidgetItem(student['email']))
                self.students_table.setItem(i, 4, QTableWidgetItem(student['roll_number']))
                self.students_table.setItem(i, 5, QTableWidgetItem(student['group_name']))

                del_btn = QPushButton("🗑 Delete")
                del_btn.clicked.connect(lambda checked, sid=student['id']: self.delete_student(sid))
                self.students_table.setCellWidget(i, 6, del_btn)

            self.status_bar.showMessage(f"Loaded {len(self.students)} students")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load students: {str(e)}")

    def load_questions(self):
        """Load questions from Google Sheets"""
        try:
            self.questions = sheets_manager.get_all_questions()
            self.questions_table.setRowCount(len(self.questions))

            for i, q in enumerate(self.questions):
                self.questions_table.setItem(i, 0, QTableWidgetItem(str(q['id'])))
                self.questions_table.setItem(i, 1, QTableWidgetItem(q['question'][:50] + "..."))
                self.questions_table.setItem(i, 2, QTableWidgetItem(q['subject']))
                self.questions_table.setItem(i, 3, QTableWidgetItem(str(q['marks'])))
                self.questions_table.setItem(i, 4, QTableWidgetItem(f"Option {q['correct_answer']+1}"))
                self.questions_table.setItem(i, 5, QTableWidgetItem(f"{q['option1'][:20]}..."))

                del_btn = QPushButton("🗑 Delete")
                del_btn.clicked.connect(lambda checked, qid=q['id']: self.delete_question(qid))
                self.questions_table.setCellWidget(i, 6, del_btn)

            self.status_bar.showMessage(f"Loaded {len(self.questions)} questions")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")

    def load_exams(self):
        """Load exams from Google Sheets"""
        try:
            self.exams = sheets_manager.get_all_exams()
            self.exams_table.setRowCount(len(self.exams))

            for i, exam in enumerate(self.exams):
                self.exams_table.setItem(i, 0, QTableWidgetItem(str(exam['exam_id'])))
                self.exams_table.setItem(i, 1, QTableWidgetItem(exam['exam_name']))
                self.exams_table.setItem(i, 2, QTableWidgetItem(exam['start_datetime']))
                self.exams_table.setItem(i, 3, QTableWidgetItem(f"{exam['duration_minutes']} min"))
                self.exams_table.setItem(i, 4, QTableWidgetItem(str(len(exam['student_ids']))))
                self.exams_table.setItem(i, 5, QTableWidgetItem(str(len(exam['question_ids']))))

                # NEW: Monitor button
                monitor_btn = QPushButton("📺 Monitor")
                monitor_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #52c41a, stop:1 #389e0d);
                    }
                """)
                monitor_btn.clicked.connect(lambda checked, ex=exam: self.open_monitoring_tab(ex))
                self.exams_table.setCellWidget(i, 6, monitor_btn)

                del_btn = QPushButton("🗑 Delete")
                del_btn.clicked.connect(lambda checked, eid=exam['exam_id']: self.delete_exam(eid))
                self.exams_table.setCellWidget(i, 7, del_btn)

            self.status_bar.showMessage(f"Loaded {len(self.exams)} exams")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load exams: {str(e)}")

    def open_monitoring_tab(self, exam):
        """Open live monitoring tab for exam"""
        exam_id = exam['exam_id']
        
        # Check if tab already exists
        if exam_id in self.monitoring_tabs:
            # Switch to existing tab
            index = self.tabs.indexOf(self.monitoring_tabs[exam_id])
            self.tabs.setCurrentIndex(index)
        else:
            # Create new monitoring tab
            monitoring_tab = LiveMonitoringTab(exam, self)
            tab_name = f"🔴 {exam['exam_name'][:15]}..."
            
            # Add tab on the right side
            index = self.tabs.addTab(monitoring_tab, tab_name)
            self.monitoring_tabs[exam_id] = monitoring_tab
            
            # Make tab closable
            self.tabs.setTabsClosable(True)
            self.tabs.tabCloseRequested.connect(self.close_monitoring_tab)
            
            # Switch to new tab
            self.tabs.setCurrentIndex(index)

    def close_monitoring_tab(self, index):
        """Close monitoring tab"""
        # Don't allow closing first 4 tabs (Students, Questions, Exams, Results)
        if index < 4:
            return
        
        # Remove from tracking dict
        widget = self.tabs.widget(index)
        for exam_id, tab_widget in list(self.monitoring_tabs.items()):
            if tab_widget == widget:
                del self.monitoring_tabs[exam_id]
                break
        
        # Remove tab
        self.tabs.removeTab(index)

    def load_results(self):
        """Load results from Google Sheets"""
        try:
            self.results = sheets_manager.get_all_results()
            self.results_table.setRowCount(len(self.results))

            for i, result in enumerate(self.results):
                self.results_table.setItem(i, 0, QTableWidgetItem(str(result['id'])))
                self.results_table.setItem(i, 1, QTableWidgetItem(str(result['student_id'])))
                self.results_table.setItem(i, 2, QTableWidgetItem(str(result['exam_id'])))
                self.results_table.setItem(i, 3, QTableWidgetItem(str(result['score'])))
                self.results_table.setItem(i, 4, QTableWidgetItem(str(result['total_marks'])))
                self.results_table.setItem(i, 5, QTableWidgetItem(f"{result['percentage']}%"))
                self.results_table.setItem(i, 6, QTableWidgetItem(result['time_taken']))
                self.results_table.setItem(i, 7, QTableWidgetItem(str(result['submitted_at'])[:16]))

            self.status_bar.showMessage(f"Loaded {len(self.results)} results")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load results: {str(e)}")

    def add_student(self):
        """Add new student"""
        dialog = AddStudentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                sheets_manager.add_student(data)
                QMessageBox.information(self, "Success", "Student added successfully!")
                self.load_students()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add student: {str(e)}")

    def add_question(self):
        """Add new question"""
        dialog = AddQuestionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            try:
                sheets_manager.add_question(data)
                QMessageBox.information(self, "Success", "Question added successfully!")
                self.load_questions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add question: {str(e)}")

    def create_exam(self):
        """Create new exam"""
        dialog = CreateExamDialog(self, self.students, self.questions)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    # Create exam
                    exam_id = sheets_manager.add_exam(data)
                    
                    # Send emails if enabled
                    if data.get('send_email', False):
                        self.send_exam_credentials_emails(data, exam_id)
                    
                    QMessageBox.information(self, "Success", "Exam created successfully!")
                    self.load_exams()
                    
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create exam: {str(e)}")

    def send_exam_credentials_emails(self, exam_data, exam_id):
        """Send credential emails to all assigned students"""
        student_ids = exam_data['student_ids']
        exam_name = exam_data['exam_name']
        exam_start = exam_data['start_datetime']
        
        success_count = 0
        fail_count = 0
        
        for student_id in student_ids:
            student = sheets_manager.get_student_by_id(student_id)
            if student:
                # Get plain password (in real app, you'd need to store it temporarily or generate new one)
                # For now, we'll just notify them to use existing credentials
                success = send_credentials_email(
                    student['email'],
                    student['name'],
                    student['username'],
                    student['password'],                     # In production, handle this properly
                    exam_name,
                    exam_start
                )
                
                if success:
                    success_count += 1
                else:
                    fail_count += 1
        
        QMessageBox.information(
            self,
            "Email Status",
            f"Emails sent: {success_count}\nFailed: {fail_count}"
        )

    def delete_student(self, student_id):
        """Delete student"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete student ID {student_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                sheets_manager.delete_student(student_id)
                QMessageBox.information(self, "Success", "Student deleted")
                self.load_students()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

    def delete_question(self, question_id):
        """Delete question"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete question ID {question_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                sheets_manager.delete_question(question_id)
                QMessageBox.information(self, "Success", "Question deleted")
                self.load_questions()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

    def delete_exam(self, exam_id):
        """Delete exam"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete exam ID {exam_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                sheets_manager.delete_exam(exam_id)
                QMessageBox.information(self, "Success", "Exam deleted")
                self.load_exams()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {str(e)}")

# ============================================================================
# MAIN
# ============================================================================
def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    login_window = AdminLoginWindow()
    login_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()





"""
STUDENT EXAM PORTAL - UPDATED WITH KICKOUT DETECTION
Modern exam taking application with Google Sheets data storage
"""

import sys
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import json
from datetime import datetime, timedelta
import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QMessageBox, QButtonGroup,
    QProgressBar, QDialog, QLineEdit, QFrame, QComboBox, QSpinBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QTabWidget, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, QDate, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

# ============================================================================
# CONFIGURATION - USE SHEET ID NOT NAME!
# ============================================================================
CREDENTIALS_FILE = "online-exam-477315-6c00539fc553.json"
SPREADSHEET_ID = "1Ahx7MKPuTDxzPBqsV5UHTnjSkE7e0NVz9EYHfQ4USKc"
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ============================================================================
# GOOGLE SHEETS MANAGER FOR STUDENTS
# ============================================================================
class GoogleSheetsStudentManager:
    """Manages Google Sheets operations for student portal"""
    def __init__(self, credentials_file, spreadsheet_id):
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
        self.connect()

    def connect(self):
        """Connect to Google Sheets using Sheet ID (NOT name)"""
        try:
            import os
            if not os.path.exists(self.credentials_file):
                raise FileNotFoundError(
                    f"❌ {self.credentials_file} not found!\n\n"
                    f"Download from Google Cloud Console and place in this folder"
                )

            # Authenticate
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            
            # ✓ IMPORTANT: Use open_by_key() not open()
            print(f"🔑 Connecting with Sheet ID: {self.spreadsheet_id}")
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"✅ Connected! Sheet: {self.spreadsheet.title}")

        except FileNotFoundError as e:
            raise Exception(str(e))
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(
                f"❌ Sheet ID not found: {self.spreadsheet_id}\n\n"
                f"Make sure:\n"
                f"1. Sheet ID is correct\n"
                f"2. Sheet is shared with service account\n"
                f"3. Google Drive API is enabled"
            )
        except gspread.auth.AuthenticationError:
            raise Exception(
                "❌ Authentication failed!\n\n"
                "Check:\n"
                "1. credentials.json is valid\n"
                "2. Google Sheets API is enabled\n"
                "3. Google Drive API is enabled\n"
                "4. Wait 2-3 minutes after enabling APIs"
            )
        except Exception as e:
            error_msg = str(e)
            if "SSL" in error_msg or "EOF" in error_msg:
                raise Exception(
                    "❌ Network/SSL Error\n\n"
                    "This usually means:\n"
                    "1. Using sheet NAME instead of ID\n"
                    "2. Poor internet connection\n"
                    "3. Firewall blocking Google API\n\n"
                    "Make sure you're using open_by_key(ID)"
                )
            else:
                raise Exception(f"Connection failed: {error_msg}")

    # Authentication
    def authenticate_student(self, username, password):
        """Authenticate student with username and password"""
        try:
            sheet = self.spreadsheet.worksheet("Students")
            records = sheet.get_all_records()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            for student in records:
                if student['username'] == username and student['password'] == password_hash:
                    return {
                        'id': int(student['id']),
                        'name': student['name'],
                        'username': student['username'],
                        'email': student['email']
                    }
            return None
        except Exception as e:
            print(f"Auth error: {str(e)}")
            return None

    # Student exam data
    def get_student_exams(self, student_id):
        """Get exams assigned to student"""
        try:
            sheet = self.spreadsheet.worksheet("Exams")
            records = sheet.get_all_records()
            student_exams = []
            
            for exam in records:
                student_ids = json.loads(exam['student_ids']) if exam['student_ids'] else []
                if student_id in student_ids:
                    exam['question_ids'] = json.loads(exam['question_ids']) if exam['question_ids'] else []
                    exam['student_ids'] = student_ids  # Keep the parsed list
                    exam['exam_id'] = int(exam['exam_id'])
                    exam['duration_minutes'] = int(exam['duration_minutes'])
                    exam['passing_percentage'] = int(exam['passing_percentage'])
                    exam['total_marks'] = int(exam['total_marks'])
                    student_exams.append(exam)
            
            return student_exams
        except Exception as e:
            print(f"Error getting exams: {str(e)}")
            return []

    def get_exam_details(self, exam_id):
        """Get detailed exam information"""
        try:
            sheet = self.spreadsheet.worksheet("Exams")
            records = sheet.get_all_records()
            
            for exam in records:
                if int(exam['exam_id']) == exam_id:
                    exam['question_ids'] = json.loads(exam['question_ids']) if exam['question_ids'] else []
                    exam['student_ids'] = json.loads(exam['student_ids']) if exam['student_ids'] else []
                    exam['exam_id'] = int(exam['exam_id'])
                    exam['duration_minutes'] = int(exam['duration_minutes'])
                    exam['passing_percentage'] = int(exam['passing_percentage'])
                    exam['total_marks'] = int(exam['total_marks'])
                    return exam
            return None
        except Exception as e:
            print(f"Error getting exam details: {str(e)}")
            return None

    def check_student_in_exam(self, exam_id, student_id):
        """Check if student is still in the exam (not kicked out)"""
        try:
            exam = self.get_exam_details(exam_id)
            if not exam:
                return False
            return student_id in exam['student_ids']
        except Exception as e:
            print(f"Error checking student status: {str(e)}")
            return False

    def get_exam_questions(self, exam_id):
        """Get all questions for an exam"""
        try:
            exam = self.get_exam_details(exam_id)
            if not exam:
                return []
            
            sheet = self.spreadsheet.worksheet("Questions")
            all_questions = sheet.get_all_records()
            question_ids = exam['question_ids']
            exam_questions = []
            
            for question in all_questions:
                if int(question['id']) in question_ids:
                    question['id'] = int(question['id'])
                    question['correct_answer'] = int(question['correct_answer'])
                    question['marks'] = int(question['marks'])
                    exam_questions.append(question)
            
            return exam_questions
        except Exception as e:
            print(f"Error getting questions: {str(e)}")
            return []

    # Results submission
    def submit_exam_result(self, exam_id, student_id, score, total_marks, time_taken, answers):
        """Submit exam result"""
        try:
            sheet = self.spreadsheet.worksheet("Results")
            records = sheet.get_all_records()
            new_id = len(records) + 1
            percentage = (score / total_marks * 100) if total_marks > 0 else 0
            
            # Use proper datetime format
            submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row = [
                new_id,
                exam_id,
                student_id,
                score,
                total_marks,
                f"{percentage:.2f}",
                time_taken,
                json.dumps(answers),
                submitted_at
            ]
            sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error submitting result: {str(e)}")
            return False

    def log_security_event(self, student_id, exam_id, event_type, details):
        """Log security events (tab switches, camera off, etc.)"""
        try:
            # Create or get SecurityLog sheet
            try:
                sheet = self.spreadsheet.worksheet("SecurityLog")
            except:
                sheet = self.spreadsheet.add_worksheet("SecurityLog", 1000, 6)
                sheet.append_row([
                    "id", "student_id", "exam_id", "event_type", "details", "timestamp"
                ])
            
            records = sheet.get_all_records()
            new_id = len(records) + 1
            
            # Use proper datetime format
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            row = [
                new_id,
                student_id,
                exam_id,
                event_type,
                details,
                timestamp
            ]
            sheet.append_row(row)
            return True
        except Exception as e:
            print(f"Error logging security event: {str(e)}")
            return False

# Global sheets manager
sheets_manager = None

# ============================================================================
# STYLES
# ============================================================================
DARK_STYLESHEET = """
QMainWindow { background-color: #1e1e2e; color: #e0e0e0; }
QWidget { background-color: #1e1e2e; color: #e0e0e0; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
    color: white; padding: 12px 25px; border: none; border-radius: 8px;
    font-weight: bold; font-size: 12px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5568d3, stop:1 #6a3f8f);
}
QLineEdit {
    background-color: #2d2d44; color: #e0e0e0; border: 2px solid #3d3d54;
    border-radius: 6px; padding: 8px 12px;
}
QLineEdit:focus { border: 2px solid #667eea; }
QLabel { color: #e0e0e0; }
QProgressBar {
    background-color: #2d2d44; border: 2px solid #3d3d54;
    border-radius: 6px; text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
}
QFrame { background-color: #1e1e2e; }
QMessageBox { background-color: #1e1e2e; }
QMessageBox QLabel { color: #e0e0e0; }
QMessageBox QPushButton { min-width: 60px; }
"""

# ============================================================================
# LOGIN WINDOW
# ============================================================================
class StudentLoginWindow(QMainWindow):
    """Student login window"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)

    def init_ui(self):
        self.setWindowTitle("🎓 Student Exam Portal - Login")
        self.setFixedSize(700, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(60, 60, 60, 60)
        layout.setSpacing(30)

        emoji = QLabel("📚")
        emoji.setFont(QFont("Segoe UI Emoji", 80))
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(emoji)

        title = QLabel("Online Exam Portal")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        user_label = QLabel("👤 Username")
        user_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(user_label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter your username")
        self.username.setMinimumHeight(50)
        layout.addWidget(self.username)

        pass_label = QLabel("🔒 Password")
        pass_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(pass_label)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(50)
        self.password.returnPressed.connect(self.login)
        layout.addWidget(self.password)

        login_btn = QPushButton("🚀 Login to Exam")
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setMinimumHeight(60)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        self.status = QLabel("Enter your credentials to access exams")
        self.status.setFont(QFont("Segoe UI", 10))
        self.status.setStyleSheet("color: #a0a0b0;")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        layout.addStretch()
        central_widget.setLayout(layout)

    def login(self):
        """Handle login"""
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Enter username and password")
            return

        try:
            global sheets_manager
            sheets_manager = GoogleSheetsStudentManager(CREDENTIALS_FILE, SPREADSHEET_ID)

            student = sheets_manager.authenticate_student(username, password)
            if student:
                self.exam_portal = StudentExamPortal(student)
                self.exam_portal.show()
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Invalid username or password")
                self.password.clear()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Failed to connect to Google Sheets:\n{str(e)}\n\n"
                "Make sure:\n1. credentials.json exists\n"
                "2. Google Sheets API is enabled\n"
                "3. Google Drive API is enabled"
            )

# ============================================================================
# EXAM PORTAL
# ============================================================================
class StudentExamPortal(QMainWindow):
    """Main exam portal window"""
    def __init__(self, student):
        super().__init__()
        self.student = student
        self.exams = []
        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)
        self.load_exams()

    def init_ui(self):
        self.setWindowTitle(f"📚 Exam Portal - Welcome {self.student['name']}")
        self.setGeometry(50, 50, 1200, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Exams list
        exams_layout = QVBoxLayout()
        exams_layout.setContentsMargins(20, 20, 20, 20)
        exams_layout.setSpacing(15)

        title = QLabel("📝 Available Exams")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        exams_layout.addWidget(title)

        self.exams_container = QWidget()
        self.exams_scroll_layout = QVBoxLayout()
        self.exams_scroll_layout.setSpacing(15)
        self.exams_container.setLayout(self.exams_scroll_layout)

        scroll = QScrollArea()
        scroll.setWidget(self.exams_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #1e1e2e; border: none; }
            QScrollBar:vertical { background-color: #2d2d44; width: 12px; border-radius: 6px; }
            QScrollBar::handle:vertical { background-color: #667eea; border-radius: 6px; }
        """)
        exams_layout.addWidget(scroll)

        main_layout.addLayout(exams_layout)
        central_widget.setLayout(main_layout)

    def create_header(self):
        """Create header"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                padding: 20px;
            }
        """)

        layout = QHBoxLayout()

        title = QLabel(f"👤 {self.student['name']} | {self.student['email']}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        layout.addStretch()

        logout_btn = QPushButton("🚪 Logout")
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

        header.setLayout(layout)
        return header

    def load_exams(self):
        """Load exams from Google Sheets"""
        try:
            self.exams = sheets_manager.get_student_exams(self.student['id'])

            # Clear existing widgets
            while self.exams_scroll_layout.count():
                child = self.exams_scroll_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if not self.exams:
                no_exams = QLabel("📭 No exams available for you right now")
                no_exams.setFont(QFont("Segoe UI", 12))
                no_exams.setStyleSheet("color: #a0a0b0;")
                no_exams.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.exams_scroll_layout.addWidget(no_exams)
            else:
                for exam in self.exams:
                    exam_card = self.create_exam_card(exam)
                    self.exams_scroll_layout.addWidget(exam_card)

            self.exams_scroll_layout.addStretch()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load exams: {str(e)}")

    def create_exam_card(self, exam):
        """Create exam card widget"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2d2d44, stop:1 #3d3d54);
                border: 2px solid #3d3d54;
                border-radius: 12px;
                padding: 20px;
            }
            QFrame:hover { border: 2px solid #667eea; }
        """)

        layout = QHBoxLayout()
        layout.setSpacing(20)

        # Exam info
        info_layout = QVBoxLayout()

        exam_name = QLabel(exam['exam_name'])
        exam_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        exam_name.setStyleSheet("color: #667eea;")
        info_layout.addWidget(exam_name)

        description = QLabel(exam['description'])
        description.setFont(QFont("Segoe UI", 10))
        description.setStyleSheet("color: #a0a0b0;")
        description.setWordWrap(True)
        info_layout.addWidget(description)

        details = QLabel(
            f"⏱ {exam['duration_minutes']} minutes | ❓ {len(exam['question_ids'])} questions | "
            f"⭐ {exam['total_marks']} marks | ✓ {exam['passing_percentage']}% to pass"
        )
        details.setFont(QFont("Segoe UI", 9))
        details.setStyleSheet("color: #8080a0;")
        info_layout.addWidget(details)

        start_time = QLabel(f"📅 Starts: {exam['start_datetime']}")
        start_time.setFont(QFont("Segoe UI", 9))
        start_time.setStyleSheet("color: #8080a0;")
        info_layout.addWidget(start_time)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Start button
        btn_layout = QVBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()

        start_btn = QPushButton("▶ Start Exam")
        start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        start_btn.setMinimumHeight(50)
        start_btn.setMinimumWidth(150)
        start_btn.clicked.connect(lambda: self.start_exam(exam['exam_id']))
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)
        card.setLayout(layout)
        return card

    def start_exam(self, exam_id):
        """Start exam"""
        try:
            # Check if student is still in the exam (not kicked out)
            if not sheets_manager.check_student_in_exam(exam_id, self.student['id']):
                QMessageBox.critical(
                    self,
                    "Access Denied",
                    "❌ You have been removed from this exam by the administrator.\n\n"
                    "Please contact your instructor for more information."
                )
                self.load_exams()  # Refresh exam list
                return

            exam = sheets_manager.get_exam_details(exam_id)
            if not exam:
                QMessageBox.warning(self, "Error", "Exam not found")
                return

            # Check start time
            start_time = datetime.fromisoformat(exam['start_datetime'])
            if datetime.now() < start_time:
                QMessageBox.warning(
                    self,
                    "Not Started",
                    f"This exam starts at {exam['start_datetime']}"
                )
                return

            exam_window = ExamWindow(self.student, exam)
            exam_window.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start exam: {str(e)}")

    def logout(self):
        """Logout"""
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            login_window = StudentLoginWindow()
            login_window.show()

# ============================================================================
# EXAM WINDOW
# ============================================================================
class ExamWindow(QMainWindow):
    """Exam taking window with live kickout detection"""
    def __init__(self, student, exam):
        super().__init__()
        self.student = student
        self.exam = exam
        self.questions = []
        self.answers = {}
        self.current_question_index = 0
        self.start_time = datetime.now()
        self.tab_switch_count = 0
        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)
        self.load_questions()
        self.start_timer()
        self.setup_security_monitoring()
        self.setup_kickout_check()  # NEW: Check for kickout periodically

    def init_ui(self):
        self.setWindowTitle(f"📝 {self.exam['exam_name']}")
        self.setGeometry(50, 50, 1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 3)

        central_widget.setLayout(main_layout)

    def create_left_panel(self):
        """Create left panel with questions list"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #2d2d44;
                border-right: 2px solid #3d3d54;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Timer
        timer_label = QLabel("⏱ Time Left")
        timer_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        timer_label.setStyleSheet("color: #667eea;")
        layout.addWidget(timer_label)

        self.timer_display = QLabel("00:00:00")
        self.timer_display.setFont(QFont("Courier New", 24, QFont.Weight.Bold))
        self.timer_display.setStyleSheet("color: #00ff00;")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_display)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        layout.addWidget(self.progress_bar)

        # Question navigation
        nav_label = QLabel("❓ Questions")
        nav_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        nav_label.setStyleSheet("color: #667eea;")
        layout.addWidget(nav_label)

        self.questions_buttons = []
        self.questions_button_group = QButtonGroup()

        questions_container = QWidget()
        questions_layout = QVBoxLayout()
        questions_layout.setSpacing(8)
        questions_container.setLayout(questions_layout)

        scroll = QScrollArea()
        scroll.setWidget(questions_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #2d2d44; border: none; }
        """)
        layout.addWidget(scroll)

        self.questions_scroll_container = questions_container
        self.questions_scroll_layout = questions_layout

        layout.addStretch()

        # Submit button
        submit_btn = QPushButton("✓ Submit Exam")
        submit_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        submit_btn.setMinimumHeight(50)
        submit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff6b6b, stop:1 #ff5252);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5555, stop:1 #ff4444);
            }
        """)
        submit_btn.clicked.connect(self.submit_exam)
        layout.addWidget(submit_btn)

        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        """Create right panel with question display"""
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #1e1e2e; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Question text
        self.question_label = QLabel()
        self.question_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("color: #667eea; line-height: 1.6;")
        layout.addWidget(self.question_label)

        # Options
        self.options_group = QButtonGroup()
        self.option_buttons = []

        for i in range(4):
            radio = QRadioButton()
            radio.setFont(QFont("Segoe UI", 12))
            radio.setStyleSheet("""
                QRadioButton {
                    color: #e0e0e0;
                    spacing: 10px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 9px;
                    border: 2px solid #667eea;
                    background-color: transparent;
                }
                QRadioButton::indicator:checked {
                    background-color: #667eea;
                }
            """)
            self.options_group.addButton(radio, i)
            layout.addWidget(radio)
            self.option_buttons.append(radio)

        layout.addStretch()

        # Navigation
        nav_layout = QHBoxLayout()

        prev_btn = QPushButton("⬅ Previous")
        prev_btn.setMinimumHeight(40)
        prev_btn.clicked.connect(self.previous_question)
        nav_layout.addWidget(prev_btn)

        self.question_counter = QLabel()
        self.question_counter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.question_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.question_counter)

        next_btn = QPushButton("Next ➜")
        next_btn.setMinimumHeight(40)
        next_btn.clicked.connect(self.next_question)
        nav_layout.addWidget(next_btn)

        layout.addLayout(nav_layout)
        panel.setLayout(layout)
        return panel

    def load_questions(self):
        """Load exam questions from Google Sheets"""
        try:
            self.questions = sheets_manager.get_exam_questions(self.exam['exam_id'])

            if not self.questions:
                QMessageBox.warning(self, "Error", "No questions found for this exam")
                self.close()
                return

            # Create question navigation buttons
            for i, question in enumerate(self.questions):
                btn = QPushButton(str(i + 1))
                btn.setFixedSize(50, 50)
                btn.setCheckable(True)
                btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3d3d54;
                        color: #e0e0e0;
                        border: 2px solid #3d3d54;
                        border-radius: 6px;
                    }
                    QPushButton:checked {
                        background-color: #667eea;
                        border: 2px solid #667eea;
                    }
                """)
                btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
                self.questions_scroll_layout.insertWidget(0, btn)
                self.questions_buttons.append(btn)

            self.progress_bar.setMaximum(len(self.questions))
            self.display_question(0)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")
            self.close()

    def display_question(self, index):
        """Display question at given index"""
        if 0 <= index < len(self.questions):
            self.current_question_index = index
            question = self.questions[index]

            self.question_label.setText(f"❓ {question['question']}")

            options = [
                question['option1'],
                question['option2'],
                question['option3'],
                question['option4']
            ]

            for i, (button, option) in enumerate(zip(self.option_buttons, options)):
                button.setText(str(option))  # Convert to string to handle numeric options

            # Restore previous answer
            if index in self.answers:
                self.option_buttons[self.answers[index]].setChecked(True)
            else:
                self.options_group.setExclusive(False)
                for btn in self.option_buttons:
                    btn.setChecked(False)
                self.options_group.setExclusive(True)

            self.question_counter.setText(f"{index + 1} / {len(self.questions)}")
            self.progress_bar.setValue(index + 1)

            # Update button styles
            for i, btn in enumerate(self.questions_buttons):
                btn.setChecked(i == index)
                if i in self.answers:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #52c41a;
                            color: white;
                            border: 2px solid #52c41a;
                            border-radius: 6px;
                            font-weight: bold;
                        }
                    """)

    def go_to_question(self, index):
        """Go to specific question"""
        self.save_current_answer()
        self.display_question(index)

    def next_question(self):
        """Go to next question"""
        self.save_current_answer()
        if self.current_question_index < len(self.questions) - 1:
            self.display_question(self.current_question_index + 1)

    def previous_question(self):
        """Go to previous question"""
        self.save_current_answer()
        if self.current_question_index > 0:
            self.display_question(self.current_question_index - 1)

    def save_current_answer(self):
        """Save answer to current question"""
        checked_button = self.options_group.checkedButton()
        if checked_button:
            answer_index = self.options_group.id(checked_button)
            self.answers[self.current_question_index] = answer_index

    def start_timer(self):
        """Start exam timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):
        """Update timer display - Calculate: (start_datetime + duration) - current_time"""
        exam_start = datetime.fromisoformat(self.exam['start_datetime'].replace(' ', 'T'))
        exam_end = exam_start + timedelta(minutes=self.exam['duration_minutes'])
        
        remaining = exam_end - datetime.now()
        remaining_seconds = int(remaining.total_seconds())

        if remaining_seconds <= 0:
            self.timer.stop()
            QMessageBox.warning(self, "Time Up", "Exam time has ended!")
            self.submit_exam()
            return

        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        seconds = remaining_seconds % 60

        self.timer_display.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        if remaining_seconds <= 300:  # Last 5 minutes
            self.timer_display.setStyleSheet("color: #ff6b6b;")

    def setup_security_monitoring(self):
        """Setup security monitoring"""
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self.check_window_focus)
        self.focus_timer.start(1000)

    def check_window_focus(self):
        """Check if exam window has focus"""
        if not self.isActiveWindow():
            self.tab_switch_count += 1
            sheets_manager.log_security_event(
                self.student['id'],
                self.exam['exam_id'],
                "tab_switch",
                f"Tab switch #{self.tab_switch_count}"
            )

            if self.tab_switch_count >= self.exam.get('tab_switch_limit', 3):
                QMessageBox.warning(
                    self,
                    "Security Warning",
                    f"⚠️ You have switched tabs {self.tab_switch_count} times!\n\n"
                    "This has been logged. Excessive tab switching may result in exam termination."
                )

    def setup_kickout_check(self):
        """Setup periodic check for kickout status"""
        self.kickout_timer = QTimer()
        self.kickout_timer.timeout.connect(self.check_kickout_status)
        self.kickout_timer.start(5000)  # Check every 5 seconds

    def check_kickout_status(self):
        """Check if student has been kicked out"""
        try:
            if not sheets_manager.check_student_in_exam(self.exam['exam_id'], self.student['id']):
                # Student has been kicked out
                self.timer.stop()
                self.focus_timer.stop()
                self.kickout_timer.stop()

                QMessageBox.critical(
                    self,
                    "Exam Terminated",
                    "❌ You have been removed from this exam by the administrator.\n\n"
                    "Your exam session has been terminated.\n\n"
                    "Please contact your instructor for more information."
                )
                self.close()
        except Exception as e:
            print(f"Error checking kickout status: {str(e)}")

    def submit_exam(self):
        """Submit exam"""
        self.timer.stop()
        self.focus_timer.stop()
        self.kickout_timer.stop()

        self.save_current_answer()

        # Check if still in exam before submitting
        if not sheets_manager.check_student_in_exam(self.exam['exam_id'], self.student['id']):
            QMessageBox.critical(
                self,
                "Submission Failed",
                "❌ You have been removed from this exam.\n\nResults cannot be submitted."
            )
            self.close()
            return

        # Calculate score
        total_marks = int(self.exam['total_marks'])
        marks_per_question = total_marks / len(self.questions)
        score = 0

        for i, question in enumerate(self.questions):
            if i in self.answers:
                if self.answers[i] == int(question['correct_answer']):
                    score += marks_per_question

        score = int(score)
        percentage = (score / total_marks * 100) if total_marks > 0 else 0

        time_taken = datetime.now() - self.start_time
        time_taken_str = str(time_taken).split('.')[0]

        # Submit to Google Sheets
        try:
            sheets_manager.submit_exam_result(
                self.exam['exam_id'],
                self.student['id'],
                score,
                total_marks,
                time_taken_str,
                self.answers
            )

            QMessageBox.information(
                self,
                "Exam Submitted",
                f"✓ Your exam has been submitted!\n\n"
                f"Score: {score}/{total_marks}\n"
                f"Percentage: {percentage:.1f}%\n"
                f"Time Taken: {time_taken_str}\n"
                f"Pass Status: {'✓ PASS' if percentage >= int(self.exam['passing_percentage']) else '✕ FAIL'}"
            )

            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit exam: {str(e)}")

    def closeEvent(self, event):
        """Handle window close"""
        if hasattr(self, 'timer') and self.timer.isActive():
            reply = QMessageBox.question(
                self,
                "Exit Exam",
                "Are you sure you want to exit?\n\nYour progress will be lost!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            self.timer.stop()
            self.focus_timer.stop()
            self.kickout_timer.stop()

        event.accept()

# ============================================================================
# MAIN
# ============================================================================
def main():
    """Application entry point"""
    app = QApplication(sys.argv)
    login_window = StudentLoginWindow()
    login_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
