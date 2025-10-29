"""
Activity Tracker Client - Fixed Version
Features: Weekend toggle in list view, Always-on wizard, Fixed drag error
FIXES:
- Weekend override toggle moved to ActivityTrackerWindow list_page
- Removed from MonthViewDialog
- Toggle can change state before set time
- Always-on-display wizard showing today's activities
- Fixed drag_position AttributeError
"""
import os
import sys
import socket
import json
import struct
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem, 
                             QPushButton, QLabel, QLineEdit, QComboBox, 
                             QDialog, QMessageBox, QSystemTrayIcon, QMenu,
                             QDateEdit, QTimeEdit, QTextEdit, QHeaderView, 
                             QTabWidget, QGridLayout, QFrame, QStackedWidget, 
                             QGroupBox, QCheckBox, QScrollArea)
from PyQt6.QtCore import Qt, QTimer, QDate, QTime, QSize, QRect
from PyQt6.QtGui import (QIcon, QAction, QColor, QFont, QPixmap, QPainter, 
                         QPen, QBrush, QPainterPath)

from PyQt6.QtSvg import QSvgRenderer

import openpyxl
from openpyxl.styles import Font as ExcelFont, PatternFill, Alignment
from openpyxl.utils import get_column_letter

class ServerConnection:
    """Handle server communication with proper large response handling"""
    def __init__(self, host='10.60.2.252', port=5555):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def send_request(self, request):
        try:
            request_data = json.dumps(request).encode('utf-8')
            length = struct.pack('>I', len(request_data))
            self.socket.sendall(length)
            self.socket.sendall(request_data)
            
            length_data = b''
            while len(length_data) < 4:
                chunk = self.socket.recv(4 - len(length_data))
                if not chunk:
                    return {'success': False, 'error': 'Connection lost'}
                length_data += chunk
            
            response_length = struct.unpack('>I', length_data)[0]
            
            response_data = b''
            while len(response_data) < response_length:
                chunk = self.socket.recv(min(4096, response_length - len(response_data)))
                if not chunk:
                    return {'success': False, 'error': 'Connection lost'}
                response_data += chunk
            
            return json.loads(response_data.decode('utf-8'))
        except Exception as e:
            print(f"Request error: {e}")
            return {'success': False, 'error': str(e)}
    
    def close(self):
        if self.socket:
            self.socket.close()

class LoginDialog(QDialog):
    """Login dialog with auto-login support"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Activity Tracker - Login')
        self.setFixedSize(400, 320)
        self.user_data = None
        self.credentials_file = os.path.join(os.path.expanduser('~'), '.activity_tracker_creds')
        self.setStyleSheet('''
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                padding: 10px;
                border-radius: 8px;
                border: 2px solid rgba(255,255,255,0.3);
                background: rgba(255,255,255,0.9);
                font-size: 13px;
            }
            QPushButton {
                padding: 10px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
        ''')
        self.init_ui()
        self.load_saved_credentials()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        title = QLabel('📊 Activity Tracker')
        title.setStyleSheet('font-size: 24px; font-weight: bold; color: white;')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('Username')
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox('Remember me')
        self.remember_checkbox.setStyleSheet('color: white; font-size: 12px;')
        layout.addWidget(self.remember_checkbox)
        
        btn_layout = QHBoxLayout()
        login_btn = QPushButton('Login')
        login_btn.setStyleSheet('background-color: #4CAF50; color: white;')
        login_btn.clicked.connect(self.handle_login)
        
        cancel_btn = QPushButton('Cancel')
        cancel_btn.setStyleSheet('background-color: rgba(0,0,0,0.3); color: white;')
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(login_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.password_input.returnPressed.connect(self.handle_login)
    
    def save_credentials(self, username, password):
        """Save encrypted credentials to file"""
        try:
            # Simple encryption using base64 (for basic obfuscation)
            import base64
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            
            with open(self.credentials_file, 'w') as f:
                f.write(encoded)
            
            # Set file permissions (read/write for user only)
            if os.name != 'nt':  # Unix-like systems
                os.chmod(self.credentials_file, 0o600)
        except Exception as e:
            print(f"Failed to save credentials: {e}")
    
    def load_saved_credentials(self):
        """Load saved credentials and auto-login"""
        try:
            if os.path.exists(self.credentials_file):
                import base64
                with open(self.credentials_file, 'r') as f:
                    encoded = f.read().strip()
                
                decoded = base64.b64decode(encoded.encode()).decode()
                username, password = decoded.split(':', 1)
                
                self.username_input.setText(username)
                self.password_input.setText(password)
                self.remember_checkbox.setChecked(True)
                
                # Auto-login
                QTimer.singleShot(500, self.handle_login)
        except Exception as e:
            print(f"Failed to load credentials: {e}")
    
    def clear_saved_credentials(self):
        """Clear saved credentials"""
        try:
            if os.path.exists(self.credentials_file):
                os.remove(self.credentials_file)
        except Exception as e:
            print(f"Failed to clear credentials: {e}")
    
    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, 'Error', 'Please enter username and password')
            return
        
        conn = ServerConnection()
        if not conn.connect():
            QMessageBox.critical(self, 'Error', 'Cannot connect to server')
            return
        
        response = conn.send_request({
            'action': 'login',
            'username': username,
            'password': password
        })
        
        if response.get('success'):
            self.user_data = response['user']
            
            # Save credentials if remember me is checked
            if self.remember_checkbox.isChecked():
                self.save_credentials(username, password)
            else:
                self.clear_saved_credentials()
            
            self.accept()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Login failed'))
        
        conn.close()

class ToggleSwitch(QCheckBox):
    """Custom Toggle Switch Widget with proper event handling"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_animating = False
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background track
        if self.isChecked():
            painter.setBrush(QBrush(QColor('#4CAF50')))
        else:
            painter.setBrush(QBrush(QColor('#BDBDBD')))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 50, 24, 12, 12)
        
        # Circle thumb
        painter.setBrush(QBrush(QColor('white')))
        if self.isChecked():
            painter.drawEllipse(28, 2, 20, 20)
        else:
            painter.drawEllipse(2, 2, 20, 20)
    
    def mousePressEvent(self, event):
        """Handle mouse press to toggle state"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Prevent default behavior"""
        event.accept()

class CalendarDayWidget(QWidget):
    """Custom calendar day widget with rounded border and holiday/weekend support"""
    def __init__(self, day, is_today=False, parent=None):
        super().__init__(parent)
        self.day = day
        self.is_today = is_today
        self.is_complete = False
        self.has_activities = False
        self.total_activities = 0
        self.completed_activities = 0
        self.is_holiday = False
        self.is_weekend_off = False
        self.setMinimumSize(50, 50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def set_activity_status(self, total, completed):
        self.has_activities = total > 0
        self.total_activities = total
        self.completed_activities = completed
        self.is_complete = total > 0 and total == completed
        self.update()
    
    def set_holiday(self, is_holiday):
        self.is_holiday = is_holiday
        self.update()
    
    def set_weekend_off(self, is_off):
        self.is_weekend_off = is_off
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(5, 5, -5, -5)
        
        # Determine colors based on status
        if self.is_holiday:
            # Holiday - Yellow
            border_color = QColor('#FFC107')
            bg_color = QColor('#FFF9C4')
            painter.setBrush(QBrush(bg_color))
        elif self.is_weekend_off:
            # Weekend Off - Orange
            border_color = QColor('#FF9800')
            bg_color = QColor('#FFE0B2')
            painter.setBrush(QBrush(bg_color))
        elif self.has_activities:
            if self.is_complete:
                border_color = QColor("#337a2c")  # Green
                painter.setBrush(QBrush(QColor("#19a337")))
            else:
                border_color = QColor("#C80018")  # Red
                painter.setBrush(QBrush(QColor("#FF0000")))
        else:
            border_color = QColor('#E0E0E0')  # Gray
            painter.setBrush(Qt.BrushStyle.NoBrush)
        
        if self.is_today:
            border_color = QColor("#6100df")
        
        # Draw rounded rectangle
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 10, 10)
        
        # Draw day number
        if self.is_holiday or self.is_weekend_off:
            text_color = QColor("#666666")
        elif self.has_activities and not self.is_complete:
            text_color = QColor("#FFFFFF")
        elif self.is_complete:
            text_color = QColor("#FFFFFF")
        else:
            text_color = QColor("#666666") if self.day else QColor('#BDBDBD')
        
        painter.setPen(QPen(text_color))
        font = QFont('Segoe UI', 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.day) if self.day else '')

