"""
===================================================
ADMIN PANEL - FIXED VERSION with Threading
Server connections in separate threads
===================================================
"""

import sys
import requests
import sqlite3
import hashlib
from datetime import datetime, timedelta
from threading import Thread
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QComboBox, QCheckBox, QDateTimeEdit,
    QSpinBox, QTabWidget, QListWidget, QListWidgetItem, QScrollArea,
    QGridLayout, QHeaderView, QFrame, QProgressBar, QStatusBar,
    QMenuBar, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QDateTime, QSize, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_URL = "http://localhost:5000"
API_TOKEN = "secure_token_12345"

# ============================================================================
# DARK THEME STYLESHEET
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

    QMenuBar {
        background-color: #2d2d44;
        color: #e0e0e0;
        border-bottom: 1px solid #3d3d54;
    }

    QMenuBar::item:selected {
        background-color: #667eea;
    }

    QMenu {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 1px solid #3d3d54;
    }

    QMenu::item:selected {
        background-color: #667eea;
    }

    QTabWidget::pane {
        border: 2px solid #3d3d54;
        background-color: #1e1e2e;
    }

    QTabBar::tab {
        background-color: #2d2d44;
        color: #a0a0b0;
        padding: 8px 25px;
        border: 1px solid #3d3d54;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }

    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
        color: white;
        border: 1px solid #667eea;
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

    QPushButton:disabled {
        background-color: #505070;
        color: #808090;
    }

    QLineEdit, QTextEdit {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 11px;
    }

    QLineEdit:focus, QTextEdit:focus {
        border: 2px solid #667eea;
        background-color: #252535;
    }

    QComboBox {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 6px 12px;
    }

    QComboBox:focus {
        border: 2px solid #667eea;
    }

    QSpinBox, QDateTimeEdit {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 6px 12px;
    }

    QCheckBox {
        color: #e0e0e0;
        spacing: 8px;
    }

    QTableWidget {
        background-color: #2d2d44;
        gridline-color: #3d3d54;
        border: 1px solid #3d3d54;
    }

    QTableWidget::item {
        padding: 5px;
        border: none;
    }

    QTableWidget::item:selected {
        background-color: #667eea;
    }

    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d3d54, stop:1 #2d2d44);
        color: #e0e0e0;
        padding: 6px;
        border: none;
        border-right: 1px solid #2d2d44;
        border-bottom: 1px solid #3d3d54;
        font-weight: bold;
    }

    QListWidget {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
    }

    QListWidget::item:selected {
        background-color: #667eea;
    }

    QProgressBar {
        background-color: #2d2d44;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        text-align: center;
        color: white;
        height: 25px;
    }

    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
        border-radius: 4px;
    }

    QStatusBar {
        background-color: #2d2d44;
        color: #e0e0e0;
        border-top: 1px solid #3d3d54;
    }

    QScrollArea {
        border: none;
        background-color: #1e1e2e;
    }

    QScrollBar:vertical {
        background-color: #2d2d44;
        width: 12px;
    }

    QScrollBar::handle:vertical {
        background-color: #667eea;
        border-radius: 6px;
        min-height: 20px;
    }
