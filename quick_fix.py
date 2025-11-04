"""
Central Examination Server
Run this on a central server accessible over the internet
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import hashlib

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# File paths
QUESTIONS_FILE = "server_questions.json"
STUDENTS_FILE = "server_students.json"
SECURITY_LOGS_FILE = "server_security_logs.json"
RESULTS_FILE = "server_results.json"
SERVER_CONFIG_FILE = "server_config.json"

# Simple authentication token (in production, use proper JWT tokens)
def verify_token(token):
    """Verify authentication token"""
    try:
        with open(SERVER_CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return token == config.get('api_token', 'secure_token_12345')
    except:
        return token == 'secure_token_12345'

def generate_api_token():
    """Generate a secure API token"""
    return hashlib.sha256(datetime.now().isoformat().encode()).hexdigest()

# Initialize server files
def init_server_files():
    """Initialize server data files"""
    if not os.path.exists(SERVER_CONFIG_FILE):
        config = {
            'api_token': 'secure_token_12345',  # Change this in production
            'server_name': 'Central Examination Server',
            'version': '1.0'
        }
        with open(SERVER_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    
    if not os.path.exists(QUESTIONS_FILE):
        default_questions = [
            {
                "question": "What does HTML stand for?",
                "options": ["Hyper Text Markup Language", "High Tech Modern Language", 
                           "Home Tool Markup Language", "Hyperlinks and Text Markup Language"],
                "answer": 0
            },
            {
                "question": "Which programming language is known as the 'language of the web'?",
                "options": ["Python", "Java", "JavaScript", "C++"],
                "answer": 2
            }
        ]
        with open(QUESTIONS_FILE, 'w') as f:
            json.dump(default_questions, f, indent=4)
    
    if not os.path.exists(STUDENTS_FILE):
        default_students = [
            {
                "name": "Demo Student",
                "email": "student@example.com",
                "username": "student",
                "password": "exam123",
                "student_id": "STU001"
            }
        ]
        with open(STUDENTS_FILE, 'w') as f:
            json.dump(default_students, f, indent=4)
    
    if not os.path.exists(SECURITY_LOGS_FILE):
        with open(SECURITY_LOGS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f:
            json.dump([], f)

init_server_files()

# API Endpoints

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'message': 'Central Examination Server is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/login', methods=['POST'])
def login():
    """Student login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        with open(STUDENTS_FILE, 'r') as f:
            students = json.load(f)
        
        for student in students:
            if student['username'] == username and student['password'] == password:
                return jsonify({
                    'success': True,
                    'student': {
                        'name': student['name'],
                        'email': student['email'],
                        'username': student['username'],
                        'student_id': student.get('student_id', 'N/A')
                    }
                })
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/questions', methods=['GET'])
def get_questions():
    """Get exam questions"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            questions = json.load(f)
        return jsonify({'success': True, 'questions': questions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/security-log', methods=['POST'])
def log_security_violation():
    """Log security violations from clients"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        data = request.json
        log_entry = {
            'username': data.get('username'),
            'student_name': data.get('student_name'),
            'violation_type': data.get('violation_type'),
            'details': data.get('details'),
            'timestamp': datetime.now().isoformat(),
            'client_ip': request.remote_addr
        }
        
        logs = []
        if os.path.exists(SECURITY_LOGS_FILE):
            with open(SECURITY_LOGS_FILE, 'r') as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        
        with open(SECURITY_LOGS_FILE, 'w') as f:
            json.dump(logs, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Violation logged'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/security-logs', methods=['GET'])
def get_security_logs():
    """Get all security logs (admin only)"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        with open(SECURITY_LOGS_FILE, 'r') as f:
            logs = json.load(f)
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/submit-exam', methods=['POST'])
def submit_exam():
    """Submit exam results"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        data = request.json
        result_entry = {
            'username': data.get('username'),
            'student_name': data.get('student_name'),
            'score': data.get('score'),
            'total_questions': data.get('total_questions'),
            'percentage': data.get('percentage'),
            'time_taken': data.get('time_taken'),
            'tab_switch_count': data.get('tab_switch_count'),
            'camera_violation_count': data.get('camera_violation_count'),
            'timestamp': datetime.now().isoformat(),
            'client_ip': request.remote_addr
        }
        
        results = []
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r') as f:
                results = json.load(f)
        
        results.append(result_entry)
        
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Exam submitted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get all exam results (admin only)"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        with open(RESULTS_FILE, 'r') as f:
            results = json.load(f)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/students', methods=['GET'])
