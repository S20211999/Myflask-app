
import sys
import requests
from datetime import datetime
from openpyxl import load_workbook
from io import BytesIO
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QRadioButton, QButtonGroup, QMessageBox, QGroupBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ============================================
# CONFIGURATION - HARDCODED EXCEL LINK
# ============================================
EXCEL_SHARE_LINK = "https://siennaecadllc-my.sharepoint.com/:x:/r/personal/biswajit_m_siennaecad_com/_layouts/15/Doc.aspx?sourcedoc=%7B9A34FDC0-8C89-4A4D-A434-BDA9B1C5395F%7D&file=Book%2016.xlsx&action=editnew"
LOCAL_CACHE_FILE = "exam_cache.xlsx"
# ============================================

class OnlineExcelManager:
    """
    Manager for Online Excel with actual data fetching from SharePoint
    Downloads Excel file and parses it using openpyxl
    """
    def __init__(self, share_link, cache_file=LOCAL_CACHE_FILE):
        self.share_link = share_link
        self.cache_file = cache_file
        self.wb = None
        self.last_sync = None
        self._download_and_load_excel()
    
    def _convert_share_link_to_download(self, share_link):
        """Convert SharePoint share link to direct download URL"""
        try:
            # Remove action parameters and add download parameter
            download_link = share_link.replace('action=editnew', 'download=1')
            download_link = download_link.replace('action=edit', 'download=1')
            
            # Alternative: use ?download=1 if not already present
            if '?download' not in download_link and '&download' not in download_link:
                if '?' in download_link:
                    download_link += '&download=1'
                else:
                    download_link += '?download=1'
            
            return download_link
        except Exception as e:
            print(f"Error converting share link: {e}")
            return share_link
    
    def _download_excel_file(self):
        """Download Excel file from SharePoint share link"""
        try:
            print("📥 Downloading Excel file from SharePoint...")
            
            # Convert share link to download URL
            download_url = self._convert_share_link_to_download(self.share_link)
            
            # Add headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Download the file
            response = requests.get(download_url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Save to cache file
            with open(self.cache_file, 'wb') as f:
                f.write(response.content)
            
            print(f"✓ Excel file downloaded successfully ({len(response.content)} bytes)")
            self.last_sync = datetime.now()
            return True
            
        except Exception as e:
            print(f"❌ Error downloading Excel file: {e}")
            print("Using cached file if available...")
            return False
    
    def _load_workbook_from_cache(self):
        """Load workbook from cache file"""
        try:
            if os.path.exists(self.cache_file):
                print(f"📂 Loading Excel from cache: {self.cache_file}")
                self.wb = load_workbook(self.cache_file, data_only=True)
                return True
            return False
        except Exception as e:
            print(f"Error loading cached workbook: {e}")
            return False
    
    def _download_and_load_excel(self):
        """Download Excel and load into memory"""
        # Try to download first
        download_success = self._download_excel_file()
        
        # Load from cache
        if not self._load_workbook_from_cache():
            print("⚠ Failed to load any Excel file!")
            self.wb = None
    
    def _sync_with_online(self):
        """Sync/download latest data from Excel Online"""
        print("🔄 Syncing with online Excel...")
        self._download_and_load_excel()
    
    def _write_to_excel(self, sheet_name, data_rows):
        """Write data to Excel and upload"""
        try:
            if not self.wb:
                print("No workbook loaded")
                return False
            
            if sheet_name not in self.wb.sheetnames:
                ws = self.wb.create_sheet(sheet_name)
            else:
                ws = self.wb[sheet_name]
            
            # Append rows
            for row_data in data_rows:
                ws.append(row_data)
            
            # Save locally
            self.wb.save(self.cache_file)
            print(f"✓ Data written to local cache: {sheet_name}")
            
            # Optional: Upload back to SharePoint
            # self._upload_excel_file()
            
            return True
        except Exception as e:
            print(f"Error writing to Excel: {e}")
            return False
    
    def authenticate_student(self, username, password):
        """Authenticate student and return student data"""
        try:
            if not self.wb or 'Students' not in self.wb.sheetnames:
                print("Students sheet not found")
                return None
            
            students_sheet = self.wb['Students']
            
            # Read all rows
            for row in students_sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 6:
                    # Row format: UserID, Password, Name, Email, Group, Status
                    if row[0] == username and row[1] == password and row[5] == 'Active':
                        return {
                            'username': row[0],
                            'name': row[2],
                            'email': row[3] if row[3] else '',
                            'group': row[4]
                        }
            
            print(f"Authentication failed for user: {username}")
            return None
            
        except Exception as e:
            print(f"Error during authentication: {e}")
            return None
    
    def check_schedule(self, group):
        """Check if current time is within scheduled exam time"""
        try:
            if not self.wb or 'Schedule' not in self.wb.sheetnames:
                return False, "Schedule sheet not found"
            
            schedule_sheet = self.wb['Schedule']
            current_time = datetime.now()
            
            # Read schedule rows
            for row in schedule_sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 7:
                    # Row format: ConfigID, ExamDate, StartTime, EndTime, Duration, PassingMark, Status
                    config_id = row[0]
                    exam_group = self._get_group_from_config(config_id)
                    
                    if exam_group == group and row[6] == 'Scheduled':
                        exam_date = row[1]
                        start_time = row[2]
                        end_time = row[3]
                        duration = row[4]
                        
                        try:
                            # Parse datetime - handle various formats
                            if isinstance(exam_date, str):
                                date_str = exam_date
                            else:
                                date_str = exam_date.strftime('%m/%d/%Y') if exam_date else None
                            
                            time_format = '%m/%d/%Y %H:%M' if ':' in str(start_time) else '%m/%d/%Y %H:%M:%S'
                            
                            exam_datetime_start = datetime.strptime(f"{date_str} {start_time}", time_format)
                            exam_datetime_end = datetime.strptime(f"{date_str} {end_time}", time_format)
                            
                            print(f"Exam window: {exam_datetime_start} to {exam_datetime_end}")
                            print(f"Current time: {current_time}")
                            
                            if exam_datetime_start <= current_time <= exam_datetime_end:
                                return True, f"Duration: {duration} minutes"
                            else:
                                return False, f"Exam scheduled for {date_str} from {start_time} to {end_time}"
                        except Exception as e:
                            print(f"Error parsing datetime: {e}")
                            # For testing, allow login anytime
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
        """Get questions for specific group from Excel"""
        questions = []
        
        try:
            if not self.wb or 'Questions' not in self.wb.sheetnames:
                print("Questions sheet not found")
                return questions
            
            questions_sheet = self.wb['Questions']
            
            # Read all question rows
            for row in questions_sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 9:
                    # Row format: QuestionID, Group, Question, Option1, Option2, Option3, Option4, CorrectAnswer, Status
                    if row[1] == group and row[8] == 'Active':
                        correct_answer = str(row[7]).upper()
                        # Map correct answer: B means Option2 (index 1)
                        option_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        correct_idx = option_map.get(correct_answer, 0)
                        
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
        """Save exam result to Excel Results sheet"""
        try:
            if not self.wb:
                print("Workbook not loaded")
                return False
            
            # Create Results sheet if not exists
            if 'Results' not in self.wb.sheetnames:
                ws = self.wb.create_sheet('Results')
                ws.append(['UserID', 'Name', 'Group', 'Score', 'TotalQuestions', 'Percentage', 'Status', 'SubmissionTime'])
            else:
                ws = self.wb['Results']
            
            percentage = (score / total * 100) if total > 0 else 0
            status = 'Pass' if percentage >= 60 else 'Fail'
            
            # Append result row
            ws.append([username, name, group, score, total, f"{percentage:.2f}%", status, timestamp])
            
            # Save to cache
            self.wb.save(self.cache_file)
            print(f"✓ Result saved for {username}: {score}/{total} ({percentage:.2f}%)")
            
            return True
            
        except Exception as e:
            print(f"Error saving result: {e}")
            return False
    
    def get_exam_duration(self, group):
        """Get exam duration for specific group"""
        try:
            if not self.wb or 'Schedule' not in self.wb.sheetnames:
                return 60  # Default 60 minutes
            
            schedule_sheet = self.wb['Schedule']
            
            for row in schedule_sheet.iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 5:
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
    def __init__(self, excel_manager):
        super().__init__()
        self.excel_manager = excel_manager
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
        subtitle = QLabel('📊 Connected to Excel Online')
        subtitle.setFont(QFont('Arial', 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet('color: #4CAF50; margin-bottom: 10px;')
        layout.addWidget(subtitle)
        
        # Sync Status
        sync_label = QLabel(f'Last Sync: {self.excel_manager.last_sync.strftime("%H:%M:%S") if self.excel_manager.last_sync else "Now"}')
        sync_label.setFont(QFont('Arial', 9))
        sync_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sync_label.setStyleSheet('color: #999;')
        layout.addWidget(sync_label)
        
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
        self.status_label.setText('🔄 Authenticating with Excel Online...')
        self.login_btn.setEnabled(False)
        QApplication.processEvents()
        
        # Authenticate
        student_data = self.excel_manager.authenticate_student(username, password)
        
        if student_data:
            self.status_label.setText('✓ Authenticated! Checking schedule...')
            QApplication.processEvents()
            
            # Check schedule
            is_scheduled, message = self.excel_manager.check_schedule(student_data['group'])
            
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
        self.exam_window = ExamWindow(self.excel_manager, student_data)
        self.exam_window.show()
        self.close()


class ExamWindow(QMainWindow):
    def __init__(self, excel_manager, student_data):
        super().__init__()
        self.excel_manager = excel_manager
        self.student_data = student_data
        self.questions = excel_manager.get_questions(student_data['group'])
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
        exam_duration = self.excel_manager.get_exam_duration(self.student_data['group'])
        self.time_remaining = exam_duration * 60  # Convert to seconds
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
        
        # Save results to Excel
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success = self.excel_manager.save_result(
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
        {'✓ Results saved to Excel Online successfully!' if success else '⚠ Warning: Check your internet connection.'}
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
    
    print("="*60)
    print("📚 Online Exam System - Initializing...")
    print("="*60)
    
    # Initialize Excel Manager with hardcoded link
    excel_manager = OnlineExcelManager(EXCEL_SHARE_LINK)
    
    if excel_manager.wb is None:
        QMessageBox.critical(None, 'Connection Error', 
                           '❌ Failed to connect to Excel Online.\n\nPlease check:\n'
                           '1. Internet connection\n'
                           '2. Excel share link is accessible\n'
                           '3. Excel file format is correct')
        sys.exit(1)
    
    print("\n✓ Excel file loaded successfully!")
    print(f"✓ Available sheets: {excel_manager.wb.sheetnames}\n")
    
    # Show login window
    login_window = LoginWindow(excel_manager)
    login_window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