"""

# ============================================================================
# THREADING CLASSES
# ============================================================================

class LoadDataThread(QThread):
    """Load data from server in background thread"""

    success = pyqtSignal(str, list)  # data_type, data
    error = pyqtSignal(str, str)  # data_type, error_message

    def __init__(self, endpoint, data_type):
        super().__init__()
        self.endpoint = endpoint
        self.data_type = data_type

    def run(self):
        try:
            response = requests.get(
                f"{SERVER_URL}{self.endpoint}",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json().get(self.data_type, [])
                self.success.emit(self.data_type, data)
            else:
                self.error.emit(self.data_type, f"Server error: {response.status_code}")

        except Exception as e:
            self.error.emit(self.data_type, str(e))

class AddDataThread(QThread):
    """Add data to server in background thread"""

    success = pyqtSignal(str)  # success message
    error = pyqtSignal(str)  # error message

    def __init__(self, endpoint, data):
        super().__init__()
        self.endpoint = endpoint
        self.data = data

    def run(self):
        try:
            response = requests.post(
                f"{SERVER_URL}{self.endpoint}",
                json=self.data,
                headers={"Authorization": API_TOKEN},
                timeout=10
            )

            if response.status_code == 200:
                msg = response.json().get('message', 'Success')
                self.success.emit(msg)
            else:
                msg = response.json().get('message', 'Failed')
                self.error.emit(msg)

        except Exception as e:
            self.error.emit(str(e))

class DeleteDataThread(QThread):
    """Delete data from server in background thread"""

    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, endpoint):
        super().__init__()
        self.endpoint = endpoint

    def run(self):
        try:
            response = requests.delete(
                f"{SERVER_URL}{self.endpoint}",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.success.emit("Deleted successfully")
            else:
                self.error.emit("Failed to delete")

        except Exception as e:
            self.error.emit(str(e))

# ============================================================================
# DIALOGS
# ============================================================================

class AddStudentDialog(QDialog):
    """Add new student dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
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

        fields = [
            ("📝 Full Name", "name"),
            ("👤 Username", "username"),
            ("🔒 Password", "password"),
            ("📧 Email", "email"),
            ("📌 Roll Number", "roll"),
            ("👥 Group", "group"),
        ]

        self.inputs = {}

        for label_text, key in fields:
            label = QLabel(label_text)
            label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            layout.addWidget(label)

            input_field = QLineEdit()
            if key == "password":
                input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self.inputs[key] = input_field
            layout.addWidget(input_field)

        layout.addStretch()

        button_layout = QHBoxLayout()

        save_btn = QPushButton("✓ Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setStyleSheet("QPushButton { background-color: #505070; }")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return {
            "name": self.inputs["name"].text(),
            "username": self.inputs["username"].text(),
            "password": self.inputs["password"].text(),
            "email": self.inputs["email"].text(),
            "roll_number": self.inputs["roll"].text(),
            "group_name": self.inputs["group"].text()
        }

class AddQuestionDialog(QDialog):
    """Add new question dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
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
        layout.addWidget(q_label)

        self.question = QTextEdit()
        self.question.setMinimumHeight(100)
        layout.addWidget(self.question)

        opt_label = QLabel("🎯 Answer Options")
        layout.addWidget(opt_label)

        self.options = []
        for i in range(4):
            opt = QLineEdit()
            opt.setPlaceholderText(f"Option {i+1}")
            self.options.append(opt)
            layout.addWidget(opt)

        ans_layout = QHBoxLayout()
        ans_label = QLabel("✓ Correct Answer:")
        self.correct_answer = QComboBox()
        self.correct_answer.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])
        ans_layout.addWidget(ans_label)
        ans_layout.addWidget(self.correct_answer)
        ans_layout.addStretch()
        layout.addLayout(ans_layout)

        meta_layout = QHBoxLayout()

        subject_label = QLabel("📚 Subject:")
        self.subject = QLineEdit()
        meta_layout.addWidget(subject_label)
        meta_layout.addWidget(self.subject)

        marks_label = QLabel("⭐ Marks:")
        self.marks = QSpinBox()
        self.marks.setValue(1)
        meta_layout.addWidget(marks_label)
        meta_layout.addWidget(self.marks)

        layout.addLayout(meta_layout)
        layout.addStretch()

        button_layout = QHBoxLayout()

        save_btn = QPushButton("✓ Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setStyleSheet("QPushButton { background-color: #505070; }")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return {
            "question": self.question.toPlainText(),
            "option1": self.options[0].text(),
            "option2": self.options[1].text(),
            "option3": self.options[2].text(),
            "option4": self.options[3].text(),
            "correct_answer": self.correct_answer.currentIndex(),
            "subject": self.subject.text(),
            "marks": self.marks.value()
        }

# FIXED CreateExamDialog - use corrected code from [code_file:16]
# (Paste the complete dialog from CREATEEXAMDIALOG_COMPLETE_FIXED.txt)

# ============================================================================
# ADMIN LOGIN WINDOW
# ============================================================================

class AdminLoginWindow(QMainWindow):
    """Admin login window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔐 Admin Login")
        self.setFixedSize(600, 500)
        self.setStyleSheet(DARK_STYLESHEET)

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

        layout.addSpacing(20)

        user_label = QLabel("👤 Username")
        user_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(user_label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("admin")
        self.username.setMinimumHeight(50)
        layout.addWidget(self.username)

        pass_label = QLabel("🔒 Password")
        pass_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(pass_label)

        self.password = QLineEdit()
        self.password.setPlaceholderText("admin123")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(50)
        self.password.returnPressed.connect(self.login)
        layout.addWidget(self.password)

        layout.addSpacing(10)

        login_btn = QPushButton("🚀 Login")
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setMinimumHeight(60)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        info = QLabel("Default: admin / admin123")
        info.setFont(QFont("Segoe UI", 10))
        info.setStyleSheet("color: #a0a0b0;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        layout.addStretch()

        central_widget.setLayout(layout)

    def login(self):
        username = self.username.text()
        password = self.password.text()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Enter credentials")
            return

        if username == "admin" and password == "admin123":
            self.admin_panel = AdminPanel(username)
            self.admin_panel.show()
            self.close()
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
        self.setWindowTitle(f"Admin Dashboard - {admin_username}")
        self.setGeometry(50, 50, 1600, 900)
        self.setStyleSheet(DARK_STYLESHEET)

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Initialize UI"""
        # Menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("📁 File")
        refresh_action = file_menu.addAction("🔄 Refresh")
        refresh_action.triggered.connect(self.load_data)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("🚪 Exit")
        exit_action.triggered.connect(self.close)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                padding: 20px;
            }
        """)
        header_layout = QHBoxLayout()

        title = QLabel(f"👤 Welcome, {self.admin_username}!")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        header.setLayout(header_layout)
        main_layout.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()

        self.students_widget = self.create_students_tab()
        self.tabs.addTab(self.students_widget, "👥 Students")

        self.questions_widget = self.create_questions_tab()
        self.tabs.addTab(self.questions_widget, "❓ Questions")

        self.exams_widget = self.create_exams_tab()
        self.tabs.addTab(self.exams_widget, "📝 Exams")

        self.results_widget = self.create_results_tab()
        self.tabs.addTab(self.results_widget, "📊 Results")

        main_layout.addWidget(self.tabs, 1)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready | Connecting to server...")

        central_widget.setLayout(main_layout)

    def create_students_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Student")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_student)
        btn_layout.addWidget(add_btn)
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
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Question")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_question)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.questions_table = QTableWidget()
        self.questions_table.setColumnCount(7)
        self.questions_table.setHorizontalHeaderLabels([
            "ID", "Question", "Subject", "Marks", "Ans", "Opt1", "Action"
        ])
        self.questions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.questions_table)

        widget.setLayout(layout)
        return widget

    def create_exams_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Create Exam")
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.create_exam)
        btn_layout.addWidget(add_btn)
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
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Student", "Exam", "Score", "Total", "Percentage", "Time", "Date", "Action"
        ])
        layout.addWidget(self.results_table)

        widget.setLayout(layout)
        return widget

    def load_data(self):
        """Load all data in background threads"""
        self.status_bar.showMessage("Loading students...")
        self.load_thread_students = LoadDataThread("/api/students", "students")
        self.load_thread_students.success.connect(self.on_students_loaded)
        self.load_thread_students.error.connect(self.on_load_error)
        self.load_thread_students.start()

        self.load_thread_questions = LoadDataThread("/api/questions", "questions")
        self.load_thread_questions.success.connect(self.on_questions_loaded)
        self.load_thread_questions.error.connect(self.on_load_error)
        self.load_thread_questions.start()

        self.load_thread_exams = LoadDataThread("/api/exams", "exams")
        self.load_thread_exams.success.connect(self.on_exams_loaded)
        self.load_thread_exams.error.connect(self.on_load_error)
        self.load_thread_exams.start()

        self.load_thread_results = LoadDataThread("/api/results", "results")
        self.load_thread_results.success.connect(self.on_results_loaded)
        self.load_thread_results.error.connect(self.on_load_error)
        self.load_thread_results.start()

    def on_students_loaded(self, data_type, data):
        """Handle students loaded"""
        self.students_table.setRowCount(len(data))
        for i, student in enumerate(data):
            self.students_table.setItem(i, 0, QTableWidgetItem(str(student.get('id', ''))))
            self.students_table.setItem(i, 1, QTableWidgetItem(student.get('name', '')))
            self.students_table.setItem(i, 2, QTableWidgetItem(student.get('username', '')))
            self.students_table.setItem(i, 3, QTableWidgetItem(student.get('email', '')))
            self.students_table.setItem(i, 4, QTableWidgetItem(student.get('roll_number', '')))
            self.students_table.setItem(i, 5, QTableWidgetItem(student.get('group_name', '')))

        self.status_bar.showMessage(f"✓ Loaded {len(data)} students")

    def on_questions_loaded(self, data_type, data):
        """Handle questions loaded"""
        self.questions_table.setRowCount(len(data))
        for i, q in enumerate(data):
            self.questions_table.setItem(i, 0, QTableWidgetItem(str(q.get('id', ''))))
            q_text = q.get('question', '')[:50]
            self.questions_table.setItem(i, 1, QTableWidgetItem(q_text))
            self.questions_table.setItem(i, 2, QTableWidgetItem(q.get('subject', '')))
            self.questions_table.setItem(i, 3, QTableWidgetItem(str(q.get('marks', ''))))
            self.questions_table.setItem(i, 4, QTableWidgetItem(str(q.get('correct_answer', ''))))
            self.questions_table.setItem(i, 5, QTableWidgetItem(q.get('option1', '')[:20]))

        self.status_bar.showMessage(f"✓ Loaded {len(data)} questions")

    def on_exams_loaded(self, data_type, data):
        """Handle exams loaded"""
        self.exams_table.setRowCount(len(data))
        for i, exam in enumerate(data):
            self.exams_table.setItem(i, 0, QTableWidgetItem(str(exam.get('id', ''))))
            self.exams_table.setItem(i, 1, QTableWidgetItem(exam.get('exam_name', '')))
            self.exams_table.setItem(i, 2, QTableWidgetItem(exam.get('start_datetime', '')[:16]))
            self.exams_table.setItem(i, 3, QTableWidgetItem(str(exam.get('duration_minutes', ''))))

        self.status_bar.showMessage(f"✓ Loaded {len(data)} exams")

    def on_results_loaded(self, data_type, data):
        """Handle results loaded"""
        self.results_table.setRowCount(len(data))
        for i, result in enumerate(data):
            self.results_table.setItem(i, 0, QTableWidgetItem(str(result.get('id', ''))))
            self.results_table.setItem(i, 1, QTableWidgetItem(result.get('name', '')))
            self.results_table.setItem(i, 2, QTableWidgetItem(result.get('exam_name', '')))
            self.results_table.setItem(i, 3, QTableWidgetItem(str(result.get('score', ''))))
            self.results_table.setItem(i, 4, QTableWidgetItem(str(result.get('total_marks', ''))))
            pct = result.get('percentage', 0)
            self.results_table.setItem(i, 5, QTableWidgetItem(f"{pct:.1f}%"))
            self.results_table.setItem(i, 6, QTableWidgetItem(result.get('time_taken', '')))

        self.status_bar.showMessage(f"✓ Loaded {len(data)} results")

    def on_load_error(self, data_type, error):
        """Handle load error"""
        self.status_bar.showMessage(f"⚠️ Error loading {data_type}: {error}")

    def add_student(self):
        """Add new student"""
        dialog = AddStudentDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.status_bar.showMessage("Adding student...")

            thread = AddDataThread("/api/admin/add-student", data)
            thread.success.connect(lambda msg: self.on_add_success("student", msg))
            thread.error.connect(lambda err: self.on_add_error("student", err))
            thread.start()

    def add_question(self):
        """Add new question"""
        dialog = AddQuestionDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.status_bar.showMessage("Adding question...")

            thread = AddDataThread("/api/admin/add-question", data)
            thread.success.connect(lambda msg: self.on_add_success("question", msg))
            thread.error.connect(lambda err: self.on_add_error("question", err))
            thread.start()

    def create_exam(self):
        """Create new exam"""
        # Use fixed CreateExamDialog from code_file:16
        QMessageBox.information(self, "Info", "Add CreateExamDialog from code_file:16")

    def on_add_success(self, item_type, msg):
        """Handle add success"""
        QMessageBox.information(self, "Success", f"{item_type.capitalize()} added successfully!")
        self.load_data()

    def on_add_error(self, item_type, err):
        """Handle add error"""
        QMessageBox.warning(self, "Error", f"Failed to add {item_type}: {err}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    app = QApplication(sys.argv)
    login = AdminLoginWindow()
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()









"""
===================================================
ADMIN PANEL - FIXED VERSION with Threading
Server connections in separate threads
===================================================
"""

import sys
import requests
import sqlite3
import hashlib
from datetime import datetime, timedelta
from threading import Thread
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QDialog, QLineEdit, QTextEdit, QComboBox, QCheckBox, QDateTimeEdit,
    QSpinBox, QTabWidget, QListWidget, QListWidgetItem, QScrollArea,
    QGridLayout, QHeaderView, QFrame, QProgressBar, QStatusBar,
    QMenuBar, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QDateTime, QSize, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVER_URL = "http://localhost:5000"  # Change to your server IP
API_TOKEN = "secure_token_12345"
LOCAL_DB = "admin_local.db"

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

    QMenuBar {
        background-color: #2d2d44;
        color: #e0e0e0;
        border-bottom: 1px solid #3d3d54;
    }

    QMenuBar::item:selected {
        background-color: #667eea;
    }

    QMenu {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 1px solid #3d3d54;
    }

    QMenu::item:selected {
        background-color: #667eea;
    }

    QTabWidget::pane {
        border: 2px solid #3d3d54;
        background-color: #1e1e2e;
    }

    QTabBar::tab {
        background-color: #2d2d44;
        color: #a0a0b0;
        padding: 8px 25px;
        border: 1px solid #3d3d54;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }

    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
        color: white;
        border: 1px solid #667eea;
    }

    QTabBar::tab:hover {
        background-color: #3d3d54;
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

    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4655b8, stop:1 #5a3380);
    }

    QPushButton:disabled {
        background-color: #505070;
        color: #808090;
    }

    QLineEdit, QTextEdit {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 11px;
    }

    QLineEdit:focus, QTextEdit:focus {
        border: 2px solid #667eea;
        background-color: #252535;
    }

    QComboBox {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 6px 12px;
    }

    QComboBox:focus {
        border: 2px solid #667eea;
    }

    QComboBox::drop-down {
        border: none;
    }

    QSpinBox, QDateTimeEdit {
        background-color: #2d2d44;
        color: #e0e0e0;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        padding: 6px 12px;
    }

    QSpinBox:focus, QDateTimeEdit:focus {
        border: 2px solid #667eea;
    }

    QCheckBox {
        color: #e0e0e0;
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        background-color: #2d2d44;
        border: 2px solid #3d3d54;
        border-radius: 4px;
    }

    QCheckBox::indicator:checked {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
        border: 2px solid #667eea;
    }

    QTableWidget {
        background-color: #2d2d44;
        gridline-color: #3d3d54;
        border: 1px solid #3d3d54;
    }

    QTableWidget::item {
        padding: 5px;
        border: none;
    }

    QTableWidget::item:selected {
        background-color: #667eea;
    }

    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d3d54, stop:1 #2d2d44);
        color: #e0e0e0;
        padding: 6px;
        border: none;
        border-right: 1px solid #2d2d44;
        border-bottom: 1px solid #3d3d54;
        font-weight: bold;
    }

    QProgressBar {
        background-color: #2d2d44;
        border: 2px solid #3d3d54;
        border-radius: 6px;
        text-align: center;
        color: white;
        height: 25px;
    }

    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
        border-radius: 4px;
    }

    QScrollBar:vertical {
        background-color: #2d2d44;
        width: 12px;
        border: none;
    }

    QScrollBar::handle:vertical {
        background-color: #667eea;
        border-radius: 6px;
        min-height: 20px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #764ba2;
    }

    QFrame {
        background-color: #1e1e2e;
        border: none;
    }

    QStatusBar {
        background-color: #2d2d44;
        color: #e0e0e0;
        border-top: 1px solid #3d3d54;
    }

    QDialogButtonBox {
        button-layout: 2;
    }