class AdminPanel(QDialog):
    """Admin panel with holiday configuration"""
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.all_users = []
        self.drag_position = None  # Initialize drag position
        self.setWindowTitle('Admin Panel')
        self.setFixedSize(1000, 600)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)        
        self.setStyleSheet('''
            QDialog {
                background: #f5f7fa;
            }
            QGroupBox {
                background: white;
                border-radius: 10px;
                padding: 15px;
                margin-top: 10px;
                font-weight: bold;
            }
            QLineEdit, QComboBox, QTimeEdit, QDateEdit {
                padding: 8px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
            }
            QPushButton {
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
            }
            QTableWidget {
                border: none;
                background: white;
                border-radius: 8px;
            }
        ''')
        self.init_ui()
        self.load_all_users()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet('''
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #667eea, stop:1 #764ba2);
            padding: 5px;
        ''')
        title_layout = QHBoxLayout(title_bar)

        title = QLabel('⚙️ Admin Panel')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
        title_layout.addWidget(title)
        title_layout.addStretch()

        close_btn = QPushButton('✕')
        close_btn.setStyleSheet('background: rgba(255,255,255,0.2); color: white; padding: 5px 10px;')
        close_btn.clicked.connect(self.accept)
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)
        
        tabs = QTabWidget()
        tabs.setStyleSheet('''
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: white;
                padding: 14px 24px;
                margin-right: 4px;
                border-radius: 8px 8px 0 0;
            }
            QTabBar::tab:selected {
                background: #637AB9;
                color: white;
            }
        ''')
        
        # User Management Tab
        user_tab = self.create_user_management_tab()
        tabs.addTab(user_tab, '👥 Users')
        
        # Hierarchy Tab
        hierarchy_tab = self.create_hierarchy_tab()
        tabs.addTab(hierarchy_tab, '🏢 Hierarchy')
        
        # Default Activities Tab
        default_tab = self.create_default_activities_tab()
        tabs.addTab(default_tab, '📋 Defaults')
        
        # Holiday Configuration Tab
        holiday_tab = self.create_holiday_tab()
        tabs.addTab(holiday_tab, '🎉 Holidays')
        
        layout.addWidget(tabs)
        self.setLayout(layout)
    
    def create_user_management_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        add_group = QGroupBox('Create New User')
        add_layout = QGridLayout()
        
        add_layout.addWidget(QLabel('Username:'), 0, 0)
        self.new_username = QLineEdit()
        add_layout.addWidget(self.new_username, 0, 1)
        
        add_layout.addWidget(QLabel('Password:'), 0, 2)
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        add_layout.addWidget(self.new_password, 0, 3)
        
        add_layout.addWidget(QLabel('Full Name:'), 1, 0)
        self.new_fullname = QLineEdit()
        add_layout.addWidget(self.new_fullname, 1, 1)
        
        add_layout.addWidget(QLabel('Role:'), 1, 2)
        self.new_role = QComboBox()
        self.new_role.addItems(['employee', 'manager', 'admin'])
        add_layout.addWidget(self.new_role, 1, 3)
        
        create_btn = QPushButton('➕ Create User')
        create_btn.setStyleSheet('background-color: #637AB9; color: white;')
        create_btn.clicked.connect(self.create_user)
        add_layout.addWidget(create_btn, 2, 0, 1, 4)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        list_group = QGroupBox('Existing Users')
        list_layout = QVBoxLayout()
        
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(['Username', 'Full Name', 'Role', 'Reports To', 'Actions'])
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        list_layout.addWidget(self.user_table)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        return widget
    
    def create_hierarchy_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel('Configure reporting relationships')
        info.setStyleSheet('color: #666; padding: 10px; background: #E3F2FD; border-radius: 5px;')
        layout.addWidget(info)
        
        form_group = QGroupBox('Reporting Structure')
        form_layout = QVBoxLayout()
        
        emp_layout = QHBoxLayout()
        emp_layout.addWidget(QLabel('Employee:'))
        self.employee_combo = QComboBox()
        emp_layout.addWidget(self.employee_combo, 1)
        form_layout.addLayout(emp_layout)
        
        mgr_layout = QHBoxLayout()
        mgr_layout.addWidget(QLabel('Reports To:'))
        self.manager_combo = QComboBox()
        mgr_layout.addWidget(self.manager_combo, 1)
        form_layout.addLayout(mgr_layout)
        
        update_btn = QPushButton('🔄 Update Relationship')
        update_btn.setStyleSheet('background-color: #637AB9; color: white;')
        update_btn.clicked.connect(self.update_hierarchy)
        form_layout.addWidget(update_btn)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        tree_group = QGroupBox('Current Hierarchy')
        tree_layout = QVBoxLayout()
        
        self.hierarchy_tree = QTextEdit()
        self.hierarchy_tree.setReadOnly(True)
        self.hierarchy_tree.setStyleSheet('background: #f9f9f9; font-family: monospace; border: none;')
        tree_layout.addWidget(self.hierarchy_tree)
        
        tree_group.setLayout(tree_layout)
        layout.addWidget(tree_group)
        
        return widget
    
    def create_default_activities_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel('Set default daily activities for all users')
        info.setStyleSheet('color: #666; padding: 10px; background: #FFF3E0; border-radius: 5px;')
        layout.addWidget(info)
        
        add_group = QGroupBox('Add Default Activity')
        add_layout = QGridLayout()
        
        add_layout.addWidget(QLabel('Title:'), 0, 0)
        self.default_title = QLineEdit()
        add_layout.addWidget(self.default_title, 0, 1, 1, 2)
        
        add_layout.addWidget(QLabel('Time:'), 1, 0)
        self.default_time = QTimeEdit()
        self.default_time.setDisplayFormat('HH:mm')
        self.default_time.setTime(QTime(9, 0))
        add_layout.addWidget(self.default_time, 1, 1)
        
        add_layout.addWidget(QLabel('Frequency:'), 1, 2)
        self.default_frequency = QComboBox()
        self.default_frequency.addItems(['daily', 'weekly', 'monthly'])
        add_layout.addWidget(self.default_frequency, 1, 3)
        
        add_btn = QPushButton('➕ Add Activity')
        add_btn.setStyleSheet('background-color: #637AB9; color: white;')
        add_btn.clicked.connect(self.add_default_activity)
        add_layout.addWidget(add_btn, 2, 0, 1, 4)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        list_group = QGroupBox('Current Defaults')
        list_layout = QVBoxLayout()
        
        self.default_table = QTableWidget()
        self.default_table.setColumnCount(4)
        self.default_table.setHorizontalHeaderLabels(['Activity', 'Time', 'Frequency', 'Actions'])
        header = self.default_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        list_layout.addWidget(self.default_table)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        return widget
    
    def create_holiday_tab(self):
        """Holiday configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info = QLabel('🎉 Configure holidays - holidays will appear in YELLOW on calendar')
        info.setStyleSheet('color: #666; padding: 10px; background: #FFF9C4; border-radius: 5px;')
        layout.addWidget(info)
        
        add_group = QGroupBox('Add Holiday')
        add_layout = QGridLayout()
        
        add_layout.addWidget(QLabel('Holiday Name:'), 0, 0)
        self.holiday_name = QLineEdit()
        self.holiday_name.setPlaceholderText('e.g., Christmas Day')
        add_layout.addWidget(self.holiday_name, 0, 1, 1, 2)
        
        add_layout.addWidget(QLabel('Date:'), 1, 0)
        self.holiday_date = QDateEdit()
        self.holiday_date.setCalendarPopup(True)
        self.holiday_date.setDate(QDate.currentDate())
        add_layout.addWidget(self.holiday_date, 1, 1)
        
        add_btn = QPushButton('➕ Add Holiday')
        add_btn.setStyleSheet('background-color: #FFC107; color: white;')
        add_btn.clicked.connect(self.add_holiday)
        add_layout.addWidget(add_btn, 1, 2)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        list_group = QGroupBox('Configured Holidays')
        list_layout = QVBoxLayout()
        
        self.holiday_table = QTableWidget()
        self.holiday_table.setColumnCount(3)
        self.holiday_table.setHorizontalHeaderLabels(['Date', 'Holiday Name', 'Actions'])
        header = self.holiday_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        list_layout.addWidget(self.holiday_table)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        return widget
    
    def load_all_users(self):
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({'action': 'get_all_users'})
        conn.close()
        
        if response.get('success'):
            self.all_users = response.get('users', [])
            self.populate_user_table()
            self.populate_hierarchy_combos()
            self.update_hierarchy_tree()
            self.load_default_activities()
            self.load_holidays()
    
    def populate_user_table(self):
        self.user_table.setRowCount(len(self.all_users))
        
        for row, user in enumerate(self.all_users):
            self.user_table.setItem(row, 0, QTableWidgetItem(user['username']))
            self.user_table.setItem(row, 1, QTableWidgetItem(user['full_name']))
            
            role_item = QTableWidgetItem(user['role'].upper())
            if user['role'] == 'admin':
                role_item.setBackground(QColor('#2196F3'))
                role_item.setForeground(QColor('white'))
            elif user['role'] == 'manager':
                role_item.setBackground(QColor('#4CAF50'))
                role_item.setForeground(QColor('white'))
            self.user_table.setItem(row, 2, role_item)
            
            self.user_table.setItem(row, 3, QTableWidgetItem(user.get('manager_name', 'None')))
            
            if user['username'] != 'admin':
                delete_btn = QPushButton('🗑️')
                delete_btn.setStyleSheet('background-color: #f44336; color: white;')
                delete_btn.clicked.connect(lambda checked, uid=user['id']: self.delete_user(uid))
                self.user_table.setCellWidget(row, 4, delete_btn)
    
    def populate_hierarchy_combos(self):
        self.employee_combo.clear()
        self.manager_combo.clear()
        self.manager_combo.addItem('None', None)
        
        for user in self.all_users:
            self.employee_combo.addItem(f"{user['full_name']} ({user['username']})", user['id'])
            if user['role'] in ['manager', 'admin']:
                self.manager_combo.addItem(f"{user['full_name']} ({user['username']})", user['id'])
    
    def update_hierarchy_tree(self):
        tree_text = "Organization Hierarchy:\n\n"
        root_users = [u for u in self.all_users if u.get('manager_id') is None]
        
        def add_tree(user, level=0):
            indent = "  " * level
            icon = "👤" if user['role'] == 'employee' else "👔" if user['role'] == 'manager' else "⭐"
            text = f"{indent}{icon} {user['full_name']} - {user['role']}\n"
            subordinates = [u for u in self.all_users if u.get('manager_id') == user['id']]
            for sub in subordinates:
                text += add_tree(sub, level + 1)
            return text
        
        for root in root_users:
            tree_text += add_tree(root)
        
        self.hierarchy_tree.setText(tree_text)
    
    def create_user(self):
        username = self.new_username.text().strip()
        password = self.new_password.text()
        fullname = self.new_fullname.text().strip()
        role = self.new_role.currentText()
        
        if not username or not password or not fullname:
            QMessageBox.warning(self, 'Error', 'Please fill all fields')
            return
        
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'add_user',
            'data': {'username': username, 'password': password, 'full_name': fullname, 'role': role}
        })
        conn.close()
        
        if response.get('success'):
            QMessageBox.information(self, 'Success', 'User created')
            self.new_username.clear()
            self.new_password.clear()
            self.new_fullname.clear()
            self.load_all_users()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed'))
    
    def delete_user(self, user_id):
        reply = QMessageBox.question(self, 'Confirm', 'Delete this user?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = ServerConnection()
            if conn.connect():
                response = conn.send_request({'action': 'delete_user', 'user_id': user_id})
                conn.close()
                if response.get('success'):
                    self.load_all_users()
    
    def update_hierarchy(self):
        employee_id = self.employee_combo.currentData()
        manager_id = self.manager_combo.currentData()
        
        if not employee_id or employee_id == manager_id:
            QMessageBox.warning(self, 'Error', 'Invalid selection')
            return
        
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({
                'action': 'update_hierarchy',
                'employee_id': employee_id,
                'manager_id': manager_id
            })
            conn.close()
            if response.get('success'):
                QMessageBox.information(self, 'Success', 'Hierarchy updated')
                self.load_all_users()                
    
    def add_default_activity(self):
        title = self.default_title.text().strip()
        if not title:
            return
        
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({
                'action': 'add_default_activity',
                'data': {
                    'title': title,
                    'time': self.default_time.time().toString('HH:mm'),
                    'frequency': self.default_frequency.currentText(),
                    'created_by': self.user_data['id']
                }
            })
            conn.close()
            if response.get('success'):
                self.default_title.clear()
                self.load_default_activities()
    
    def load_default_activities(self):
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({'action': 'get_default_activities'})
            conn.close()
            if response.get('success'):
                activities = response.get('activities', [])
                self.default_table.setRowCount(len(activities))
                for row, act in enumerate(activities):
                    self.default_table.setItem(row, 0, QTableWidgetItem(act['title']))
                    self.default_table.setItem(row, 1, QTableWidgetItem(act['time']))
                    self.default_table.setItem(row, 2, QTableWidgetItem(act['frequency']))
                    
                    del_btn = QPushButton('🗑️')
                    del_btn.setStyleSheet('background-color: #f44336; color: white;')
                    del_btn.clicked.connect(lambda checked, aid=act['id']: self.delete_default(aid))
                    self.default_table.setCellWidget(row, 3, del_btn)
    
    def delete_default(self, activity_id):
        """Delete default activity template"""
        # Simple confirmation dialog
        reply = QMessageBox.question(
            self, 
            'Delete Default Activity', 
            'Are you sure you want to delete this default activity template?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({
                'action': 'delete_default_activity', 
                'activity_id': activity_id,
                'delete_generated': True  # Only delete template, keep generated activities
            })
            conn.close()
            
            if response.get('success'):
                self.load_default_activities()
                QMessageBox.information(self, 'Success', 'Default activity template deleted')
            else:
                QMessageBox.warning(self, 'Error', response.get('error', 'Failed to delete'))
    
    def add_holiday(self):
        """Add holiday"""
        name = self.holiday_name.text().strip()
        if not name:
            QMessageBox.warning(self, 'Error', 'Please enter holiday name')
            return
        
        date = self.holiday_date.date().toString('yyyy-MM-dd')
        
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({
                'action': 'add_holiday',
                'data': {'name': name, 'date': date}
            })
            conn.close()
            if response.get('success'):
                self.holiday_name.clear()
                self.load_holidays()
                QMessageBox.information(self, 'Success', 'Holiday added')
    
    def load_holidays(self):
        """Load holidays"""
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({'action': 'get_holidays'})
            conn.close()
            if response.get('success'):
                holidays = response.get('holidays', [])
                self.holiday_table.setRowCount(len(holidays))
                for row, holiday in enumerate(holidays):
                    self.holiday_table.setItem(row, 0, QTableWidgetItem(holiday['date']))
                    self.holiday_table.setItem(row, 1, QTableWidgetItem(holiday['name']))
                    
                    del_btn = QPushButton('🗑️')
                    del_btn.setStyleSheet('background-color: #f44336; color: white;')
                    del_btn.clicked.connect(lambda checked, hid=holiday['id']: self.delete_holiday(hid))
                    self.holiday_table.setCellWidget(row, 2, del_btn)
    
    def delete_holiday(self, holiday_id):
        """Delete holiday"""
        conn = ServerConnection()
        if conn.connect():
            conn.send_request({'action': 'delete_holiday', 'holiday_id': holiday_id})
            conn.close()
            self.load_holidays()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()            

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)

class AlwaysOnWizard(QWidget):
    """Always-on display wizard - permanent wallpaper widget at bottom-right corner"""
    def __init__(self, user_id, user_data, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.user_data = user_data
        
        # Window flags for wallpaper-like behavior
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnBottomHint |  # Behind all windows
            Qt.WindowType.Tool |  # Don't show in taskbar
            Qt.WindowType.X11BypassWindowManagerHint  # Bypass window manager (Linux)
        )
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Allow mouse interaction
        
        self.setFixedSize(380, 320)
        
        self.setStyleSheet('''
            QWidget {
                background: transparent;
            }
            QLabel {
                color: rgba(255, 255, 255, 200);
            }
            QTableWidget {
                background: rgba(0, 0, 0, 100);
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 8px;
                color: white;
                font-size: 14px; font-weight: bold;
            }
            QHeaderView::section {
                background: transparent;
                color: white;
                padding: 5px;
                border: none;
                font-size: 14px; font-weight: bold;
                           
            }
            QTableWidget::item {
                padding: 5px;
            }
            QScrollBar:vertical {
                background: rgba(30, 30, 30, 150);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 100, 100, 200);
                border-radius: 4px;
            }                           
        ''')
        
        self.init_ui()
        self.load_today_activities()
        
        # Position permanently at bottom-right
        self.position_to_bottom_right()
        
        # Monitor screen changes
        screen = QApplication.primaryScreen()
        screen.geometryChanged.connect(self.position_to_bottom_right)
        
        # Auto-refresh every 5 minutes
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_today_activities)
        self.refresh_timer.start(1800)  # 5 minutes
        
        # Keep on bottom timer (ensures it stays as wallpaper)
        self.wallpaper_timer = QTimer()
        self.wallpaper_timer.timeout.connect(self.maintain_wallpaper_position)
        self.wallpaper_timer.start(2000)  # Every 2 seconds
    
    def position_to_bottom_right(self):
        """Position widget permanently at bottom-right corner"""
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - 15
        y = 15
        self.move(x, y)
    
    def maintain_wallpaper_position(self):
        """Maintain wallpaper position and z-order"""
        # Ensure it's at bottom-right
        self.position_to_bottom_right()
        
        # Ensure it stays on bottom
        self.lower()
        
        # Keep window flags consistent
        if not (self.windowFlags() & Qt.WindowType.WindowStaysOnBottomHint):
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnBottomHint |
                Qt.WindowType.Tool |
                Qt.WindowType.X11BypassWindowManagerHint
            )
            self.show()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Semi-transparent background container
        container = QFrame()
        container.setStyleSheet('''
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(30, 30, 30, 200), 
                    stop:1 rgba(0, 0, 0, 200));
                border-radius: 15px;
                border: 2px solid rgba(255, 247, 0, 60);
            }
        ''')

        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)
        
        # Title with drag handle indicator
        title_layout = QHBoxLayout()
        drag_icon = QLabel('📅')
        drag_icon.setStyleSheet('font-size: 20px; color: rgba(255, 255, 255, 150);')
        title_layout.addWidget(drag_icon)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet('font-size: 16px; font-weight: bold; color: white;')
        title_layout.addWidget(self.date_label)
        title_layout.addStretch()
        
        container_layout.addLayout(title_layout)
        

        
        
        # Activities table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Activity', 'Time', 'Status'])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        container_layout.addWidget(self.table)
        

        layout.addWidget(container)
    
    def load_today_activities(self):
        """Load today's activities"""
        today = datetime.now()
        self.date_label.setText(today.strftime('%a, %b %d, %Y'))
        
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'get_activities',
            'user_id': self.user_id,
            'date': today.strftime('%Y-%m-%d')
        })
        conn.close()
        
        if not response.get('success'):
            return
        
        activities = response.get('activities', [])
        
        # Populate table
        self.table.setRowCount(len(activities))
        
        for row, act in enumerate(activities):
            # Activity
            title_item = QTableWidgetItem(act['title'])
            title_item.setForeground(QColor(255, 255, 255, 220))
            if act['status'] == 'complete':
                font = title_item.font()
                font.setStrikeOut(True)
                title_item.setFont(font)
                title_item.setForeground(QColor(160, 160, 160, 180))
            self.table.setItem(row, 0, title_item)
            
            # Time
            time_item = QTableWidgetItem(act['time'])
            time_item.setForeground(QColor(200, 200, 200, 200))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, time_item)
            
            # Status
            status_item = QTableWidgetItem(act['status'].upper())
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if act['status'] == 'complete':
                status_item.setBackground(QColor(76, 175, 80, 180))
                status_item.setForeground(QColor('white'))
            else:
                status_item.setBackground(QColor(244, 67, 54, 180))
                status_item.setForeground(QColor('white'))
            self.table.setItem(row, 2, status_item)
        
        # Adjust row heights
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 32)
    
    def closeEvent(self, event):
        """Prevent closing, hide instead"""
        event.ignore()
        self.hide()
    
    def showEvent(self, event):
        """Ensure proper position on show"""
        super().showEvent(event)
        self.position_to_bottom_right()
        self.lower()


