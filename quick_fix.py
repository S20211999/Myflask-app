PyQt6==6.6.1
gspread==6.1.4
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-auth==2.27.0



https://docs.google.com/spreadsheets/d/1qNxYdRyhBL6SOhw9c3zScheJYqU_gYuvziq423JWOq8/edit?usp=drivesdk
import sys
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QRadioButton, QButtonGroup, QMessageBox, QGroupBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ============================================
# CONFIGURATION - GOOGLE SHEETS SETUP
# ============================================
# Path to your Google Service Account JSON file
SERVICE_ACCOUNT_FILE = 'service_account.json'
# Google Sheet URL or Sheet ID
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
# Or just use the Sheet ID:
# GOOGLE_SHEET_ID = "YOUR_SHEET_ID"
# ============================================

class GoogleSheetsManager:
    """
    Manager for Google Sheets with gspread
    Handles authentication and all sheet operations
    """
    def __init__(self, service_account_file, sheet_url_or_id):
        self.service_account_file = service_account_file
        self.sheet_url_or_id = sheet_url_or_id
        self.gc = None
        self.spreadsheet = None
        self.sheets_data = {}
        self._authenticate_and_connect()
    
    def _authenticate_and_connect(self):
        """Authenticate with Google Sheets API using service account"""
        try:
            print("🔐 Authenticating with Google Sheets API...")
            
            # Define the scope
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials from service account JSON
            credentials = Credentials.from_service_account_file(
                self.service_account_file,
                scopes=scopes
            )
            
            # Authorize with gspread
            self.gc = gspread.authorize(credentials)
            
            print("✓ Authentication successful!")
            
            # Open the spreadsheet
            self._open_spreadsheet()
            
        except FileNotFoundError:
            print(f"❌ Service account file not found: {self.service_account_file}")
            print("Please download credentials from Google Cloud Console")
            self.gc = None
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            self.gc = None
    
    def _open_spreadsheet(self):
        """Open the Google Sheet"""
        try:
            print("📂 Opening Google Sheet...")
            
            # Try to open by URL or ID
            if "docs.google.com" in str(self.sheet_url_or_id):
                # Extract Sheet ID from URL
                sheet_id = self.sheet_url_or_id.split('/d/')[1].split('/')[0]
                self.spreadsheet = self.gc.open_by_key(sheet_id)
            else:
                # Direct Sheet ID
                self.spreadsheet = self.gc.open_by_key(self.sheet_url_or_id)
            
            print(f"✓ Sheet opened: {self.spreadsheet.title}")
            print(f"✓ Available worksheets: {[ws.title for ws in self.spreadsheet.worksheets()]}")
            
        except Exception as e:
            print(f"❌ Error opening spreadsheet: {e}")
            self.spreadsheet = None
    
    def _get_sheet_data(self, sheet_name):
        """Get all data from a specific sheet"""
        try:
            if not self.spreadsheet:
                print(f"Spreadsheet not loaded")
                return []
            
            worksheet = self.spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_values()
            
            print(f"✓ Loaded {len(data)} rows from sheet '{sheet_name}'")
            return data
            
        except gspread.exceptions.WorksheetNotFound:
            print(f"⚠ Worksheet '{sheet_name}' not found")
            return []
        except Exception as e:
            print(f"❌ Error reading sheet '{sheet_name}': {e}")
            return []
    
    def authenticate_student(self, username, password):
        """Authenticate student from Students sheet"""
        try:
            students_data = self._get_sheet_data('Students')
            
            if not students_data or len(students_data) < 2:
                print("No student data found")
                return None
            
            # Skip header row (row 0)
            for row in students_data[1:]:
                if len(row) >= 6:
                    # Row format: UserID, Password, Name, Email, Group, Status
                    if row[0] == username and row[1] == password and row[5] == 'Active':
                        return {
                            'username': row[0],
                            'name': row[2],
                            'email': row[3] if len(row) > 3 else '',
                            'group': row[4] if len(row) > 4 else ''
                        }
            
            print(f"Authentication failed for user: {username}")
            return None
            
        except Exception as e:
            print(f"Error during authentication: {e}")
            return None
    
    def check_schedule(self, group):
        """Check if current time is within scheduled exam time"""
        try:
            schedule_data = self._get_sheet_data('Schedule')
            
            if not schedule_data or len(schedule_data) < 2:
                return False, "Schedule sheet not found"
            
            current_time = datetime.now()
            
            # Skip header row
            for row in schedule_data[1:]:
                if len(row) >= 7:
                    # Row format: ConfigID, ExamDate, StartTime, EndTime, Duration, PassingMark, Status
                    config_id = row[0]
                    exam_group = self._get_group_from_config(config_id)
                    
                    if exam_group == group and row[6] == 'Scheduled':
                        exam_date_str = row[1]
                        start_time_str = row[2]
                        end_time_str = row[3]
                        duration = row[4] if len(row) > 4 else '60'
                        
                        try:
                            # Parse datetime
                            exam_datetime_start = datetime.strptime(
                                f"{exam_date_str} {start_time_str}", 
                                '%m/%d/%Y %H:%M'
                            )
                            exam_datetime_end = datetime.strptime(
                                f"{exam_date_str} {end_time_str}", 
                                '%m/%d/%Y %H:%M'
                            )
                            
                            print(f"Exam window: {exam_datetime_start} to {exam_datetime_end}")
                            print(f"Current time: {current_time}")
                            
                            if exam_datetime_start <= current_time <= exam_datetime_end:
                                return True, f"Duration: {duration} minutes"
                            else:
                                return False, f"Exam scheduled for {exam_date_str} from {start_time_str} to {end_time_str}"
                        
                        except Exception as e:
                            print(f"Error parsing datetime: {e}")
                            return True, ""
            
            return False, "No schedule found for your group"
            
        except Exception as e:
            print(f"Error checking schedule: {e}")
            return False, f"Schedule check error: {e}"
    
    def _get_group_from_config(self, config_id):
        """Map ConfigID to Group"""
        config_map = {
            'EXAM001': 'A',
            'EXAM002': 'B',
            'EXAM003': 'C'
        }
        return config_map.get(config_id, '')
    
    def get_questions(self, group):
        """Get questions for specific group from Questions sheet"""
        questions = []
        
        try:
            questions_data = self._get_sheet_data('Questions')
            
            if not questions_data or len(questions_data) < 2:
                print("Questions sheet not found")
                return questions
            
            # Skip header row
            for row in questions_data[1:]:
                if len(row) >= 9:
                    # Row format: QuestionID, Group, Question, Option1, Option2, Option3, Option4, CorrectAnswer, Status
                    if row[1] == group and row[8] == 'Active':
                        correct_answer = str(row[7]).upper()
                        
                        questions.append({
                            'question_id': row[0],
                            'question': row[2],
                            'options': {
                                'A': row[3],
                                'B': row[4],
                                'C': row[5],
                                'D': row[6]
                            },
                            'correct': correct_answer
                        })
            
            print(f"✓ Loaded {len(questions)} questions for Group {group}")
            return questions
            
        except Exception as e:
            print(f"Error getting questions: {e}")
            return questions
    
    def save_result(self, username, name, group, score, total, timestamp):
        """Save exam result to Results sheet"""
        try:
            if not self.spreadsheet:
                print("Spreadsheet not loaded")
                return False
            
            # Get or create Results sheet
            try:
                results_sheet = self.spreadsheet.worksheet('Results')
            except gspread.exceptions.WorksheetNotFound:
                print("Creating Results sheet...")
                results_sheet = self.spreadsheet.add_worksheet(title='Results', rows=1000, cols=10)
                # Add headers
                results_sheet.append_row([
                    'UserID', 'Name', 'Group', 'Score', 'TotalQuestions', 
                    'Percentage', 'Status', 'SubmissionTime'
                ])
            
            percentage = (score / total * 100) if total > 0 else 0
            status = 'Pass' if percentage >= 60 else 'Fail'
            
            # Append result row
            results_sheet.append_row([
                username,
                name,
                group,
                score,
                total,
                f"{percentage:.2f}%",
                status,
                timestamp
            ])
            
            print(f"✓ Result saved for {username}: {score}/{total} ({percentage:.2f}%)")
            return True
            
        except Exception as e:
            print(f"❌ Error saving result: {e}")
            return False
    
    def get_exam_duration(self, group):
        """Get exam duration for specific group"""
        try:
            schedule_data = self._get_sheet_data('Schedule')
            
            if not schedule_data or len(schedule_data) < 2:
                return 60
            
            for row in schedule_data[1:]:
                if len(row) >= 5:
                    exam_group = self._get_group_from_config(row[0])
                    if exam_group == group:
                        try:
                            return int(row[4])
                        except:
                            return 60
            
            return 60
        except Exception as e:
            print(f"Error getting exam duration: {e}")
            return 60