"""


# ============================================================================
# THREADING CLASSES
# ============================================================================

class LoadDataThread(QThread):
    """Load data from server in background thread"""

    success = pyqtSignal(str, list)  # data_type, data
    error = pyqtSignal(str, str)  # data_type, error_message

    def __init__(self, endpoint, data_type):
        super().__init__()
        self.endpoint = endpoint
        self.data_type = data_type

    def run(self):
        try:
            response = requests.get(
                f"{SERVER_URL}{self.endpoint}",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json().get(self.data_type, [])
                self.success.emit(self.data_type, data)
            else:
                self.error.emit(self.data_type, f"Server error: {response.status_code}")

        except Exception as e:
            self.error.emit(self.data_type, str(e))

class AddDataThread(QThread):
    """Add data to server in background thread"""

    success = pyqtSignal(str)  # success message
    error = pyqtSignal(str)  # error message

    def __init__(self, endpoint, data):
        super().__init__()
        self.endpoint = endpoint
        self.data = data

    def run(self):
        try:
            response = requests.post(
                f"{SERVER_URL}{self.endpoint}",
                json=self.data,
                headers={"Authorization": API_TOKEN},
                timeout=10
            )

            if response.status_code == 200:
                msg = response.json().get('message', 'Success')
                self.success.emit(msg)
            else:
                msg = response.json().get('message', 'Failed')
                self.error.emit(msg)

        except Exception as e:
            self.error.emit(str(e))

class DeleteDataThread(QThread):
    """Delete data from server in background thread"""

    success = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, endpoint):
        super().__init__()
        self.endpoint = endpoint

    def run(self):
        try:
            response = requests.delete(
                f"{SERVER_URL}{self.endpoint}",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.success.emit("Deleted successfully")
            else:
                self.error.emit("Failed to delete")

        except Exception as e:
            self.error.emit(str(e))



# ============================================================================
# SERVER CONNECTION THREAD
# ============================================================================

class ServerSyncThread(QThread):
    """Background thread for syncing with server"""

    sync_completed = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, action, data):
        super().__init__()
        self.action = action
        self.data = data

    def run(self):
        try:
            if self.action == "add_student":
                self.progress_updated.emit(25, "Validating student...")
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-student",
                    json=self.data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )
                self.progress_updated.emit(75, "Saving to server...")

            elif self.action == "add_question":
                self.progress_updated.emit(25, "Validating question...")
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-question",
                    json=self.data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )
                self.progress_updated.emit(75, "Saving to server...")

            elif self.action == "add_exam":
                self.progress_updated.emit(25, "Creating exam...")
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-exam",
                    json=self.data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )
                self.progress_updated.emit(75, "Finalizing...")

            if response.status_code == 200:
                self.progress_updated.emit(100, "Completed")
                self.sync_completed.emit(True, response.json().get('message', 'Success'))
            else:
                self.sync_completed.emit(False, response.json().get('message', 'Error'))

        except Exception as e:
            self.sync_completed.emit(False, str(e))

# ============================================================================
# DIALOGS
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

        # Title
        title = QLabel("Add New Student")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        # Form fields
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

        # Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("✓ Save Student")
        save_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #505070;
                color: white;
            }
            QPushButton:hover {
                background-color: #606080;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_input_field(self, label_text, placeholder):
        """Create labeled input field"""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel(label_text)
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #e0e0e0;")
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

        # Title
        title = QLabel("Add New Question")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        # Question
        q_label = QLabel("❓ Question Text")
        q_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(q_label)

        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("Enter the question...")
        self.question_input.setMinimumHeight(100)
        layout.addWidget(self.question_input)

        # Options
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

        # Correct answer
        ans_layout = QHBoxLayout()
        ans_label = QLabel("✓ Correct Answer:")
        ans_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        ans_layout.addWidget(ans_label)

        self.correct_answer = QComboBox()
        self.correct_answer.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])
        ans_layout.addWidget(self.correct_answer)
        ans_layout.addStretch()
        layout.addLayout(ans_layout)

        # Subject and marks
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(15)

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

        # Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("✓ Save Question")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #505070;
                color: white;
            }
        """)
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

# ============================================================================
# IMPROVED CreateExamDialog with Group Filter & Assign Students
# ============================================================================

class CreateExamDialog(QDialog):
    """Create new exam dialog with student & question assignment"""

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

        # Title
        title = QLabel("Create New Exam")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        main_layout.addWidget(title)

        # ===== BASIC INFO SECTION =====
        basic_label = QLabel("📝 Basic Information")
        basic_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        basic_label.setStyleSheet("color: #667eea;")
        main_layout.addWidget(basic_label)

        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(10)

        name_label = QLabel("Exam Name:")
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.exam_name = QLineEdit()
        self.exam_name.setPlaceholderText("e.g., Physics Final Exam")
        self.exam_name.setMinimumHeight(40)
        basic_layout.addWidget(name_label)
        basic_layout.addWidget(self.exam_name)

        desc_label = QLabel("Description:")
        desc_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.description = QTextEdit()
        self.description.setPlaceholderText("Enter exam description...")
        self.description.setMinimumHeight(80)
        basic_layout.addWidget(desc_label)
        basic_layout.addWidget(self.description)

        main_layout.addLayout(basic_layout)
        main_layout.addSpacing(10)

        # ===== EXAM SETTINGS SECTION =====
        settings_label = QLabel("⚙️ Exam Settings")
        settings_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        settings_label.setStyleSheet("color: #667eea;")
        main_layout.addWidget(settings_label)

        settings_layout = QGridLayout()
        settings_layout.setSpacing(15)

        # Row 1: DateTime & Duration
        start_label = QLabel("Start DateTime:")
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setDateTime(QDateTime.currentDateTime())
        self.start_datetime.setMinimumHeight(40)
        settings_layout.addWidget(start_label, 0, 0)
        settings_layout.addWidget(self.start_datetime, 0, 1)

        duration_label = QLabel("Duration (min):")
        self.duration = QSpinBox()
        self.duration.setValue(60)
        self.duration.setMinimum(10)
        self.duration.setMaximum(600)
        self.duration.setMinimumHeight(40)
        settings_layout.addWidget(duration_label, 0, 2)
        settings_layout.addWidget(self.duration, 0, 3)

        # Row 2: Passing & Total Marks
        passing_label = QLabel("Passing %:")
        self.passing = QSpinBox()
        self.passing.setValue(40)
        self.passing.setMinimum(0)
        self.passing.setMaximum(100)
        self.passing.setMinimumHeight(40)
        settings_layout.addWidget(passing_label, 1, 0)
        settings_layout.addWidget(self.passing, 1, 1)

        marks_label = QLabel("Total Marks:")
        self.total_marks = QSpinBox()
        self.total_marks.setValue(100)
        self.total_marks.setMinimum(1)
        self.total_marks.setMaximum(1000)
        self.total_marks.setMinimumHeight(40)
        settings_layout.addWidget(marks_label, 1, 2)
        settings_layout.addWidget(self.total_marks, 1, 3)

        # Row 3: Tab Switch & Camera
        tab_label = QLabel("Tab Switch Limit:")
        self.tab_limit = QSpinBox()
        self.tab_limit.setValue(3)
        self.tab_limit.setMinimum(0)
        self.tab_limit.setMinimumHeight(40)
        settings_layout.addWidget(tab_label, 2, 0)
        settings_layout.addWidget(self.tab_limit, 2, 1)

        self.camera_required = QCheckBox("📷 Require Webcam")
        self.camera_required.setChecked(True)
        settings_layout.addWidget(self.camera_required, 2, 2)

        main_layout.addLayout(settings_layout)
        main_layout.addSpacing(10)

        # ===== STUDENTS & QUESTIONS SECTION =====
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # LEFT: STUDENTS
        students_label = QLabel("👥 Assign Students")
        students_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        students_label.setStyleSheet("color: #667eea;")

        students_container = QWidget()
        students_layout = QVBoxLayout()
        students_layout.setContentsMargins(0, 0, 0, 0)
        students_layout.setSpacing(10)
        students_layout.addWidget(students_label)

        # Group Filter
        group_layout = QHBoxLayout()
        group_filter_label = QLabel("Filter by Group:")
        self.group_filter = QComboBox()
        self.group_filter.addItem("All Groups")
        groups = sorted(set([s.get('group_name', 'Unknown') for s in self.students]))
        self.group_filter.addItems(groups)
        self.group_filter.currentTextChanged.connect(self.update_students_list)
        group_layout.addWidget(group_filter_label)
        group_layout.addWidget(self.group_filter)
        group_layout.addStretch()
        students_layout.addLayout(group_layout)

        # Students List
        students_list_label = QLabel("Select Students:")
        self.students_list = QListWidget()
        self.students_list.setMinimumHeight(200)
        self.students_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        students_layout.addWidget(students_list_label)
        students_layout.addWidget(self.students_list)

        select_all_students_btn = QPushButton("✓ Select All Students")
        select_all_students_btn.setMinimumHeight(35)
        select_all_students_btn.clicked.connect(self.select_all_students)
        students_layout.addWidget(select_all_students_btn)

        students_container.setLayout(students_layout)
        content_layout.addWidget(students_container)

        # RIGHT: QUESTIONS
        questions_label = QLabel("❓ Select Questions")
        questions_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        questions_label.setStyleSheet("color: #667eea;")

        questions_container = QWidget()
        questions_layout = QVBoxLayout()
        questions_layout.setContentsMargins(0, 0, 0, 0)
        questions_layout.setSpacing(10)
        questions_layout.addWidget(questions_label)

        # Subject Filter
        subject_layout = QHBoxLayout()
        subject_filter_label = QLabel("Filter by Subject:")
        self.subject_filter = QComboBox()
        self.subject_filter.addItem("All Subjects")
        subjects = sorted(set([q.get('subject', 'General') for q in self.questions]))
        self.subject_filter.addItems(subjects)
        self.subject_filter.currentTextChanged.connect(self.update_questions_list)
        subject_layout.addWidget(subject_filter_label)
        subject_layout.addWidget(self.subject_filter)
        subject_layout.addStretch()
        questions_layout.addLayout(subject_layout)

        # Questions List
        questions_list_label = QLabel("Select Questions:")
        self.questions_list = QListWidget()
        self.questions_list.setMinimumHeight(200)
        self.questions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        questions_layout.addWidget(questions_list_label)
        questions_layout.addWidget(self.questions_list)

        select_all_questions_btn = QPushButton("✓ Select All Questions")
        select_all_questions_btn.setMinimumHeight(35)
        select_all_questions_btn.clicked.connect(self.select_all_questions)
        questions_layout.addWidget(select_all_questions_btn)

        questions_container.setLayout(questions_layout)
        content_layout.addWidget(questions_container)

        main_layout.addLayout(content_layout, 1)
        main_layout.addSpacing(15)

        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        create_btn = QPushButton("✓ Create Exam")
        create_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        create_btn.setMinimumHeight(50)
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cancel_btn.setMinimumHeight(50)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #505070;
                color: white;
            }
            QPushButton:hover {
                background-color: #606080;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # Populate lists
        self.update_students_list()
        self.update_questions_list()

    def update_students_list(self):
        """Update students list based on group filter"""
        self.students_list.clear()
        selected_group = self.group_filter.currentText()

        for student in self.students:
            if selected_group == "All Groups" or student.get('group_name') == selected_group:
                student_name = student.get('name', '')
                student_username = student.get('username', '')
                student_group = student.get('group_name', '')
                item_text = f"{student_name} ({student_username}) - {student_group}"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, student.get('id'))
                self.students_list.addItem(item)

    def update_questions_list(self):
        """Update questions list based on subject filter"""
        self.questions_list.clear()
        selected_subject = self.subject_filter.currentText()

        for question in self.questions:
            if selected_subject == "All Subjects" or question.get('subject') == selected_subject:
                q_text = question.get('question', '')[:50]
                subject = question.get('subject', 'N/A')
                marks = question.get('marks', 1)

                item_text = f"{q_text}... [{subject}] - {marks}M"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, question.get('id'))
                self.questions_list.addItem(item)

    def select_all_students(self):
        """Select all students in list"""
        for i in range(self.students_list.count()):
            self.students_list.item(i).setSelected(True)

    def select_all_questions(self):
        """Select all questions in list"""
        for i in range(self.questions_list.count()):
            self.questions_list.item(i).setSelected(True)

    def get_data(self):
        """Get form data with selected students and questions"""
        # Get selected students
        selected_students = []
        for item in self.students_list.selectedItems():
            sid = item.data(Qt.ItemDataRole.UserRole)
            if sid:
                selected_students.append(sid)

        # Get selected questions
        selected_questions = []
        for item in self.questions_list.selectedItems():
            qid = item.data(Qt.ItemDataRole.UserRole)
            if qid:
                selected_questions.append(qid)

        # Validation
        if not self.exam_name.text().strip():
            QMessageBox.warning(self, "Error", "❌ Please enter exam name")
            return None

        if not self.start_datetime.dateTime():
            QMessageBox.warning(self, "Error", "❌ Please set start datetime")
            return None

        if not selected_students:
            QMessageBox.warning(self, "Error", "❌ Please select at least one student")
            return None

        if not selected_questions:
            QMessageBox.warning(self, "Error", "❌ Please select at least one question")
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
# ADMIN LOGIN WINDOW
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

        # Logo
        emoji = QLabel("🔑")
        emoji.setFont(QFont("Segoe UI Emoji", 80))
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(emoji)

        # Title
        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        # Username
        user_label = QLabel("👤 Username")
        user_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(user_label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter admin username")
        self.username.setMinimumHeight(50)
        layout.addWidget(self.username)

        # Password
        pass_label = QLabel("🔒 Password")
        pass_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(pass_label)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(50)
        self.password.returnPressed.connect(self.login)
        layout.addWidget(self.password)

        layout.addSpacing(10)

        # Login button
        login_btn = QPushButton("🚀 Login")
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setMinimumHeight(60)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)

        # Status
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

        # Default credentials for testing
        if username == "admin" and password == "admin123":
            self.admin_panel = AdminPanel(username)
            self.admin_panel.show()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Invalid credentials")
            self.password.clear()