class MonthViewDialog(QDialog):
    """Dialog to show full month activities with calendar, day, and detail views"""
    def __init__(self, user_id, user_data, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.user_data = user_data
        self.current_date = datetime.now()
        self.selected_date = datetime.now()
        self.activities = []
        self.activities_by_date = {}
        self.subordinates = []
        self.selected_user_id = user_id
        self.holidays = []
        self.weekend_overrides = {}
        self.drag_position = None  # Initialize drag position
        self.setWindowTitle('Monthly Activity View')
        self.setFixedSize(1000, 600)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)        
        self.init_ui()
        self.load_subordinates()
        self.load_holidays()
        self.load_month_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet('''
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #667eea, stop:1 #764ba2);
            padding: 5px;
        ''')
        title_layout = QHBoxLayout(title_bar)

        title = QLabel('📅 Sienna Calendar Month')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
        title_layout.addWidget(title)
        title_layout.addStretch()

        close_btn = QPushButton('✕')
        close_btn.setStyleSheet('background: rgba(255,255,255,0.2); color: white; padding: 5px 10px;')
        close_btn.clicked.connect(self.accept)
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        # Top bar with navigation
        top_bar = QHBoxLayout()
        
        prev_btn = QPushButton('< Previous')
        prev_btn.clicked.connect(self.previous_month)
        
        self.month_label = QLabel()
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setStyleSheet('font-size: 18px; font-weight: bold;')
        
        next_btn = QPushButton('Next >')
        next_btn.clicked.connect(self.next_month)
        
        top_bar.addWidget(prev_btn)
        top_bar.addWidget(self.month_label, 1)
        
        # User selector (for managers)
        if self.user_data['role'] in ['manager', 'admin']:
            user_label = QLabel('View For:')
            user_label.setStyleSheet('font-weight: bold;')
            top_bar.addWidget(user_label)
            
            self.user_selector = QComboBox()
            self.user_selector.setMinimumWidth(200)
            self.user_selector.setStyleSheet('padding: 5px;')
            self.user_selector.currentIndexChanged.connect(self.on_user_changed)
            top_bar.addWidget(self.user_selector)
        
        top_bar.addWidget(next_btn)
        layout.addLayout(top_bar)
        
        # Stacked widget for views
        self.stacked_widget = QStackedWidget()
        
        # Detail view (table)
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            'Date', 'Activity', 'Time', 'Status', 
            'Completed At', 'Action'
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        detail_layout.addWidget(self.table)
        self.stacked_widget.addWidget(detail_widget)
        
        layout.addWidget(self.stacked_widget)
        
        # Statistics
        stats_layout = QHBoxLayout()
        self.total_label = QLabel()
        self.total_label.setStyleSheet('font-weight: bold; padding: 5px;')
        self.completed_label = QLabel()
        self.completed_label.setStyleSheet('color: #4CAF50; font-weight: bold; padding: 5px;')
        self.pending_label = QLabel()
        self.pending_label.setStyleSheet('color: #f44336; font-weight: bold; padding: 5px;')
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(self.pending_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        export_btn = QPushButton('📥 Export to Excel')
        export_btn.clicked.connect(self.export_to_excel)
        export_btn.setStyleSheet('background-color: #637AB9; color: white; padding: 10px; font-weight: bold; border-radius: 5px;')
        
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_holidays(self):
        """Load holidays from server"""
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({'action': 'get_holidays'})
            conn.close()
            if response.get('success'):
                self.holidays = response.get('holidays', [])
    
    def is_date_holiday(self, date_str):
        """Check if date is a holiday"""
        return any(h['date'] == date_str for h in self.holidays)
    
    def is_weekend(self, date_obj):
        """Check if date is weekend (Saturday=5, Sunday=6)"""
        return date_obj.weekday() in [5, 6]
    
    def is_working_day_override(self, date_str):
        """Check if weekend has been marked as working day"""
        return self.weekend_overrides.get(date_str, False)
    
    def load_subordinates(self):
        """Load subordinates if user is manager"""
        if self.user_data['role'] not in ['manager', 'admin']:
            return
        
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'get_hierarchy',
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.subordinates = response.get('users', [])
            
            if hasattr(self, 'user_selector'):
                self.user_selector.clear()
                self.user_selector.addItem(f"👤 {self.user_data['full_name']} (Me)", self.user_data['id'])
                
                for sub in self.subordinates:
                    self.user_selector.addItem(f"👤 {sub['full_name']}", sub['id'])
    
    def on_user_changed(self, index):
        """Handle user selection change"""
        if hasattr(self, 'user_selector'):
            self.selected_user_id = self.user_selector.currentData()
            self.load_month_data()
    
    def can_user_complete_activity(self, activity):
        """Check if current user can complete this activity based on complex rules"""
        activity_time = activity['time']
        due_date = activity['due_date']
        assigned_to = activity.get('assigned_to', self.user_data['id'])
        
        try:
            activity_datetime_str = f"{due_date} {activity_time}"
            activity_datetime = datetime.strptime(activity_datetime_str, '%Y-%m-%d %H:%M')
            now = datetime.now()
            is_time_passed = now > activity_datetime
            
            if self.user_data['role'] == 'admin':
                return True
            elif self.user_data['role'] == 'manager':
                if assigned_to == self.user_data['id']:
                    return not is_time_passed
                else:
                    return True
            else:
                return not is_time_passed
                
        except ValueError:
            return True
    
    def mark_complete_month_view(self, activity_id):
        """Mark activity as complete from month view"""
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'update_activity',
            'activity_id': activity_id,
            'status': 'complete',
            'user_role': self.user_data['role'],
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.load_month_data()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed to update activity'))
    
    def previous_month(self):
        """Go to previous month"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.load_month_data()
    
    def next_month(self):
        """Go to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.load_month_data()
    
    def load_month_data(self):
        """Load activities for current month"""
        user_name = self.user_data['full_name'] if self.selected_user_id == self.user_data['id'] else next((s['full_name'] for s in self.subordinates if s['id'] == self.selected_user_id), '')
        self.month_label.setText(f"{self.current_date.strftime('%B %Y')} - {user_name}")
        
        conn = ServerConnection()
        if not conn.connect():
            QMessageBox.critical(self, 'Error', 'Cannot connect to server')
            return
        
        # Get weekend overrides
        override_response = conn.send_request({
            'action': 'get_working_day_overrides',
            'year': self.current_date.year,
            'month': self.current_date.month
        })
        
        if override_response.get('success'):
            overrides = override_response.get('overrides', [])
            self.weekend_overrides = {o['date']: o['is_working'] for o in overrides}
        
        # Get month activities
        response = conn.send_request({
            'action': 'get_month_activities',
            'user_id': self.selected_user_id,
            'year': self.current_date.year,
            'month': self.current_date.month
        })
        
        conn.close()
        
        if response.get('success'):
            self.activities = response['activities']
            self.organize_activities_by_date()
            self.populate_table()
            self.update_statistics()
        else:
            QMessageBox.warning(self, 'Error', 'Failed to load activities')
    
    def organize_activities_by_date(self):
        """Organize activities by date"""
        self.activities_by_date = {}
        for activity in self.activities:
            date = activity['due_date']
            if date not in self.activities_by_date:
                self.activities_by_date[date] = []
            self.activities_by_date[date].append(activity)
    
    def populate_table(self):
        """Populate detail table grouped by date with toggle switches for completion"""
        activities_by_date = {}
        for act in self.activities:
            date = act['due_date']
            if date not in activities_by_date:
                activities_by_date[date] = []
            activities_by_date[date].append(act)

        # Count total rows
        total_rows = sum(len(acts) + 2 for acts in activities_by_date.values())
        self.table.setRowCount(total_rows)

        self.table.setHorizontalHeaderLabels([
            'Date', 'Activity', 'Time', 'Status',
            'Completed At', 'Action'
        ])

        row = 0
        for date, acts in sorted(activities_by_date.items()):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            
            # Determine date background color
            date_bg_color = QColor('#C8E6C9')  # Default green
            if self.is_date_holiday(date):
                date_bg_color = QColor('#FFF9C4')  # Yellow for holidays
            elif self.is_weekend(date_obj) and not self.is_working_day_override(date):
                date_bg_color = QColor('#FFE0B2')  # Orange for weekend off
            
            # Date header row
            date_item = QTableWidgetItem(date)
            date_item.setBackground(date_bg_color)
            date_item.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, date_item)
            self.table.setSpan(row, 0, 1, self.table.columnCount())
            row += 1

            # Activity rows
            for act in acts:
                self.table.setItem(row, 0, QTableWidgetItem(''))
                self.table.setItem(row, 1, QTableWidgetItem(act['title']))
                self.table.setItem(row, 2, QTableWidgetItem(act['time']))

                # Status styling
                status_item = QTableWidgetItem(act['status'].upper())
                if act['status'] == 'complete':
                    status_item.setBackground(QColor('#4CAF50'))
                    status_item.setForeground(QColor('white'))
                else:
                    status_item.setBackground(QColor('#f44336'))
                    status_item.setForeground(QColor('white'))
                self.table.setItem(row, 3, status_item)

                # Completed At
                completed = act.get('completed_at', '')
                if completed:
                    try:
                        completed = datetime.fromisoformat(completed).strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        pass
                self.table.setItem(row, 4, QTableWidgetItem(completed))

                # Action - Toggle Switch
                if act['status'] == 'pending':
                    can_complete = self.can_user_complete_activity(act)
                    
                    toggle_widget = QWidget()
                    toggle_layout = QHBoxLayout(toggle_widget)
                    toggle_layout.setContentsMargins(5, 0, 5, 0)
                    
                    toggle = ToggleSwitch()
                    toggle.setChecked(False)
                    
                    if can_complete:
                        toggle.setEnabled(True)
                        toggle.stateChanged.connect(lambda state, aid=act['id']: self.mark_complete_month_view(aid) if state else None)
                    else:
                        toggle.setEnabled(False)
                        toggle.setToolTip('Time has passed - only manager can complete')
                    
                    toggle_layout.addWidget(toggle)
                    toggle_layout.addStretch()
                    self.table.setCellWidget(row, 5, toggle_widget)
                else:
                    toggle_widget = QWidget()
                    toggle_layout = QHBoxLayout(toggle_widget)
                    toggle_layout.setContentsMargins(5, 0, 5, 0)
                    
                    toggle = ToggleSwitch()
                    toggle.setChecked(True)
                    toggle.setEnabled(False)
                    
                    toggle_layout.addWidget(toggle)
                    toggle_layout.addStretch()
                    self.table.setCellWidget(row, 5, toggle_widget)
                
                row += 1

            # Blank row separator
            for col in range(self.table.columnCount()):
                blank_item = QTableWidgetItem('')
                blank_item.setBackground(QColor('#F9F9F9'))
                self.table.setItem(row, col, blank_item)
            row += 1

        # Resize columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.table.verticalHeader().setVisible(False)

    def update_statistics(self):
        """Update statistics labels - count working days instead of activities"""
        # Get unique dates from activities
        unique_dates = set(a['due_date'] for a in self.activities)
        
        total_working_days = 0
        completed_days = 0
        pending_days = 0
        
        for date_str in unique_dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Skip if holiday
            if self.is_date_holiday(date_str):
                continue
            
            # Skip if weekend and not marked as working day
            if self.is_weekend(date_obj) and not self.is_working_day_override(date_str):
                continue
            
            # This is a working day
            total_working_days += 1
            
            # Get activities for this date
            day_activities = [a for a in self.activities if a['due_date'] == date_str]
            
            # Check if all activities are completed
            if day_activities:
                all_completed = all(a['status'] == 'complete' for a in day_activities)
                if all_completed:
                    completed_days += 1
                else:
                    pending_days += 1
        
        # Update labels
        self.total_label.setText(f'📊 Working Days: {total_working_days}')
        self.completed_label.setText(f'✅ Completed: {completed_days}')
        self.pending_label.setText(f'⏳ Pending: {pending_days}')
    
    def export_to_excel(self):
        """Export data to Excel file grouped by date"""
        if not self.activities:
            QMessageBox.information(self, 'Info', 'No activities to export')
            return

        try:

            # Get Downloads folder path
            downloads_path = str(Path.home() / "Downloads") 

            wb = openpyxl.Workbook()
            ws = wb.active

            user_name = (
                self.user_data['full_name']
                if self.selected_user_id == self.user_data['id']
                else next((s['full_name'] for s in self.subordinates if s['id'] == self.selected_user_id), 'User')
            )
            ws.title = self.current_date.strftime('%B %Y')

            # Title
            ws.merge_cells('A1:G1')
            title_cell = ws['A1']
            title_cell.value = f"Activity Report - {user_name} - {self.current_date.strftime('%B %Y')}"
            title_cell.font = ExcelFont(size=14, bold=True, color='FFFFFF')
            title_cell.fill = PatternFill(start_color='2196F3', end_color='2196F3', fill_type='solid')
            title_cell.alignment = Alignment(horizontal='center', vertical='center')

            header_fill = PatternFill(start_color='4CAF50', end_color='4CAF50', fill_type='solid')
            header_font = ExcelFont(bold=True, color='FFFFFF')

            activities_by_date = {}
            for activity in self.activities:
                date = activity['due_date']
                if date not in activities_by_date:
                    activities_by_date[date] = []
                activities_by_date[date].append(activity)

            current_row = 3

            for date, activities in sorted(activities_by_date.items()):
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                
                # Determine background color
                if self.is_date_holiday(date):
                    date_color = 'FFF9C4'  # Yellow
                elif self.is_weekend(date_obj) and not self.is_working_day_override(date):
                    date_color = 'FFE0B2'  # Orange
                else:
                    date_color = 'C8E6C9'  # Green
                
                ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
                date_cell = ws.cell(row=current_row, column=1, value=date)
                date_cell.font = ExcelFont(bold=True, size=12, color='000000')
                date_cell.fill = PatternFill(start_color=date_color, end_color=date_color, fill_type='solid')
                date_cell.alignment = Alignment(horizontal='left', vertical='center')
                current_row += 1

                headers = ['Activity', 'Description', 'Time', 'Frequency', 'Status', 'Completed At', 'Assigned By']
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=current_row, column=col, value=header)
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center')
                current_row += 1

                for act in activities:
                    ws.cell(row=current_row, column=1, value=act['title'])
                    ws.cell(row=current_row, column=2, value=act.get('description', ''))
                    ws.cell(row=current_row, column=3, value=act['time'])
                    ws.cell(row=current_row, column=4, value=act['frequency'])
                    
                    status_cell = ws.cell(row=current_row, column=5, value=act['status'].upper())
                    if act['status'] == 'complete':
                        status_cell.fill = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
                    else:
                        status_cell.fill = PatternFill(start_color='FFE0B2', end_color='FFE0B2', fill_type='solid')

                    completed = act.get('completed_at', '')
                    if completed:
                        try:
                            completed = datetime.fromisoformat(completed).strftime('%Y-%m-%d %H:%M')
                        except Exception:
                            pass
                    ws.cell(row=current_row, column=6, value=completed)
                    ws.cell(row=current_row, column=7, value=act.get('assigner_name', ''))
                    current_row += 1

                current_row += 1

            # Auto-adjust column widths
            for i, col_cells in enumerate(ws.columns, 1):
                max_length = 0
                for cell in col_cells:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                ws.column_dimensions[get_column_letter(i)].width = min(max_length + 2, 50)

            # ✅ Always save to Downloads folder
            filename = f"Activities_{user_name.replace(' ', '_')}_{self.current_date.strftime('%B_%Y')}.xlsx"
            file_path = os.path.join(downloads_path, filename)

            wb.save(file_path)            
            QMessageBox.information(self, 'Success', f'Activities exported to {filename}')

        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to export: {str(e)}')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)

