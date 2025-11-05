
"""
STUDENT EXAM PORTAL - Google Sheets Version (ENHANCED)
Modern exam taking application with Google Sheets data storage
Adds features from the server-based build: full-screen exam UI, progress status,
unanswered warning on submit, clearer timer + header, and refined navigation flow.
"""

import sys
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import json
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QRadioButton, QMessageBox, QButtonGroup,
    QProgressBar, QLineEdit, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ============================================================================
# CONFIGURATION - USE SHEET ID NOT NAME!
# ============================================================================
CREDENTIALS_FILE = "online-exam-477315-2cbccea77532.json"
SPREADSHEET_ID = "1Ahx7MKPuTDxzPBqsV5UHTnjSkE7e0NVz9EYHfQ4USKc"  # ✓ Use ID, not name!

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
        import os
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(
                f"{self.credentials_file} not found! "
                f"Download the service account JSON from Google Cloud Console and place it next to this script."
            )

        # Authenticate
        creds = Credentials.from_service_account_file(self.credentials_file, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)

    # Authentication
    def authenticate_student(self, username, password):
        """Authenticate student with username and password"""
        try:
            sheet = self.spreadsheet.worksheet("Students")
            records = sheet.get_all_records()
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            for student in records:
                if student.get('username') == username and student.get('password') == password_hash:
                    return {
                        'id': int(student['id']),
                        'name': student['name'],
                        'username': student['username'],
                        'email': student['email']
                    }
            return None
        except Exception:
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
                    exam['exam_id'] = int(exam['exam_id'])
                    exam['duration_minutes'] = int(exam['duration_minutes'])
                    exam['passing_percentage'] = int(exam['passing_percentage'])
                    exam['total_marks'] = int(exam['total_marks'])
                    student_exams.append(exam)
            return student_exams
        except Exception:
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
        except Exception:
            return None

    def get_exam_questions(self, exam_id):
        """Get all questions for an exam"""
        exam = self.get_exam_details(exam_id)
        if not exam:
            return []
        try:
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
        except Exception:
            return []

    # Results submission
    def submit_exam_result(self, exam_id, student_id, score, total_marks, time_taken, answers, tab_switches):
        """Submit exam result"""
        try:
            sheet = self.spreadsheet.worksheet("Results")
        except gspread.exceptions.WorksheetNotFound:
            sheet = self.spreadsheet.add_worksheet("Results", rows=1000, cols=9)
            sheet.append_row(["id","exam_id","student_id","score","total_marks","percentage","time_taken","tab_switches","answers","timestamp"])

        records = sheet.get_all_records()
        new_id = len(records) + 1
        percentage = (score / total_marks * 100) if total_marks > 0 else 0
        row = [
            new_id,
            exam_id,
            student_id,
            score,
            total_marks,
            f"{percentage:.2f}",
            time_taken,
            tab_switches,
            json.dumps(answers),
            datetime.now().isoformat()
        ]
        sheet.append_row(row)
        return True

    def log_security_event(self, student_id, exam_id, event_type, details):
        """Log security events (tab switches, camera off, etc.)"""
        try:
            try:
                sheet = self.spreadsheet.worksheet("SecurityLog")
            except gspread.exceptions.WorksheetNotFound:
                sheet = self.spreadsheet.add_worksheet("SecurityLog", rows=1000, cols=6)
                sheet.append_row(["id","student_id","exam_id","event_type","details","timestamp"])
            records = sheet.get_all_records()
            new_id = len(records) + 1
            row = [new_id, student_id, exam_id, event_type, details, datetime.now().isoformat()]
            sheet.append_row(row)
            return True
        except Exception:
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
    color: white; padding: 12px 25px; border: none; border-radius: 10px;
    font-weight: bold; font-size: 13px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5568d3, stop:1 #6a3f8f);
}
QLineEdit {
    background-color: #2d2d44; color: #e0e0e0; border: 2px solid #3d3d54;
    border-radius: 10px; padding: 12px 14px;
}
QLineEdit:focus { border: 2px solid #667eea; }
QLabel { color: #e0e0e0; }
QProgressBar {
    background-color: #2d2d44; border: 2px solid #3d3d54;
    border-radius: 10px; text-align: center; height: 20px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
    border-radius: 8px;
}
QFrame { background-color: #1e1e2e; }
QScrollArea { border: none; }
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
                "Make sure the credentials file exists and the sheet ID is correct."
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

        header = self.create_header()
        main_layout.addWidget(header)

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

        info_layout = QVBoxLayout()

        exam_name = QLabel(exam['exam_name'])
        exam_name.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        exam_name.setStyleSheet("color: #667eea;")
        info_layout.addWidget(exam_name)

        description = QLabel(exam.get('description', ''))
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
            exam = sheets_manager.get_exam_details(exam_id)
            if not exam:
                QMessageBox.warning(self, "Error", "Exam not found")
                return

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
# EXAM WINDOW (ENHANCED)
# ============================================================================
class ExamWindow(QMainWindow):
    """Exam taking window with enhanced UX"""
    def __init__(self, student, exam):
        super().__init__()
        self.student = student
        self.exam = exam
        self.questions = []
        self.answers = {}
        self.current_question_index = 0
        self.start_time = datetime.now()
        self.tab_switch_count = 0

        self.duration_minutes = int(exam.get('duration_minutes', 60))
        self.time_limit = self.duration_minutes * 60
        self.time_remaining = self.time_limit

        self.init_ui()
        self.setStyleSheet(DARK_STYLESHEET)
        self.load_questions()
        self.start_timer()
        self.setup_security_monitoring()

        # Go fullscreen for better focus (esc can exit)
        self.showFullScreen()

    def init_ui(self):
        self.setWindowTitle(f"📝 {self.exam['exam_name']}")
        self.setGeometry(50, 50, 1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # ===== Header with Timer and Student =====
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                border-radius: 16px;
                padding: 18px;
            }
        """)
        h = QHBoxLayout()

        title = QLabel(f"📝 {self.exam['exam_name']}")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        h.addWidget(title)

        h.addStretch()

        self.timer_display = QLabel(f"{self.duration_minutes:02d}:00")
        self.timer_display.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.timer_display.setStyleSheet("color: white;")
        h.addWidget(self.timer_display)

        h.addSpacing(20)

        student_lbl = QLabel(f"Student: {self.student['name']}")
        student_lbl.setFont(QFont("Segoe UI", 12))
        student_lbl.setStyleSheet("color: rgba(255,255,255,0.9);")
        h.addWidget(student_lbl)

        header.setLayout(h)
        main_layout.addWidget(header)

        # ===== Progress summary =====
        progress_frame = QFrame()
        progress_frame.setStyleSheet("QFrame { background-color: #2d2d44; border-radius: 16px; padding: 16px; }")
        v = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        v.addWidget(self.progress_bar)

        self.status_label = QLabel("Question 0 of 0 | Answered: 0/0 | Progress: 0%")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.status_label.setStyleSheet("color: #a0a0b0;")
        v.addWidget(self.status_label)
        progress_frame.setLayout(v)
        main_layout.addWidget(progress_frame)

        # ===== Content area (left nav + right question) =====
        content = QHBoxLayout()
        content.setSpacing(16)

        # Left: question numbers + submit
        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background-color: #2d2d44; border-radius: 16px; padding: 14px; }")
        left_v = QVBoxLayout()
        left_v.setSpacing(10)

        nav_label = QLabel("❓ Questions")
        nav_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        nav_label.setStyleSheet("color: #667eea;")
        left_v.addWidget(nav_label)

        self.questions_buttons = []
        self.questions_button_group = QButtonGroup()

        self.questions_container = QWidget()
        self.questions_layout = QVBoxLayout()
        self.questions_layout.setSpacing(8)
        self.questions_container.setLayout(self.questions_layout)

        scroll = QScrollArea()
        scroll.setWidget(self.questions_container)
        scroll.setWidgetResizable(True)
        left_v.addWidget(scroll, 1)

        self.submit_btn_side = QPushButton("✓ Submit Exam")
        self.submit_btn_side.setMinimumHeight(48)
        self.submit_btn_side.clicked.connect(self.submit_exam)
        left_v.addWidget(self.submit_btn_side)

        left_panel.setLayout(left_v)
        content.addWidget(left_panel, 1)

        # Right: question + options + nav
        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background-color: #1e1e2e; border-radius: 16px; padding: 24px; }")

        right_v = QVBoxLayout()
        right_v.setSpacing(16)

        self.question_label = QLabel()
        self.question_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("color: #b3c3ff; line-height: 1.6;")
        right_v.addWidget(self.question_label)

        self.options_group = QButtonGroup()
        self.option_buttons = []
        for i in range(4):
            radio = QRadioButton()
            radio.setFont(QFont("Segoe UI", 13))
            radio.setStyleSheet("""
                QRadioButton {
                    color: #e0e0e0;
                    spacing: 10px;
                    padding: 8px 4px;
                }
                QRadioButton::indicator {
                    width: 18px; height: 18px;
                    border-radius: 9px;
                    border: 2px solid #667eea;
                    background-color: transparent;
                }
                QRadioButton::indicator:checked { background-color: #667eea; }
            """)
            self.options_group.addButton(radio, i)
            right_v.addWidget(radio)
            self.option_buttons.append(radio)

        right_v.addStretch()

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("⬅ Previous")
        self.prev_btn.setMinimumHeight(44)
        self.prev_btn.clicked.connect(self.previous_question)
        nav_layout.addWidget(self.prev_btn)

        self.question_counter = QLabel()
        self.question_counter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.question_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.question_counter, 1)

        self.next_btn = QPushButton("Next ➜")
        self.next_btn.setMinimumHeight(44)
        self.next_btn.clicked.connect(self.next_question)
        nav_layout.addWidget(self.next_btn)

        right_v.addLayout(nav_layout)
        right_panel.setLayout(right_v)
        content.addWidget(right_panel, 3)

        main_layout.addLayout(content, 1)
        central_widget.setLayout(main_layout)

    def load_questions(self):
        """Load exam questions from Google Sheets"""
        self.questions = sheets_manager.get_exam_questions(self.exam['exam_id'])
        if not self.questions:
            QMessageBox.warning(self, "Error", "No questions found for this exam")
            self.close()
            return

        # Build left navigation buttons
        for i, _ in enumerate(self.questions):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(50, 44)
            btn.setCheckable(True)
            btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d54;
                    color: #e0e0e0;
                    border: 2px solid #3d3d54;
                    border-radius: 8px;
                }
                QPushButton:checked {
                    background-color: #667eea;
                    border: 2px solid #667eea;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self.go_to_question(idx))
            self.questions_layout.addWidget(btn)
            self.questions_buttons.append(btn)

        # Initialize answer tracking
        for i in range(len(self.questions)):
            self.answers[i] = None

        self.update_progress()
        self.display_question(0)

    def display_question(self, index):
        """Display question at given index"""
        if not (0 <= index < len(self.questions)):
            return
        self.current_question_index = index
        question = self.questions[index]

        self.question_label.setText(f"❓ {str(question.get('question', ''))}")
        options = [
            str(question.get('option1', '')),
            str(question.get('option2', '')),
            str(question.get('option3', '')),
            str(question.get('option4', ''))
        ]
        for i, (btn, text) in enumerate(zip(self.option_buttons, options)):
            btn.setText(text)


        # Restore selection
        sel = self.answers.get(index)
        self.options_group.setExclusive(False)
        for i, btn in enumerate(self.option_buttons):
            btn.setChecked(i == sel)
        self.options_group.setExclusive(True)

        # Update nav buttons visibility to mirror improved UX:
        self.prev_btn.setEnabled(index > 0)
        is_last = index == len(self.questions) - 1
        self.next_btn.setVisible(not is_last)
        self.submit_btn_side.setVisible(True)  # Keep side submit always visible

        # Counter
        self.question_counter.setText(f"{index + 1} / {len(self.questions)}")

        # Mark answered buttons
        for i, btn in enumerate(self.questions_buttons):
            btn.setChecked(i == index)
            if self.answers.get(i) is not None:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #52c41a;
                        color: #ffffff;
                        border: 2px solid #52c41a;
                        border-radius: 8px;
                        font-weight: bold;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3d3d54;
                        color: #e0e0e0;
                        border: 2px solid #3d3d54;
                        border-radius: 8px;
                    }
                    QPushButton:checked {
                        background-color: #667eea;
                        border: 2px solid #667eea;
                    }
                """)

        self.update_progress()

    def go_to_question(self, index):
        self.save_current_answer()
        self.display_question(index)

    def next_question(self):
        self.save_current_answer()
        if self.current_question_index < len(self.questions) - 1:
            self.display_question(self.current_question_index + 1)

    def previous_question(self):
        self.save_current_answer()
        if self.current_question_index > 0:
            self.display_question(self.current_question_index - 1)

    def save_current_answer(self):
        """Save answer to current question"""
        checked_id = self.options_group.checkedId()
        if checked_id != -1:
            self.answers[self.current_question_index] = checked_id
        else:
            self.answers[self.current_question_index] = None

    def update_progress(self):
        """Update progress display"""
        answered = sum(1 for ans in self.answers.values() if ans is not None)
        total = len(self.questions) if self.questions else 0
        percent = int((answered / total) * 100) if total else 0
        self.progress_bar.setValue(percent)
        self.status_label.setText(
            f"Question {self.current_question_index + 1} of {total} | "
            f"Answered: {answered}/{total} | Progress: {percent}%"
        )

    def start_timer(self):
        """Start exam countdown timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):
        """Update timer display"""
        self.time_remaining -= 1

        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(self, "Time Up", "Exam time has ended! Submitting now.")
            self.submit_exam()
            return

        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_display.setText(f"{minutes:02d}:{seconds:02d}")

        if self.time_remaining <= 300:  # last 5 minutes
            self.timer_display.setStyleSheet("color: #ff6b6b; font-weight: 700;")

    def setup_security_monitoring(self):
        """Basic focus monitoring for tab switches"""
        self.focus_timer = QTimer()
        self.focus_timer.timeout.connect(self.check_window_focus)
        self.focus_timer.start(1000)

    def check_window_focus(self):
        if not self.isActiveWindow():
            self.tab_switch_count += 1
            sheets_manager.log_security_event(
                self.student['id'],
                self.exam['exam_id'],
                "tab_switch",
                f"Tab switch #{self.tab_switch_count}"
            )

    def submit_exam(self):
        """Submit exam with unanswered warning and pass/fail info"""
        # Save current state
        self.save_current_answer()

        # Warning for unanswered
        unanswered = sum(1 for ans in self.answers.values() if ans is None)
        if unanswered > 0:
            reply = QMessageBox.question(
                self,
                "Unanswered Questions",
                f"You have {unanswered} unanswered question(s).\n\n"
                "Are you sure you want to submit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Stop timers
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'focus_timer'):
            self.focus_timer.stop()

        # Score
        total_marks = int(self.exam['total_marks']) if self.exam.get('total_marks') else len(self.questions)
        marks_per_question = total_marks / len(self.questions) if self.questions else 0

        score = 0
        for i, q in enumerate(self.questions):
            selected = self.answers.get(i)
            if selected is not None and selected == int(q['correct_answer']):
                score += marks_per_question

        score = int(round(score))
        percentage = (score / total_marks * 100) if total_marks > 0 else 0

        # Time taken
        time_taken_seconds = self.time_limit - self.time_remaining
        time_taken = f"{time_taken_seconds // 60}m {time_taken_seconds % 60}s"

        # Persist to Sheets
        try:
            sheets_manager.submit_exam_result(
                self.exam['exam_id'],
                self.student['id'],
                score,
                total_marks,
                time_taken,
                self.answers,
                self.tab_switch_count
            )

            passing_percentage = int(self.exam.get('passing_percentage', 40))
            passed = percentage >= passing_percentage

            QMessageBox.information(
                self,
                "Exam Submitted",
                (
                    f"✓ Your exam has been submitted!\n\n"
                    f"Score: {score}/{total_marks}\n"
                    f"Percentage: {percentage:.1f}%\n"
                    f"Time Taken: {time_taken}\n"
                    f"Tab Switches: {self.tab_switch_count}\n"
                    f"Status: {'✓ PASS' if passed else '✕ FAIL'}\n"
                    f"Passing Score: {passing_percentage}%"
                )
            )
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit exam: {str(e)}")

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








import sys
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import json
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QComboBox, QCheckBox, QDateTimeEdit,
    QSpinBox, QTabWidget, QListWidget, QListWidgetItem, QScrollArea,
    QGridLayout, QHeaderView, QFrame, QProgressBar, QStatusBar,
    QMenuBar, QMenu, QInputDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QDateTime, QSize, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# ============================================================================
# CONFIGURATION - USE SHEET ID NOT NAME!
# ============================================================================
CREDENTIALS_FILE = "online-exam-477315-2cbccea77532.json"
SPREADSHEET_ID = "1Ahx7MKPuTDxzPBqsV5UHTnjSkE7e0NVz9EYHfQ4USKc"  # ✓ Use ID, not name!

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
        
        print("✓ All worksheets ready!")
    
    # Students operations
    def add_student(self, data):
        """Add new student"""
        sheet = self.spreadsheet.worksheet("Students")
        records = sheet.get_all_records()
        new_id = len(records) + 1
        
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        row = [
            new_id,
            data['name'],
            data['username'],
            password_hash,
            data['email'],
            data['roll_number'],
            data['group_name'],
            datetime.now().isoformat()
        ]
        sheet.append_row(row)
        return new_id
    
    def get_all_students(self):
        """Get all students"""
        sheet = self.spreadsheet.worksheet("Students")
        return sheet.get_all_records()
    
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
            datetime.now().isoformat()
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
            datetime.now().isoformat()
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
    
    def delete_exam(self, exam_id):
        """Delete exam by ID"""
        sheet = self.spreadsheet.worksheet("Exams")
        records = sheet.get_all_records()
        for i, record in enumerate(records, start=2):
            if int(record['exam_id']) == exam_id:
                sheet.delete_rows(i)
                return True
        return False
    
    # Results operations
    def get_all_results(self):
        """Get all results"""
        sheet = self.spreadsheet.worksheet("Results")
        return sheet.get_all_records()
    
    def submit_result(self, exam_id, student_id, score, total_marks, time_taken, answers):
        """Submit exam result"""
        sheet = self.spreadsheet.worksheet("Results")
        records = sheet.get_all_records()
        new_id = len(records) + 1
        
        percentage = (score / total_marks * 100) if total_marks > 0 else 0
        
        row = [
            new_id,
            exam_id,
            student_id,
            score,
            total_marks,
            f"{percentage:.2f}",
            time_taken,
            json.dumps(answers),
            datetime.now().isoformat()
        ]
        sheet.append_row(row)
        return True


# Global sheets manager
sheets_manager = None


# ============================================================================
# STYLES (same as before)
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
"""

# ============================================================================
# DIALOGS (mostly same, simplified)
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
    """Create new exam dialog"""
    def __init__(self, parent=None, students=None, questions=None):
        super().__init__(parent)
        self.students = students or []
        self.questions = questions or []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("📝 Create New Exam")
        self.setFixedSize(900, 800)
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
            "student_ids": selected_students
        }


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
                QMessageBox.critical(self, "Error", f"Failed to connect to Google Sheets:\n{str(e)}\n\nMake sure:\n1. credentials.json exists\n2. Google Sheets API is enabled\n3. Service account has access")
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
            self.password.clear()


# ============================================================================
# ADMIN PANEL
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
        
        # Share button
        share_btn = QPushButton("🔗 Get Share Link")
        share_btn.clicked.connect(self.show_share_link)
        layout.addWidget(share_btn)
        
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
        self.exams_table.setColumnCount(7)
        self.exams_table.setHorizontalHeaderLabels([
            "ID", "Exam Name", "Start", "Duration", "Students", "Questions", "Action"
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
    
    def show_share_link(self):
        """Show Google Sheets share link"""
        url = sheets_manager.make_shareable()
        if url:
            QMessageBox.information(
                self,
                "Share Link",
                f"Google Sheets URL:\n{url}\n\nThis link allows anyone with it to view and edit the spreadsheet."
            )
        else:
            QMessageBox.warning(self, "Error", "Failed to generate share link")
    
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
                
                del_btn = QPushButton("🗑 Delete")
                del_btn.clicked.connect(lambda checked, eid=exam['exam_id']: self.delete_exam(eid))
                self.exams_table.setCellWidget(i, 6, del_btn)
            
            self.status_bar.showMessage(f"Loaded {len(self.exams)} exams")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load exams: {str(e)}")
    
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
                self.results_table.setItem(i, 5, QTableWidgetItem(f"{result['percentage']:.1f}%"))
                self.results_table.setItem(i, 6, QTableWidgetItem(result['time_taken']))
                self.results_table.setItem(i, 7, QTableWidgetItem(result['submitted_at'][:16]))
            
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
                    sheets_manager.add_exam(data)
                    QMessageBox.information(self, "Success", "Exam created successfully!")
                    self.load_exams()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create exam: {str(e)}")
    
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