# ============================================================================
# ADMIN PANEL - MAIN WINDOW
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
        """Initialize admin panel UI"""
        self.setWindowTitle(f"Admin Dashboard - {self.admin_username}")
        self.setGeometry(50, 50, 1600, 900)

        # Create menu bar
        self.create_menu_bar()

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 11))

        # Students tab
        students_widget = self.create_students_tab()
        self.tabs.addTab(students_widget, "👥 Students")

        # Questions tab
        questions_widget = self.create_questions_tab()
        self.tabs.addTab(questions_widget, "❓ Questions")

        # Exams tab
        exams_widget = self.create_exams_tab()
        self.tabs.addTab(exams_widget, "📝 Exams")

        # Results tab
        results_widget = self.create_results_tab()
        self.tabs.addTab(results_widget, "📊 Results")

        # Security tab
        security_widget = self.create_security_tab()
        self.tabs.addTab(security_widget, "🔒 Security")

        main_layout.addWidget(self.tabs, 1)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("color: #e0e0e0;")
        self.status_bar.showMessage(f"Ready | Server: {SERVER_URL}")

        central_widget.setLayout(main_layout)

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet(DARK_STYLESHEET)

        # File menu
        file_menu = menubar.addMenu("📁 File")

        refresh_action = file_menu.addAction("🔄 Refresh")
        refresh_action.triggered.connect(self.load_all_data)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("🚪 Exit")
        exit_action.triggered.connect(self.close)

        # Tools menu
        tools_menu = menubar.addMenu("⚙️ Tools")

        sync_action = tools_menu.addAction("☁️ Sync with Server")
        sync_action.triggered.connect(self.sync_with_server)

        # Help menu
        help_menu = menubar.addMenu("❓ Help")

        about_action = help_menu.addAction("ℹ️ About")
        about_action.triggered.connect(self.show_about)

    def create_header(self):
        """Create header with stats"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                padding: 20px;
            }
        """)

        layout = QHBoxLayout()

        # Title
        title = QLabel(f"👤 Welcome, {self.admin_username}!")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        layout.addStretch()

        # Stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(30)

        self.students_stat = self.create_stat_widget("👥 Students", "0")
        stats_layout.addWidget(self.students_stat)

        self.questions_stat = self.create_stat_widget("❓ Questions", "0")
        stats_layout.addWidget(self.questions_stat)

        self.exams_stat = self.create_stat_widget("📝 Exams", "0")
        stats_layout.addWidget(self.exams_stat)

        self.results_stat = self.create_stat_widget("📊 Results", "0")
        stats_layout.addWidget(self.results_stat)

        layout.addLayout(stats_layout)

        header.setLayout(layout)
        return header

    def create_stat_widget(self, label, value):
        """Create stat widget"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        label_text = QLabel(label)
        label_text.setFont(QFont("Segoe UI", 10))
        label_text.setStyleSheet("color: rgba(255,255,255,0.8);")
        layout.addWidget(label_text)

        value_text = QLabel(value)
        value_text.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        value_text.setStyleSheet("color: white;")
        layout.addWidget(value_text)

        widget.setLayout(layout)
        return widget

    def create_students_tab(self):
        """Create students tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add Student")
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_student)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_students)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(7)
        self.students_table.setHorizontalHeaderLabels([
            "ID", "Name", "Username", "Email", "Roll #", "Group", "Action"
        ])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setMinimumHeight(500)
        layout.addWidget(self.students_table)

        widget.setLayout(layout)
        return widget

    def create_questions_tab(self):
        """Create questions tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Add Question")
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.add_question)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_questions)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.questions_table = QTableWidget()
        self.questions_table.setColumnCount(7)
        self.questions_table.setHorizontalHeaderLabels([
            "ID", "Question", "Subject", "Marks", "Ans", "Opt1", "Action"
        ])
        self.questions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.questions_table.setAlternatingRowColors(True)
        self.questions_table.setMinimumHeight(500)
        layout.addWidget(self.questions_table)

        widget.setLayout(layout)
        return widget

    def create_exams_tab(self):
        """Create exams tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buttons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("➕ Create Exam")
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        add_btn.setMinimumHeight(45)
        add_btn.clicked.connect(self.create_exam)
        btn_layout.addWidget(add_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_exams)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.exams_table = QTableWidget()
        self.exams_table.setColumnCount(7)
        self.exams_table.setHorizontalHeaderLabels([
            "ID", "Exam Name", "Start", "Duration", "Students", "Questions", "Action"
        ])
        self.exams_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.exams_table.setAlternatingRowColors(True)
        self.exams_table.setMinimumHeight(500)
        layout.addWidget(self.exams_table)

        widget.setLayout(layout)
        return widget

    def create_results_tab(self):
        """Create results tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        refresh_btn.setMinimumHeight(45)
        refresh_btn.clicked.connect(self.load_results)
        btn_layout.addWidget(refresh_btn)

        export_btn = QPushButton("📥 Export Results")
        export_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        export_btn.setMinimumHeight(45)
        btn_layout.addWidget(export_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(9)
        self.results_table.setHorizontalHeaderLabels([
            "ID", "Student", "Exam", "Score", "Total", "Percentage", "Time", "Date", "Action"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setMinimumHeight(500)
        layout.addWidget(self.results_table)

        widget.setLayout(layout)
        return widget

    def create_security_tab(self):
        """Create security tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Info
        info = QLabel("🔒 Security Logs & Violations")
        info.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        info.setStyleSheet("color: #667eea;")
        layout.addWidget(info)

        # Buttons
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Refresh Logs")
        refresh_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        refresh_btn.setMinimumHeight(45)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table
        self.security_table = QTableWidget()
        self.security_table.setColumnCount(6)
        self.security_table.setHorizontalHeaderLabels([
            "ID", "Student", "Exam", "Violation Type", "Details", "Time"
        ])
        self.security_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.security_table.setAlternatingRowColors(True)
        self.security_table.setMinimumHeight(500)
        layout.addWidget(self.security_table)

        widget.setLayout(layout)
        return widget

    def load_all_data(self):
        """Load all data in background threads"""
        self.status_bar.showMessage("Loading students...")
        self.load_thread_students = LoadDataThread("/api/students", "students")
        self.load_thread_students.success.connect(self.on_students_loaded)
        self.load_thread_students.error.connect(self.on_load_error)
        self.load_thread_students.start()

        self.load_thread_questions = LoadDataThread("/api/questions", "questions")
        self.load_thread_questions.success.connect(self.on_questions_loaded)
        self.load_thread_questions.error.connect(self.on_load_error)
        self.load_thread_questions.start()

        self.load_thread_exams = LoadDataThread("/api/exams", "exams")
        self.load_thread_exams.success.connect(self.on_exams_loaded)
        self.load_thread_exams.error.connect(self.on_load_error)
        self.load_thread_exams.start()

        self.load_thread_results = LoadDataThread("/api/results", "results")
        self.load_thread_results.success.connect(self.on_results_loaded)
        self.load_thread_results.error.connect(self.on_load_error)
        self.load_thread_results.start()
        
    def load_students(self):
        """Load students from server"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/students",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.students = response.json().get('students', [])
                self.students_table.setRowCount(len(self.students))

                for i, student in enumerate(self.students):
                    self.students_table.setItem(i, 0, QTableWidgetItem(str(student.get('id', ''))))
                    self.students_table.setItem(i, 1, QTableWidgetItem(student.get('name', '')))
                    self.students_table.setItem(i, 2, QTableWidgetItem(student.get('username', '')))
                    self.students_table.setItem(i, 3, QTableWidgetItem(student.get('email', '')))
                    self.students_table.setItem(i, 4, QTableWidgetItem(student.get('roll_number', '')))
                    self.students_table.setItem(i, 5, QTableWidgetItem(student.get('group_name', '')))

                    delete_btn = QPushButton("🗑️")
                    delete_btn.clicked.connect(lambda checked, sid=student.get('id'): self.delete_student(sid))
                    self.students_table.setCellWidget(i, 6, delete_btn)

                self.students_stat.findChild(QLabel, text=str(len(self.students))).setText(str(len(self.students)))
                self.status_bar.showMessage(f"Loaded {len(self.students)} students")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load students: {str(e)}")

    def load_questions(self):
        """Load questions from server"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/questions",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.questions = response.json().get('questions', [])
                self.questions_table.setRowCount(len(self.questions))

                for i, question in enumerate(self.questions):
                    self.questions_table.setItem(i, 0, QTableWidgetItem(str(question.get('id', ''))))
                    q_text = question.get('question', '')[:50]
                    self.questions_table.setItem(i, 1, QTableWidgetItem(q_text))
                    self.questions_table.setItem(i, 2, QTableWidgetItem(question.get('subject', '')))
                    self.questions_table.setItem(i, 3, QTableWidgetItem(str(question.get('marks', ''))))
                    self.questions_table.setItem(i, 4, QTableWidgetItem(str(question.get('correct_answer', ''))))
                    self.questions_table.setItem(i, 5, QTableWidgetItem(question.get('option1', '')[:20]))

                    delete_btn = QPushButton("🗑️")
                    delete_btn.clicked.connect(lambda checked, qid=question.get('id'): self.delete_question(qid))
                    self.questions_table.setCellWidget(i, 6, delete_btn)

                self.status_bar.showMessage(f"Loaded {len(self.questions)} questions")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load questions: {str(e)}")

    def load_exams(self):
        """Load exams from server"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/exams",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.exams = response.json().get('exams', [])
                self.exams_table.setRowCount(len(self.exams))

                for i, exam in enumerate(self.exams):
                    self.exams_table.setItem(i, 0, QTableWidgetItem(str(exam.get('id', ''))))
                    self.exams_table.setItem(i, 1, QTableWidgetItem(exam.get('exam_name', '')))
                    self.exams_table.setItem(i, 2, QTableWidgetItem(exam.get('start_datetime', '')[:16]))
                    self.exams_table.setItem(i, 3, QTableWidgetItem(str(exam.get('duration_minutes', ''))))
                    self.exams_table.setItem(i, 4, QTableWidgetItem("0"))
                    self.exams_table.setItem(i, 5, QTableWidgetItem("0"))

                    delete_btn = QPushButton("🗑️")
                    delete_btn.clicked.connect(lambda checked, eid=exam.get('id'): self.delete_exam(eid))
                    self.exams_table.setCellWidget(i, 6, delete_btn)

                self.status_bar.showMessage(f"Loaded {len(self.exams)} exams")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load exams: {str(e)}")

    def load_results(self):
        """Load results from server"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/results",
                headers={"Authorization": API_TOKEN},
                timeout=5
            )

            if response.status_code == 200:
                self.results = response.json().get('results', [])
                self.results_table.setRowCount(len(self.results))

                for i, result in enumerate(self.results):
                    self.results_table.setItem(i, 0, QTableWidgetItem(str(result.get('id', ''))))
                    self.results_table.setItem(i, 1, QTableWidgetItem(result.get('name', '')))
                    self.results_table.setItem(i, 2, QTableWidgetItem(result.get('exam_name', '')))
                    self.results_table.setItem(i, 3, QTableWidgetItem(str(result.get('score', ''))))
                    self.results_table.setItem(i, 4, QTableWidgetItem(str(result.get('total_marks', ''))))
                    percentage = result.get('percentage', 0)
                    self.results_table.setItem(i, 5, QTableWidgetItem(f"{percentage:.1f}%"))
                    self.results_table.setItem(i, 6, QTableWidgetItem(result.get('time_taken', '')))
                    self.results_table.setItem(i, 7, QTableWidgetItem(result.get('submission_time', '')[:10]))

                self.status_bar.showMessage(f"Loaded {len(self.results)} results")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load results: {str(e)}")

    def add_student(self):
        """Add new student"""
        dialog = AddStudentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            if not data['name'] or not data['username'] or not data['password']:
                QMessageBox.warning(self, "Error", "Please fill all required fields")
                return

            try:
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-student",
                    json=data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )

                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Student added successfully")
                    self.load_students()
                else:
                    msg = response.json().get('message', 'Failed to add student')
                    QMessageBox.warning(self, "Error", msg)

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def add_question(self):
        """Add new question"""
        dialog = AddQuestionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()

            if not data['question'] or not all([data['option1'], data['option2'], data['option3'], data['option4']]):
                QMessageBox.warning(self, "Error", "Please fill all required fields")
                return

            try:
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-question",
                    json=data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )

                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Question added successfully")
                    self.load_questions()
                else:
                    msg = response.json().get('message', 'Failed to add question')
                    QMessageBox.warning(self, "Error", msg)

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def create_exam(self):
        """Create new exam"""
        dialog = CreateExamDialog(self, self.students, self.questions)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            if data is None:  # Validation failed
                return
            
            if not data['exam_name'] or not data['start_datetime']:
                QMessageBox.warning(self, "Error", "Please fill all required fields")
                return
            
            try:
                response = requests.post(
                    f"{SERVER_URL}/api/admin/add-exam",
                    json=data,
                    headers={"Authorization": API_TOKEN},
                    timeout=10
                )
                
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Exam created successfully!")
                    self.load_exams()
                else:
                    msg = response.json().get('message', 'Failed to create exam')
                    QMessageBox.warning(self, "Error", msg)
            
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_student(self, student_id):
        """Delete student"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete student ID {student_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                response = requests.delete(
                    f"{SERVER_URL}/api/admin/delete-student/{student_id}",
                    headers={"Authorization": API_TOKEN},
                    timeout=5
                )

                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Student deleted")
                    self.load_students()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete student")

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_question(self, question_id):
        """Delete question"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete question ID {question_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                response = requests.delete(
                    f"{SERVER_URL}/api/admin/delete-question/{question_id}",
                    headers={"Authorization": API_TOKEN},
                    timeout=5
                )

                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Question deleted")
                    self.load_questions()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete question")

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def delete_exam(self, exam_id):
        """Delete exam"""
        reply = QMessageBox.question(
            self, "Confirm",
            f"Delete exam ID {exam_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                response = requests.delete(
                    f"{SERVER_URL}/api/admin/delete-exam/{exam_id}",
                    headers={"Authorization": API_TOKEN},
                    timeout=5
                )

                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Exam deleted")
                    self.load_exams()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete exam")

            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def sync_with_server(self):
        """Sync data with server"""
        QMessageBox.information(self, "Sync", "Syncing with server...")
        self.load_all_data()

    def show_about(self):
        """Show about dialog"""
        QMessageBox.information(
            self,
            "About",
            "Admin Dashboard v1.0\n\n"
            "Central Examination System\n"
            "Server-based with SQLite Database\n\n"
            "© 2025 All Rights Reserved"
        )