def get_students():
    """Get all students (admin only)"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        with open(STUDENTS_FILE, 'r') as f:
            students = json.load(f)
        # Remove passwords from response
        safe_students = [{'name': s['name'], 'email': s['email'], 
                         'username': s['username'], 'student_id': s.get('student_id', 'N/A')} 
                        for s in students]
        return jsonify({'success': True, 'students': safe_students})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-question', methods=['POST'])
def add_question():
    """Add a new question (admin only)"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        data = request.json
        
        with open(QUESTIONS_FILE, 'r') as f:
            questions = json.load(f)
        
        questions.append(data)
        
        with open(QUESTIONS_FILE, 'w') as f:
            json.dump(questions, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Question added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/add-student', methods=['POST'])
def add_student():
    """Add a new student (admin only)"""
    token = request.headers.get('Authorization')
    
    if not verify_token(token):
        return jsonify({'success': False, 'message': 'Invalid API token'}), 401
    
    try:
        data = request.json
        
        with open(STUDENTS_FILE, 'r') as f:
            students = json.load(f)
        
        # Check for duplicate username
        if any(s['username'] == data.get('username') for s in students):
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        students.append(data)
        
        with open(STUDENTS_FILE, 'w') as f:
            json.dump(students, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Student added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  CENTRAL EXAMINATION SERVER")
    print("="*60)
    print("\n📡 Server starting...")
    print("🔐 API Token: secure_token_12345 (Change in server_config.json)")
    print("🌐 Server will be accessible at: http://YOUR_IP:5000")
    print("\nTo access from other computers:")
    print("  1. Find your IP address (ipconfig/ifconfig)")
    print("  2. Update client applications with your IP")
    print("  3. Ensure port 5000 is open in firewall")
    print("\n" + "="*60 + "\n")
    
    # Run on all interfaces to be accessible from network
    app.run(host='0.0.0.0', port=5000, debug=True)

"""
Enhanced Admin Panel with Test Scheduling and Email Notifications
Features: Schedule tests, set marks per question, email notifications (SMTP & Power Automate), time-based access
"""

import sys
import json
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTabWidget,
                             QTableWidget, QTableWidgetItem, QMessageBox,
                             QDialog, QLineEdit, QTextEdit, QComboBox,
                             QScrollArea, QFrame, QSpinBox, QCheckBox,
                             QListWidget, QListWidgetItem, QGroupBox,
                             QDateTimeEdit, QDoubleSpinBox, QProgressDialog,
                             QRadioButton, QButtonGroup)
from PyQt6.QtWidgets import QLabel, QHBoxLayout
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont, QColor

# File paths
STUDENTS_FILE = "students.json"
QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.json"
SECURITY_LOGS_FILE = "security_logs.json"
EXAM_CONFIG_FILE = "exam_config.json"
RULES_FILE = "rules.json"
CHEATING_ALERTS_FILE = "cheating_alerts.json"
SCHEDULED_EXAMS_FILE = "scheduled_exams.json"
EMAIL_CONFIG_FILE = "email_config.json"


class EmailConfigDialog(QDialog):
    """Configure email settings for notifications (SMTP & Power Automate)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        self.setWindowTitle("Email Configuration")
        self.setGeometry(200, 200, 550, 600)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("📧 Email Configuration")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        # Email Method Selection
        method_group = QGroupBox("Select Email Method")
        method_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        method_layout = QVBoxLayout()
        
        self.button_group = QButtonGroup()
        
        self.smtp_radio = QRadioButton("📨 SMTP (Gmail, Outlook, etc.)")
        self.smtp_radio.setChecked(True)
        self.smtp_radio.toggled.connect(self.toggle_email_method)
        self.button_group.addButton(self.smtp_radio)
        method_layout.addWidget(self.smtp_radio)
        
        self.power_automate_radio = QRadioButton("⚡ Microsoft Power Automate")
        self.power_automate_radio.toggled.connect(self.toggle_email_method)
        self.button_group.addButton(self.power_automate_radio)
        method_layout.addWidget(self.power_automate_radio)
        
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)
        
        # SMTP Configuration
        self.smtp_group = QGroupBox("📨 SMTP Configuration")
        self.smtp_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        smtp_layout = QVBoxLayout()
        
        smtp_layout.addWidget(QLabel("SMTP Server:"))
        self.smtp_input = QLineEdit()
        self.smtp_input.setPlaceholderText("smtp.gmail.com")
        self.smtp_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        smtp_layout.addWidget(self.smtp_input)
        
        smtp_layout.addWidget(QLabel("SMTP Port:"))
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(587)
        self.port_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        smtp_layout.addWidget(self.port_input)
        
        smtp_layout.addWidget(QLabel("Admin Email:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("admin@example.com")
        self.email_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        smtp_layout.addWidget(self.email_input)
        
        smtp_layout.addWidget(QLabel("Email Password:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("App password for Gmail")
        self.password_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        smtp_layout.addWidget(self.password_input)
        
        smtp_info = QLabel("ℹ️ For Gmail: Enable 2FA and use App Password\nGo to: Google Account → Security → App Passwords")
        smtp_info.setStyleSheet("color: #7f8c8d; background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
        smtp_info.setWordWrap(True)
        smtp_layout.addWidget(smtp_info)
        
        self.smtp_group.setLayout(smtp_layout)
        layout.addWidget(self.smtp_group)
        
        # Power Automate Configuration
        self.power_automate_group = QGroupBox("⚡ Microsoft Power Automate Configuration")
        self.power_automate_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #9b59b6;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
        """)
        pa_layout = QVBoxLayout()
        
        pa_layout.addWidget(QLabel("Power Automate Webhook URL:"))
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://prod-xx.xx.logic.azure.com:443/workflows/...")
        self.webhook_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        pa_layout.addWidget(self.webhook_input)
        
        pa_info = QLabel("""ℹ️ Setup Instructions:
1. Go to Power Automate (flow.microsoft.com)
2. Create a new flow → "Instant cloud flow"
3. Choose trigger: "When an HTTP request is received"
4. Add action: "Send an email (V2)" from Office 365 Outlook
5. Configure email template with dynamic content
6. Save and copy the HTTP POST URL
7. Paste the URL above""")
        pa_info.setStyleSheet("color: #7f8c8d; background-color: #f8f9fa; padding: 10px; border-radius: 5px;")
        pa_info.setWordWrap(True)
        pa_layout.addWidget(pa_info)
        
        self.power_automate_group.setLayout(pa_layout)
        layout.addWidget(self.power_automate_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save Configuration")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(self.save_config)
        btn_layout.addWidget(save_btn)
        
        test_btn = QPushButton("🔧 Test Email")
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        test_btn.clicked.connect(self.test_email)
        btn_layout.addWidget(test_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Initial toggle
        self.toggle_email_method()
    
    def toggle_email_method(self):
        """Toggle between SMTP and Power Automate"""
        if self.smtp_radio.isChecked():
            self.smtp_group.setVisible(True)
            self.power_automate_group.setVisible(False)
        else:
            self.smtp_group.setVisible(False)
            self.power_automate_group.setVisible(True)
    
    def load_config(self):
        """Load existing email config"""
        try:
            if os.path.exists(EMAIL_CONFIG_FILE):
                with open(EMAIL_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                method = config.get('method', 'smtp')
                if method == 'power_automate':
                    self.power_automate_radio.setChecked(True)
                    self.webhook_input.setText(config.get('webhook_url', ''))
                else:
                    self.smtp_radio.setChecked(True)
                    self.smtp_input.setText(config.get('smtp_server', 'smtp.gmail.com'))
                    self.port_input.setValue(config.get('smtp_port', 587))
                    self.email_input.setText(config.get('admin_email', ''))
                    self.password_input.setText(config.get('email_password', ''))
                
                self.toggle_email_method()
        except:
            pass
    
    def save_config(self):
        """Save email configuration"""
        try:
            config = {}
            
            if self.smtp_radio.isChecked():
                config = {
                    'method': 'smtp',
                    'smtp_server': self.smtp_input.text().strip(),
                    'smtp_port': self.port_input.value(),
                    'admin_email': self.email_input.text().strip(),
                    'email_password': self.password_input.text().strip()
                }
                
                if not all([config['smtp_server'], config['admin_email'], config['email_password']]):
                    QMessageBox.warning(self, "Error", "All SMTP fields are required!")
                    return
            else:
                config = {
                    'method': 'power_automate',
                    'webhook_url': self.webhook_input.text().strip()
                }
                
                if not config['webhook_url']:
                    QMessageBox.warning(self, "Error", "Webhook URL is required!")
                    return
                
                if not config['webhook_url'].startswith('http'):
                    QMessageBox.warning(self, "Error", "Please enter a valid webhook URL!")
                    return
            
            with open(EMAIL_CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            
            QMessageBox.information(self, "Success", "Email configuration saved successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    
    def test_email(self):
        """Test email configuration"""
        try:
            if self.smtp_radio.isChecked():
                self.test_smtp_email()
            else:
                self.test_power_automate()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send test email:\n{str(e)}")
    
    def test_smtp_email(self):
        """Test SMTP email"""
        config = {
            'smtp_server': self.smtp_input.text().strip(),
            'smtp_port': self.port_input.value(),
            'admin_email': self.email_input.text().strip(),
            'email_password': self.password_input.text().strip()
        }
        
        # Try to send test email
        msg = MIMEMultipart()
        msg['From'] = config['admin_email']
        msg['To'] = config['admin_email']
        msg['Subject'] = "Test Email - Exam System"
        
        body = "This is a test email from the Examination Management System using SMTP."
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['admin_email'], config['email_password'])
            server.send_message(msg)
        
        QMessageBox.information(self, "Success", "Test SMTP email sent successfully!")
    
    def test_power_automate(self):
        """Test Power Automate webhook"""
        webhook_url = self.webhook_input.text().strip()
        
        if not webhook_url:
            QMessageBox.warning(self, "Error", "Please enter webhook URL!")
            return
        
        # Send test payload
        payload = {
            "student_name": "Test Student",
            "student_email": "test@example.com",
            "student_username": "test_user",
            "student_password": "test_pass",
            "exam_name": "Test Exam",
            "exam_description": "This is a test exam notification",
            "start_datetime": datetime.now().strftime('%Y-%m-%d %I:%M %p'),
            "duration_minutes": 60,
            "total_questions": 10,
            "total_marks": 10,
            "passing_percentage": 40,
            "camera_required": True
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code in [200, 202]:
            QMessageBox.information(self, "Success", 
                f"Test notification sent successfully!\n\n"
                f"Status Code: {response.status_code}\n"
                f"Check your email inbox for the test email.")
        else:
            QMessageBox.warning(self, "Warning", 
                f"Request sent but received status code: {response.status_code}\n"
                f"Response: {response.text[:200]}")


class ScheduleExamDialog(QDialog):
    """Dialog to schedule a new exam"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_questions = []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Schedule New Exam")
        self.setGeometry(100, 100, 800, 700)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(20)
        
        # Title
        title = QLabel("📅 Schedule New Exam")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        scroll_layout.addWidget(title)
        
        # Exam Name
        name_group = QGroupBox("📝 Exam Details")
        name_group.setStyleSheet(self.get_group_style("#3498db"))
        name_layout = QVBoxLayout()
        
        name_layout.addWidget(QLabel("Exam Name/Title:"))
        self.exam_name_input = QLineEdit()
        self.exam_name_input.setPlaceholderText("e.g., Mid-Term Mathematics Exam")
        self.exam_name_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        name_layout.addWidget(self.exam_name_input)
        
        name_layout.addWidget(QLabel("Exam Description:"))
        self.exam_desc_input = QTextEdit()
        self.exam_desc_input.setPlaceholderText("Brief description of the exam")
        self.exam_desc_input.setMaximumHeight(80)
        self.exam_desc_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        name_layout.addWidget(self.exam_desc_input)
        
        name_group.setLayout(name_layout)
        scroll_layout.addWidget(name_group)
        
        # Student Group Selection
        group_box = QGroupBox("👥 Select Student Group")
        group_box.setStyleSheet(self.get_group_style("#27ae60"))
        group_layout = QVBoxLayout()
        
        self.group_combo = QComboBox()
        self.group_combo.addItems(["Group A", "Group B", "Group C", "All Students"])
        self.group_combo.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        group_layout.addWidget(self.group_combo)
        
        # Show student count
        self.student_count_label = QLabel("Students in this group: Calculating...")
        self.student_count_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        group_layout.addWidget(self.student_count_label)
        self.group_combo.currentTextChanged.connect(self.update_student_count)
        
        group_box.setLayout(group_layout)
        scroll_layout.addWidget(group_box)
        
        # Date and Time
        datetime_group = QGroupBox("⏰ Schedule Date & Time")
        datetime_group.setStyleSheet(self.get_group_style("#e67e22"))
        datetime_layout = QVBoxLayout()
        
        datetime_layout.addWidget(QLabel("Start Date & Time:"))
        self.start_datetime = QDateTimeEdit()
        self.start_datetime.setCalendarPopup(True)
        self.start_datetime.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.start_datetime.setDisplayFormat("yyyy-MM-dd hh:mm AP")
        self.start_datetime.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        datetime_layout.addWidget(self.start_datetime)
        
        datetime_layout.addWidget(QLabel("Duration (minutes):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(10, 300)
        self.duration_spin.setValue(60)
        self.duration_spin.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        datetime_layout.addWidget(self.duration_spin)
        
        # Calculate end time
        self.end_time_label = QLabel("End Time: (will be calculated)")
        self.end_time_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        datetime_layout.addWidget(self.end_time_label)
        self.duration_spin.valueChanged.connect(self.update_end_time)
        self.start_datetime.dateTimeChanged.connect(self.update_end_time)
        
        datetime_group.setLayout(datetime_layout)
        scroll_layout.addWidget(datetime_group)
        
        # Question Selection
        questions_group = QGroupBox("❓ Select Questions")
        questions_group.setStyleSheet(self.get_group_style("#9b59b6"))
        questions_layout = QVBoxLayout()
        
        # Load questions button
        load_questions_btn = QPushButton("📋 Load & Select Questions")
        load_questions_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        load_questions_btn.clicked.connect(self.select_questions)
        questions_layout.addWidget(load_questions_btn)
        
        self.selected_questions_label = QLabel("Selected Questions: 0")
        self.selected_questions_label.setStyleSheet("color: #7f8c8d; padding: 5px; font-weight: bold;")
        questions_layout.addWidget(self.selected_questions_label)
        
        questions_group.setLayout(questions_layout)
        scroll_layout.addWidget(questions_group)
        
        # Marks Configuration
        marks_group = QGroupBox("📊 Marks Configuration")
        marks_group.setStyleSheet(self.get_group_style("#e74c3c"))
        marks_layout = QVBoxLayout()
        
        marks_layout.addWidget(QLabel("Marks per Question:"))
        self.marks_per_question = QDoubleSpinBox()
        self.marks_per_question.setRange(0.5, 100)
        self.marks_per_question.setValue(1.0)
        self.marks_per_question.setSingleStep(0.5)
        self.marks_per_question.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        marks_layout.addWidget(self.marks_per_question)
        
        self.total_marks_label = QLabel("Total Marks: 0")
        self.total_marks_label.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 5px;")
        marks_layout.addWidget(self.total_marks_label)
        self.marks_per_question.valueChanged.connect(self.update_total_marks)
        
        marks_group.setLayout(marks_layout)
        scroll_layout.addWidget(marks_group)
        
        # Additional Settings
        settings_group = QGroupBox("⚙️ Additional Settings")
        settings_group.setStyleSheet(self.get_group_style("#34495e"))
        settings_layout = QVBoxLayout()
        
        self.camera_check = QCheckBox("Enable Camera Monitoring")
        self.camera_check.setChecked(True)
        settings_layout.addWidget(self.camera_check)
        
        self.shuffle_check = QCheckBox("Shuffle Questions")
        settings_layout.addWidget(self.shuffle_check)
        
        self.email_notification_check = QCheckBox("Send Email Notifications to Students")
        self.email_notification_check.setChecked(True)
        settings_layout.addWidget(self.email_notification_check)
        
        self.passing_marks_layout = QHBoxLayout()
        self.passing_marks_layout.addWidget(QLabel("Passing Percentage:"))
        self.passing_percent = QSpinBox()
        self.passing_percent.setRange(0, 100)
        self.passing_percent.setValue(40)
        self.passing_percent.setSuffix("%")
        self.passing_percent.setStyleSheet("padding: 5px;")
        self.passing_marks_layout.addWidget(self.passing_percent)
        settings_layout.addLayout(self.passing_marks_layout)
        
        settings_group.setLayout(settings_layout)
        scroll_layout.addWidget(settings_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        
        schedule_btn = QPushButton("📅 Schedule Exam & Send Notifications")
        schedule_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        schedule_btn.clicked.connect(self.schedule_exam)
        btn_layout.addWidget(schedule_btn)
        
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Initial updates
        self.update_student_count()
        self.update_end_time()
    
    def get_group_style(self, color):
        return f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {color};
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }}
            QGroupBox::title {{
                color: {color};
            }}
        """
    
    def update_student_count(self):
        """Update student count for selected group"""
        try:
            if os.path.exists(STUDENTS_FILE):
                with open(STUDENTS_FILE, 'r') as f:
                    students = json.load(f)
                
                group = self.group_combo.currentText()
                if group == "All Students":
                    count = len(students)
                else:
                    count = sum(1 for s in students if s.get('group') == group)
                
                self.student_count_label.setText(f"Students in this group: {count}")
        except:
            self.student_count_label.setText("Students in this group: 0")
    
    def update_end_time(self):
        """Update end time based on start time and duration"""
        start = self.start_datetime.dateTime().toPyDateTime()
        duration = self.duration_spin.value()
        end = start + timedelta(minutes=duration)
        self.end_time_label.setText(f"End Time: {end.strftime('%Y-%m-%d %I:%M %p')}")
    
    def update_total_marks(self):
        """Update total marks"""
        total = len(self.selected_questions) * self.marks_per_question.value()
        self.total_marks_label.setText(f"Total Marks: {total}")
    
    def select_questions(self):
        """Open question selection dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Questions for Exam")
        dialog.setGeometry(150, 150, 700, 600)
        dialog.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Select Questions for This Exam")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Question list with checkboxes
        questions_list = QListWidget()
        questions_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        try:
            if os.path.exists(QUESTIONS_FILE):
                with open(QUESTIONS_FILE, 'r') as f:
                    all_questions = json.load(f)
                
                for i, q in enumerate(all_questions):
                    item = QListWidgetItem(f"Q{i+1}: {q['question'][:80]}...")
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked)
                    item.setData(Qt.ItemDataRole.UserRole, i)
                    questions_list.addItem(item)
        except:
            pass
        
        layout.addWidget(questions_list)
        
        # Select all / Deselect all
        select_btn_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ Select All")
        select_all_btn.clicked.connect(lambda: self.toggle_all_questions(questions_list, True))
        select_btn_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("❌ Deselect All")
        deselect_all_btn.clicked.connect(lambda: self.toggle_all_questions(questions_list, False))
        select_btn_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(select_btn_layout)
        
        # Confirm button
        confirm_btn = QPushButton("✅ Confirm Selection")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        
        def confirm_selection():
            self.selected_questions = []
            for i in range(questions_list.count()):
                item = questions_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    self.selected_questions.append(item.data(Qt.ItemDataRole.UserRole))
            
            self.selected_questions_label.setText(f"Selected Questions: {len(self.selected_questions)}")
            self.update_total_marks()
            dialog.accept()
        
        confirm_btn.clicked.connect(confirm_selection)
        layout.addWidget(confirm_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def toggle_all_questions(self, questions_list, checked):
        """Toggle all questions selection"""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for i in range(questions_list.count()):
            questions_list.item(i).setCheckState(state)
    
    def schedule_exam(self):
        """Schedule the exam"""
        exam_name = self.exam_name_input.text().strip()
        exam_desc = self.exam_desc_input.toPlainText().strip()
        group = self.group_combo.currentText()
        
        if not exam_name:
            QMessageBox.warning(self, "Error", "Exam name is required!")
            return
        
        if not self.selected_questions:
            QMessageBox.warning(self, "Error", "Please select at least one question!")
            return
        
        try:
            # Create exam data
            exam_data = {
                'exam_id': f"EXAM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'exam_name': exam_name,
                'description': exam_desc,
                'group': group if group != "All Students" else None,
                'start_datetime': self.start_datetime.dateTime().toString("yyyy-MM-dd hh:mm:ss"),
                'duration_minutes': self.duration_spin.value(),
                'end_datetime': (self.start_datetime.dateTime().toPyDateTime() + 
                               timedelta(minutes=self.duration_spin.value())).strftime("%Y-%m-%d %H:%M:%S"),
                'question_indices': self.selected_questions,
                'marks_per_question': self.marks_per_question.value(),
                'total_marks': len(self.selected_questions) * self.marks_per_question.value(),
                'passing_percentage': self.passing_percent.value(),
                'camera_required': self.camera_check.isChecked(),
                'shuffle_questions': self.shuffle_check.isChecked(),
                'created_by': 'admin',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'scheduled',
                'send_email': self.email_notification_check.isChecked()
            }
            
            # Save to scheduled exams
            scheduled_exams = []
            if os.path.exists(SCHEDULED_EXAMS_FILE):
                with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                    scheduled_exams = json.load(f)
            
            scheduled_exams.append(exam_data)
            
            with open(SCHEDULED_EXAMS_FILE, 'w') as f:
                json.dump(scheduled_exams, f, indent=4)
            
            # Send email notifications if enabled
            if self.email_notification_check.isChecked():
                self.send_notifications(exam_data)
            
            QMessageBox.information(self, "Success", 
                                  f"Exam '{exam_name}' scheduled successfully!\n\n"
                                  f"Start: {exam_data['start_datetime']}\n"
                                  f"Duration: {exam_data['duration_minutes']} minutes\n"
                                  f"Questions: {len(self.selected_questions)}\n"
                                  f"Total Marks: {exam_data['total_marks']}")
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to schedule exam:\n{str(e)}")
    
    def send_notifications(self, exam_data):
        """Send email notifications to students"""
        try:
            # Load email config
            if not os.path.exists(EMAIL_CONFIG_FILE):
                QMessageBox.warning(self, "Warning", 
                                  "Email not configured. Please configure email settings first.")
                return
            
            with open(EMAIL_CONFIG_FILE, 'r') as f:
                email_config = json.load(f)
            
            # Load students
            if not os.path.exists(STUDENTS_FILE):
                return
            
            with open(STUDENTS_FILE, 'r') as f:
                all_students = json.load(f)
            
            # Filter students by group
            group = exam_data['group']
            if group:
                students = [s for s in all_students if s.get('group') == group]
            else:
                students = all_students
            
            if not students:
                return
            
            # Progress dialog
            progress = QProgressDialog("Sending email notifications...", "Cancel", 0, len(students), self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # Send emails based on method
            method = email_config.get('method', 'smtp')
            sent_count = 0
            failed_count = 0
            
            for i, student in enumerate(students):
                if progress.wasCanceled():
                    break
                
                try:
                    if method == 'power_automate':
                        self.send_power_automate_notification(student, exam_data, email_config)
                    else:
                        self.send_smtp_notification(student, exam_data, email_config)
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to send email to {student.get('email')}: {str(e)}")
                
                progress.setValue(i + 1)
            
            progress.close()
            
            # Show summary
            if sent_count > 0:
                message = f"Successfully sent {sent_count} email notification(s)!"
                if failed_count > 0:
                    message += f"\n{failed_count} email(s) failed to send."
                QMessageBox.information(self, "Email Sent", message)
            elif failed_count > 0:
                QMessageBox.warning(self, "Email Error", 
                                  f"Failed to send {failed_count} email(s). Please check your configuration.")
            
        except Exception as e:
            QMessageBox.warning(self, "Email Error", f"Error sending notifications:\n{str(e)}")
    
    def send_power_automate_notification(self, student, exam_data, email_config):
        """Send notification via Power Automate webhook"""
        webhook_url = email_config.get('webhook_url', '')
        
        if not webhook_url:
            raise Exception("Power Automate webhook URL not configured")
        
        # Prepare payload for Power Automate
        payload = {
            "student_name": student.get('name', ''),
            "student_email": student.get('email', ''),
            "student_username": student.get('username', ''),
            "student_password": student.get('password', ''),
            "exam_name": exam_data['exam_name'],
            "exam_description": exam_data.get('description', 'N/A'),
            "start_datetime": exam_data['start_datetime'],
            "duration_minutes": exam_data['duration_minutes'],
            "total_questions": len(exam_data['question_indices']),
            "total_marks": exam_data['total_marks'],
            "passing_percentage": exam_data['passing_percentage'],
            "camera_required": exam_data['camera_required']
        }
        
        # Send POST request to Power Automate
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Check response
        if response.status_code not in [200, 202]:
            raise Exception(f"Power Automate returned status code: {response.status_code}")
    
    def send_smtp_notification(self, student, exam_data, email_config):
        """Send notification via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['From'] = email_config['admin_email']
        msg['To'] = student.get('email', '')
        msg['Subject'] = f"Exam Scheduled: {exam_data['exam_name']}"
        
        # Create email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #3498db; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #ddd; }}
                .credentials {{ background-color: #fff; padding: 15px; margin: 15px 0; border-left: 4px solid #27ae60; }}
                .info-box {{ background-color: #fff; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .warning {{ background-color: #fadbd8; color: #e74c3c; padding: 10px; border-radius: 5px; margin: 15px 0; }}
                .footer {{ text-align: center; padding: 15px; color: #7f8c8d; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                td {{ padding: 8px; }}
                .label {{ font-weight: bold; color: #2c3e50; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📝 Exam Scheduled</h1>
                </div>
                <div class="content">
                    <p>Dear <strong>{student.get('name', 'Student')}</strong>,</p>
                    
                    <p>An exam has been scheduled for you. Please find the details below:</p>
                    
                    <div class="info-box">
                        <h3 style="color: #3498db; margin-top: 0;">📋 Exam Details</h3>
                        <table>
                            <tr>
                                <td class="label">Exam Name:</td>
                                <td>{exam_data['exam_name']}</td>
                            </tr>
                            <tr>
                                <td class="label">Description:</td>
                                <td>{exam_data.get('description', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td class="label">Start Date & Time:</td>
                                <td><strong style="color: #e67e22;">{exam_data['start_datetime']}</strong></td>
                            </tr>
                            <tr>
                                <td class="label">Duration:</td>
                                <td>{exam_data['duration_minutes']} minutes</td>
                            </tr>
                            <tr>
                                <td class="label">Total Questions:</td>
                                <td>{len(exam_data['question_indices'])}</td>
                            </tr>
                            <tr>
                                <td class="label">Total Marks:</td>
                                <td>{exam_data['total_marks']}</td>
                            </tr>
                            <tr>
                                <td class="label">Passing Marks:</td>
                                <td>{exam_data['passing_percentage']}%</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="credentials">
                        <h3 style="color: #27ae60; margin-top: 0;">🔐 Your Login Credentials</h3>
                        <table>
                            <tr>
                                <td class="label">Username:</td>
                                <td><code>{student.get('username', '')}</code></td>
                            </tr>
                            <tr>
                                <td class="label">Password:</td>
                                <td><code>{student.get('password', '')}</code></td>
                            </tr>
                        </table>
                        <p style="margin-bottom: 0;"><em>Please keep these credentials secure and do not share them.</em></p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Important Instructions:</strong>
                        <ul style="margin: 10px 0;">
                            <li>Login at least 5 minutes before the scheduled time</li>
                            <li>The exam will only be accessible during the scheduled time window</li>
                            {"<li>Camera monitoring is enabled - keep your face visible</li>" if exam_data['camera_required'] else ""}
                            <li>Do not switch tabs or minimize the exam window</li>
                            <li>Ensure stable internet connection throughout the exam</li>
                            <li>The exam will auto-submit when time expires</li>
                        </ul>
                    </div>
                    
                    <p style="margin-top: 20px;">Good luck with your exam!</p>
                </div>
                <div class="footer">
                    <p>This is an automated email from the Examination Management System.<br>
                    Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            server.starttls()
            server.login(email_config['admin_email'], email_config['email_password'])
            server.send_message(msg)


class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logged_in_username = "admin"
        self.init_ui()
        self.load_data()
        
        # Auto-refresh cheating alerts and exam status
        self.alert_timer = QTimer()
        self.alert_timer.timeout.connect(self.load_cheating_alerts)
        self.alert_timer.start(5000)  # Refresh every 5 seconds
        
        # Check exam status
        self.exam_status_timer = QTimer()
        self.exam_status_timer.timeout.connect(self.update_exam_status)
        self.exam_status_timer.start(60000)  # Check every minute
    
    def init_ui(self):
        self.setWindowTitle("Admin Panel - Examination Management System")
        self.setGeometry(50, 50, 1400, 800)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        svg_path = os.path.join(os.path.dirname(__file__),  "sym.svg")  # <-- your SVG path
        svg_icon = QSvgWidget(svg_path)
        svg_icon.setFixedSize(190, 100)  # Adjust size to your liking
        svg_icon.setStyleSheet("background: transparent; border: none;")  # ✅ Transparent background
        header_layout.addWidget(svg_icon)

        # --- Title Label ---
        title = QLabel("Admin Panel")
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        title.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title)        
        header_layout.addStretch()
        
        # Email config button
        email_config_btn = QPushButton("📧 Email Config")
        email_config_btn.setFont(QFont("Arial", 10))
        email_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        email_config_btn.clicked.connect(self.configure_email)
        header_layout.addWidget(email_config_btn)
        
        # Alert indicator
        self.alert_indicator = QLabel("🔔 0 New Alerts")
        
        self.alert_indicator.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.alert_indicator.setStyleSheet("""
            color: white;
            background-color: #27ae60;
            padding: 5px 5px;
            border-radius: 6px;
        """)
        header_layout.addWidget(self.alert_indicator)
        
        user_label = QLabel(f"👤 {self.logged_in_username}")
        user_label.setFont(QFont("Arial", 12))
        user_label.setStyleSheet("color: #7f8c8d; padding: 10px;")
        header_layout.addWidget(user_label)
        
        logout_btn = QPushButton("🚪 Logout")
        logout_btn.setFont(QFont("Arial", 11))
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        logout_btn.clicked.connect(self.close)
        header_layout.addWidget(logout_btn)
        
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
                margin: 2px;
                border-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
            }
        """)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_schedule_exam_tab()
        self.create_scheduled_exams_tab()
        self.create_students_tab()
        self.create_questions_tab()
        self.create_results_tab()
        self.create_cheating_alerts_tab()
        self.create_security_tab()
        
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
    
    def create_dashboard_tab(self):
        """Dashboard tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        title = QLabel("📊 System Dashboard")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.students_card_label = self.create_stat_card_with_label("👥 Students", "0", "#3498db", stats_layout)
        self.questions_card_label = self.create_stat_card_with_label("❓ Questions", "0", "#27ae60", stats_layout)
        self.scheduled_exams_label = self.create_stat_card_with_label("📅 Scheduled Exams", "0", "#9b59b6", stats_layout)
        self.results_card_label = self.create_stat_card_with_label("📊 Results", "0", "#e67e22", stats_layout)
        self.alerts_card_label = self.create_stat_card_with_label("⚠️ Alerts", "0", "#e74c3c", stats_layout)
        
        layout.addLayout(stats_layout)
        
        # Quick actions
        actions_label = QLabel("⚡ Quick Actions")
        actions_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        actions_label.setStyleSheet("color: #2c3e50; margin-top: 20px;")
        layout.addWidget(actions_label)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        schedule_btn = self.create_action_button("📅 Schedule Exam", "#9b59b6")
        schedule_btn.clicked.connect(self.open_schedule_dialog)
        actions_layout.addWidget(schedule_btn)
        
        add_student_btn = self.create_action_button("➕ Add Student", "#3498db")
        add_student_btn.clicked.connect(self.add_student)
        actions_layout.addWidget(add_student_btn)
        
        add_question_btn = self.create_action_button("➕ Add Question", "#27ae60")
        add_question_btn.clicked.connect(self.add_question)
        actions_layout.addWidget(add_question_btn)
        
        view_alerts_btn = self.create_action_button("🚨 View Alerts", "#e74c3c")
        view_alerts_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(6))
        actions_layout.addWidget(view_alerts_btn)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🏠 Dashboard")
    
    def create_stat_card_with_label(self, title, count, color, parent_layout):
        """Create stat card and return label reference"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 5px solid {color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)
        
        count_label = QLabel(count)
        count_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        count_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(count_label)
        
        card.setLayout(layout)
        parent_layout.addWidget(card)
        return count_label
    
    def create_action_button(self, text, color):
        """Create action button"""
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 15px;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """)
        return btn
    
    def create_schedule_exam_tab(self):
        """Schedule exam tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("📅 Schedule New Exam")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        info = QLabel("Click the button below to schedule a new exam for students")
        info.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(info)
        
        schedule_btn = QPushButton("📅 Schedule New Exam")
        schedule_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        schedule_btn.setFixedSize(300, 60)
        schedule_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        schedule_btn.clicked.connect(self.open_schedule_dialog)
        
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        btn_container.addWidget(schedule_btn)
        btn_container.addStretch()
        
        layout.addLayout(btn_container)
        layout.addStretch()
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📅 Schedule Exam")
    
    def create_scheduled_exams_tab(self):
        """Scheduled exams tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("📋 Scheduled Exams")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_scheduled_exams)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.scheduled_exams_table = QTableWidget()
        self.scheduled_exams_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.scheduled_exams_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📋 Scheduled Exams")
    
    def create_students_tab(self):
        """Students management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("👥 Student Management")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("➕ Add Student")
        add_btn.setStyleSheet(self.get_button_style("#27ae60"))
        add_btn.clicked.connect(self.add_student)
        header_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_students)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.students_table = QTableWidget()
        self.students_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.students_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "👥 Students")
    
    def create_questions_tab(self):
        """Questions management tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("❓ Question Bank")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("➕ Add Question")
        add_btn.setStyleSheet(self.get_button_style("#27ae60"))
        add_btn.clicked.connect(self.add_question)
        header_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_questions)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.questions_table = QTableWidget()
        self.questions_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.questions_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "❓ Questions")
    
    def create_results_tab(self):
        """Results tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("📊 Exam Results")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_results)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.results_table = QTableWidget()
        self.results_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.results_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "📊 Results")
    
    def create_cheating_alerts_tab(self):
        """Cheating alerts tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("🚨 Cheating Alerts (Real-time)")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e74c3c;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.setStyleSheet(self.get_button_style("#e74c3c"))
        clear_btn.clicked.connect(self.clear_cheating_alerts)
        header_layout.addWidget(clear_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_cheating_alerts)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.cheating_table = QTableWidget()
        self.cheating_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.cheating_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🚨 Cheating Alerts")
    
    def create_security_tab(self):
        """Security logs tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("🔒 Security Logs")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#3498db"))
        refresh_btn.clicked.connect(self.load_security_logs)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.security_table = QTableWidget()
        self.security_table.setStyleSheet(self.get_table_style())
        layout.addWidget(self.security_table)
        
        tab.setLayout(layout)
        self.tabs.addTab(tab, "🔒 Security")
    
    def get_button_style(self, color):
        """Get button style"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """
    
    def get_table_style(self):
        """Get table style"""
        return """
            QTableWidget {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
        """
    
    def configure_email(self):
        """Open email configuration dialog"""
        dialog = EmailConfigDialog(self)
        dialog.exec()
    
    def open_schedule_dialog(self):
        """Open schedule exam dialog"""
        dialog = ScheduleExamDialog(self)
        if dialog.exec():
            self.load_scheduled_exams()
            self.update_dashboard()
    
    def load_data(self):
        """Load all data"""
        self.load_students()
        self.load_questions()
        self.load_scheduled_exams()
        self.load_results()
        self.load_security_logs()
        self.load_cheating_alerts()
        self.update_dashboard()
    
    def load_students(self):
        """Load students"""
        try:
            students = []
            if os.path.exists(STUDENTS_FILE):
                with open(STUDENTS_FILE, 'r') as f:
                    students = json.load(f)
            
            self.students_table.setRowCount(len(students))
            self.students_table.setColumnCount(6)
            self.students_table.setHorizontalHeaderLabels(["Name", "Email", "Username", "Password", "Group", "Actions"])
            
            for i, student in enumerate(students):
                self.students_table.setItem(i, 0, QTableWidgetItem(student.get('name', '')))
                self.students_table.setItem(i, 1, QTableWidgetItem(student.get('email', '')))
                self.students_table.setItem(i, 2, QTableWidgetItem(student.get('username', '')))
                self.students_table.setItem(i, 3, QTableWidgetItem(student.get('password', '')))
                self.students_table.setItem(i, 4, QTableWidgetItem(student.get('group', 'N/A')))
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px;")
                delete_btn.clicked.connect(lambda checked, idx=i: self.delete_student(idx))
                self.students_table.setCellWidget(i, 5, delete_btn)
            
            self.students_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load students: {str(e)}")
    
    def load_questions(self):
        """Load questions"""
        try:
            questions = []
            if os.path.exists(QUESTIONS_FILE):
                with open(QUESTIONS_FILE, 'r') as f:
                    questions = json.load(f)
            
            self.questions_table.setRowCount(len(questions))
            self.questions_table.setColumnCount(5)
            self.questions_table.setHorizontalHeaderLabels(["#", "Question", "Group", "Options", "Actions"])
            
            for i, q in enumerate(questions):
                self.questions_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
                self.questions_table.setItem(i, 1, QTableWidgetItem(q.get('question', '')[:100]))
                self.questions_table.setItem(i, 2, QTableWidgetItem(q.get('group', 'All')))
                
                options = q.get('options', [])
                answer_idx = q.get('answer', 0)
                options_text = "\n".join([f"{'✓' if j == answer_idx else '•'} {opt}" 
                                         for j, opt in enumerate(options)])
                self.questions_table.setItem(i, 3, QTableWidgetItem(options_text))
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px;")
                delete_btn.clicked.connect(lambda checked, idx=i: self.delete_question(idx))
                self.questions_table.setCellWidget(i, 4, delete_btn)
            
            self.questions_table.resizeColumnsToContents()
            self.questions_table.resizeRowsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions: {str(e)}")
    
    def load_scheduled_exams(self):
        """Load scheduled exams"""
        try:
            exams = []
            if os.path.exists(SCHEDULED_EXAMS_FILE):
                with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                    exams = json.load(f)
            
            self.scheduled_exams_table.setRowCount(len(exams))
            self.scheduled_exams_table.setColumnCount(9)
            self.scheduled_exams_table.setHorizontalHeaderLabels(
                ["Exam Name", "Group", "Start Time", "Duration", "Questions", "Total Marks", "Status", "Actions", "Delete"])
            
            for i, exam in enumerate(exams):
                self.scheduled_exams_table.setItem(i, 0, QTableWidgetItem(exam.get('exam_name', '')))
                self.scheduled_exams_table.setItem(i, 1, QTableWidgetItem(exam.get('group', 'All')))
                self.scheduled_exams_table.setItem(i, 2, QTableWidgetItem(exam.get('start_datetime', '')))
                self.scheduled_exams_table.setItem(i, 3, QTableWidgetItem(f"{exam.get('duration_minutes', 0)} min"))
                self.scheduled_exams_table.setItem(i, 4, QTableWidgetItem(str(len(exam.get('question_indices', [])))))
                self.scheduled_exams_table.setItem(i, 5, QTableWidgetItem(str(exam.get('total_marks', 0))))
                
                # Status with color
                status = exam.get('status', 'scheduled')
                status_item = QTableWidgetItem(status.upper())
                if status == 'completed':
                    status_item.setBackground(QColor(46, 204, 113))
                elif status == 'active':
                    status_item.setBackground(QColor(52, 152, 219))
                else:
                    status_item.setBackground(QColor(241, 196, 15))
                status_item.setForeground(QColor(255, 255, 255))
                self.scheduled_exams_table.setItem(i, 6, status_item)
                
                # View details button
                view_btn = QPushButton("👁️ View")
                view_btn.setStyleSheet("background-color: #3498db; color: white; padding: 5px;")
                view_btn.clicked.connect(lambda checked, exam_data=exam: self.view_exam_details(exam_data))
                self.scheduled_exams_table.setCellWidget(i, 7, view_btn)
                
                # Delete button
                delete_btn = QPushButton("🗑️")
                delete_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 5px;")
                delete_btn.clicked.connect(lambda checked, idx=i: self.delete_scheduled_exam(idx))
                self.scheduled_exams_table.setCellWidget(i, 8, delete_btn)
            
            self.scheduled_exams_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load scheduled exams: {str(e)}")
    
    def load_results(self):
        """Load results"""
        try:
            results = []
            if os.path.exists(RESULTS_FILE):
                with open(RESULTS_FILE, 'r') as f:
                    results = json.load(f)
            
            self.results_table.setRowCount(len(results))
            self.results_table.setColumnCount(8)
            self.results_table.setHorizontalHeaderLabels(
                ["Student", "Username", "Exam", "Score", "Percentage", "Time", "Camera", "Date"])
            
            for i, result in enumerate(results):
                self.results_table.setItem(i, 0, QTableWidgetItem(result.get('student_name', '')))
                self.results_table.setItem(i, 1, QTableWidgetItem(result.get('username', '')))
                self.results_table.setItem(i, 2, QTableWidgetItem(result.get('exam_name', 'N/A')))
                
                score = f"{result.get('score', 0)}/{result.get('total_questions', 0)}"
                self.results_table.setItem(i, 3, QTableWidgetItem(score))
                
                percentage = result.get('percentage', 0)
                percent_item = QTableWidgetItem(f"{percentage:.1f}%")
                if percentage >= 40:
                    percent_item.setForeground(QColor(39, 174, 96))
                else:
                    percent_item.setForeground(QColor(231, 76, 60))
                self.results_table.setItem(i, 4, percent_item)
                
                self.results_table.setItem(i, 5, QTableWidgetItem(result.get('time_taken', '')))
                
                camera = "Yes" if result.get('camera_monitoring', False) else "No"
                self.results_table.setItem(i, 6, QTableWidgetItem(camera))
                
                self.results_table.setItem(i, 7, QTableWidgetItem(result.get('timestamp', '')))
            
            self.results_table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load results: {str(e)}")
    
    def load_cheating_alerts(self):
        """Load cheating alerts"""
        try:
            alerts = []
            if os.path.exists(CHEATING_ALERTS_FILE):
                with open(CHEATING_ALERTS_FILE, 'r') as f:
                    alerts = json.load(f)
            
            # Update dashboard indicator
            self.alert_indicator.setText(f"🔔 {len(alerts)} New Alerts")
            if len(alerts) > 0:
                self.alert_indicator.setStyleSheet("""
                    color: white;
                    background-color: #e74c3c;
                    padding: 8px 15px;
                    border-radius: 6px;
                """)
            else:
                self.alert_indicator.setStyleSheet("""
                    color: white;
                    background-color: #27ae60;
                    padding: 8px 15px;
                    border-radius: 6px;
                """)
            
            self.cheating_table.setRowCount(len(alerts))
            self.cheating_table.setColumnCount(6)
            self.cheating_table.setHorizontalHeaderLabels(
                ["Student", "Username", "Alert Type", "Details", "Question #", "Timestamp"])
            
            for i, alert in enumerate(alerts):
                student_item = QTableWidgetItem(alert.get('student_name', ''))
                student_item.setBackground(QColor(255, 235, 235))
                self.cheating_table.setItem(i, 0, student_item)
                
                username_item = QTableWidgetItem(alert.get('username', ''))
                username_item.setBackground(QColor(255, 235, 235))
                self.cheating_table.setItem(i, 1, username_item)
                
                alert_type = alert.get('alert_type', '')
                alert_item = QTableWidgetItem(alert_type)
                alert_item.setBackground(QColor(255, 235, 235))
                alert_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.cheating_table.setItem(i, 2, alert_item)
                
                details_item = QTableWidgetItem(alert.get('details', ''))
                details_item.setBackground(QColor(255, 235, 235))
                self.cheating_table.setItem(i, 3, details_item)
                
                question_item = QTableWidgetItem(str(alert.get('question_number', 'N/A')))
                question_item.setBackground(QColor(255, 235, 235))
                self.cheating_table.setItem(i, 4, question_item)
                
                timestamp_item = QTableWidgetItem(alert.get('timestamp', ''))
                timestamp_item.setBackground(QColor(255, 235, 235))
                self.cheating_table.setItem(i, 5, timestamp_item)
            
            self.cheating_table.resizeColumnsToContents()
            
        except Exception as e:
            pass
    
    def load_security_logs(self):
        """Load security logs"""
        try:
            logs = []
            if os.path.exists(SECURITY_LOGS_FILE):
                with open(SECURITY_LOGS_FILE, 'r') as f:
                    logs = json.load(f)
            
            self.security_table.setRowCount(len(logs))
            self.security_table.setColumnCount(5)
            self.security_table.setHorizontalHeaderLabels(
                ["Student", "Username", "Violation Type", "Details", "Timestamp"])
            
            for i, log in enumerate(logs):
                self.security_table.setItem(i, 0, QTableWidgetItem(log.get('student_name', '')))
                self.security_table.setItem(i, 1, QTableWidgetItem(log.get('username', '')))
                self.security_table.setItem(i, 2, QTableWidgetItem(log.get('violation_type', '')))
                self.security_table.setItem(i, 3, QTableWidgetItem(log.get('details', '')))
                self.security_table.setItem(i, 4, QTableWidgetItem(log.get('timestamp', '')))
            
            self.security_table.resizeColumnsToContents()
            
        except Exception as e:
            pass
    
    def update_dashboard(self):
        """Update dashboard statistics"""
        try:
            # Students count
            if os.path.exists(STUDENTS_FILE):
                with open(STUDENTS_FILE, 'r') as f:
                    students = json.load(f)
                    self.students_card_label.setText(str(len(students)))
            
            # Questions count
            if os.path.exists(QUESTIONS_FILE):
                with open(QUESTIONS_FILE, 'r') as f:
                    questions = json.load(f)
                    self.questions_card_label.setText(str(len(questions)))
            
            # Scheduled exams count
            if os.path.exists(SCHEDULED_EXAMS_FILE):
                with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                    exams = json.load(f)
                    active_exams = sum(1 for e in exams if e.get('status') != 'completed')
                    self.scheduled_exams_label.setText(str(active_exams))
            
            # Results count
            if os.path.exists(RESULTS_FILE):
                with open(RESULTS_FILE, 'r') as f:
                    results = json.load(f)
                    self.results_card_label.setText(str(len(results)))
            
            # Alerts count
            if os.path.exists(CHEATING_ALERTS_FILE):
                with open(CHEATING_ALERTS_FILE, 'r') as f:
                    alerts = json.load(f)
                    self.alerts_card_label.setText(str(len(alerts)))
        except:
            pass
    
    def update_exam_status(self):
        """Update exam status based on current time"""
        try:
            if not os.path.exists(SCHEDULED_EXAMS_FILE):
                return
            
            with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                exams = json.load(f)
            
            now = datetime.now()
            updated = False
            
            for exam in exams:
                start_time = datetime.strptime(exam['start_datetime'], '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(exam['end_datetime'], '%Y-%m-%d %H:%M:%S')
                
                if exam['status'] == 'scheduled' and now >= start_time:
                    exam['status'] = 'active'
                    updated = True
                elif exam['status'] == 'active' and now >= end_time:
                    exam['status'] = 'completed'
                    updated = True
            
            if updated:
                with open(SCHEDULED_EXAMS_FILE, 'w') as f:
                    json.dump(exams, f, indent=4)
                self.load_scheduled_exams()
                self.update_dashboard()
                
        except Exception as e:
            pass
    
    def view_exam_details(self, exam_data):
        """View detailed exam information"""
        details = f"""
        <h2>📋 Exam Details</h2>
        <table style='width: 100%; border-collapse: collapse;'>
            <tr><td style='padding: 8px; font-weight: bold;'>Exam Name:</td><td style='padding: 8px;'>{exam_data.get('exam_name', '')}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Description:</td><td style='padding: 8px;'>{exam_data.get('description', 'N/A')}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Group:</td><td style='padding: 8px;'>{exam_data.get('group', 'All Students')}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Start Time:</td><td style='padding: 8px;'>{exam_data.get('start_datetime', '')}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>End Time:</td><td style='padding: 8px;'>{exam_data.get('end_datetime', '')}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Duration:</td><td style='padding: 8px;'>{exam_data.get('duration_minutes', 0)} minutes</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Questions:</td><td style='padding: 8px;'>{len(exam_data.get('question_indices', []))}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Marks per Question:</td><td style='padding: 8px;'>{exam_data.get('marks_per_question', 0)}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Total Marks:</td><td style='padding: 8px;'>{exam_data.get('total_marks', 0)}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Passing Percentage:</td><td style='padding: 8px;'>{exam_data.get('passing_percentage', 0)}%</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Camera Monitoring:</td><td style='padding: 8px;'>{'Yes' if exam_data.get('camera_required', False) else 'No'}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Shuffle Questions:</td><td style='padding: 8px;'>{'Yes' if exam_data.get('shuffle_questions', False) else 'No'}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Status:</td><td style='padding: 8px;'>{exam_data.get('status', 'scheduled').upper()}</td></tr>
            <tr><td style='padding: 8px; font-weight: bold;'>Created:</td><td style='padding: 8px;'>{exam_data.get('created_at', '')}</td></tr>
        </table>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Exam Details")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(details)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
    
    def clear_cheating_alerts(self):
        """Clear all cheating alerts"""
        reply = QMessageBox.question(
            self, 'Clear Alerts',
            'Are you sure you want to clear all cheating alerts?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(CHEATING_ALERTS_FILE, 'w') as f:
                    json.dump([], f)
                
                self.load_cheating_alerts()
                self.update_dashboard()
                QMessageBox.information(self, "Success", "All alerts cleared!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear alerts: {str(e)}")
    
    def delete_scheduled_exam(self, index):
        """Delete scheduled exam"""
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            'Delete this scheduled exam?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                    exams = json.load(f)
                
                del exams[index]
                
                with open(SCHEDULED_EXAMS_FILE, 'w') as f:
                    json.dump(exams, f, indent=4)
                
                self.load_scheduled_exams()
                self.update_dashboard()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
    
    def add_student(self):
        """Add new student"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Student")
        dialog.setGeometry(200, 200, 450, 500)
        dialog.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("➕ Add New Student")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Name
        layout.addWidget(QLabel("Full Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter student's full name")
        name_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(name_input)
        
        # Email
        layout.addWidget(QLabel("Email:"))
        email_input = QLineEdit()
        email_input.setPlaceholderText("Enter email address")
        email_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(email_input)
        
        # Username
        layout.addWidget(QLabel("Username:"))
        username_input = QLineEdit()
        username_input.setPlaceholderText("Enter username")
        username_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(username_input)
        
        # Password
        layout.addWidget(QLabel("Password:"))
        password_input = QLineEdit()
        password_input.setPlaceholderText("Enter password")
        password_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(password_input)
        
        # Group
        layout.addWidget(QLabel("Group:"))
        group_combo = QComboBox()
        group_combo.addItems(["Group A", "Group B", "Group C"])
        group_combo.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(group_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet(self.get_button_style("#27ae60"))
        
        def save_student():
            name = name_input.text().strip()
            email = email_input.text().strip()
            username = username_input.text().strip()
            password = password_input.text().strip()
            group = group_combo.currentText()
            
            if not all([name, email, username, password]):
                QMessageBox.warning(dialog, "Error", "All fields are required!")
                return
            
            try:
                students = []
                if os.path.exists(STUDENTS_FILE):
                    with open(STUDENTS_FILE, 'r') as f:
                        students = json.load(f)
                
                if any(s['username'] == username for s in students):
                    QMessageBox.warning(dialog, "Error", "Username already exists!")
                    return
                
                new_student = {
                    'name': name,
                    'email': email,
                    'username': username,
                    'password': password,
                    'group': group,
                    'student_id': f"STU{len(students) + 1:03d}"
                }
                
                students.append(new_student)
                
                with open(STUDENTS_FILE, 'w') as f:
                    json.dump(students, f, indent=4)
                
                QMessageBox.information(dialog, "Success", "Student added successfully!")
                dialog.accept()
                self.load_students()
                self.update_dashboard()
                
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed: {str(e)}")
        
        save_btn.clicked.connect(save_student)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.setStyleSheet(self.get_button_style("#95a5a6"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()
    
    def add_question(self):
        """Add new question"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Question")
        dialog.setGeometry(150, 150, 600, 600)
        dialog.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("➕ Add New Question")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Question
        layout.addWidget(QLabel("Question:"))
        question_input = QTextEdit()
        question_input.setPlaceholderText("Enter question text")
        question_input.setMaximumHeight(80)
        question_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(question_input)
        
        # Group
        layout.addWidget(QLabel("Assign to Group:"))
        group_combo = QComboBox()
        group_combo.addItems(["All Students", "Group A", "Group B", "Group C"])
        group_combo.setStyleSheet("padding: 8px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(group_combo)
        
        # Options
        layout.addWidget(QLabel("Options (4 required):"))
        option_inputs = []
        for i in range(4):
            opt_input = QLineEdit()
            opt_input.setPlaceholderText(f"Option {i + 1}")
            opt_input.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
            layout.addWidget(opt_input)
            option_inputs.append(opt_input)
        
        # Correct answer
        layout.addWidget(QLabel("Correct Answer:"))
        answer_combo = QComboBox()
        answer_combo.addItems(["Option 1", "Option 2", "Option 3", "Option 4"])
        answer_combo.setStyleSheet("padding: 10px; border: 2px solid #bdc3c7; border-radius: 6px;")
        layout.addWidget(answer_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet(self.get_button_style("#27ae60"))
        
        def save_question():
            question = question_input.toPlainText().strip()
            options = [opt.text().strip() for opt in option_inputs]
            answer_idx = answer_combo.currentIndex()
            group = group_combo.currentText()
            
            if not question:
                QMessageBox.warning(dialog, "Error", "Question text is required!")
                return
            
            if not all(options):
                QMessageBox.warning(dialog, "Error", "All 4 options are required!")
                return
            
            try:
                questions = []
                if os.path.exists(QUESTIONS_FILE):
                    with open(QUESTIONS_FILE, 'r') as f:
                        questions = json.load(f)
                
                new_question = {
                    'question': question,
                    'options': options,
                    'answer': answer_idx,
                    'group': None if group == "All Students" else group
                }
                
                questions.append(new_question)
                
                with open(QUESTIONS_FILE, 'w') as f:
                    json.dump(questions, f, indent=4)
                
                QMessageBox.information(dialog, "Success", "Question added successfully!")
                dialog.accept()
                self.load_questions()
                self.update_dashboard()
                
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed: {str(e)}")
        
        save_btn.clicked.connect(save_question)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("✖ Cancel")
        cancel_btn.setStyleSheet(self.get_button_style("#95a5a6"))
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()
    
    def delete_student(self, index):
        """Delete student"""
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            'Delete this student?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(STUDENTS_FILE, 'r') as f:
                    students = json.load(f)
                
                del students[index]
                
                with open(STUDENTS_FILE, 'w') as f:
                    json.dump(students, f, indent=4)
                
                self.load_students()
                self.update_dashboard()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
    
    def delete_question(self, index):
        """Delete question"""
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            'Delete this question?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(QUESTIONS_FILE, 'r') as f:
                    questions = json.load(f)
                
                del questions[index]
                
                with open(QUESTIONS_FILE, 'w') as f:
                    json.dump(questions, f, indent=4)
                
                self.load_questions()
                self.update_dashboard()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    panel = AdminPanel()
    panel.show()
    sys.exit(app.exec())



"""
Admin Account Management System
Manage multiple administrator accounts
"""

import sys
import json
import os
import hashlib
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTableWidget,
                             QTableWidgetItem, QMessageBox, QDialog, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

ADMIN_CREDENTIALS_FILE = "admin_credentials.json"

class AdminManagementWindow(QMainWindow):
    def __init__(self, current_admin_username="admin"):
        super().__init__()
        self.current_admin = current_admin_username
        self.init_ui()
        self.load_admins()
    
    def init_ui(self):
        self.setWindowTitle("Admin Account Management")
        self.setGeometry(150, 150, 800, 600)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("👥 Admin Account Management")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        current_user = QLabel(f"Logged in as: {self.current_admin}")
        current_user.setFont(QFont("Arial", 10))
        current_user.setStyleSheet("color: #7f8c8d;")
        header_layout.addWidget(current_user)
        
        layout.addLayout(header_layout)
        
        # Info box
        info = QLabel("Manage administrator accounts. Add, remove, or change passwords.")
        info.setStyleSheet("""
            background-color: #d6eaf8;
            color: #2c3e50;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        add_btn = QPushButton("➕ Add Admin")
        add_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        add_btn.clicked.connect(self.add_admin)
        btn_layout.addWidget(add_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self.load_admins)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("✗ Close")
        close_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        # Admin table
        self.admin_table = QTableWidget()
        self.admin_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        layout.addWidget(self.admin_table)
        
        # Warning
        warning = QLabel("⚠️ Warning: Deleting your own account will log you out immediately!")
        warning.setFont(QFont("Arial", 9))
        warning.setStyleSheet("""
            background-color: #fadbd8;
            color: #e74c3c;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #e74c3c;
        """)
        layout.addWidget(warning)
        
        central_widget.setLayout(layout)
    
    def load_admins(self):
        """Load admin accounts"""
        try:
            if not os.path.exists(ADMIN_CREDENTIALS_FILE):
                # Create default admin
                default_creds = [{
                    "username": "admin",
                    "password": hashlib.sha256("admin123".encode()).hexdigest()
                }]
                with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                    json.dump(default_creds, f, indent=4)
            
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
            
            # Handle both dict and list formats
            if isinstance(creds, dict):
                admins = [creds]
            else:
                admins = creds
            
            # Setup table
            self.admin_table.setRowCount(len(admins))
            self.admin_table.setColumnCount(3)
            self.admin_table.setHorizontalHeaderLabels(["Username", "Status", "Actions"])
            
            for i, admin in enumerate(admins):
                # Username
                username_item = QTableWidgetItem(admin['username'])
                username_item.setFont(QFont("Arial", 11))
                self.admin_table.setItem(i, 0, username_item)
                
                # Status
                is_current = admin['username'] == self.current_admin
                status = "🟢 Current User" if is_current else "👤 Admin"
                status_item = QTableWidgetItem(status)
                status_item.setFont(QFont("Arial", 10))
                self.admin_table.setItem(i, 1, status_item)
                
                # Action buttons
                action_widget = QWidget()
                action_layout = QHBoxLayout()
                action_layout.setContentsMargins(5, 2, 5, 2)
                action_layout.setSpacing(5)
                
                # Change password button
                change_pwd_btn = QPushButton("🔑 Change Password")
                change_pwd_btn.setFont(QFont("Arial", 9))
                change_pwd_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f39c12;
                        color: white;
                        padding: 5px 10px;
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #e67e22;
                    }
                """)
                change_pwd_btn.clicked.connect(lambda checked, idx=i: self.change_password(idx))
                action_layout.addWidget(change_pwd_btn)
                
                # Delete button
                delete_btn = QPushButton("🗑 Delete")
                delete_btn.setFont(QFont("Arial", 9))
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        padding: 5px 10px;
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, idx=i: self.delete_admin(idx))
                action_layout.addWidget(delete_btn)
                
                action_widget.setLayout(action_layout)
                self.admin_table.setCellWidget(i, 2, action_widget)
            
            self.admin_table.resizeColumnsToContents()
            self.admin_table.horizontalHeader().setStretchLastSection(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load admins:\n{str(e)}")
    
    def add_admin(self):
        """Add new admin dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Admin")
        dialog.setGeometry(250, 250, 400, 300)
        dialog.setStyleSheet("background-color: #ecf0f1;")
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("➕ Add New Administrator")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        layout.addWidget(title)
        
        # Username
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(username_label)
        
        username_input = QLineEdit()
        username_input.setPlaceholderText("Enter new admin username")
        username_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
            }
        """)
        layout.addWidget(username_input)
        
        # Password
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(password_label)
        
        password_input = QLineEdit()
        password_input.setPlaceholderText("Enter password")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
            }
        """)
        layout.addWidget(password_input)
        
        # Confirm password
        confirm_label = QLabel("Confirm Password:")
        confirm_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(confirm_label)
        
        confirm_input = QLineEdit()
        confirm_input.setPlaceholderText("Confirm password")
        confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
            }
        """)
        layout.addWidget(confirm_input)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        
        def save_admin():
            username = username_input.text().strip()
            password = password_input.text().strip()
            confirm = confirm_input.text().strip()
            
            if not username or not password:
                QMessageBox.warning(dialog, "Input Error", "Username and password are required!")
                return
            
            if password != confirm:
                QMessageBox.warning(dialog, "Password Mismatch", "Passwords do not match!")
                return
            
            if len(password) < 6:
                QMessageBox.warning(dialog, "Weak Password", "Password must be at least 6 characters!")
                return
            
            try:
                with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                    creds = json.load(f)
                
                if isinstance(creds, dict):
                    admins = [creds]
                else:
                    admins = creds
                
                # Check duplicate
                if any(a['username'] == username for a in admins):
                    QMessageBox.warning(dialog, "Duplicate", "Username already exists!")
                    return
                
                # Add new admin
                new_admin = {
                    'username': username,
                    'password': hashlib.sha256(password.encode()).hexdigest()
                }
                
                admins.append(new_admin)
                
                with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                    json.dump(admins, f, indent=4)
                
                QMessageBox.information(dialog, "Success", "Admin added successfully!")
                dialog.accept()
                self.load_admins()
                
            except Exception as e:
                QMessageBox.critical(dialog, "Error", f"Failed to add admin:\n{str(e)}")
        
        save_btn.clicked.connect(save_admin)
        confirm_input.returnPressed.connect(save_admin)
        
        cancel_btn = QPushButton("✗ Cancel")
        cancel_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def change_password(self, index):
        """Change admin password"""
        try:
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
            
            if isinstance(creds, dict):
                admins = [creds]
            else:
                admins = creds
            
            admin = admins[index]
            username = admin['username']
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Change Password - {username}")
            dialog.setGeometry(250, 250, 400, 250)
            dialog.setStyleSheet("background-color: #ecf0f1;")
            
            layout = QVBoxLayout()
            layout.setSpacing(15)
            layout.setContentsMargins(30, 30, 30, 30)
            
            title = QLabel(f"🔑 Change Password for: {username}")
            title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            title.setStyleSheet("color: #2c3e50;")
            layout.addWidget(title)
            
            # New password
            new_pwd_label = QLabel("New Password:")
            new_pwd_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            layout.addWidget(new_pwd_label)
            
            new_pwd_input = QLineEdit()
            new_pwd_input.setPlaceholderText("Enter new password")
            new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
            new_pwd_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                    border: 2px solid #bdc3c7;
                    border-radius: 6px;
                }
            """)
            layout.addWidget(new_pwd_input)
            
            # Confirm password
            confirm_label = QLabel("Confirm Password:")
            confirm_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            layout.addWidget(confirm_label)
            
            confirm_input = QLineEdit()
            confirm_input.setPlaceholderText("Confirm new password")
            confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
            confirm_input.setStyleSheet("""
                QLineEdit {
                    padding: 10px;
                    border: 2px solid #bdc3c7;
                    border-radius: 6px;
                }
            """)
            layout.addWidget(confirm_input)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            update_btn = QPushButton("✓ Update")
            update_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            update_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #229954;
                }
            """)
            
            def update_password():
                new_pwd = new_pwd_input.text().strip()
                confirm = confirm_input.text().strip()
                
                if not new_pwd:
                    QMessageBox.warning(dialog, "Input Error", "Password is required!")
                    return
                
                if new_pwd != confirm:
                    QMessageBox.warning(dialog, "Password Mismatch", "Passwords do not match!")
                    return
                
                if len(new_pwd) < 6:
                    QMessageBox.warning(dialog, "Weak Password", "Password must be at least 6 characters!")
                    return
                
                try:
                    admins[index]['password'] = hashlib.sha256(new_pwd.encode()).hexdigest()
                    
                    with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                        json.dump(admins, f, indent=4)
                    
                    QMessageBox.information(dialog, "Success", "Password changed successfully!")
                    dialog.accept()
                    
                except Exception as e:
                    QMessageBox.critical(dialog, "Error", f"Failed to change password:\n{str(e)}")
            
            update_btn.clicked.connect(update_password)
            confirm_input.returnPressed.connect(update_password)
            
            cancel_btn = QPushButton("✗ Cancel")
            cancel_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #7f8c8d;
                }
            """)
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(update_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change password:\n{str(e)}")
    
    def delete_admin(self, index):
        """Delete admin account"""
        try:
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
            
            if isinstance(creds, dict):
                admins = [creds]
            else:
                admins = creds
            
            if len(admins) <= 1:
                QMessageBox.warning(self, "Cannot Delete", 
                                  "Cannot delete the last admin account!\n\n"
                                  "At least one admin must exist.")
                return
            
            admin = admins[index]
            username = admin['username']
            
            reply = QMessageBox.question(
                self,
                'Confirm Delete',
                f'Are you sure you want to delete admin "{username}"?\n\n'
                f'{"⚠️ You will be logged out immediately!" if username == self.current_admin else "This action cannot be undone!"}',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del admins[index]
                
                with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                    json.dump(admins, f, indent=4)
                
                QMessageBox.information(self, "Success", "Admin deleted successfully!")
                
                if username == self.current_admin:
                    self.close()
                else:
                    self.load_admins()
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete admin:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminManagementWindow()
    window.show()
    sys.exit(app.exec())


"""
Updated Student Exam Window with Scheduling Support
Checks scheduled exams, validates access time, shows thank you message
"""

import sys
import json
import os
import random
from datetime import datetime
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QRadioButton,
                             QMessageBox, QButtonGroup, QProgressBar, QDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# File paths
QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.json"
SECURITY_LOGS_FILE = "security_logs.json"
SCHEDULED_EXAMS_FILE = "scheduled_exams.json"
CHEATING_ALERTS_FILE = "cheating_alerts.json"


class ThankYouDialog(QDialog):
    """Thank you dialog after exam submission"""
    def __init__(self, result_data, parent=None):
        super().__init__(parent)
        self.result_data = result_data
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Exam Submitted")
        self.setGeometry(200, 200, 600, 500)
        self.setStyleSheet("background-color: #ecf0f1;")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Success icon
        icon_label = QLabel("✅")
        icon_label.setFont(QFont("Arial", 80))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Thank you message
        thank_you = QLabel("Thank You!")
        thank_you.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        thank_you.setStyleSheet("color: #27ae60;")
        thank_you.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thank_you)
        
        # Message
        message = QLabel(f"Dear {self.result_data.get('student_name', 'Student')},\n\n"
                        "Your exam has been submitted successfully!\n"
                        "Your responses have been recorded.")
        message.setFont(QFont("Arial", 13))
        message.setStyleSheet("color: #2c3e50;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Info box
        info_box = QWidget()
        info_box.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #3498db;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        info_layout = QVBoxLayout()
        
        exam_name = QLabel(f"📝 {self.result_data.get('exam_name', 'Exam')}")
        exam_name.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        exam_name.setStyleSheet("color: #3498db;")
        info_layout.addWidget(exam_name)
        
        questions_completed = QLabel(f"Questions Completed: {self.result_data.get('questions_answered', 0)}/{self.result_data.get('total_questions', 0)}")
        questions_completed.setFont(QFont("Arial", 12))
        info_layout.addWidget(questions_completed)
        
        time_taken = QLabel(f"Time Taken: {self.result_data.get('time_taken', 'N/A')}")
        time_taken.setFont(QFont("Arial", 12))
        info_layout.addWidget(time_taken)
        
        submission_time = QLabel(f"Submitted at: {self.result_data.get('timestamp', '')}")
        submission_time.setFont(QFont("Arial", 10))
        submission_time.setStyleSheet("color: #7f8c8d;")
        info_layout.addWidget(submission_time)
        
        info_box.setLayout(info_layout)
        layout.addWidget(info_box)
        
        # Note
        note = QLabel("📊 Your results will be available soon.\n"
                     "Please contact your administrator for result inquiries.")
        note.setFont(QFont("Arial", 11))
        note.setStyleSheet("color: #7f8c8d; padding: 15px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Close button
        close_btn = QPushButton("✓ Close")
        close_btn.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)


class ExamWindow(QMainWindow):
    def __init__(self, username, student_name, student_data=None):
        super().__init__()
        self.username = username
        self.student_name = student_name
        self.student_data = student_data or {}
        self.current_exam = None
        self.questions = []
        self.current_question_index = 0
        self.answers = {}
        self.tab_switch_count = 0
        self.start_time = datetime.now()
        self.capture = None
        self.monitoring_timer = None
        self.face_cascade = None
        self.no_face_count = 0
        self.multiple_face_count = 0
        
        # Check for scheduled exam
        if not self.check_scheduled_exam():
            QMessageBox.critical(self, "No Exam Available", 
                               "No exam is currently scheduled for you or the exam time has not started yet.")
            sys.exit(0)
        
        self.time_limit = self.current_exam.get('duration_minutes', 60) * 60
        self.time_remaining = self.time_limit
        self.camera_required = self.current_exam.get('camera_required', False)
        
        # Camera verification if required
        if self.camera_required:
            if not self.verify_camera():
                QMessageBox.critical(self, "Camera Required", 
                                   "Camera verification is mandatory for this exam.")
                sys.exit(0)
        
        self.init_ui()
        self.load_questions()
        self.start_timer()
        self.display_question()
        
        # Start monitoring if camera is required
        if self.camera_required:
            self.start_monitoring()
        
        # Freeze screen
        self.freeze_screen()
    
    def check_scheduled_exam(self):
        """Check if there's a scheduled exam available for this student"""
        try:
            if not os.path.exists(SCHEDULED_EXAMS_FILE):
                return False
            
            with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                scheduled_exams = json.load(f)
            
            student_group = self.student_data.get('group')
            now = datetime.now()
            
            # Find active exam for this student's group
            for exam in scheduled_exams:
                exam_group = exam.get('group')
                start_time = datetime.strptime(exam['start_datetime'], '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(exam['end_datetime'], '%Y-%m-%d %H:%M:%S')
                
                # Check if exam is for this student's group (or all students)
                if exam_group and exam_group != student_group:
                    continue
                
                # Check if exam is currently active
                if start_time <= now <= end_time and exam['status'] in ['scheduled', 'active']:
                    self.current_exam = exam
                    
                    # Update exam status to active if needed
                    if exam['status'] == 'scheduled':
                        exam['status'] = 'active'
                        with open(SCHEDULED_EXAMS_FILE, 'w') as f:
                            json.dump(scheduled_exams, f, indent=4)
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking scheduled exam: {str(e)}")
            return False
    
    def verify_camera(self):
        """Simple camera verification"""
        try:
            capture = cv2.VideoCapture(0)
            if not capture.isOpened():
                return False
            
            ret, frame = capture.read()
            capture.release()
            
            if not ret:
                return False
            
            # In real implementation, add face detection here
            return True
            
        except:
            return False
    
    def freeze_screen(self):
        """Freeze screen to exam window"""
        self.setWindowFlags(Qt.WindowType.Window | 
                          Qt.WindowType.WindowStaysOnTopHint |
                          Qt.WindowType.CustomizeWindowHint)
        self.showFullScreen()
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.grabKeyboard()
    
    def start_monitoring(self):
        """Start camera monitoring for cheating detection"""
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            self.capture = cv2.VideoCapture(0)
            if not self.capture.isOpened():
                self.log_security_violation("Camera Error", "Failed to start monitoring camera")
                return
            
            self.monitoring_timer = QTimer()
            self.monitoring_timer.timeout.connect(self.check_for_cheating)
            self.monitoring_timer.start(2000)
            
        except Exception as e:
            self.log_security_violation("Monitoring Error", f"Failed to start monitoring: {str(e)}")
    
    def check_for_cheating(self):
        """Check for cheating behavior"""
        if self.capture is None:
            return
        
        ret, frame = self.capture.read()
        if not ret:
            return
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        # Check for no face
        if len(faces) == 0:
            self.no_face_count += 1
            if self.no_face_count >= 3:
                self.send_cheating_alert("No Face Detected", 
                                        "Student's face not visible in camera")
                self.no_face_count = 0
        else:
            self.no_face_count = 0
        
        # Check for multiple faces
        if len(faces) > 1:
            self.multiple_face_count += 1
            if self.multiple_face_count >= 2:
                self.send_cheating_alert("Multiple Faces Detected", 
                                        f"Detected {len(faces)} faces in frame")
                self.multiple_face_count = 0
        else:
            self.multiple_face_count = 0
    
    def send_cheating_alert(self, alert_type, details):
        """Send cheating alert to admin"""
        try:
            alerts = []
            if os.path.exists(CHEATING_ALERTS_FILE):
                with open(CHEATING_ALERTS_FILE, 'r') as f:
                    alerts = json.load(f)
            
            alert = {
                'username': self.username,
                'student_name': self.student_name,
                'exam_name': self.current_exam.get('exam_name', 'Unknown'),
                'alert_type': alert_type,
                'details': details,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'question_number': self.current_question_index + 1
            }
            
            alerts.append(alert)
            
            with open(CHEATING_ALERTS_FILE, 'w') as f:
                json.dump(alerts, f, indent=4)
            
            self.log_security_violation(alert_type, details)
            
            QMessageBox.warning(self, "⚠️ Security Alert", 
                              f"{alert_type}\n\nThis incident has been reported to the administrator.")
            
        except Exception as e:
            pass
    
    def init_ui(self):
        self.setWindowTitle(f"Examination Portal - {self.current_exam.get('exam_name', 'Exam')}")
        self.setGeometry(0, 0, 1920, 1080)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(f"📝 {self.current_exam.get('exam_name', 'Online Examination')}")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Camera indicator
        if self.camera_required:
            camera_status = QLabel("📷 Monitored")
            camera_status.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            camera_status.setStyleSheet("""
                color: white;
                background-color: #e74c3c;
                padding: 8px 15px;
                border-radius: 6px;
            """)
            header_layout.addWidget(camera_status)
        
        student_label = QLabel(f"Student: {self.student_name}")
        student_label.setFont(QFont("Arial", 12))
        student_label.setStyleSheet("color: #7f8c8d; margin-left: 15px;")
        header_layout.addWidget(student_label)
        
        layout.addLayout(header_layout)
        
        # Timer and info
        info_layout = QHBoxLayout()
        
        # Timer
        timer_frame = QWidget()
        timer_frame.setStyleSheet("""
            QWidget {
                background-color: #e74c3c;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        timer_layout = QHBoxLayout()
        timer_layout.setContentsMargins(15, 10, 15, 10)
        
        self.timer_label = QLabel(f"⏱ Time: {self.time_limit//60}:00")
        self.timer_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: white;")
        timer_layout.addWidget(self.timer_label)
        
        timer_frame.setLayout(timer_layout)
        info_layout.addWidget(timer_frame)
        
        info_layout.addStretch()
        
        # Marks info
        marks_label = QLabel(f"Total Marks: {self.current_exam.get('total_marks', 0)}")
        marks_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        marks_label.setStyleSheet("color: #2c3e50;")
        info_layout.addWidget(marks_label)
        
        # Question counter
        self.question_counter = QLabel("Question: 1/0")
        self.question_counter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.question_counter.setStyleSheet("color: #2c3e50;")
        info_layout.addWidget(self.question_counter)
        
        layout.addLayout(info_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Question display
        question_frame = QWidget()
        question_frame.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #3498db;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        question_layout = QVBoxLayout()
        
        self.question_label = QLabel("Question will appear here")
        self.question_label.setFont(QFont("Arial", 14))
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet("color: #2c3e50; padding: 10px;")
        question_layout.addWidget(self.question_label)
        
        # Marks for this question
        self.question_marks_label = QLabel(f"[Marks: {self.current_exam.get('marks_per_question', 1)}]")
        self.question_marks_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.question_marks_label.setStyleSheet("color: #e67e22;")
        question_layout.addWidget(self.question_marks_label)
        
        question_frame.setLayout(question_layout)
        layout.addWidget(question_frame)
        
        # Options
        self.options_group = QButtonGroup()
        self.option_buttons = []
        
        for i in range(4):
            option = QRadioButton()
            option.setFont(QFont("Arial", 12))
            option.setStyleSheet("""
                QRadioButton {
                    padding: 12px;
                    background-color: white;
                    border: 2px solid #bdc3c7;
                    border-radius: 8px;
                    margin: 5px;
                }
                QRadioButton:hover {
                    border: 2px solid #3498db;
                    background-color: #ebf5fb;
                }
                QRadioButton:checked {
                    border: 2px solid #27ae60;
                    background-color: #d5f4e6;
                }
            """)
            self.options_group.addButton(option, i)
            self.option_buttons.append(option)
            layout.addWidget(option)
        
        layout.addStretch()
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("⬅ Previous")
        self.prev_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.prev_btn.clicked.connect(self.previous_question)
        nav_layout.addWidget(self.prev_btn)
        
        nav_layout.addStretch()
        
        self.status_label = QLabel("0 answered / 0 total")
        self.status_label.setFont(QFont("Arial", 11))
        self.status_label.setStyleSheet("color: #7f8c8d;")
        nav_layout.addWidget(self.status_label)
        
        nav_layout.addStretch()
        
        self.next_btn = QPushButton("Next ➡")
        self.next_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.next_btn.clicked.connect(self.next_question)
        nav_layout.addWidget(self.next_btn)
        
        self.submit_btn = QPushButton("✅ Submit Exam")
        self.submit_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.submit_btn.clicked.connect(self.submit_exam)
        self.submit_btn.hide()
        nav_layout.addWidget(self.submit_btn)
        
        layout.addLayout(nav_layout)
        
        # Warning
        warning_text = "⚠️ Warning: "
        if self.camera_required:
            warning_text += "Keep your face visible • "
        warning_text += "Do not switch tabs or minimize window • All activities are monitored"
        
        warning = QLabel(warning_text)
        warning.setFont(QFont("Arial", 10))
        warning.setStyleSheet("""
            color: #e74c3c;
            background-color: #fadbd8;
            padding: 10px;
            border-radius: 5px;
        """)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)
        
        central_widget.setLayout(layout)
    
    def load_questions(self):
        """Load questions for this exam"""
        try:
            if not os.path.exists(QUESTIONS_FILE):
                QMessageBox.critical(self, "Error", "No questions found!")
                self.close()
                return
            
            with open(QUESTIONS_FILE, 'r') as f:
                all_questions = json.load(f)
            
            # Get questions based on indices from scheduled exam
            question_indices = self.current_exam.get('question_indices', [])
            self.questions = [all_questions[i] for i in question_indices if i < len(all_questions)]
            
            # Shuffle if required
            if self.current_exam.get('shuffle_questions', False):
                random.shuffle(self.questions)
            
            if not self.questions:
                QMessageBox.critical(self, "Error", "No questions available for this exam!")
                self.close()
                return
            
            for i in range(len(self.questions)):
                self.answers[i] = None
            
            self.progress_bar.setMaximum(len(self.questions))
            self.question_counter.setText(f"Question: 1/{len(self.questions)}")
            self.update_status()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load questions:\n{str(e)}")
            self.close()
    
    def start_timer(self):
        """Start exam timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
    
    def update_timer(self):
        """Update timer"""
        self.time_remaining -= 1
        
        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(self, "Time's Up!", "Submitting your exam now...")
            self.submit_exam()
            return
        
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_label.setText(f"⏱ Time: {minutes:02d}:{seconds:02d}")
    
    def display_question(self):
        """Display current question"""
        if self.current_question_index >= len(self.questions):
            return
        
        question = self.questions[self.current_question_index]
        self.question_label.setText(f"Q{self.current_question_index + 1}. {question['question']}")
        
        options = question.get('options', [])
        for i, option in enumerate(options):
            if i < len(self.option_buttons):
                self.option_buttons[i].setText(option)
                self.option_buttons[i].show()
        
        for i in range(len(options), 4):
            self.option_buttons[i].hide()
        
        saved_answer = self.answers.get(self.current_question_index)
        if saved_answer is not None:
            self.option_buttons[saved_answer].setChecked(True)
        else:
            self.options_group.setExclusive(False)
            for btn in self.option_buttons:
                btn.setChecked(False)
            self.options_group.setExclusive(True)
        
        self.prev_btn.setEnabled(self.current_question_index > 0)
        is_last_question = self.current_question_index == len(self.questions) - 1
        self.next_btn.setVisible(not is_last_question)
        self.submit_btn.setVisible(is_last_question)
        
        self.question_counter.setText(f"Question: {self.current_question_index + 1}/{len(self.questions)}")
        self.progress_bar.setValue(self.current_question_index + 1)
        self.update_status()
    
    def save_current_answer(self):
        """Save current answer"""
        selected = self.options_group.checkedId()
        if selected != -1:
            self.answers[self.current_question_index] = selected
    
    def next_question(self):
        """Next question"""
        self.save_current_answer()
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.display_question()
    
    def previous_question(self):
        """Previous question"""
        self.save_current_answer()
        if self.current_question_index > 0:
            self.current_question_index -= 1
            self.display_question()
    
    def update_status(self):
        """Update status"""
        answered = sum(1 for ans in self.answers.values() if ans is not None)
        total = len(self.questions)
        self.status_label.setText(f"{answered} answered / {total} total")
    
    def submit_exam(self):
        """Submit exam"""
        self.save_current_answer()
        
        unanswered = sum(1 for ans in self.answers.values() if ans is None)
        if unanswered > 0:
            reply = QMessageBox.question(
                self, 'Incomplete Exam',
                f'You have {unanswered} unanswered question(s).\n\nSubmit anyway?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.timer.stop()
        if self.monitoring_timer:
            self.monitoring_timer.stop()
        
        # Calculate score based on marks per question
        correct_answers = 0
        for i, question in enumerate(self.questions):
            if self.answers.get(i) == question.get('answer', 0):
                correct_answers += 1
        
        marks_per_question = self.current_exam.get('marks_per_question', 1)
        total_marks = self.current_exam.get('total_marks', len(self.questions))
        obtained_marks = correct_answers * marks_per_question
        percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
        
        time_taken_sec = self.time_limit - self.time_remaining
        time_taken = f"{time_taken_sec // 60}m {time_taken_sec % 60}s"
        
        passing_percentage = self.current_exam.get('passing_percentage', 40)
        status = "PASS" if percentage >= passing_percentage else "FAIL"
        
        try:
            results = []
            if os.path.exists(RESULTS_FILE):
                with open(RESULTS_FILE, 'r') as f:
                    results = json.load(f)
            
            result = {
                'username': self.username,
                'student_name': self.student_name,
                'exam_name': self.current_exam.get('exam_name', 'Exam'),
                'exam_id': self.current_exam.get('exam_id', 'N/A'),
                'score': correct_answers,
                'total_questions': len(self.questions),
                'obtained_marks': obtained_marks,
                'total_marks': total_marks,
                'percentage': percentage,
                'time_taken': time_taken,
                'tab_switch_count': self.tab_switch_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'camera_monitoring': self.camera_required,
                'status': status,
                'questions_answered': sum(1 for ans in self.answers.values() if ans is not None)
            }
            
            results.append(result)
            
            with open(RESULTS_FILE, 'w') as f:
                json.dump(results, f, indent=4)
            
            # Show thank you dialog
            self.show_thank_you(result)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save results:\n{str(e)}")
            self.close()
    
    def show_thank_you(self, result_data):
        """Show thank you dialog"""
        dialog = ThankYouDialog(result_data, self)
        dialog.exec()
        self.cleanup_and_close()
    
    def log_security_violation(self, violation_type, details):
        """Log security violation"""
        try:
            logs = []
            if os.path.exists(SECURITY_LOGS_FILE):
                with open(SECURITY_LOGS_FILE, 'r') as f:
                    logs = json.load(f)
            
            log_entry = {
                'username': self.username,
                'student_name': self.student_name,
                'exam_name': self.current_exam.get('exam_name', 'Unknown'),
                'violation_type': violation_type,
                'details': details,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logs.append(log_entry)
            
            with open(SECURITY_LOGS_FILE, 'w') as f:
                json.dump(logs, f, indent=4)
        except:
            pass
    
    def cleanup_and_close(self):
        """Cleanup resources"""
        if self.capture:
            self.capture.release()
        if self.monitoring_timer:
            self.monitoring_timer.stop()
        self.releaseKeyboard()
        self.close()
    
    def closeEvent(self, event):
        """Handle close"""
        if hasattr(self, 'timer') and self.timer.isActive():
            reply = QMessageBox.question(
                self, 'Exit Exam',
                'Are you sure you want to exit and submit the exam?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.submit_exam()
                event.accept()
            else:
                event.ignore()
        else:
            self.cleanup_and_close()
            event.accept()
    
    def changeEvent(self, event):
        """Detect window changes"""
        if event.type() == event.Type.WindowStateChange:
            if self.windowState() == Qt.WindowState.WindowMinimized:
                self.tab_switch_count += 1
                self.log_security_violation("Window Minimized", "Student minimized exam window")
                self.send_cheating_alert("Window Minimized", f"Violation #{self.tab_switch_count}")
    
    def keyPressEvent(self, event):
        """Block certain key combinations"""
        # Block Alt+Tab, Alt+F4, Ctrl+Alt+Del, Windows key, etc.
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            event.ignore()
            return
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:  # Windows/Command key
            event.ignore()
            return
        super().keyPressEvent(event)


if __name__ == "__main__":
    # For testing - normally called from login system
    app = QApplication(sys.argv)
    
    # Sample student data
    student_data = {
        'username': 'student1',
        'name': 'John Doe',
        'group': 'Group A'
    }
    
    window = ExamWindow(student_data['username'], student_data['name'], student_data)
    window.show()
    sys.exit(app.exec())

"""
Login Page for Examination Management System
Handles authentication for both students and administrators
UPDATED: Integrates with enhanced exam system with camera monitoring and waiting room
"""

import sys
import json
import os
import hashlib
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit,
                             QMessageBox, QRadioButton, QButtonGroup, QFrame)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# File paths
STUDENTS_FILE = "students.json"
ADMIN_CREDENTIALS_FILE = "admin_credentials.json"
QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.json"
SECURITY_LOGS_FILE = "security_logs.json"
EXAM_CONFIG_FILE = "exam_config.json"
RULES_FILE = "rules.json"
CHEATING_ALERTS_FILE = "cheating_alerts.json"
SCHEDULED_EXAMS_FILE = "scheduled_exams.json"

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.admin_panel = None
        self.exam_window = None
        self.admin_mgmt_window = None
        self.waiting_room_window = None
        self.init_ui()
        self.create_default_files()
    
    def init_ui(self):
        self.setWindowTitle("SIENNA ECAD - Login")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #ecf0f1;")
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 15px;
                padding: 25px;
            }
        """)
        header_layout = QVBoxLayout()
        
        # --- Title Row (SVG + Label) ---
        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Relative path to the SVG file (e.g., "./assets/logo.svg")
        svg_path = os.path.join(os.path.dirname(__file__), "sym.svg")
        svg_icon = QSvgWidget(svg_path)
        svg_icon.setStyleSheet("background: transparent; border: none;")
        svg_icon.setFixedSize(250, 150)  # Adjust as needed
        title_row.addWidget(svg_icon)
        
        # Title Label
        # Add title row to header
        header_layout.addLayout(title_row)
        
        # Subtitle
        subtitle = QLabel("ONLINE ASSESSMENT")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setStyleSheet("color: #ecf0f1;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)
        
        header_frame.setLayout(header_layout)
        layout.addWidget(header_frame)

        # Radio buttons for login type
        type_layout = QHBoxLayout()
        type_layout.setSpacing(20)
        
        self.login_type_group = QButtonGroup()
        
        self.student_radio = QRadioButton("👨‍🎓 Student")
        self.student_radio.setFont(QFont("Arial", 11))
        self.student_radio.setStyleSheet("""
            QRadioButton {
                color: #2c3e50;
                padding: 10px;
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QRadioButton:checked {
                border: 2px solid #3498db;
                background-color: #ebf5fb;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.student_radio.setChecked(True)
        self.login_type_group.addButton(self.student_radio, 1)
        type_layout.addWidget(self.student_radio)
        
        self.admin_radio = QRadioButton("🔒 Administrator")
        self.admin_radio.setFont(QFont("Arial", 11))
        self.admin_radio.setStyleSheet("""
            QRadioButton {
                color: #2c3e50;
                padding: 10px;
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
            }
            QRadioButton:checked {
                border: 2px solid #e74c3c;
                background-color: #fadbd8;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        self.login_type_group.addButton(self.admin_radio, 2)
        type_layout.addWidget(self.admin_radio)
        
        layout.addLayout(type_layout)
        
        # Username field
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFont(QFont("Arial", 11))
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        layout.addWidget(self.username_input)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        password_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Arial", 11))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498db;
            }
        """)
        self.password_input.returnPressed.connect(self.login)
        layout.addWidget(self.password_input)
        
        # Login button
        login_btn = QPushButton("🔓 Login")
        login_btn.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        login_btn.clicked.connect(self.login)
        layout.addWidget(login_btn)
        
        # Admin management button (only for administrators)
        self.admin_mgmt_btn = QPushButton("⚙️ Admin Account Management")
        self.admin_mgmt_btn.setFont(QFont("Arial", 10))
        self.admin_mgmt_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 6px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        self.admin_mgmt_btn.clicked.connect(self.open_admin_management)
        layout.addWidget(self.admin_mgmt_btn)
        
        layout.addStretch()
        
        # Footer
        footer = QLabel("© 2024 Examination System | Secure & Monitored")
        footer.setFont(QFont("Arial", 9))
        footer.setStyleSheet("color: #7f8c8d;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
        
        central_widget.setLayout(layout)
    
    def create_default_files(self):
        """Create default credential files if they don't exist"""
        # Create default admin credentials
        if not os.path.exists(ADMIN_CREDENTIALS_FILE):
            default_admin = [{
                "username": "admin",
                "password": hashlib.sha256("admin123".encode()).hexdigest()
            }]
            with open(ADMIN_CREDENTIALS_FILE, 'w') as f:
                json.dump(default_admin, f, indent=4)
        
        # Create empty students file if it doesn't exist
        if not os.path.exists(STUDENTS_FILE):
            with open(STUDENTS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty questions file
        if not os.path.exists(QUESTIONS_FILE):
            with open(QUESTIONS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty results file
        if not os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty security logs file
        if not os.path.exists(SECURITY_LOGS_FILE):
            with open(SECURITY_LOGS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty cheating alerts file
        if not os.path.exists(CHEATING_ALERTS_FILE):
            with open(CHEATING_ALERTS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty rules file
        if not os.path.exists(RULES_FILE):
            with open(RULES_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create empty scheduled exams file
        if not os.path.exists(SCHEDULED_EXAMS_FILE):
            with open(SCHEDULED_EXAMS_FILE, 'w') as f:
                json.dump([], f, indent=4)
        
        # Create default exam config
        if not os.path.exists(EXAM_CONFIG_FILE):
            default_config = {
                "time_limit": 30,
                "camera_required": False,
                "group": None,
                "rules": [
                    "Complete the exam within the given time limit",
                    "Keep your face visible to the camera at all times (if monitoring enabled)",
                    "Do not switch tabs or minimize the exam window",
                    "Only one person should be visible in the camera",
                    "Do not use any external materials, books, or devices",
                    "Answer all questions to the best of your ability",
                    "The exam will auto-submit when time expires",
                    "Any violation will be reported and may result in disqualification"
                ]
            }
            with open(EXAM_CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
    
    def login(self):
        """Handle login authentication"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password!")
            return
        
        if self.admin_radio.isChecked():
            # Admin login
            if self.authenticate_admin(username, password):
                QMessageBox.information(self, "Success", f"Welcome, Administrator {username}!")
                self.open_admin_panel(username)
            else:
                QMessageBox.critical(self, "Login Failed", "Invalid admin credentials!\n\nPlease try again.")
                self.password_input.clear()
        else:
            # Student login
            student = self.authenticate_student(username, password)
            if student:
                QMessageBox.information(self, "Success", f"Welcome, {student['name']}!")
                self.open_exam_window(username, student['name'], student)
            else:
                QMessageBox.critical(self, "Login Failed", 
                                   "Invalid student credentials!\n\n"
                                   "Please check your username and password.\n"
                                   "Contact administrator if you need assistance.")
                self.password_input.clear()
    
    def authenticate_admin(self, username, password):
        """Authenticate admin credentials"""
        try:
            if not os.path.exists(ADMIN_CREDENTIALS_FILE):
                return False
            
            with open(ADMIN_CREDENTIALS_FILE, 'r') as f:
                admins = json.load(f)
            
            # Handle both dict and list formats
            if isinstance(admins, dict):
                admins = [admins]
            
            # Hash the input password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Check credentials
            for admin in admins:
                if admin['username'] == username and admin['password'] == hashed_password:
                    return True
            
            return False
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication error:\n{str(e)}")
            return False
    
    def authenticate_student(self, username, password):
        """Authenticate student credentials"""
        try:
            if not os.path.exists(STUDENTS_FILE):
                return None
            
            with open(STUDENTS_FILE, 'r') as f:
                students = json.load(f)
            
            # Find matching student
            for student in students:
                if student['username'] == username and student['password'] == password:
                    return student
            
            return None
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Authentication error:\n{str(e)}")
            return None
    
    def open_admin_panel(self, username):
        """Open admin panel"""
        try:
            # Import here to avoid circular imports
            from admin_panel import AdminPanel
            
            self.admin_panel = AdminPanel()
            self.admin_panel.logged_in_username = username
            self.admin_panel.show()
            self.hide()  # Hide login window instead of closing
            
            # Connect closed signal to show login window again
            self.admin_panel.destroyed.connect(self.show_login_again)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open admin panel:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def open_exam_window(self, username, student_name, student_data):
        """Open exam window for student - checks for scheduled exams first"""
        try:
            student_group = student_data.get('group')
            
            # Check for scheduled exams
            scheduled_exam = self.get_scheduled_exam_for_student(student_group)
            
            if scheduled_exam:
                # Check if exam time is appropriate
                now = datetime.now()
                start_time = datetime.strptime(scheduled_exam['start_datetime'], '%Y-%m-%d %H:%M:%S')
                early_access_time = start_time - timedelta(minutes=30)
                
                if now < early_access_time:
                    QMessageBox.information(
                        self,
                        "Exam Not Available Yet",
                        f"The exam '{scheduled_exam['exam_name']}' is scheduled for:\n\n"
                        f"Start Time: {scheduled_exam['start_datetime']}\n\n"
                        f"You can login 30 minutes before the exam starts.\n"
                        f"Please come back at: {early_access_time.strftime('%Y-%m-%d %I:%M %p')}"
                    )
                    return
                
            
                
            # Open waiting room for scheduled exam
                self.waiting_room_window(username, student_name, student_data, scheduled_exam)
            else:
                # No scheduled exam - show message
                self.open_default_exam(username, student_name, student_data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open exam:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def get_scheduled_exam_for_student(self, student_group):
        """Find active scheduled exam for student's group"""
        try:
            if not os.path.exists(SCHEDULED_EXAMS_FILE):
                return None
            
            with open(SCHEDULED_EXAMS_FILE, 'r') as f:
                scheduled_exams = json.load(f)
            
            now = datetime.now()
            
            for exam in scheduled_exams:
                # Skip completed exams
                if exam.get('status') == 'completed':
                    continue
                
                # Check if exam is for this student's group or all students
                exam_group = exam.get('group')
                if exam_group and exam_group != student_group:
                    continue
                
                # Check if exam is scheduled or active
                start_time = datetime.strptime(exam['start_datetime'], '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(exam['end_datetime'], '%Y-%m-%d %H:%M:%S')
                
                # Allow login 30 minutes before exam starts
                early_access_time = start_time - timedelta(minutes=30)
                
                if early_access_time <= now <= end_time:
                    return exam
            
            return None
            
        except Exception as e:
            print(f"Error finding scheduled exam: {str(e)}")
            return None
    
    def open_waiting_room(self, username, student_name, student_data, exam_data):
        """Open waiting room window for scheduled exam"""
        try:
            from waiting_room import WaitingRoomWindow
            
            self.waiting_room_window = WaitingRoomWindow(
                username, 
                student_name, 
                student_data, 
                exam_data
            )
            self.waiting_room_window.show()
            self.hide()
            
            # Connect closed signal to show login window again
            self.waiting_room_window.destroyed.connect(self.show_login_again)
            
        except ImportError as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to load waiting room:\n{str(e)}\n\n"
                               "Please ensure 'waiting_room.py' is in the same directory.")
            import traceback
            traceback.print_exc()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open waiting room:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def open_default_exam(self, username, student_name, student_data):
        """Open default exam (when no scheduled exam exists)"""
        try:
            # No scheduled exam found - show error message
            QMessageBox.warning(
                self,
                "No Exam Available",
                "No exam is currently scheduled for you.\n\n"
                "Please contact your administrator for more information."
            )
            return
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to check exam availability:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def show_login_again(self):
        """Show login window again and clear fields"""
        self.username_input.clear()
        self.password_input.clear()
        self.student_radio.setChecked(True)
        self.show()
    
    def open_admin_management(self):
        """Open admin account management"""
        # Ask for admin credentials before opening
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Authentication Required", 
                              "Please enter admin credentials first!")
            return
        
        if self.authenticate_admin(username, password):
            try:
                # Import here to avoid circular imports
                from admng import AdminManagementWindow
                
                self.admin_mgmt_window = AdminManagementWindow(username)
                self.admin_mgmt_window.show()
            except ImportError:
                QMessageBox.warning(self, "Module Not Found", 
                                  "Admin management module (admng.py) not found.\n\n"
                                  "This feature is optional.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open admin management:\n{str(e)}")
                import traceback
                traceback.print_exc()
        else:
            QMessageBox.critical(self, "Access Denied", 
                               "Invalid admin credentials!\n\n"
                               "Only administrators can access this feature.")
            self.password_input.clear()


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = LoginWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


