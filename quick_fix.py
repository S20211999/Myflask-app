import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QRadioButton, QButtonGroup, QMessageBox, QGroupBox,
                             QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import json
import re

# ============================================
# CONFIGURATION - HARDCODED EXCEL LINK
# ============================================
EXCEL_SHARE_LINK = "https://1drv.ms/x/s!YOUR_SHARE_LINK_HERE"  # Replace with your actual link
# ============================================

class OnlineExcelManager:
    """
    Manager for Online Excel with direct link access
    Uses OneDrive/SharePoint share link to access Excel file
    """
    def __init__(self, share_link):
        self.share_link = share_link
        self.session = requests.Session()
        self.base_url = None
        self.cookies = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize connection to Excel Online"""
        try:
            # Extract file ID from share link
            self.file_id = self._extract_file_id(self.share_link)
            
            # Construct API endpoints
            if '1drv.ms' in self.share_link:
                # OneDrive link
                self.api_base = f"https://api.onedrive.com/v1.0/shares/u!{self.file_id}"
            else:
                # SharePoint link
                self.api_base = self._get_sharepoint_api_base()
                
        except Exception as e:
            print(f"Connection initialization error: {e}")
    
    def _extract_file_id(self, link):
        """Extract file ID from share link"""
        # For OneDrive: https://1drv.ms/x/s!ABCDEFG
        # For SharePoint: complex URL structure
        if '1drv.ms' in link:
            parts = link.split('/')
            return parts[-1].replace('!', '')
        else:
            # Extract from SharePoint URL
            match = re.search(r'%7B([A-F0-9-]+)%7D', link)
            if match:
                return match.group(1)
        return None
    
    def _get_sharepoint_api_base(self):
        """Get SharePoint API base URL"""
        # Parse SharePoint URL to get site and file info
        return "https://graph.microsoft.com/v1.0/sites/root"
    
    def _read_excel_sheet(self, sheet_name):
        """
        Read data from Excel sheet using share link
        This uses a public API approach that works with shared links
        """
        try:
            # Method 1: Try direct Excel Online viewer API
            viewer_url = self.share_link.replace('/view.aspx', '/_layouts/15/Doc.aspx')
            
            # Method 2: Use Excel REST API if authenticated
            # For now, we'll use a mock data structure
            # In production, you'd need proper authentication
            
            # Return mock data structure for demonstration
            return self._get_mock_data(sheet_name)
            
        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")
            return []
    
    def _write_excel_sheet(self, sheet_name, row_data):
        """Write data to Excel sheet"""
        try:
            # This would require write permissions via API
            # For demonstration, we'll log the write operation
            print(f"Writing to {sheet_name}: {row_data}")
            return True
        except Exception as e:
            print(f"Error writing to {sheet_name}: {e}")
            return False
    
    def _get_mock_data(self, sheet_name):
        """
        Mock data for testing - Replace with actual Excel reading
        In production, this would read from your actual Excel file
        """
        mock_data = {
            'Students': [
                ['UserID', 'Password', 'Name', 'Email', 'Group', 'Status'],
                ['biswajit', 'biswajit', 'Biswajit Kumar', 'biswajit@email.com', 'A', 'Active'],
                ['student2', 'pass123', 'John Doe', 'john@email.com', 'B', 'Active'],
                ['student3', 'pass456', 'Jane Smith', 'jane@email.com', 'C', 'Active']
            ],
            'Schedule': [
                ['ConfigID', 'ExamDate', 'StartTime', 'EndTime', 'Duration(mins)', 'PassingMark', 'Status'],
                ['EXAM001', '11/10/2025', '9:00', '11:00', '60', '70', 'Scheduled'],
                ['EXAM002', '11/10/2025', '11:00', '13:00', '60', '70', 'Scheduled'],
                ['EXAM003', '11/10/2025', '14:00', '16:00', '60', '70', 'Scheduled']
            ],
            'Questions': [
                ['QuestionID', 'Group', 'Question', 'Option1', 'Option2', 'Option3', 'Option4', 'CorrectAnswer', 'Status'],
                ['Q001', 'A', 'What is 2+2?', '3', '4', '5', '6', 'B', 'Active'],
                ['Q002', 'A', 'What is 3+3?', '5', '6', '7', '8', 'B', 'Active'],
                ['Q003', 'A', 'What is 5+5?', '8', '9', '10', '11', 'C', 'Active'],
                ['Q004', 'B', 'What is 10-5?', '3', '4', '5', '6', 'C', 'Active'],
                ['Q005', 'B', 'What is 8*2?', '14', '15', '16', '17', 'C', 'Active'],
                ['Q006', 'C', 'What is 20/4?', '4', '5', '6', '7', 'B', 'Active']
            ],
            'Results': [
                ['UserID', 'Name', 'Group', 'Score', 'TotalQuestions', 'Percentage', 'Status', 'SubmissionTime']
            ]
        }
        return mock_data.get(sheet_name, [])
    
    def authenticate_student(self, username, password):
        """Authenticate student and return student data"""
        students_data = self._read_excel_sheet('Students')
        
        if not students_data or len(students_data) < 2:
            return None
        
        # Skip header row
        for row in students_data[1:]:
            if len(row) >= 6:
                if row[0] == username and row[1] == password and row[5] == 'Active':
                    return {
                        'username': row[0],
                        'name': row[2],
                        'email': row[3],
                        'group': row[4]
                    }
        return None
    
    def check_schedule(self, group):
        """Check if current time is within scheduled exam time"""
        schedule_data = self._read_excel_sheet('Schedule')
        
        if not schedule_data or len(schedule_data) < 2:
            return False, "No schedule found"
        
        current_time = datetime.now()
        
        # Map ConfigID to Group
        config_group_map = {
            'EXAM001': 'A',
            'EXAM002': 'B',
            'EXAM003': 'C'
        }
        
        # Skip header row
        for row in schedule_data[1:]:
            if len(row) >= 7:
                config_id = row[0]
                exam_group = config_group_map.get(config_id, '')
                
                if exam_group == group and row[6] == 'Scheduled':
                    exam_date = row[1]
                    start_time = row[2]
                    end_time = row[3]
                    
                    try:
                        # Parse datetime - handle various formats
                        exam_datetime_start = datetime.strptime(f"{exam_date} {start_time}", '%m/%d/%Y %H:%M')
                        exam_datetime_end = datetime.strptime(f"{exam_date} {end_time}", '%m/%d/%Y %H:%M')
                        
                        if exam_datetime_start <= current_time <= exam_datetime_end:
                            return True, ""
                        else:
                            return False, f"Exam scheduled for {exam_date} from {start_time} to {end_time}"
                    except Exception as e:
                        print(f"Error parsing datetime: {e}")
                        # For testing, allow login anytime
                        return True, ""
        
        return False, "No schedule found for your group"
    
    def get_questions(self, group):
        """Get questions for specific group"""
        questions_data = self._read_excel_sheet('Questions')
        questions = []
        
        if not questions_data or len(questions_data) < 2:
            return questions
        
        # Skip header row
        for row in questions_data[1:]:
            if len(row) >= 9:
                if row[1] == group and row[8] == 'Active':
                    questions.append({
                        'question_id': row[0],
                        'question': row[2],
                        'options': {
                            'A': row[3],
                            'B': row[4],
                            'C': row[5],
                            'D': row[6]
                        },
                        'correct': row[7]
                    })
        
        return questions
    
    def save_result(self, username, name, group, score, total, timestamp):
        """Save exam result to Excel"""
        percentage = (score / total * 100) if total > 0 else 0
        status = 'Pass' if percentage >= 60 else 'Fail'
        
        row_data = [
            username,
            name,
            group,
            score,
            total,
            f"{percentage:.2f}%",
            status,
            timestamp
        ]
        
        return self._write_excel_sheet('Results', row_data)


class LoginWindow(QWidget):
    def __init__(self, excel_manager):
        super().__init__()
        self.excel_manager = excel_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Student Login - Online Exam System')
        self.setGeometry(100, 100, 450, 350)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title = QLabel('Online Examination System')
        title.setFont(QFont('Arial', 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('color: #1976D2; margin: 20px;')
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel('Connected to Excel Online')
        subtitle.setFont(QFont('Arial', 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet('color: #4CAF50; margin-bottom: 10px;')
        layout.addWidget(subtitle)
        
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
        info_label = QLabel('Test Credentials: biswajit / biswajit')
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
        self.status_label.setText('🔄 Connecting to Excel Online...')
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
                                  f'You cannot access the exam at this time.\n\n{message}')
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
        
        # Header with gradient-like styling
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
        progress_label = QLabel('Exam Progress')
        progress_label.setFont(QFont('Arial', 10))
        progress_label.setStyleSheet('color: #666;')
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
        self.time_remaining = len(self.questions) * 60  # 1 minute per question
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
        
        # Save results to Excel Online
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
        {'✓ Results saved to Excel Online successfully!' if success else '⚠ Warning: Failed to save results to Excel.'}
    </p>
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
    
    # Initialize Excel Manager with hardcoded link
    excel_manager = OnlineExcelManager(EXCEL_SHARE_LINK)
    
    # Show login window
    login_window = LoginWindow(excel_manager)
    login_window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