# ============================================================================
# MAIN APPLICATION
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
STUDENT EXAM PORTAL - Complete Version (No Default Login)
Modern exam taking application with server-based authentication
Students MUST login with credentials added by admin
"""

import sys
import requests
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
# CONFIGURATION
# ============================================================================

SERVER_URL = "http://localhost:5000"  # Change to your server IP
API_TOKEN = "secure_token_12345"  # Must match server.py
EXAM_DB = "student_exam.db"

# ============================================================================
# MAIN WINDOW - STUDENT LOGIN
# ============================================================================

class StudentLoginWindow(QMainWindow):
    """
    Modern student login interface
    NO default login - students must be added by admin first
    """

    def __init__(self):
        super().__init__()
        self.student_data = None
        self.server_online = False
        self.init_ui()
        self.check_server()

    def init_ui(self):
        """Initialize the login UI"""
        self.setWindowTitle("Student Exam Portal - Login")
        self.setFixedSize(900, 700)

        # Main stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2
                );
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(60, 40, 60, 40)
        main_layout.setSpacing(30)

        # Logo/Icon
        logo_label = QLabel("🎓")
        logo_label.setFont(QFont("Segoe UI Emoji", 80))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(logo_label)

        # Title
        title = QLabel("Student Exam Portal")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Secure Online Examination System")
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("color: rgba(255, 255, 255, 0.95);")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)

        # Server status
        self.server_status = QLabel("🟡 Checking server...")
        self.server_status.setFont(QFont("Segoe UI", 11))
        self.server_status.setStyleSheet("color: rgba(255, 255, 255, 0.85); padding: 8px;")
        self.server_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.server_status)

        main_layout.addSpacing(15)

        # Form Frame
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 25px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
        """)
        form_frame.setMinimumWidth(350)

        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(50, 50, 50, 50)
        form_layout.setSpacing(25)

        # Username Field
        username_label = QLabel("👤 Username")
        username_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #2c3e50;")
        form_layout.addWidget(username_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username (provided by admin)")
        self.username_input.setFont(QFont("Segoe UI", 12))
        self.username_input.setMinimumHeight(50)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 14px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                background-color: #f5f7fa;
                color: #2c3e50;
                font-size: 12px;
                selection-background-color: #667eea;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background-color: #ffffff;
            }
            QLineEdit:hover {
                border: 2px solid #667eea;
            }
        """)
        form_layout.addWidget(self.username_input)

        # Password Field
        password_label = QLabel("🔒 Password")
        password_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        password_label.setStyleSheet("color: #2c3e50;")
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFont(QFont("Segoe UI", 12))
        self.password_input.setMinimumHeight(50)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 14px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 12px;
                background-color: #f5f7fa;
                color: #2c3e50;
                font-size: 12px;
                selection-background-color: #667eea;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background-color: #ffffff;
            }
            QLineEdit:hover {
                border: 2px solid #667eea;
            }
        """)
        self.password_input.returnPressed.connect(self.login)
        form_layout.addWidget(self.password_input)

        form_layout.addSpacing(10)

        # Remember Me Checkbox
        remember_label = QLabel("💡 Credentials provided by your administrator")
        remember_label.setFont(QFont("Segoe UI", 10))
        remember_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        form_layout.addWidget(remember_label)

        form_layout.addSpacing(15)

        # Login Button
        login_btn = QPushButton("🚀 Login to Exam")
        login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        login_btn.setMinimumHeight(60)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2
                );
                color: white;
                padding: 16px 30px;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5568d3, stop:1 #6a3f8f
                );
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4458b3, stop:1 #5a2f7f
                );
            }
        """)
        login_btn.clicked.connect(self.login)
        form_layout.addWidget(login_btn)

        form_frame.setLayout(form_layout)
        main_layout.addWidget(form_frame, 0, Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()

        # Footer
        footer = QLabel("ℹ️ If you don't have login credentials, contact your administrator")
        footer.setFont(QFont("Segoe UI", 10))
        footer.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)

        central_widget.setLayout(main_layout)

    def check_server(self):
        """Check if server is online"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/health",
                timeout=3
            )
            if response.status_code == 200:
                self.server_online = True
                self.server_status.setText("🟢 Server Online - Ready to login")
                self.server_status.setStyleSheet("color: #2ecc71; padding: 8px; font-weight: bold;")
            else:
                self.server_online = False
                self.server_status.setText("🔴 Server Offline")
                self.server_status.setStyleSheet("color: #e74c3c; padding: 8px;")
        except:
            self.server_online = False
            self.server_status.setText("🔴 Cannot reach server")
            self.server_status.setStyleSheet("color: #e74c3c; padding: 8px;")

    def login(self):
        """
        Authenticate student with central server
        NO default login - must be added by admin
        """
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        # Validation
        if not username:
            QMessageBox.warning(self, "Input Error", "Please enter your username")
            self.username_input.setFocus()
            return

        if not password:
            QMessageBox.warning(self, "Input Error", "Please enter your password")
            self.password_input.setFocus()
            return

        if not self.server_online:
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Cannot connect to server at {SERVER_URL}\n\n"
                "Please check:\n"
                "1. Server is running\n"
                "2. Correct IP address in configuration\n"
                "3. Network connectivity"
            )
            return

        # Show loading message
        self.username_input.setEnabled(False)
        self.password_input.setEnabled(False)

        try:
            # Authenticate with server
            response = requests.post(
                f"{SERVER_URL}/api/login",
                json={
                    "username": username,
                    "password": password
                },
                headers={"Authorization": API_TOKEN},
                timeout=10
            )

            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)

            # Handle response
            if response.status_code == 401:
                QMessageBox.warning(
                    self,
                    "Authentication Failed",
                    "Invalid username or password.\n\n"
                    "Please check your credentials and try again.\n"
                    "If you don't have an account, contact your administrator."
                )
                self.password_input.clear()
                self.password_input.setFocus()
                return

            if response.status_code != 200:
                QMessageBox.critical(
                    self,
                    "Server Error",
                    f"Server error: {response.status_code}\n{response.text}"
                )
                return

            # Parse response
            data = response.json()

            if not data.get('success'):
                QMessageBox.warning(
                    self,
                    "Login Failed",
                    data.get('message', 'Authentication failed')
                )
                self.password_input.clear()
                self.password_input.setFocus()
                return

            # Get student data
            student_data = data.get('student', {})
            exams = data.get('exams', [])

            # Check if exam is scheduled
            if not exams:
                QMessageBox.information(
                    self,
                    "No Exam Scheduled",
                    f"Hello {student_data.get('name')}!\n\n"
                    "No exam is currently scheduled for you.\n"
                    "Please check back later or contact your administrator."
                )
                self.password_input.clear()
                return

            # Launch exam window
            self.launch_exam(student_data, exams[0])

        except requests.exceptions.Timeout:
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            QMessageBox.critical(
                self,
                "Connection Timeout",
                f"Server not responding.\n\nURL: {SERVER_URL}"
            )
        except requests.exceptions.ConnectionError:
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Cannot connect to server.\n\nURL: {SERVER_URL}\n\n"
                "Make sure:\n"
                "1. Server is running (python server.py)\n"
                "2. Correct IP address is configured\n"
                "3. Firewall allows port 5000"
            )
        except Exception as e:
            self.username_input.setEnabled(True)
            self.password_input.setEnabled(True)
            QMessageBox.critical(
                self,
                "Error",
                f"Login error: {str(e)}"
            )

    def launch_exam(self, student_data, exam_data):
        """Launch exam window after successful login"""
        try:
            self.exam_window = ExamWindow(student_data, exam_data)
            self.exam_window.show()
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start exam: {str(e)}")

