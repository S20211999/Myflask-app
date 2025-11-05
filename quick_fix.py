
import sys
import openpyxl
from openpyxl import Workbook, load_workbook
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QRadioButton, QButtonGroup, QMessageBox, QGroupBox,
                             QTextEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class ExcelManager:
    def __init__(self, filename='exam_data.xlsx'):
        self.filename = filename
        self.init_excel()
    
    def init_excel(self):
        """Initialize Excel file with required sheets"""
        try:
            self.wb = load_workbook(self.filename)
        except FileNotFoundError:
            self.wb = Workbook()
            self.create_initial_structure()
            self.wb.save(self.filename)
    
    def create_initial_structure(self):
        """Create initial sheets and sample data"""
        # Students Sheet
        if 'Students' in self.wb.sheetnames:
            del self.wb['Students']
        students_sheet = self.wb.create_sheet('Students')
        students_sheet.append(['Username', 'Password', 'Group', 'Name'])
        students_sheet.append(['student1', 'pass123', 'A', 'John Doe'])
        students_sheet.append(['student2', 'pass456', 'B', 'Jane Smith'])
        students_sheet.append(['student3', 'pass789', 'C', 'Bob Johnson'])
        
        # Schedule Sheet
        if 'Schedule' in self.wb.sheetnames:
            del self.wb['Schedule']
        schedule_sheet = self.wb.create_sheet('Schedule')
        schedule_sheet.append(['Group', 'Start_Time', 'End_Time', 'Date'])
        schedule_sheet.append(['A', '09:00', '10:00', '2025-11-05'])
        schedule_sheet.append(['B', '11:00', '12:00', '2025-11-05'])
        schedule_sheet.append(['C', '14:00', '15:00', '2025-11-05'])
        
        # Questions Sheet
        if 'Questions' in self.wb.sheetnames:
            del self.wb['Questions']
        questions_sheet = self.wb.create_sheet('Questions')
        questions_sheet.append(['Group', 'Question', 'Option_A', 'Option_B', 'Option_C', 'Option_D', 'Correct_Answer'])
        
        # Group A Questions
        questions_sheet.append(['A', 'What is Python?', 'A programming language', 'A snake', 'A software', 'A game', 'A'])
        questions_sheet.append(['A', 'What is PyQt6?', 'Database', 'GUI Framework', 'Web Framework', 'Testing Tool', 'B'])
        questions_sheet.append(['A', 'What is Excel?', 'Programming Language', 'Spreadsheet Software', 'Database', 'IDE', 'B'])
        
        # Group B Questions
        questions_sheet.append(['B', 'What is HTML?', 'Programming Language', 'Markup Language', 'Database', 'Framework', 'B'])
        questions_sheet.append(['B', 'What is CSS?', 'Programming Language', 'Style Sheet Language', 'Database', 'Framework', 'B'])
        questions_sheet.append(['B', 'What is JavaScript?', 'Markup Language', 'Programming Language', 'Database', 'Style Sheet', 'B'])
        
        # Group C Questions
        questions_sheet.append(['C', 'What is SQL?', 'Programming Language', 'Query Language', 'Markup Language', 'Framework', 'B'])
        questions_sheet.append(['C', 'What is MySQL?', 'Programming Language', 'Database System', 'Framework', 'IDE', 'B'])
        questions_sheet.append(['C', 'What is MongoDB?', 'SQL Database', 'NoSQL Database', 'Framework', 'IDE', 'B'])
        
        # Results Sheet
        if 'Results' in self.wb.sheetnames:
            del self.wb['Results']
        results_sheet = self.wb.create_sheet('Results')
        results_sheet.append(['Username', 'Name', 'Group', 'Score', 'Total_Questions', 'Percentage', 'Timestamp'])
        
        if 'Sheet' in self.wb.sheetnames:
            del self.wb['Sheet']
    
    def authenticate_student(self, username, password):
        """Authenticate student and return student data"""
        self.wb = load_workbook(self.filename)
        students_sheet = self.wb['Students']
        
        for row in students_sheet.iter_rows(min_row=2, values_only=True):
            if row[0] == username and row[1] == password:
                return {'username': row[0], 'group': row[2], 'name': row[3]}
        return None
    
    def check_schedule(self, group):
        """Check if current time is within scheduled exam time"""
        self.wb = load_workbook(self.filename)
        schedule_sheet = self.wb['Schedule']
        
        current_time = datetime.now()
        current_date_str = current_time.strftime('%Y-%m-%d')
        current_time_str = current_time.strftime('%H:%M')
        
        for row in schedule_sheet.iter_rows(min_row=2, values_only=True):
            if row[0] == group:
                exam_date = row[3]
                start_time = row[1]
                end_time = row[2]
                
                # Convert to datetime objects for comparison
                exam_datetime_start = datetime.strptime(f"{exam_date} {start_time}", '%Y-%m-%d %H:%M')
                exam_datetime_end = datetime.strptime(f"{exam_date} {end_time}", '%Y-%m-%d %H:%M')
                
                if exam_datetime_start <= current_time <= exam_datetime_end:
                    return True, ""
                else:
                    return False, f"Exam scheduled for {exam_date} from {start_time} to {end_time}"
        
        return False, "No schedule found for your group"
    
    def get_questions(self, group):
        """Get questions for specific group"""
        self.wb = load_workbook(self.filename)
        questions_sheet = self.wb['Questions']
        questions = []
        
        for row in questions_sheet.iter_rows(min_row=2, values_only=True):
            if row[0] == group:
                questions.append({
                    'question': row[1],
                    'options': {'A': row[2], 'B': row[3], 'C': row[4], 'D': row[5]},
                    'correct': row[6]
                })
        
        return questions
    
    def save_result(self, username, name, group, score, total, timestamp):
        """Save exam result to Excel"""
        self.wb = load_workbook(self.filename)
        results_sheet = self.wb['Results']
        
        percentage = (score / total * 100) if total > 0 else 0
        results_sheet.append([username, name, group, score, total, f"{percentage:.2f}%", timestamp])
        
        self.wb.save(self.filename)