class LoginWindow(QWidget):
    def __init__(self, sheets_manager):
        super().__init__()
        self.sheets_manager = sheets_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Student Login - Online Exam System')
        self.setGeometry(100, 100, 450, 380)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title = QLabel('Online Examination System')
        title.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('color: #1976D2; margin: 20px;')
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel('📊 Connected to Google Sheets')
        subtitle.setFont(QFont('Arial', 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet('color: #4CAF50; margin-bottom: 10px;')
        layout.addWidget(subtitle)
        
        # Connection Status
        if self.sheets_manager.spreadsheet:
            status_text = f'✓ Connected: {self.sheets_manager.spreadsheet.title}'
            status_color = '#4CAF50'
        else:
            status_text = '❌ Not Connected'
            status_color = '#f44336'
        
        status_label = QLabel(status_text)
        status_label.setFont(QFont('Arial', 9))
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet(f'color: {status_color};')
        layout.addWidget(status_label)
        
        # Username
        username_label = QLabel('Username:')
        username_label.setFont(QFont('Arial', 12))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Enter your username')
        self.username_input.setFont(QFont('Arial', 11))
        self.username_input.setStyleSheet('padding: 8px; border: 2px solid #ddd; border-radius: 4px;')
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel('Password:')
        password_label.setFont(QFont('Arial', 12))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText('Enter your password')
        self.password_input.setFont(QFont('Arial', 11))
        self.password_input.setStyleSheet('padding: 8px; border: 2px solid #ddd; border-radius: 4px;')
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        
        # Login Button
        self.login_btn = QPushButton('Login to Exam')
        self.login_btn.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border-radius: 6px;
                border: none;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        # Status Label
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont('Arial', 10))
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Test Credentials Info
        info_label = QLabel('Test User: biswajit / biswajit')
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setFont(QFont('Arial', 9))
        info_label.setStyleSheet('color: #757575; margin-top: 10px;')
        layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setStyleSheet('color: #f44336;')
            self.status_label.setText('⚠ Please enter both username and password')
            return
        
        # Show loading
        self.status_label.setStyleSheet('color: #2196F3;')
        self.status_label.setText('🔄 Authenticating with Google Sheets...')
        self.login_btn.setEnabled(False)
        QApplication.processEvents()
        
        # Authenticate
        student_data = self.sheets_manager.authenticate_student(username, password)
        
        if student_data:
            self.status_label.setText('✓ Authenticated! Checking schedule...')
            QApplication.processEvents()
            
            # Check schedule
            is_scheduled, message = self.sheets_manager.check_schedule(student_data['group'])
            
            if is_scheduled:
                self.status_label.setStyleSheet('color: #4CAF50;')
                self.status_label.setText('✓ Access granted! Loading exam...')
                QTimer.singleShot(500, lambda: self.open_exam_window(student_data))
            else:
                self.login_btn.setEnabled(True)
                QMessageBox.warning(self, 'Schedule Error', 
                                  f'❌ You cannot access the exam at this time.\n\n{message}')
                self.status_label.setText('')
        else:
            self.status_label.setStyleSheet('color: #f44336;')
            self.status_label.setText('✗ Invalid username or password')
            self.login_btn.setEnabled(True)
    
    def open_exam_window(self, student_data):
        self.exam_window = ExamWindow(self.sheets_manager, student_data)
        self.exam_window.show()
        self.close()


class ExamWindow(QMainWindow):
    def __init__(self, sheets_manager, student_data):
        super().__init__()
        self.sheets_manager = sheets_manager
        self.student_data = student_data
        self.questions = sheets_manager.get_questions(student_data['group'])
        self.current_question = 0
        self.answers = {}
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Online Exam - {self.student_data['name']} (Group {self.student_data['group']})")
        self.setGeometry(100, 100, 900, 650)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # Header
        header_widget = QWidget()
        header_widget.setStyleSheet('background-color: #1976D2; padding: 15px; border-radius: 8px;')
        header_layout = QHBoxLayout()
        
        student_info = QLabel(f"👤 {self.student_data['name']} | Group {self.student_data['group']}")
        student_info.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        student_info.setStyleSheet('color: white;')
        header_layout.addWidget(student_info)
        
        header_layout.addStretch()
        
        self.timer_label = QLabel('⏱ Time: --:--')
        self.timer_label.setFont(QFont('Arial', 13, QFont.Weight.Bold))
        self.timer_label.setStyleSheet('color: #FFEB3B;')
        header_layout.addWidget(self.timer_label)
        
        header_widget.setLayout(header_layout)
        main_layout.addWidget(header_widget)
        
        # Progress Bar
        progress_widget = QWidget()
        progress_layout = QVBoxLayout()
        progress_label = QLabel(f'Exam Progress: Question {self.current_question + 1} of {len(self.questions)}')
        progress_label.setFont(QFont('Arial', 10))
        progress_label.setStyleSheet('color: #666;')
        self.progress_label_widget = progress_label
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.questions))
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        progress_widget.setLayout(progress_layout)
        main_layout.addWidget(progress_widget)
        
        # Question Area
        self.question_group = QGroupBox()
        self.question_group.setStyleSheet("""
            QGroupBox {
                background-color: #f9f9f9;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-top: 10px;
            }
        """)
        question_layout = QVBoxLayout()
        
        self.question_label = QLabel()
        self.question_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.question_label.setWordWrap(True)
        self.question_label.setStyleSheet('color: #333; margin-bottom: 15px;')
        question_layout.addWidget(self.question_label)
        
        # Options
        self.option_group = QButtonGroup()
        self.option_buttons = []
        
        for option in ['A', 'B', 'C', 'D']:
            radio_btn = QRadioButton()
            radio_btn.setFont(QFont('Arial', 12))
            radio_btn.setStyleSheet("""
                QRadioButton {
                    padding: 10px;
                    spacing: 10px;
                }
                QRadioButton::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            self.option_group.addButton(radio_btn)
            self.option_buttons.append(radio_btn)
            question_layout.addWidget(radio_btn)
        
        self.question_group.setLayout(question_layout)
        main_layout.addWidget(self.question_group)
        
        # Navigation Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.prev_btn = QPushButton('← Previous')
        self.prev_btn.setFont(QFont('Arial', 12))
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #9e9e9e;
            }
        """)
        self.prev_btn.clicked.connect(self.previous_question)
        self.prev_btn.setEnabled(False)
        button_layout.addWidget(self.prev_btn)
        
        button_layout.addStretch()
        
        self.next_btn = QPushButton('Next →')
        self.next_btn.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 25px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.next_btn.clicked.connect(self.next_question)
        button_layout.addWidget(self.next_btn)
        
        self.submit_btn = QPushButton('✓ Submit Exam')
        self.submit_btn.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.submit_btn.clicked.connect(self.submit_exam)
        self.submit_btn.setVisible(False)
        button_layout.addWidget(self.submit_btn)
        
        main_layout.addLayout(button_layout)
        
        central_widget.setLayout(main_layout)
        
        # Timer
        exam_duration = self.sheets_manager.get_exam_duration(self.student_data['group'])
        self.time_remaining = exam_duration * 60
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        # Load first question
        if self.questions:
            self.load_question()
        else:
            QMessageBox.warning(self, 'No Questions', 'No active questions found for your group.')
            self.close()
    
    def load_question(self):
        if self.current_question < len(self.questions):
            question_data = self.questions[self.current_question]
            
            self.question_label.setText(
                f"Question {self.current_question + 1} of {len(self.questions)}:\n\n"
                f"{question_data['question']}"
            )
            
            for idx, (key, text) in enumerate(question_data['options'].items()):
                self.option_buttons[idx].setText(f"{key}. {text}")
            
            # Load previous answer if exists
            if self.current_question in self.answers:
                selected_option = self.answers[self.current_question]
                option_index = ord(selected_option) - ord('A')
                self.option_buttons[option_index].setChecked(True)
            else:
                self.option_group.setExclusive(False)
                for btn in self.option_buttons:
                    btn.setChecked(False)
                self.option_group.setExclusive(True)
            
            self.progress_bar.setValue(self.current_question + 1)
            self.progress_label_widget.setText(f'Exam Progress: Question {self.current_question + 1} of {len(self.questions)}')
            
            # Update navigation buttons
            self.prev_btn.setEnabled(self.current_question > 0)
            
            if self.current_question == len(self.questions) - 1:
                self.next_btn.setVisible(False)
                self.submit_btn.setVisible(True)
            else:
                self.next_btn.setVisible(True)
                self.submit_btn.setVisible(False)
    
    def save_current_answer(self):
        selected_button = self.option_group.checkedButton()
        if selected_button:
            option_index = self.option_buttons.index(selected_button)
            self.answers[self.current_question] = chr(ord('A') + option_index)
    
    def next_question(self):
        self.save_current_answer()
        if self.current_question < len(self.questions) - 1:
            self.current_question += 1
            self.load_question()
    
    def previous_question(self):
        self.save_current_answer()
        if self.current_question > 0:
            self.current_question -= 1
            self.load_question()
    
    def update_timer(self):
        self.time_remaining -= 1
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        self.timer_label.setText(f'⏱ Time: {minutes:02d}:{seconds:02d}')
        
        if self.time_remaining <= 60:
            self.timer_label.setStyleSheet('color: #FF5252;')
        
        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(self, 'Time Up', '⏰ Time is up! Submitting your exam automatically.')
            self.submit_exam()
    
    def submit_exam(self):
        self.save_current_answer()
        self.timer.stop()
        
        # Calculate score
        score = 0
        for idx, question in enumerate(self.questions):
            if idx in self.answers and self.answers[idx] == question['correct']:
                score += 1
        
        total_questions = len(self.questions)
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        
        # Save results to Google Sheets
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success = self.sheets_manager.save_result(
            self.student_data['username'],
            self.student_data['name'],
            self.student_data['group'],
            score,
            total_questions,
            timestamp
        )
        
        # Determine pass/fail
        status = "PASSED ✓" if percentage >= 60 else "FAILED ✗"
        status_color = "#4CAF50" if percentage >= 60 else "#f44336"
        
        # Show results
        result_msg = f"""
<html>
<body style="font-family: Arial;">
    <h2 style="color: {status_color};">Exam Completed - {status}</h2>
    
    <p><b>Student:</b> {self.student_data['name']}</p>
    <p><b>Group:</b> {self.student_data['group']}</p>
    
    <hr>
    
    <p style="font-size: 18px;"><b>Score:</b> {score} / {total_questions}</p>
    <p style="font-size: 18px;"><b>Percentage:</b> {percentage:.2f}%</p>
    
    <hr>
    
    <p style="color: {'green' if success else 'red'};">
        {'✓ Results saved to Google Sheets successfully!' if success else '⚠ Warning: Check your internet connection.'}
    </p>
    <p style="font-size: 12px; color: #999;">Submitted at: {timestamp}</p>
</body>
</html>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Exam Results')
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(result_msg)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
        
        self.close()


def main():
    app = QApplication(sys.argv)
    
    # Apply global stylesheet
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QMessageBox {
            background-color: white;
        }
    """)
    
    print("="*70)
    print("📚 Online Exam System with Google Sheets - Initializing...")
    print("="*70)
    
    # Initialize Google Sheets Manager
    sheets_manager = GoogleSheetsManager(SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_URL)
    
    if sheets_manager.spreadsheet is None:
        QMessageBox.critical(None, 'Connection Error', 
                           '❌ Failed to connect to Google Sheets.\n\n'
                           'Please check:\n'
                           '1. service_account.json file exists\n'
                           '2. Google Sheet URL/ID is correct\n'
                           '3. Service account has access to the sheet\n'
                           '4. Internet connection is working')
        sys.exit(1)
    
    print("\n✓ Google Sheets connected successfully!")
    print(f"✓ Spreadsheet: {sheets_manager.spreadsheet.title}")
    print(f"✓ Available worksheets: {[ws.title for ws in sheets_manager.spreadsheet.worksheets()]}\n")
    
    # Show login window
    login_window = LoginWindow(sheets_manager)
    login_window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