# ============================================================================
# EXAM WINDOW
# ============================================================================

class ExamWindow(QMainWindow):
    """Complete exam taking interface"""

    def __init__(self, student_data, exam_data):
        super().__init__()
        self.student_data = student_data
        self.exam_data = exam_data

        # Store exam details
        self.student_id = student_data.get('id')
        self.student_name = student_data.get('name')
        self.exam_id = exam_data.get('exam_id')
        self.exam_name = exam_data.get('exam_name')

        # Question tracking
        self.questions = []
        self.current_question_index = 0
        self.answers = {}

        # Security tracking
        self.tab_switch_count = 0
        self.camera_violations = 0

        # Timer
        self.start_time = datetime.now()
        self.duration_minutes = exam_data.get('duration_minutes', 60)
        self.time_limit = self.duration_minutes * 60
        self.time_remaining = self.time_limit

        self.init_ui()
        self.load_questions()
        self.start_timer()
        self.display_question()

        # Set fullscreen
        self.showFullScreen()

    def init_ui(self):
        """Initialize exam interface"""
        self.setWindowTitle(f"Exam: {self.exam_name}")

        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)

        # ===== HEADER =====
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                border-radius: 20px;
                padding: 25px;
            }
        """)
        header_layout = QHBoxLayout()

        # Exam name
        title = QLabel(f"📝 {self.exam_name}")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Timer
        self.timer_label = QLabel(f"{self.duration_minutes:02d}:00")
        self.timer_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: white;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(self.timer_label)

        header_layout.addSpacing(20)

        # Student info
        student_label = QLabel(f"Student: {self.student_name}")
        student_label.setFont(QFont("Segoe UI", 12))
        student_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        header_layout.addWidget(student_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header_frame.setLayout(header_layout)
        main_layout.addWidget(header_frame)

        # ===== PROGRESS BAR =====
        progress_frame = QFrame()
        progress_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 20px;
            }
        """)
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 10px;
                background-color: #e9ecef;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                border-radius: 10px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Question 0 of 0")
        self.status_label.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.status_label.setStyleSheet("color: #6c757d;")
        progress_layout.addWidget(self.status_label)

        progress_frame.setLayout(progress_layout)
        main_layout.addWidget(progress_frame)

        # ===== QUESTION CONTAINER =====
        question_frame = QFrame()
        question_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 20px;
                padding: 40px;
            }
        """)
        question_layout = QVBoxLayout()
        question_layout.setSpacing(20)

        # Question text
        self.question_label = QLabel("Loading question...")
        self.question_label.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        self.question_label.setStyleSheet("color: #2c3e50; line-height: 1.6;")
        self.question_label.setWordWrap(True)
        question_layout.addWidget(self.question_label)

        question_layout.addSpacing(15)

        # Options
        self.options_group = QButtonGroup()
        self.option_buttons = []

        for i in range(4):
            option = QRadioButton()
            option.setFont(QFont("Segoe UI", 14))
            option.setStyleSheet("""
                QRadioButton {
                    color: #495057;
                    padding: 15px;
                    spacing: 15px;
                }
                QRadioButton:hover {
                    color: #667eea;
                }
            """)
            self.options_group.addButton(option, i)
            self.option_buttons.append(option)
            question_layout.addWidget(option)

        question_frame.setLayout(question_layout)
        main_layout.addWidget(question_frame, 1)

        # ===== NAVIGATION BUTTONS =====
        nav_frame = QFrame()
        nav_frame.setStyleSheet("QFrame { background-color: transparent; }")
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(15)

        # Previous button
        self.prev_btn = QPushButton("⬅ Previous")
        self.prev_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.prev_btn.setMinimumHeight(55)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #667eea;
                padding: 12px 25px;
                border: 2px solid #667eea;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #667eea;
                color: white;
            }
            QPushButton:pressed {
                background-color: #5568d3;
            }
            QPushButton:disabled {
                color: #bdc3c7;
                border: 2px solid #bdc3c7;
                background-color: white;
            }
        """)
        self.prev_btn.clicked.connect(self.previous_question)
        nav_layout.addWidget(self.prev_btn)

        nav_layout.addStretch()

        # Next button
        self.next_btn = QPushButton("Next ➜")
        self.next_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.next_btn.setMinimumHeight(55)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5568d3, stop:1 #6a3f8f);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4458b3, stop:1 #5a2f7f);
            }
        """)
        self.next_btn.clicked.connect(self.next_question)
        nav_layout.addWidget(self.next_btn)

        # Submit button
        self.submit_btn = QPushButton("✓ Submit Exam")
        self.submit_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.submit_btn.setMinimumHeight(55)
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #11998e, stop:1 #38ef7d);
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0d7a70, stop:1 #2dc76a);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a5d59, stop:1 #219852);
            }
        """)
        self.submit_btn.clicked.connect(self.submit_exam)
        self.submit_btn.hide()
        nav_layout.addWidget(self.submit_btn)

        nav_frame.setLayout(nav_layout)
        main_layout.addWidget(nav_frame)

        central_widget.setLayout(main_layout)

    def load_questions(self):
        """Fetch exam questions from server"""
        try:
            response = requests.get(
                f"{SERVER_URL}/api/exam/{self.exam_id}",
                headers={"Authorization": API_TOKEN},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.questions = data.get('questions', [])

                if not self.questions:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "No questions available for this exam. Please contact administrator."
                    )
                    self.close()
                    return

                # Initialize answer tracking
                for i in range(len(self.questions)):
                    self.answers[i] = None

                self.update_progress()
            else:
                QMessageBox.critical(self, "Error", f"Server error: {response.status_code}")
                self.close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")
            self.close()

    def start_timer(self):
        """Start exam countdown timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):
        """Update countdown timer"""
        self.time_remaining -= 1

        # Update display
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Change color when time is running out
        if self.time_remaining <= 300:  # Last 5 minutes
            self.timer_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(
                self,
                "Time Expired",
                "Time is up! Your exam will be submitted automatically."
            )
            self.submit_exam()

    def display_question(self):
        """Display current question"""
        if self.current_question_index >= len(self.questions):
            return

        question = self.questions[self.current_question_index]

        # Display question text
        question_num = self.current_question_index + 1
        question_text = question.get('question', 'No question text')
        self.question_label.setText(f"Q{question_num}. {question_text}")

        # Display options
        options = [
            question.get('option1', ''),
            question.get('option2', ''),
            question.get('option3', ''),
            question.get('option4', '')
        ]

        for i, option in enumerate(options):
            if i < len(self.option_buttons):
                self.option_buttons[i].setText(option)

        # Restore saved answer if exists
        saved_answer = self.answers.get(self.current_question_index)
        if saved_answer is not None and saved_answer < len(self.option_buttons):
            self.option_buttons[saved_answer].setChecked(True)
        else:
            # Uncheck all
            self.options_group.setExclusive(False)
            for btn in self.option_buttons:
                btn.setChecked(False)
            self.options_group.setExclusive(True)

        # Update navigation buttons
        self.prev_btn.setEnabled(self.current_question_index > 0)

        is_last_question = self.current_question_index == len(self.questions) - 1
        self.next_btn.setVisible(not is_last_question)
        self.submit_btn.setVisible(is_last_question)

        self.update_progress()

    def save_current_answer(self):
        """Save currently selected answer"""
        selected = self.options_group.checkedId()
        if selected != -1:
            self.answers[self.current_question_index] = selected

    def next_question(self):
        """Move to next question"""
        self.save_current_answer()
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.display_question()

    def previous_question(self):
        """Move to previous question"""
        self.save_current_answer()
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.display_question()

    def update_progress(self):
        """Update progress bar and status"""
        answered = sum(1 for ans in self.answers.values() if ans is not None)
        total = len(self.questions)

        progress_percent = int((answered / total * 100)) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)

        self.status_label.setText(
            f"Question {self.current_question_index + 1} of {total} | "
            f"Answered: {answered}/{total} | Progress: {progress_percent}%"
        )

    def submit_exam(self):
        """Submit exam to server"""
        # Save last answer
        self.save_current_answer()

        # Check for unanswered questions
        unanswered = sum(1 for ans in self.answers.values() if ans is None)

        if unanswered > 0:
            reply = QMessageBox.question(
                self,
                "Incomplete Exam",
                f"You have {unanswered} unanswered question(s).\n\nAre you sure you want to submit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Stop timer
        self.timer.stop()

        # Calculate results
        correct_count = 0
        answers_data = []

        for i, question in enumerate(self.questions):
            student_answer = self.answers.get(i)
            correct_answer = question.get('correct_answer', 0)
            is_correct = (student_answer == correct_answer)

            if is_correct:
                correct_count += 1

            answers_data.append({
                'question_id': question.get('id'),
                'selected_answer': student_answer,
                'is_correct': 1 if is_correct else 0
            })

        # Calculate score
        total_marks = self.exam_data.get('total_marks', len(self.questions))
        percentage = (correct_count / total_marks * 100) if total_marks > 0 else 0

        # Calculate time taken
        time_taken_seconds = self.time_limit - self.time_remaining
        time_taken = f"{time_taken_seconds // 60}m {time_taken_seconds % 60}s"

        # Submit to server
        try:
            response = requests.post(
                f"{SERVER_URL}/api/submit-exam",
                json={
                    "exam_id": self.exam_id,
                    "student_id": self.student_id,
                    "score": correct_count,
                    "total_marks": total_marks,
                    "percentage": percentage,
                    "time_taken": time_taken,
                    "tab_switches": self.tab_switch_count,
                    "answers": answers_data
                },
                headers={"Authorization": API_TOKEN},
                timeout=10
            )

            if response.status_code == 200:
                # Show result
                passing_percentage = self.exam_data.get('passing_percentage', 40)
                passed = percentage >= passing_percentage

                result_message = (
                    f"Exam Submitted Successfully!\n\n"
                    f"Your Score: {correct_count}/{total_marks}\n"
                    f"Percentage: {percentage:.1f}%\n"
                    f"Time Taken: {time_taken}\n"
                    f"Status: {'✓ PASSED' if passed else '✗ FAILED'}\n"
                    f"Passing Score: {passing_percentage}%"
                )

                QMessageBox.information(self, "Exam Submitted", result_message)

                # Close application
                QApplication.quit()
            else:
                QMessageBox.warning(
                    self,
                    "Submission Error",
                    f"Failed to submit exam: {response.status_code}"
                )

        except requests.exceptions.Timeout:
            QMessageBox.critical(
                self,
                "Connection Error",
                "Server not responding. Please try again."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to submit exam: {str(e)}"
            )

# ============================================================================
# MAIN APPLICATION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print(" STUDENT EXAM PORTAL")
    print("="*70)
    print("\n✓ Server URL: " + SERVER_URL)
    print("✓ NO default login - credentials must be provided by administrator")
    print("\n" + "="*70 + "\n")

    app = QApplication(sys.argv)

    # Check for command line server URL override
    if len(sys.argv) > 1:
        SERVER_URL = sys.argv[1]
        print(f"Using server URL: {SERVER_URL}")

    login_window = StudentLoginWindow()
    login_window.show()

    sys.exit(app.exec())





"""
===================================================
CENTRAL EXAMINATION SERVER - Complete Fixed Version
SQLite Database Backend
===================================================
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta
import hashlib
from functools import wraps