class LoginWindow(QWidget):
    def __init__(self, excel_manager):
        super().__init__()
        self.excel_manager = excel_manager
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Student Login - Online Exam System')
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel('Online Examination System')
        title.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Username
        username_label = QLabel('Username:')
        username_label.setFont(QFont('Arial', 12))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Enter your username')
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel('Password:')
        password_label.setFont(QFont('Arial', 12))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText('Enter your password')
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        
        # Login Button
        self.login_btn = QPushButton('Login')
        self.login_btn.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        # Status Label
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet('color: red;')
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText('Please enter both username and password')
            return
        
        # Authenticate
        student_data = self.excel_manager.authenticate_student(username, password)
        
        if student_data:
            # Check schedule
            is_scheduled, message = self.excel_manager.check_schedule(student_data['group'])
            
            if is_scheduled:
                self.open_exam_window(student_data)
            else:
                QMessageBox.warning(self, 'Schedule Error', 
                                  f'You cannot login at this time.\n{message}')
        else:
            self.status_label.setText('Invalid username or password')
    
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
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        student_info = QLabel(f"Student: {self.student_data['name']} | Group: {self.student_data['group']}")
        student_info.setFont(QFont('Arial', 12))
        header_layout.addWidget(student_info)
        
        self.timer_label = QLabel('Time Remaining: --:--')
        self.timer_label.setFont(QFont('Arial', 12, QFont.Weight.Bold))
        self.timer_label.setStyleSheet('color: #d32f2f;')
        header_layout.addWidget(self.timer_label)
        main_layout.addLayout(header_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.questions))
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        # Question Area
        self.question_group = QGroupBox()
        question_layout = QVBoxLayout()
        
        self.question_label = QLabel()
        self.question_label.setFont(QFont('Arial', 14, QFont.Weight.Bold))
        self.question_label.setWordWrap(True)
        question_layout.addWidget(self.question_label)
        
        # Options
        self.option_group = QButtonGroup()
        self.option_buttons = []
        
        for option in ['A', 'B', 'C', 'D']:
            radio_btn = QRadioButton()
            radio_btn.setFont(QFont('Arial', 11))
            self.option_group.addButton(radio_btn)
            self.option_buttons.append(radio_btn)
            question_layout.addWidget(radio_btn)
        
        self.question_group.setLayout(question_layout)
        main_layout.addWidget(self.question_group)
        
        # Navigation Buttons
        button_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton('Previous')
        self.prev_btn.setFont(QFont('Arial', 11))
        self.prev_btn.clicked.connect(self.previous_question)
        self.prev_btn.setEnabled(False)
        button_layout.addWidget(self.prev_btn)
        
        button_layout.addStretch()
        
        self.next_btn = QPushButton('Next')
        self.next_btn.setFont(QFont('Arial', 11))
        self.next_btn.setStyleSheet('background-color: #2196F3; color: white; padding: 8px;')
        self.next_btn.clicked.connect(self.next_question)
        button_layout.addWidget(self.next_btn)
        
        self.submit_btn = QPushButton('Submit Exam')
        self.submit_btn.setFont(QFont('Arial', 11, QFont.Weight.Bold))
        self.submit_btn.setStyleSheet('background-color: #4CAF50; color: white; padding: 8px;')
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
        self.load_question()
    
    def load_question(self):
        if self.current_question < len(self.questions):
            question_data = self.questions[self.current_question]
            
            self.question_label.setText(f"Question {self.current_question + 1} of {len(self.questions)}: {question_data['question']}")
            
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
        self.timer_label.setText(f'Time Remaining: {minutes:02d}:{seconds:02d}')
        
        if self.time_remaining <= 0:
            self.timer.stop()
            QMessageBox.warning(self, 'Time Up', 'Time is up! Submitting your exam.')
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
        
        # Save results
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.excel_manager.save_result(
            self.student_data['username'],
            self.student_data['name'],
            self.student_data['group'],
            score,
            total_questions,
            timestamp
        )
        
        # Show results
        result_msg = f"""
        Exam Completed!
        
        Student: {self.student_data['name']}
        Group: {self.student_data['group']}
        
        Score: {score}/{total_questions}
        Percentage: {percentage:.2f}%
        
        Results saved to Excel file.
        """
        
        QMessageBox.information(self, 'Exam Results', result_msg)
        self.close()


def main():
    app = QApplication(sys.argv)
    
    # Apply global stylesheet
    app.setStyleSheet("""
        QWidget {
            font-family: Arial;
        }
        QGroupBox {
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            padding: 15px;
        }
    """)
    
    excel_manager = ExcelManager('exam_data.xlsx')
    login_window = LoginWindow(excel_manager)
    login_window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