class ActivityTrackerWindow(QMainWindow):
    """Modern Calendar View with subordinate dropdown, wizard, and weekend toggle"""
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.current_date = datetime.now()
        self.selected_date = datetime.now()
        self.calendar_widgets = []
        self.month_activities = {}
        self.holidays = []
        self.weekend_overrides = {}
        self.subordinates = []
        self.selected_user_id = user_data['id']
        self.drag_position = None  # Initialize drag position
        
        self.setWindowTitle('Activity Tracker')
        self.setFixedSize(400, 500)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self.setStyleSheet('''
            QMainWindow {
                background: white;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QTableWidget {
                border: none;
                background: white;
            }
            QComboBox {
                padding: 5px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                background: white;
            }
        ''')
        
        self.init_ui()
        self.load_holidays()
        self.load_subordinates()
        self.load_month_activities()
        # Create always-on wizard
        self.always_on_wizard = AlwaysOnWizard(self.user_data['id'], self.user_data)
        self.always_on_wizard.show()
        
        self.refresh_timer1 = QTimer()
        self.refresh_timer1.timeout.connect(self.load_subordinates)
        self.refresh_timer1.start(30000)  # Refresh subordinates every 30 seconds
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_month_activities)
        self.refresh_timer.start(2000)


        
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Title bar
        title_bar = QFrame()
        title_bar.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2); padding: 2px;')
        title_layout = QHBoxLayout(title_bar)
        
        title = QLabel('📅 Sienna Calendar')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: white;')
        title_layout.addWidget(title)
        title_layout.addStretch()



        month_btn = QPushButton('📅')
        month_btn.clicked.connect(self.show_month_view)
        month_btn.setStyleSheet('background: rgba(255,255,255,0.2); color: white; padding: 5px 10px;')
        title_layout.addWidget(month_btn)
        
        if self.user_data['role'] == 'admin':
            admin_btn = QPushButton('⚙️')
            admin_btn.setStyleSheet('background: rgba(255,255,255,0.2); color: white; padding: 5px 10px;')
            admin_btn.clicked.connect(self.open_admin)
            title_layout.addWidget(admin_btn)
        
        close_btn = QPushButton('✕')
        close_btn.setStyleSheet('background: rgba(255,255,255,0.2); color: white; padding: 5px 10px;')
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # Stacked widget for views
        self.stacked = QStackedWidget()
        
        # Calendar view
        calendar_page = self.create_calendar_view()
        self.stacked.addWidget(calendar_page)
        
        # Activity list view
        list_page = self.create_list_view()
        self.stacked.addWidget(list_page)
        
        layout.addWidget(self.stacked)
        
    def create_calendar_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Subordinate dropdown for managers/admins
        if self.user_data['role'] in ['manager', 'admin']:
            self.user_selector = QComboBox()
            self.user_selector.setMinimumWidth(200)
            self.user_selector.setStyleSheet('''
                QComboBox {
                    background: rgba(255,255,255,0.9);
                    color: #333;
                    padding: 1px;
                    border-radius: 5px;
                }
            ''')
            self.user_selector.currentIndexChanged.connect(self.on_user_changed)
            layout.addWidget(self.user_selector)
        
        # Month header
        header_layout = QHBoxLayout()
        
        prev_btn = QPushButton('◀')
        prev_btn.setStyleSheet('background: #f5f5f5; color: #666;')
        prev_btn.clicked.connect(self.prev_month)
        header_layout.addWidget(prev_btn)
        
        self.month_label = QLabel()
        self.month_label.setStyleSheet('font-size: 20px; font-weight: bold; color: #333;')
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.month_label, 1)
        
        next_btn = QPushButton('▶')
        next_btn.setStyleSheet('background: #f5f5f5; color: #666;')
        next_btn.clicked.connect(self.next_month)
        header_layout.addWidget(next_btn)
        
        layout.addLayout(header_layout)
        
        # Day headers
        days_layout = QHBoxLayout()
        for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
            lbl = QLabel(day)
            lbl.setStyleSheet('font-weight: bold; color: #666; font-size: 12px;')
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            days_layout.addWidget(lbl)
        layout.addLayout(days_layout)
        
        # Calendar grid
        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(8)
        
        for row in range(6):
            for col in range(7):
                day_widget = CalendarDayWidget(0)
                day_widget.mousePressEvent = lambda e, r=row, c=col: self.on_day_click(r, c)
                self.calendar_widgets.append(day_widget)
                self.calendar_grid.addWidget(day_widget, row, col)
        
        layout.addLayout(self.calendar_grid)
        layout.addStretch()
        
        return widget
    
    def create_list_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton('◀ Back')
        back_btn.setStyleSheet('background: #f5f5f5; color: #666;')
        back_btn.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        header_layout.addWidget(back_btn)
        
        self.date_label = QLabel()
        self.date_label.setStyleSheet('font-size: 18px; font-weight: bold; color: #333;')
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.date_label, 1)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Weekend override section (for managers/admins) - ONLY VISIBLE FOR WEEKENDS
        if self.user_data['role'] in ['manager', 'admin']:
            self.override_frame = QFrame()
            self.override_frame.setStyleSheet('background: #FFF3E0; padding: 10px; border-radius: 5px;')
            override_layout = QHBoxLayout(self.override_frame)
            
            override_label = QLabel('🔄 Mark as working day:')
            override_label.setStyleSheet('font-weight: bold; color: #FF6F00;')
            override_layout.addWidget(override_label)
            
            self.working_day_toggle = ToggleSwitch()
            self.working_day_toggle.stateChanged.connect(self.toggle_working_day)
            override_layout.addWidget(self.working_day_toggle)
            
            self.override_status_label = QLabel()
            self.override_status_label.setStyleSheet('color: #666;')
            override_layout.addWidget(self.override_status_label)
            override_layout.addStretch()
            
            layout.addWidget(self.override_frame)
            self.override_frame.setVisible(False)  # Hidden by default
        
        # Activity table
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels(['Activity', 'Time', 'Status', 'Action'])
        self.activity_table.verticalHeader().setVisible(False)
        
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.activity_table.setStyleSheet('''
            QTableWidget {
                border-radius: 8px;
                background: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        ''')
        
        layout.addWidget(self.activity_table)
        
        return widget    

    def mark_complete_from_wizard(self, activity_id, wizard_dialog):
        """Mark activity complete from wizard"""
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'update_activity',
            'activity_id': activity_id,
            'status': 'complete',
            'user_role': self.user_data['role'],
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.load_month_activities()
            wizard_dialog.accept()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed to update activity'))
    
    def toggle_working_day(self, state):
        """Toggle working day status for selected date"""
        date_str = self.selected_date.strftime('%Y-%m-%d')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Double-check it's a weekend (safety check)
        if not self.is_weekend(date_obj):
            QMessageBox.information(self, 'Info', 'Selected date is not a weekend (Saturday/Sunday)')
            self.working_day_toggle.blockSignals(True)
            self.working_day_toggle.setChecked(False)
            self.working_day_toggle.blockSignals(False)
            return
        
        is_working = self.working_day_toggle.isChecked()
        
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({
                'action': 'set_working_day_override',
                'date': date_str,
                'is_working': is_working,
                'user_id': self.user_data['id']
            })
            conn.close()
            if response.get('success'):
                self.weekend_overrides[date_str] = is_working
                self.load_month_activities()
                
                # Update status label
                day_name = date_obj.strftime('%A')
                status = "Working Day ✓" if is_working else "Off Day"
                self.override_status_label.setText(f'{day_name}, {date_str} - Currently: {status}')
                
                # Show confirmation
                msg = f"✓ {day_name} marked as {status}"
                QMessageBox.information(self, 'Updated', msg)
            else:
                QMessageBox.warning(self, 'Error', 'Failed to update weekend override')
                # Revert toggle state
                self.working_day_toggle.blockSignals(True)
                self.working_day_toggle.setChecked(not is_working)
                self.working_day_toggle.blockSignals(False)
        
    def update_working_day_toggle(self):
        """Update toggle state based on selected date - ONLY SHOW FOR WEEKENDS"""
        if self.user_data['role'] not in ['manager', 'admin']:
            return
        
        if not hasattr(self, 'working_day_toggle'):
            return
        
        date_str = self.selected_date.strftime('%Y-%m-%d')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Check if selected date is weekend (Saturday=5, Sunday=6)
        if self.is_weekend(date_obj):
            # Show the override frame
            self.override_frame.setVisible(True)
            
            self.working_day_toggle.setEnabled(True)
            is_working = self.is_working_day_override(date_str)
            self.working_day_toggle.blockSignals(True)  # Prevent triggering stateChanged
            self.working_day_toggle.setChecked(is_working)
            self.working_day_toggle.blockSignals(False)
            
            day_name = date_obj.strftime('%A')  # Get day name (Saturday/Sunday)
            status = "Currently: Working Day ✓" if is_working else "Currently: Off Day"
            self.override_status_label.setText(f'{day_name}, {date_str} - {status}')
        else:
            # Hide the override frame for non-weekend days
            self.override_frame.setVisible(False)
    
    def load_holidays(self):
        """Load holidays from server"""
        conn = ServerConnection()
        if conn.connect():
            response = conn.send_request({'action': 'get_holidays'})
            conn.close()
            if response.get('success'):
                self.holidays = response.get('holidays', [])
    
    def is_date_holiday(self, date_str):
        """Check if date is a holiday"""
        return any(h['date'] == date_str for h in self.holidays)
    
    def is_weekend(self, date_obj):
        """Check if date is weekend"""
        return date_obj.weekday() in [5, 6]
    
    def is_working_day_override(self, date_str):
        """Check if weekend has been marked as working day"""
        return self.weekend_overrides.get(date_str, False)
    
    def load_subordinates(self):
        """Load subordinates if user is manager"""
        if self.user_data['role'] not in ['manager', 'admin']:
            return
        
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'get_hierarchy',
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.subordinates = response.get('users', [])
            
            if hasattr(self, 'user_selector'):
                self.user_selector.clear()
                self.user_selector.addItem(f"👤 {self.user_data['full_name']} (Me)", self.user_data['id'])
                
                for sub in self.subordinates:
                    self.user_selector.addItem(f"👤 {sub['full_name']}", sub['id'])
    
    def on_user_changed(self, index):
        """Handle user selection change"""
        if hasattr(self, 'user_selector'):
            self.selected_user_id = self.user_selector.currentData()
            self.load_month_activities()
    
    def show_month_view(self):
        """Show month view dialog"""
        dialog = MonthViewDialog(self.selected_user_id, self.user_data, self)
        dialog.exec()
        self.load_month_activities()

    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.load_month_activities()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.load_month_activities()
    
    def load_month_activities(self):
        conn = ServerConnection()
        if not conn.connect():
            return
        
        # Get weekend overrides
        override_response = conn.send_request({
            'action': 'get_working_day_overrides',
            'year': self.current_date.year,
            'month': self.current_date.month
        })
        
        if override_response.get('success'):
            overrides = override_response.get('overrides', [])
            self.weekend_overrides = {o['date']: o['is_working'] for o in overrides}
        
        response = conn.send_request({
            'action': 'get_month_activities',
            'user_id': self.selected_user_id,
            'year': self.current_date.year,
            'month': self.current_date.month
        })
        
        conn.close()
        
        if response.get('success'):
            activities = response['activities']
            
            # Organize by date
            self.month_activities = {}
            for act in activities:
                date = act['due_date']
                if date not in self.month_activities:
                    self.month_activities[date] = []
                self.month_activities[date].append(act)
            
            self.populate_calendar()
    
    def populate_calendar(self):
        self.month_label.setText(self.current_date.strftime('%B %Y'))
        
        first_day = self.current_date.replace(day=1)
        first_weekday = first_day.weekday()
        
        if self.current_date.month == 12:
            next_month = self.current_date.replace(year=self.current_date.year+1, month=1, day=1)
        else:
            next_month = self.current_date.replace(month=self.current_date.month+1, day=1)
        days_in_month = (next_month - first_day).days
        
        current_day = 1
        today = datetime.now().date()
        
        for idx, widget in enumerate(self.calendar_widgets):
            if idx < first_weekday or current_day > days_in_month:
                widget.day = 0
                widget.set_activity_status(0, 0)
                widget.set_holiday(False)
                widget.set_weekend_off(False)
            else:
                date = self.current_date.replace(day=current_day)
                widget.day = current_day
                widget.is_today = date.date() == today
                
                date_str = date.strftime('%Y-%m-%d')
                
                # Check if holiday
                is_holiday = self.is_date_holiday(date_str)
                widget.set_holiday(is_holiday)
                
                # Check if weekend off (not overridden as working day)
                is_weekend_off = self.is_weekend(date) and not self.is_working_day_override(date_str)
                widget.set_weekend_off(is_weekend_off)
                
                if date_str in self.month_activities:
                    activities = self.month_activities[date_str]
                    total = len(activities)
                    completed = sum(1 for a in activities if a['status'] == 'complete')
                    widget.set_activity_status(total, completed)
                else:
                    widget.set_activity_status(0, 0)
                
                current_day += 1
    
    def on_day_click(self, row, col):
        idx = row * 7 + col
        widget = self.calendar_widgets[idx]
        
        if widget.day > 0:
            self.selected_date = self.current_date.replace(day=widget.day)
            self.show_activities_for_date()
    
    def show_activities_for_date(self):
        self.date_label.setText(self.selected_date.strftime('%A, %B %d, %Y'))
        
        date_str = self.selected_date.strftime('%Y-%m-%d')
        activities = self.month_activities.get(date_str, [])
        
        # Update weekend override toggle if applicable
        if self.user_data['role'] in ['manager', 'admin']:
            self.update_working_day_toggle()
        
        self.activity_table.setRowCount(len(activities))
        
        for row, act in enumerate(activities):
            # Activity title
            title_item = QTableWidgetItem(act['title'])
            if act['status'] == 'complete':
                font = title_item.font()
                font.setStrikeOut(True)
                title_item.setFont(font)
                title_item.setForeground(QColor('#999'))
            self.activity_table.setItem(row, 0, title_item)
            
            # Time
            self.activity_table.setItem(row, 1, QTableWidgetItem(act['time']))
            
            # Status
            status_item = QTableWidgetItem(act['status'].upper())
            if act['status'] == 'complete':
                status_item.setBackground(QColor('#4CAF50'))
                status_item.setForeground(QColor('white'))
            else:
                status_item.setBackground(QColor('#f44336'))
                status_item.setForeground(QColor('white'))
            self.activity_table.setItem(row, 2, status_item)
            
            # Action - Toggle Switch (ALWAYS ENABLED before set time)
            if act['status'] == 'pending':
                toggle_widget = QWidget()
                toggle_layout = QHBoxLayout(toggle_widget)
                toggle_layout.setContentsMargins(5, 0, 5, 0)
                
                toggle = ToggleSwitch()
                toggle.setChecked(False)
                
                # Check if time has passed
                activity_time = act['time']
                due_date = act['due_date']
                time_passed = False
                
                try:
                    activity_datetime_str = f"{due_date} {activity_time}"
                    activity_datetime = datetime.strptime(activity_datetime_str, '%Y-%m-%d %H:%M')
                    now = datetime.now()
                    time_passed = now > activity_datetime
                except ValueError:
                    pass
                
                # ALWAYS enabled if time hasn't passed, managers can always toggle
                if not time_passed or self.user_data['role'] in ['manager', 'admin']:
                    toggle.setEnabled(True)
                    toggle.stateChanged.connect(lambda state, aid=act['id']: self.mark_complete(aid) if state else None)
                else:
                    toggle.setEnabled(False)
                    toggle.setToolTip('Time has passed - contact your manager')
                
                toggle_layout.addWidget(toggle)
                toggle_layout.addStretch()
                self.activity_table.setCellWidget(row, 3, toggle_widget)
            else:
                # Completed - show checked toggle (can be unchecked by managers/admins)
                toggle_widget = QWidget()
                toggle_layout = QHBoxLayout(toggle_widget)
                toggle_layout.setContentsMargins(5, 0, 5, 0)
                
                toggle = ToggleSwitch()
                toggle.setChecked(True)
                
                # Allow managers/admins to uncheck
                if self.user_data['role'] in ['manager', 'admin']:
                    toggle.setEnabled(True)
                    toggle.stateChanged.connect(lambda state, aid=act['id']: self.mark_pending(aid) if not state else None)
                else:
                    toggle.setEnabled(False)
                
                toggle_layout.addWidget(toggle)
                toggle_layout.addStretch()
                self.activity_table.setCellWidget(row, 3, toggle_widget)
        
        self.stacked.setCurrentIndex(1)
    
    def can_user_complete_activity(self, activity):
        """Check if current user can complete this activity"""
        activity_time = activity['time']
        due_date = activity['due_date']
        assigned_to = self.selected_user_id
        
        try:
            activity_datetime_str = f"{due_date} {activity_time}"
            activity_datetime = datetime.strptime(activity_datetime_str, '%Y-%m-%d %H:%M')
            now = datetime.now()
            is_time_passed = now > activity_datetime
            
            if self.user_data['role'] == 'admin':
                return True
            elif self.user_data['role'] == 'manager':
                if assigned_to == self.user_data['id']:
                    return not is_time_passed
                else:
                    return True
            else:
                return not is_time_passed
                
        except ValueError:
            return True
    
    def mark_complete(self, activity_id):
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'update_activity',
            'activity_id': activity_id,
            'status': 'complete',
            'user_role': self.user_data['role'],
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.load_month_activities()
            self.show_activities_for_date()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed to update activity'))
    
    def mark_pending(self, activity_id):
        """Mark activity as pending (managers/admins only)"""
        conn = ServerConnection()
        if not conn.connect():
            return
        
        response = conn.send_request({
            'action': 'update_activity',
            'activity_id': activity_id,
            'status': 'pending',
            'user_role': self.user_data['role'],
            'user_id': self.user_data['id']
        })
        
        conn.close()
        
        if response.get('success'):
            self.load_month_activities()
            self.show_activities_for_date()
        else:
            QMessageBox.warning(self, 'Error', response.get('error', 'Failed to update activity'))
    
    def open_admin(self):
        dialog = AdminPanel(self.user_data, self)
        dialog.exec()
        self.load_holidays()
        self.load_month_activities()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)