app = Flask(__name__)
CORS(app)

# ============================================================================
# CONFIGURATION
# ============================================================================

DATABASE = "exam_system_server.db"
API_TOKEN = "secure_token_12345"

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize server database with all required tables"""
    conn = get_db()
    cursor = conn.cursor()

    print("📊 Creating database tables...")

    # Admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Admins table created")

    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            roll_number TEXT,
            group_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Students table created")

    # Questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option1 TEXT NOT NULL,
            option2 TEXT NOT NULL,
            option3 TEXT NOT NULL,
            option4 TEXT NOT NULL,
            correct_answer INTEGER NOT NULL,
            subject TEXT,
            marks INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Questions table created")

    # Exams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_name TEXT NOT NULL,
            description TEXT,
            start_datetime TIMESTAMP NOT NULL,
            duration_minutes INTEGER NOT NULL,
            passing_percentage INTEGER DEFAULT 40,
            camera_required INTEGER DEFAULT 1,
            tab_switch_limit INTEGER DEFAULT 3,
            total_marks INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Exams table created")

    # Exam questions mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)
    print("✓ Exam questions table created")

    # Exam students mapping
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    print("✓ Exam students table created")

    # Results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exam_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total_marks INTEGER NOT NULL,
            percentage REAL NOT NULL,
            time_taken TEXT,
            tab_switches INTEGER DEFAULT 0,
            camera_violations INTEGER DEFAULT 0,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (exam_id) REFERENCES exams(id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    print("✓ Results table created")

    # Student answers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            result_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_answer INTEGER,
            is_correct INTEGER DEFAULT 0,
            FOREIGN KEY (result_id) REFERENCES results(id),
            FOREIGN KEY (question_id) REFERENCES questions(id)
        )
    """)
    print("✓ Student answers table created")

    # Security logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            exam_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (exam_id) REFERENCES exams(id)
        )
    """)
    print("✓ Security logs table created")

    conn.commit()
    conn.close()
    print("\n✅ Database initialization complete!\n")

# ============================================================================
# AUTHENTICATION DECORATOR
# ============================================================================

def require_token(f):
    """Decorator to verify API token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token != API_TOKEN:
            return jsonify({'success': False, 'message': 'Invalid API token'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# HEALTH CHECK & INIT
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint - NO token required"""
    return jsonify({
        'status': 'online',
        'message': 'Central Examination Server is running',
        'timestamp': datetime.now().isoformat()
    })

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.route('/api/login', methods=['POST'])
@require_token
def student_login():
    """Student login endpoint"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Missing credentials'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Find student
        cursor.execute(
            "SELECT id, name, username, email, roll_number, group_name FROM students WHERE username = ? AND password = ?",
            (username, password)
        )
        student = cursor.fetchone()

        if not student:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

        student_id = student['id']

        # Get scheduled exams
        cursor.execute("""
            SELECT DISTINCT e.id, e.exam_name, e.description, e.start_datetime,
                   e.duration_minutes, e.passing_percentage, e.camera_required,
                   e.tab_switch_limit, e.total_marks
            FROM exams e
            INNER JOIN exam_students es ON e.id = es.exam_id
            WHERE es.student_id = ?
            ORDER BY e.start_datetime DESC
        """, (student_id,))

        exams = cursor.fetchall()
        scheduled_exams = [dict(exam) for exam in exams]

        conn.close()

        return jsonify({
            'success': True,
            'student': dict(student),
            'exams': scheduled_exams,
            'has_scheduled_exam': len(scheduled_exams) > 0
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
@require_token
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Missing credentials'}), 400

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email FROM admins WHERE username = ? AND password = ?",
            (username, password_hash)
        )
        admin = cursor.fetchone()
        conn.close()

        if not admin:
            return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401

        return jsonify({
            'success': True,
            'admin': dict(admin)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@app.route('/api/students', methods=['GET'])
@require_token
def get_students():
    """Get all students"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id, name, username, email, roll_number, group_name, created_at FROM students ORDER BY created_at DESC")
        students = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-student', methods=['POST'])
@require_token
def add_student():
    """Add new student"""
    try:
        data = request.json
        name = data.get('name')
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        roll_number = data.get('roll_number')
        group_name = data.get('group_name')

        if not all([name, username, password]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """INSERT INTO students (name, username, password, email, roll_number, group_name)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, username, password, email, roll_number, group_name)
            )
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Student added successfully'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'message': 'Username already exists'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/delete-student/<int:student_id>', methods=['DELETE'])
@require_token
def delete_student(student_id):
    """Delete student"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Student deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# QUESTION ENDPOINTS
# ============================================================================

@app.route('/api/questions', methods=['GET'])
@require_token
def get_questions():
    """Get all questions"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, question, option1, option2, option3, option4,
                   correct_answer, subject, marks FROM questions ORDER BY created_at DESC
        """)
        questions = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'questions': questions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-question', methods=['POST'])
@require_token
def add_question():
    """Add new question"""
    try:
        data = request.json
        question = data.get('question')
        option1 = data.get('option1')
        option2 = data.get('option2')
        option3 = data.get('option3')
        option4 = data.get('option4')
        correct_answer = data.get('correct_answer')
        subject = data.get('subject')
        marks = data.get('marks', 1)

        if not all([question, option1, option2, option3, option4, correct_answer is not None]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO questions (question, option1, option2, option3, option4, 
                                       correct_answer, subject, marks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (question, option1, option2, option3, option4, correct_answer, subject, marks)
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Question added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/delete-question/<int:question_id>', methods=['DELETE'])
@require_token
def delete_question(question_id):
    """Delete question"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Question deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# EXAM ENDPOINTS
# ============================================================================

@app.route('/api/exams', methods=['GET'])
@require_token
def get_exams():
    """Get all exams"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, exam_name, description, start_datetime, duration_minutes,
                   passing_percentage, camera_required, tab_switch_limit, total_marks 
            FROM exams ORDER BY start_datetime DESC
        """)
        exams = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'exams': exams})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-exam', methods=['POST'])
@require_token
def add_exam():
    """Add new exam"""
    try:
        data = request.json
        exam_name = data.get('exam_name')
        description = data.get('description')
        start_datetime = data.get('start_datetime')
        duration_minutes = data.get('duration_minutes')
        passing_percentage = data.get('passing_percentage', 40)
        camera_required = data.get('camera_required', 1)
        tab_switch_limit = data.get('tab_switch_limit', 3)
        total_marks = data.get('total_marks', 100)
        question_ids = data.get('question_ids', [])
        student_ids = data.get('student_ids', [])

        if not all([exam_name, start_datetime, duration_minutes]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Insert exam
        cursor.execute(
            """INSERT INTO exams (exam_name, description, start_datetime, duration_minutes,
                                   passing_percentage, camera_required, tab_switch_limit, total_marks)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (exam_name, description, start_datetime, duration_minutes,
             passing_percentage, camera_required, tab_switch_limit, total_marks)
        )
        exam_id = cursor.lastrowid

        # Add questions
        for question_id in question_ids:
            cursor.execute(
                "INSERT INTO exam_questions (exam_id, question_id) VALUES (?, ?)",
                (exam_id, question_id)
            )

        # Add students
        for student_id in student_ids:
            cursor.execute(
                "INSERT INTO exam_students (exam_id, student_id) VALUES (?, ?)",
                (exam_id, student_id)
            )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Exam created successfully', 'exam_id': exam_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/exam/<int:exam_id>', methods=['GET'])
@require_token
def get_exam_detail(exam_id):
    """Get exam with questions"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Get exam
        cursor.execute("""
            SELECT id, exam_name, description, start_datetime, duration_minutes,
                   passing_percentage, camera_required, tab_switch_limit, total_marks FROM exams
            WHERE id = ?
        """, (exam_id,))
        exam = cursor.fetchone()

        if not exam:
            conn.close()
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        # Get questions
        cursor.execute("""
            SELECT q.id, q.question, q.option1, q.option2, q.option3, q.option4,
                   q.correct_answer, q.subject, q.marks
            FROM questions q
            INNER JOIN exam_questions eq ON q.id = eq.question_id
            WHERE eq.exam_id = ?
        """, (exam_id,))
        questions = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'success': True,
            'exam': dict(exam),
            'questions': questions
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/delete-exam/<int:exam_id>', methods=['DELETE'])
@require_token
def delete_exam(exam_id):
    """Delete exam"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Exam deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# RESULTS ENDPOINTS
# ============================================================================

@app.route('/api/results', methods=['GET'])
@require_token
def get_results():
    """Get all exam results"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.id, e.exam_name, s.name, r.score, r.total_marks, r.percentage,
                   r.time_taken, r.tab_switches, r.submission_time
            FROM results r
            INNER JOIN exams e ON r.exam_id = e.id
            INNER JOIN students s ON r.student_id = s.id
            ORDER BY r.submission_time DESC
        """)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/submit-exam', methods=['POST'])
@require_token
def submit_exam():
    """Submit exam results"""
    try:
        data = request.json
        exam_id = data.get('exam_id')
        student_id = data.get('student_id')
        score = data.get('score')
        total_marks = data.get('total_marks')
        percentage = data.get('percentage')
        time_taken = data.get('time_taken')
        tab_switches = data.get('tab_switches', 0)
        answers_data = data.get('answers', [])

        conn = get_db()
        cursor = conn.cursor()

        # Insert result
        cursor.execute(
            """INSERT INTO results (exam_id, student_id, score, total_marks, percentage, time_taken, tab_switches)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (exam_id, student_id, score, total_marks, percentage, time_taken, tab_switches)
        )
        result_id = cursor.lastrowid

        # Insert answers
        for answer in answers_data:
            cursor.execute(
                """INSERT INTO student_answers (result_id, question_id, selected_answer, is_correct)
                   VALUES (?, ?, ?, ?)""",
                (result_id, answer.get('question_id'), answer.get('selected_answer'), answer.get('is_correct'))
            )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Exam submitted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# SECURITY ENDPOINTS
# ============================================================================

@app.route('/api/security-logs', methods=['GET'])
@require_token
def get_security_logs():
    """Get security logs"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sl.id, s.name, e.exam_name, sl.alert_type, sl.details, sl.timestamp
            FROM security_logs sl
            INNER JOIN students s ON sl.student_id = s.id
            INNER JOIN exams e ON sl.exam_id = e.id
            ORDER BY sl.timestamp DESC
        """)
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/security-log', methods=['POST'])
@require_token
def log_security_violation():
    """Log security violation"""
    try:
        data = request.json
        student_id = data.get('student_id')
        exam_id = data.get('exam_id')
        alert_type = data.get('alert_type')
        details = data.get('details')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO security_logs (student_id, exam_id, alert_type, details)
               VALUES (?, ?, ?, ?)""",
            (student_id, exam_id, alert_type, details)
        )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Security violation logged'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'success': False, 'message': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ============================================================================
# MAIN APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print(" 🚀 CENTRAL EXAMINATION SERVER - Database Version")
    print("="*70)

    print("\n📡 Initializing database...")
    init_database()

    print("🔐 API Token: secure_token_12345")
    print("🌐 Server starting on: http://0.0.0.0:5000")
    print("\n📝 Endpoints Available:")
    print("  ✓ /api/health - Health check (no auth needed)")
    print("  ✓ /api/login - Student login")
    print("  ✓ /api/admin/login - Admin login")
    print("  ✓ /api/students - Get all students")
    print("  ✓ /api/admin/add-student - Add student")
    print("  ✓ /api/questions - Get all questions")
    print("  ✓ /api/admin/add-question - Add question")
    print("  ✓ /api/exams - Get all exams")
    print("  ✓ /api/admin/add-exam - Create exam")
    print("  ✓ /api/exam/<id> - Get exam details")
    print("  ✓ /api/results - Get all results")
    print("  ✓ /api/submit-exam - Submit exam")
    print("  ✓ /api/security-logs - View security logs")
    print("\n⚠️  To access from other computers:")
    print("   Change http://localhost:5000 to http://<YOUR_IP>:5000")
    print("\n" + "="*70 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
    