class SystemTray:
    """System tray functionality with SVG icon from file"""
    def __init__(self, app, main_window):
        self.app = app
        self.main_window = main_window
        
        self.tray_icon = QSystemTrayIcon(self.load_svg_icon(), app)
        self.menu = QMenu()
        
        self.show_action = QAction("Show / Hide")
        self.wizard_action = QAction("Today's Activities 🧙")
        self.quit_action = QAction("Quit")
        
        self.menu.addAction(self.show_action)
        self.menu.addAction(self.wizard_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.setToolTip("Activity Tracker")
        self.tray_icon.show()
        
        self.show_action.triggered.connect(self.toggle_window)
        self.wizard_action.triggered.connect(self.show_wizard)
        self.quit_action.triggered.connect(self.quit_app)
        self.tray_icon.activated.connect(self.on_tray_activated)
    
    def load_svg_icon(self):
        """Load icon from SVG file"""
        try:
            
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            svg_path = os.path.join(script_dir, 'icon.svg')
            
            # Check if file exists
            if not os.path.exists(svg_path):
                print(f"Warning: icon.svg not found at {svg_path}")
                return self.create_fallback_icon()
            
            # Create pixmap from SVG file
            pixmap = QPixmap(128, 128)
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            
            # Load and render SVG from file
            renderer = QSvgRenderer(svg_path)
            renderer.render(painter)
            
            painter.end()
            
            return QIcon(pixmap)
        
        except Exception as e:
            print(f"Error loading SVG icon: {e}")
            return self.create_fallback_icon()
    
    def create_fallback_icon(self):
        """Create a simple fallback icon if SVG loading fails"""
        pixmap = QPixmap(128, 128)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Simple purple calendar
        painter.setBrush(QBrush(QColor('#9575CD')))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(16, 24, 96, 80, 12, 12)
        
        # White body
        painter.setBrush(QBrush(QColor('white')))
        painter.drawRoundedRect(16, 40, 96, 64, 8, 8)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def toggle_window(self):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.activateWindow()
    
    def show_wizard(self):
        """Show today's activities wizard from tray"""
        if hasattr(self.main_window, 'always_on_wizard'):
            self.main_window.always_on_wizard.load_today_activities()
            self.main_window.always_on_wizard.raise_()
            self.main_window.always_on_wizard.show()
    
    def quit_app(self):
        self.tray_icon.hide()
        if hasattr(self.main_window, 'always_on_wizard'):
            self.main_window.always_on_wizard.close()
        self.app.quit()
    
    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()



def main():
    def setup_auto_start():
        """Setup application to auto-start on boot"""
        app_name = "ActivityTracker"
        script_path = os.path.abspath(__file__)
        
        if sys.platform == 'win32':
            # Windows: Add to startup folder
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                
                # Create command with pythonw to hide console
                python_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                
                command = f'"{python_exe}" "{script_path}"'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
                winreg.CloseKey(key)
                print("✓ Auto-start enabled (Windows Registry)")
                return True
            except Exception as e:
                print(f"Failed to setup auto-start: {e}")
                return False
        
        elif sys.platform == 'darwin':
            # macOS: Create launch agent
            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>Label</key>
        <string>com.activitytracker.app</string>
        <key>ProgramArguments</key>
        <array>
            <string>{sys.executable}</string>
            <string>{script_path}</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <false/>
    </dict>
    </plist>'''
            
            launch_agents_dir = os.path.expanduser('~/Library/LaunchAgents')
            plist_path = os.path.join(launch_agents_dir, 'com.activitytracker.app.plist')
            
            try:
                os.makedirs(launch_agents_dir, exist_ok=True)
                with open(plist_path, 'w') as f:
                    f.write(plist_content)
                print("✓ Auto-start enabled (macOS LaunchAgent)")
                return True
            except Exception as e:
                print(f"Failed to setup auto-start: {e}")
                return False
        
        elif sys.platform.startswith('linux'):
            # Linux: Create .desktop file in autostart
            desktop_content = f'''[Desktop Entry]
    Type=Application
    Name=Activity Tracker
    Exec={sys.executable} {script_path}
    Hidden=false
    NoDisplay=false
    X-GNOME-Autostart-enabled=true
    '''
            
            autostart_dir = os.path.expanduser('~/.config/autostart')
            desktop_path = os.path.join(autostart_dir, 'activity-tracker.desktop')
            
            try:
                os.makedirs(autostart_dir, exist_ok=True)
                with open(desktop_path, 'w') as f:
                    f.write(desktop_content)
                os.chmod(desktop_path, 0o755)
                print("✓ Auto-start enabled (Linux .desktop)")
                return True
            except Exception as e:
                print(f"Failed to setup auto-start: {e}")
                return False
        
        return False

    def remove_auto_start():
        """Remove auto-start configuration"""
        app_name = "ActivityTracker"
        
        if sys.platform == 'win32':
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
                print("✓ Auto-start disabled")
                return True
            except Exception as e:
                print(f"Failed to remove auto-start: {e}")
                return False
        
        elif sys.platform == 'darwin':
            plist_path = os.path.expanduser('~/Library/LaunchAgents/com.activitytracker.app.plist')
            try:
                if os.path.exists(plist_path):
                    os.remove(plist_path)
                print("✓ Auto-start disabled")
                return True
            except Exception as e:
                print(f"Failed to remove auto-start: {e}")
                return False
        
        elif sys.platform.startswith('linux'):
            desktop_path = os.path.expanduser('~/.config/autostart/activity-tracker.desktop')
            try:
                if os.path.exists(desktop_path):
                    os.remove(desktop_path)
                print("✓ Auto-start disabled")
                return True
            except Exception as e:
                print(f"Failed to remove auto-start: {e}")
                return False
        
        return False
    # Check if --setup-autostart argument is passed
    if '--setup-autostart' in sys.argv:
        setup_auto_start()
    
    # Check if --remove-autostart argument is passed
    if '--remove-autostart' in sys.argv:
        remove_auto_start()
        return
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Attempt auto-start setup (silent, won't show error to user)
    setup_auto_start()
    
    login = LoginDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        main_window = ActivityTrackerWindow(login.user_data)
        tray = SystemTray(app, main_window)
        main_window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
