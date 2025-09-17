
I'll help you modify both applications to integrate them. Here's the complete solution:

## 1. Modified PySide6 Application

First, let's update the main PySide6 application to remove database functionality and add Flask integration:

```python
# --- CRITICAL FIX: SET QT_API ---
# This line MUST be at the very top, before any other imports.
import os
os.environ['QT_API'] = 'pyside6'
# --- END FIX ---

import sys
import qtawesome
import json
import requests
import struct
import math

from PySide6.QtCore import (Qt, QSize, Signal, QPoint, QTimer)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QGroupBox, QCheckBox,
    QPushButton, QStackedWidget, QLabel, QLineEdit, QGridLayout, QTabWidget,
    QFrame, QScrollArea, QSizePolicy, QFileDialog, QMessageBox, QFormLayout,
    QTextEdit, QButtonGroup, QDialog
)
from PySide6.QtGui import QPixmap, QIcon, QMouseEvent, QClipboard, QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget

# --- Constants ---
FLASK_BASE_URL = "http://localhost:5000"  # Configure your Flask server URL

# --- Login Dialog ---
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Username
        layout.addWidget(QLabel("Username:"))
        self.username_edit = QLineEdit()
        layout.addWidget(self.username_edit)
        
        # Password
        layout.addWidget(QLabel("Password:"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_edit)
        
        # Server URL
        layout.addWidget(QLabel("Server URL:"))
        self.server_edit = QLineEdit(FLASK_BASE_URL)
        layout.addWidget(self.server_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.cancel_button = QPushButton("Cancel")
        
        self.login_button.clicked.connect(self.attempt_login)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.auth_token = None
        self.user_info = None

    def attempt_login(self):
        username = self.username_edit.text()
        password = self.password_edit.text()
        server_url = self.server_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter username and password")
            return
        
        try:
            # Attempt login to Flask server
            response = requests.post(f"{server_url}/api/login", 
                                   json={"username": username, "password": password},
                                   timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.auth_token = data.get('token')
                    self.user_info = data.get('user')
                    global FLASK_BASE_URL
                    FLASK_BASE_URL = server_url
                    self.accept()
                else:
                    QMessageBox.warning(self, "Login Failed", data.get('message', 'Invalid credentials'))
            else:
                QMessageBox.warning(self, "Login Failed", "Invalid credentials")
                
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to server:\n{str(e)}")

# --- DEFINE THE CUSTOM WIDGET HERE ---
class ToggleSwitch(QCheckBox):
    """A custom toggle switch widget. Its appearance is defined in the stylesheet."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class ClickableLabel(QLabel):
    """A QLabel that emits signals for single and double clicks."""
    doubleClicked = Signal()
    singleClicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("class", "ClickableLabel")

    def mousePressEvent(self, event: QMouseEvent):
        self._mouse_press_pos = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._mouse_press_pos == event.pos() and event.button() == Qt.LeftButton:
            self.singleClicked.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.doubleClicked.emit()

# --- Generator Page Base Class ---
class BaseGeneratorPage(QWidget):
    """
    A base class that encapsulates generation AND data submission to Flask server.
    """
    generationFinalized = Signal(dict)
    
    def __init__(self, table_name, parent=None):
        super().__init__(parent)
        self.table_name = table_name
        self.parent_window = parent

        # Initialize paths for all 4 script types
        self.script_paths = {
            'altium': os.path.join(os.path.expanduser("~"), "altium_scripts"),
            'allegro': os.path.join(os.path.expanduser("~"), "allegro_scripts"),
            'pads': os.path.join(os.path.expanduser("~"), "pads_scripts"),
            'xpedition': os.path.join(os.path.expanduser("~"), "xpedition_scripts")
        }
        
        self.setObjectName("GeneratorPage")
        layout = QGridLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        
        self.title_label = QLabel()
        layout.addWidget(self.title_label, 0, 0)
        
        input_frame = QFrame()
        self.form_layout = QFormLayout(input_frame)
        self.form_layout.setSpacing(12)
        self.form_layout.setLabelAlignment(Qt.AlignRight)
        self.input_fields = {}
        layout.addWidget(input_frame, 0, 0)
        
        right_panel_layout = QVBoxLayout()
        self.image_label = QSvgWidget()
        self.image_label.setMinimumSize(250, 300)
        self.image_label.setStyleSheet("background-color: #232730; border-radius: 8px;")
        right_panel_layout.addWidget(self.image_label)
        layout.addLayout(right_panel_layout, 0, 1)
        layout.setColumnStretch(1, 1)
        
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Generate All Scripts")
        self.generate_button.setObjectName("GenerateButton")
        self.generate_button.setCursor(Qt.PointingHandCursor)
        self.generate_button.clicked.connect(self._on_generate_clicked)
        button_layout.addWidget(self.generate_button)
        button_layout.addStretch()
        layout.addLayout(button_layout, 2, 0, 1, 2)

    def _on_generate_clicked(self):
        """Generate scripts and submit data to Flask server"""
        data = self.collect_data()
        if not data.get("part_number") or not data.get("footprint_name"):
            QMessageBox.warning(self, "Input Error", "Part Number and Footprint Name are required.")
            return
        
        # Check authentication
        main_window = self.get_main_window()
        if not main_window or not main_window.auth_token:
            QMessageBox.warning(self, "Authentication Error", "Please login first from Settings > Account")
            return
        
        try:
            generated_files = []
            errors = []
            
            # Generate scripts for all 4 tools
            for script_type in ['altium', 'allegro', 'pads', 'xpedition']:
                try:
                    script_content, filename = self.generate_script_for_tool(data, script_type)
                    self._write_script_to_file(script_type, filename, script_content)
                    generated_files.append(f"{script_type.title()}: {filename}")
                except Exception as e:
                    errors.append(f"{script_type.title()}: {str(e)}")
            
            # Submit data to Flask server
            success = self._submit_to_flask_server(data)
            
            # Show results
            if generated_files:
                success_msg = "Successfully generated scripts:\n\n" + "\n".join(generated_files)
                if errors:
                    success_msg += f"\n\nErrors encountered:\n" + "\n".join(errors)
                if success:
                    success_msg += "\n\nData successfully saved to server."
                else:
                    success_msg += "\n\nWarning: Could not save data to server."
                QMessageBox.information(self, "Scripts Generated", success_msg)
                
                # Emit with table name
                self.generationFinalized.emit({"data": data, "table_name": self.table_name})
            else:
                QMessageBox.critical(self, "Generation Failed", "Failed to generate any scripts:\n\n" + "\n".join(errors))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during the process:\n\n{e}")

    def _submit_to_flask_server(self, data):
        """Submit footprint data to Flask server"""
        try:
            main_window = self.get_main_window()
            if not main_window:
                return False
                
            # Prepare data for submission
            submission_data = {
                "package_type": self.table_name,
                "part_number": data.get('part_number', ''),
                "footprint_name": data.get('footprint_name', ''),
                "specifications": data,
                "user_created": main_window.user_info.get('username', 'Unknown') if main_window.user_info else 'Unknown'
            }
            
            headers = {
                'Authorization': f'Bearer {main_window.auth_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{FLASK_BASE_URL}/api/footprint/add",
                json=submission_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('status') == 'success'
            else:
                print(f"Server error: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
            return False
        except Exception as e:
            print(f"Submission error: {e}")
            return False

    def get_main_window(self):
        """Get the main window instance"""
        widget = self
        while widget:
            if isinstance(widget, MainWindow):
                return widget
            widget = widget.parent()
        return None

    def _write_script_to_file(self, script_type, filename, script_content):
        """Write script file to the appropriate output path"""
        output_path = self.script_paths.get(script_type)
        if not output_path:
            raise ValueError(f"Output path for {script_type} has not been set.")
        
        os.makedirs(output_path, exist_ok=True)
        output_filepath = os.path.join(output_path, filename)
        with open(output_filepath, "w") as f:
            f.write(script_content)

    def generate_script_for_tool(self, data, tool_type):
        """Generate script for specific tool - must be implemented by subclasses"""
        raise NotImplementedError("Each generator page must implement generate_script_for_tool")

    def set_script_paths(self, paths_dict):
        """Update all script output paths"""
        self.script_paths.update(paths_dict)
        
    def set_output_path(self, path):
        """Legacy method for backward compatibility"""
        self.script_paths['altium'] = path

    def collect_data(self):
        return {k.replace(" ", "_").lower().replace("(mm)", "").strip(): v.text() for k, v in self.input_fields.items()}

# --- Specific Generator Page Implementations ---
class DiscreteN(BaseGeneratorPage):
    """Generator page for discrete normal packages"""
    
    def __init__(self, parent=None):
        super().__init__("DiscreteN", parent)
        self.input_fields = {
            "Part Number": QLineEdit(),
            "Footprint Name": QLineEdit(),
            "Body Length (mm)": QLineEdit(),
            "Body Width (mm)": QLineEdit(),
            "Body Height (mm)": QLineEdit(),
            "Pad Length (mm)": QLineEdit(),
            "Pad Width (mm)": QLineEdit(),
            "Mask Expansion (mm)": QLineEdit(),
            "Paste Expansion (mm)": QLineEdit(),
            "Airgap (mm)": QLineEdit(),
        }
        for label, field in self.input_fields.items():
            self.form_layout.addRow(label, field)
        
        self.image_label.load("generator_resistor_chip.svg")

    def generate_script_for_tool(self, data, tool_type):
        """Generate script for specific tool type"""
        if tool_type == 'altium':
            return self._generate_altium_script(data)
        elif tool_type == 'allegro':
            return self._generate_allegro_script(data)
        elif tool_type == 'pads':
            return self._generate_pads_script(data)
        elif tool_type == 'xpedition':
            return self._generate_xpedition_script(data)
        else:
            raise ValueError(f"Unsupported tool type: {tool_type}")

    def _generate_altium_script(self, data):
        """Generate Altium Designer script (Ultra Librarian format)"""
        try:
            part_number = data.get('part_number', '')
            footprint_name = data.get('footprint_name', '')
            body_l = float(data.get('body_length', 0))
            body_w = float(data.get('body_width', 0))
            pad_l = float(data.get('pad_length', 0))
            pad_w = float(data.get('pad_width', 0))
            mask_expansion = float(data.get('mask_expansion', 0))
            paste_expansion = float(data.get('paste_expansion', 0))
            airgap = float(data.get('airgap', 0))
        except (ValueError, TypeError):
            raise ValueError("All dimensions must be valid numbers.")

        def mm_to_ul(val):
            return round(val / 0.000254)

        pad_offset = (body_l - pad_l) / 2
        pad_x = mm_to_ul(pad_offset)
        pad_w_ul = mm_to_ul(pad_w)
        pad_l_ul = mm_to_ul(pad_l)

        script = f"""# Created by Footprint Generator - Altium Designer
# Part Number: {part_number}
# Footprint: {footprint_name}
StartFootprints
Footprint (Name "{footprint_name}")
Pad (Name "1") (Location -{pad_x}, 0) (Surface True) (Rotation 0) (ExpandMask 0) (ExpandPaste 0)
PadShape (Size {pad_w_ul}, {pad_l_ul}) (Shape Rectangular) (Layer Top)
EndPad
Pad (Name "2") (Location {pad_x}, 0) (Surface True) (Rotation 0) (ExpandMask 0) (ExpandPaste 0)
PadShape (Size {pad_w_ul}, {pad_l_ul}) (Shape Rectangular) (Layer Top)
EndPad
Text (Location -75, -25) (Height 50) (Width 3) (Rotation 0) (Layer TopOverlay) (Value "RefDes")
Step (Name {footprint_name}.step)
EndFootprint
EndFootprints
"""
        return script, f"{part_number}_altium.txt"

    def _generate_allegro_script(self, data):
        """Generate Cadence Allegro script"""
        part_number = data.get('part_number', '')
        footprint_name = data.get('footprint_name', '')
        
        script = f"""# Allegro PCB Editor Script
# Part Number: {part_number}
# Footprint: {footprint_name}

# Create footprint
create footprint {footprint_name}

# Add pads
shape add rect {data.get('pad_length', '0')} {data.get('pad_width', '0')}
pad add {data.get('body_length', '0')}/2 0 1 rect
pad add -{data.get('body_length', '0')}/2 0 2 rect

# Add assembly outline
line add assembly {data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2
line add assembly -{data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2

# Add reference designator
text add refdes 0 {data.get('body_width', '0')}/2+0.5 \\$REFDES

done
"""
        return script, f"{part_number}_allegro.scr"

    def _generate_pads_script(self, data):
        """Generate Mentor Graphics PADS script"""
        part_number = data.get('part_number', '')
        footprint_name = data.get('footprint_name', '')
        
        script = f"""! PADS PowerPCB Script
! Part Number: {part_number}
! Footprint: {footprint_name}

*PART*
{footprint_name}

*PAD*
P1 {data.get('pad_length', '0')} {data.get('pad_width', '0')} R 0 0 {data.get('body_length', '0')}/2 0
P2 {data.get('pad_length', '0')} {data.get('pad_width', '0')} R 0 0 -{data.get('body_length', '0')}/2 0

*LINE*
15 0 {data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2
15 0 -{data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2
15 0 -{data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2
15 0 {data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2
15 0 {data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2

*TEXT*
0 0 {data.get('body_width', '0')}/2+1 0 \\$REFDES

*END*
"""
        return script, f"{part_number}_pads.asc"

    def _generate_xpedition_script(self, data):
        """Generate Mentor Graphics Xpedition script"""
        part_number = data.get('part_number', '')
        footprint_name = data.get('footprint_name', '')
        
        script = f"""# Xpedition PCB Script
# Part Number: {part_number}
# Footprint: {footprint_name}

# Create new cell
cell new {footprint_name}

# Define pad stack
padstack new rect_{data.get('pad_length', '0')}x{data.get('pad_width', '0')}
layer TOP copper rectangle {data.get('pad_length', '0')} {data.get('pad_width', '0')}
padstack end

# Place pads
pin new 1 {data.get('body_length', '0')}/2 0 rect_{data.get('pad_length', '0')}x{data.get('pad_width', '0')}
pin new 2 -{data.get('body_length', '0')}/2 0 rect_{data.get('pad_length', '0')}x{data.get('pad_width', '0')}

# Add assembly outline
line new ASSEMBLY {data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2 -{data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2
line new ASSEMBLY -{data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2 -{data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2
line new ASSEMBLY -{data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2 {data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2
line new ASSEMBLY {data.get('body_length', '0')}/2 -{data.get('body_width', '0')}/2 {data.get('body_length', '0')}/2 {data.get('body_width', '0')}/2

# Add reference designator
text new SILKSCREEN_TOP 0 {data.get('body_width', '0')}/2+0.5 \\$REFDES

cell save
cell end
"""
        return script, f"{part_number}_xpedition.scr"

# Placeholder classes for other generator pages
class DiscreteF(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DiscreteF", parent)

class DiscreteFMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DiscreteFMPE", parent)

class Sot23N(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("Sot23N", parent)

class Sot23NMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("Sot23NMPE", parent)

class Sot23F(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("Sot23F", parent)

class Sot23FMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("Sot23FMPE", parent)

class TOPackageN(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("TOPackageN", parent)

class TOPackageNMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("TOPackageNMPE", parent)

class TOPackageF(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("TOPackageF", parent)

class TOPackageFMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("TOPackageFMPE", parent)

class DualSideN(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideN", parent)

class DualSideNMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideNMPE", parent)

class DualSideF(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideF", parent)

class DualSideFMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideFMPE", parent)

class DualSideTN(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideTN", parent)

class DualSideTNMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideTNMPE", parent)

class DualSideTF(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideTF", parent)

class DualSideTFMPE(BaseGeneratorPage):
    def __init__(self, parent=None):
        super().__init__("DualSideTFMPE", parent)

# --- Main Application Window ---
class MainWindow(QMainWindow):
    """The main window that orchestrates all pages and Flask integration."""

    DEFAULT_CATEGORY_IMAGE_MAP = {
        "Discrete": "images/Chip2PinSM.svg",
        "Sot-23": "images/SOT23.svg",
        "Sot-143": "images/SOT143.svg",
        "TO Package": "images/DPAK.svg",
        "Dual Side": "images/SOIC.svg",
        "Dual with thermal": "images/SON.svg",
        "QF Package": "images/PQFP.svg",
        "QF Package with thermal": "images/QFN.svg",
        "QFN TWO ROW": "images/QFN2ROW.svg",
        "Connectors": "images/PLCC.svg",
        "Crystals": "images/PrecisionWireWound.svg",
        "BGA Package": "images/BGA.svg",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern UI Footprint Generator")
        self.setGeometry(100, 100, 1000, 600)
        
        self.system_fonts = QFontDatabase.families()
        self.stroke_fonts = ["Default", "Sans Serif", "Serif"]
        
        # Authentication data
        self.auth_token = None
        self.user_info = None
        
        # Initialize script paths for all tools
        self.script_paths = {
            'altium': os.path.join(os.path.expanduser("~"), "altium_scripts"),
            'allegro': os.path.join(os.path.expanduser("~"), "allegro_scripts"),
            'pads': os.path.join(os.path.expanduser("~"), "pads_scripts"),
            'xpedition': os.path.join(os.path.expanduser("~"), "xpedition_scripts")
        }
        
        # Create directories if they don't exist
        for path in self.script_paths.values():
            os.makedirs(path, exist_ok=True)
        
        self.current_script_path = self.script_paths['altium']
        
        central_container = QWidget()
        self.main_layout = QHBoxLayout(central_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.setCentralWidget(central_container)
        
        self.create_sidebar()
        self.create_main_content()
        self.load_stylesheet("style.qss")

    def load_stylesheet(self, filename):
        try:
            with open(filename, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"Stylesheet '{filename}' not found. Using default styles.")

    def create_sidebar(self):
        sidebar_container = QWidget()
        sidebar_container.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)
        sidebar_layout.setAlignment(Qt.AlignTop)
        
        self.button_group = []
        for text, icon in self.get_sidebar_options().items():
            button = QPushButton(f"  {text}")
            button.setIcon(qtawesome.icon(icon, color='#d0d0d0'))
            button.setIconSize(QSize(20, 20))
            button.setCheckable(True)
            sidebar_layout.addWidget(button)
            self.button_group.append(button)

        self.button_group[0].setChecked(True)
        for button in self.button_group:
            button.clicked.connect(self.handle_sidebar_click)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(sidebar_container)
        scroll_area.setFixedWidth(250)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_layout.addWidget(scroll_area)

    def handle_sidebar_click(self):
        clicked_button = self.sender()
        for button in self.button_group:
            button.setChecked(button == clicked_button)
        self.stacked_widget.setCurrentIndex(self.button_group.index(clicked_button))

    def create_main_content(self):
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.create_home_page())
        
        for page_title in list(self.get_sidebar_options().keys())[1:]:
            self.stacked_widget.addWidget(self.create_component_page(page_title))
        
        self.settings_page = self.create_settings_page()
        self.settings_page_index = self.stacked_widget.addWidget(self.settings_page)

        self.generator_pages = {}
        page_map = {
            ("Discrete", "Discrete Narmal"): DiscreteN,
            ("Discrete", "Discrete Fillet-Shape"): DiscreteF,
            ("Sot-23", "Narmal"): Sot23N,
            ("Sot-23", "Narmal with MP Expantion"): Sot23NMPE,
            ("Sot-23", "Fillet-Shape"): Sot23F,
            ("Sot-23", "Fillet with MP Expantion"): Sot23FMPE,
            ("TO Package", "Narmal"): TOPackageN,
            ("TO Package", "Narmal with MP Expantion"): TOPackageNMPE,
            ("TO Package", "Fillet-Shape"): TOPackageF,
            ("TO Package", "Fillet with MP Expantion"): TOPackageFMPE,
            ("Dual Side", "Narmal"): DualSideN,
            ("Dual Side", "Narmal with MP Expantion"): DualSideNMPE,
            ("Dual Side", "Fillet-Shape"): DualSideF,
            ("Dual Side", "Fillet with MP Expantion"): DualSideFMPE,
            ("Dual with thermal", "Narmal"): DualSideTN,
            ("Dual with thermal", "Narmal with MP Expantion"): DualSideTNMPE,
            ("Dual with thermal", "Fillet-Shape"): DualSideTF,
            ("Dual with thermal", "Fillet with MP Expantion"): DualSideTFMPE,
        }

        for (comp_type, opt_name), PageClass in page_map.items():
            page_instance = PageClass(self)
            page_instance.generationFinalized.connect(self.on_generation_finalized)
            page_instance.set_script_paths(self.script_paths)
            self.stacked_widget.addWidget(page_instance)
            self.generator_pages[(comp_type, opt_name)] = page_instance

    def on_generation_finalized(self, payload):
        """Handle generation completion"""
        print(f"Generated footprint: {payload['data']['footprint_name']} for {payload['table_name']}")

    def get_sidebar_options(self):
        return {
            "Home": "fa5s.home",
            "Discrete": "fa5s.sliders-h",
            "Sot-23": "fa5s.microchip",
            "Sot-143": "fa5s.satellite",
            "TO Package": "fa5s.battery-half",
            "Dual Side": "fa5s.clone",
            "Dual with thermal": "fa5s.fire",
            "QF Package": "fa5s.shapes",
            "QF with thermal": "fa5s.thermometer-half",
            "QFN TWO ROW": "fa5s.border-style",
            "Connectors": "fa5s.plug",
            "Crystals": "fa5s.icicles",
            "BGA Package": "fa5s.th",
        }

    def create_home_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        
        top_bar_layout = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("HomePageTitle")
        top_bar_layout.addWidget(title)
        top_bar_layout.addStretch()
        
        settings_button = QPushButton()
        settings_button.setIcon(qtawesome.icon('fa5s.cog', color='#d0d0d0'))
        settings_button.setIconSize(QSize(24, 24))
        settings_button.setFixedSize(40, 40)
        settings_button.setCursor(Qt.PointingHandCursor)
        settings_button.clicked.connect(self.go_to_settings)
        top_bar_layout.addWidget(settings_button)
        
        layout.addLayout(top_bar_layout, 0, 0, 1, 4)
        
        # Authentication status card
        auth_status = "Authenticated" if self.auth_token else "Not Authenticated"
        auth_icon = "fa5s.check-circle" if self.auth_token else "fa5s.times-circle"
        card1 = self.create_dashboard_card("Authentication", auth_status, auth_icon)
        
        card2 = self.create_dashboard_card("Scripts Generated", "Local Only", "fa5s.file-code")
        card3 = self.create_dashboard_card("Server Status", "Flask Integration", "fa5s.server")
        
        layout.addWidget(card1, 1, 0)
        layout.addWidget(card2, 1, 1)
        layout.addWidget(card3, 1, 2)
        layout.setRowStretch(2, 1)
        
        return page

    def create_dashboard_card(self, title_text, value_text, icon_name):
        card = QFrame()
        card.setObjectName("DashboardCard")
        card_layout = QVBoxLayout(card)
        
        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 11pt; color: #a0a0a0;")
        
        value_layout = QHBoxLayout()
        icon_label = QLabel()
        icon_color = '#5d9afc' if 'check' in icon_name else '#ff6b6b' if 'times' in icon_name else '#5d9afc'
        icon_label.setPixmap(qtawesome.icon(icon_name, color=icon_color).pixmap(QSize(32, 32)))
        
        value_label = QLabel(value_text)
        value_label.setStyleSheet("font-size: 20pt; font-weight: bold;")
        
        value_layout.addWidget(icon_label)
        value_layout.addWidget(value_label)
        value_layout.addStretch()
        
        card_layout.addWidget(title_label)
        card_layout.addLayout(value_layout)
        
        return card

    def create_component_page(self, component_type):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)

        title = QLabel(f"{component_type} Footprint")
        title.setObjectName("PageTitle")

        font = title.font()
        font.setPointSize(36)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title, 0, 0, 1, 2)
        
        image_label = QSvgWidget()
        image_label.setMinimumSize(400, 400)
        image_label.setStyleSheet("background-color:#232730; border-radius:8px;")

        default_svg = self.DEFAULT_CATEGORY_IMAGE_MAP.get(component_type)
        image_label.load(default_svg) 
        
        layout.addWidget(image_label, 1, 1, 2, 1)
        layout.setColumnStretch(1, 1)
        
        options_layout = QVBoxLayout()
        options_layout.setSpacing(15)

        options = {
            "Discrete": ["Discrete Narmal", "Discrete Fillet-Shape"],
            "Sot-23": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "Sot-143": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "TO Package": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "Dual Side": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "Dual with thermal": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "QF Package": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "QF with thermal": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "QFN TWO ROW": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "Connectors": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "Crystals": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
            "BGA Package": ["Narmal", "Narmal with MP Expantion", "Fillet-Shape", "Fillet with MP Expantion"],
        }

        component_options = options.get(component_type, ["Option A", "Option B"])
                
        for i, option_text in enumerate(component_options):
            option_label = ClickableLabel(option_text)
            option_label.setFixedWidth(300)
            option_label.singleClicked.connect(lambda checked=True, p=default_svg: image_label.load(default_svg))
            option_label.doubleClicked.connect(lambda checked=True, c=component_type, o=option_text: self.go_to_generator(c, o))
            options_layout.addWidget(option_label)
        
        options_layout.addStretch()
        layout.addLayout(options_layout, 1, 0)
        return page

    def create_settings_page(self):
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("SettingsScrollArea")
        page_layout.addWidget(scroll_area)

        container_widget = QWidget()
        scroll_area.setWidget(container_widget)
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(25, 25, 25, 25)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        container_layout.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        container_layout.addWidget(title)

        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_default_settings_tab(), "Default Settings")
        tab_widget.addTab(self._create_account_tab(), "Account")

        container_layout.addWidget(tab_widget)

        return page_widget

    def _create_default_settings_tab(self):
        tab_widget = QWidget()
        main_layout = QVBoxLayout(tab_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setSpacing(15)

        # Script Output Paths Group
        paths_group = QGroupBox("Script Output Paths")
        paths_layout = QGridLayout(paths_group)
        
        # Altium Path
        paths_layout.addWidget(QLabel("Altium Script Path:"), 0, 0)
        self.altium_path_edit = QLineEdit(self.script_paths['altium'])
        self.altium_path_edit.setReadOnly(True)
        altium_browse_btn = QPushButton("Browse")
        altium_browse_btn.clicked.connect(lambda: self.browse_for_script_path('altium'))
        paths_layout.addWidget(self.altium_path_edit, 0, 1)
        paths_layout.addWidget(altium_browse_btn, 0, 2)
        
        # Allegro Path
        paths_layout.addWidget(QLabel("Allegro Script Path:"), 1, 0)
        self.allegro_path_edit = QLineEdit(self.script_paths['allegro'])
        self.allegro_path_edit.setReadOnly(True)
        allegro_browse_btn = QPushButton("Browse")
        allegro_browse_btn.clicked.connect(lambda: self.browse_for_script_path('allegro'))
        paths_layout.addWidget(self.allegro_path_edit, 1, 1)
        paths_layout.addWidget(allegro_browse_btn, 1, 2)
        
        # PADS Path
        paths_layout.addWidget(QLabel("PADS Script Path:"), 2, 0)
        self.pads_path_edit = QLineEdit(self.script_paths['pads'])
        self.pads_path_edit.setReadOnly(True)
        pads_browse_btn = QPushButton("Browse")
        pads_browse_btn.clicked.connect(lambda: self.browse_for_script_path('pads'))
        paths_layout.addWidget(self.pads_path_edit, 2, 1)
        paths_layout.addWidget(pads_browse_btn, 2, 2)
        
        # Xpedition Path
        paths_layout.addWidget(QLabel("Xpedition Script Path:"), 3, 0)
        self.xpedition_path_edit = QLineEdit(self.script_paths['xpedition'])
        self.xpedition_path_edit.setReadOnly(True)
        xpedition_browse_btn = QPushButton("Browse")
        xpedition_browse_btn.clicked.connect(lambda: self.browse_for_script_path('xpedition'))
        paths_layout.addWidget(self.xpedition_path_edit, 3, 1)
        paths_layout.addWidget(xpedition_browse_btn, 3, 2)
        
        main_layout.addWidget(paths_group)
        main_layout.addWidget(self._create_clearance_settings_group())
        main_layout.addWidget(self._create_layer_settings_group())
        main_layout.addWidget(self._create_3d_settings_group())
        return tab_widget

    def _create_account_tab(self):
        """Create account/authentication tab"""
        tab_widget = QWidget()
        main_layout = QVBoxLayout(tab_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setSpacing(15)

        # Authentication Group
        auth_group = QGroupBox("Authentication")
        auth_layout = QGridLayout(auth_group)
        
        # Status
        auth_layout.addWidget(QLabel("Status:"), 0, 0)
        self.auth_status_label = QLabel("Not Authenticated")
        if self.auth_token:
            self.auth_status_label.setText("Authenticated")
            self.auth_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
        auth_layout.addWidget(self.auth_status_label, 0, 1)
        
        # User info
        if self.user_info:
            auth_layout.addWidget(QLabel("Username:"), 1, 0)
            auth_layout.addWidget(QLabel(self.user_info.get('username', 'Unknown')), 1, 1)
            
            auth_layout.addWidget(QLabel("Email:"), 2, 0)
            auth_layout.addWidget(QLabel(self.user_info.get('email', 'Unknown')), 2, 1)
        
        # Login/Logout buttons
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.show_login_dialog)
        button_layout.addWidget(self.login_button)
        
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout_user)
        self.logout_button.setEnabled(bool(self.auth_token))
        button_layout.addWidget(self.logout_button)
        
        button_layout.addStretch()
        auth_layout.addLayout(button_layout, 3, 0, 1, 2)
        
        main_layout.addWidget(auth_group)
        
        # Server Settings Group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout(server_group)
        
        self.server_url_edit = QLineEdit(FLASK_BASE_URL)
        server_layout.addRow("Flask Server URL:", self.server_url_edit)
        
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self.test_server_connection)
        server_layout.addRow("", test_button)
        
        main_layout.addWidget(server_group)
        
        return tab_widget

    def show_login_dialog(self):
        """Show login dialog"""
        login_dialog = LoginDialog(self)
        if login_dialog.exec() == QDialog.Accepted:
            self.auth_token = login_dialog.auth_token
            self.user_info = login_dialog.user_info
            self.update_auth_ui()
            QMessageBox.information(self, "Success", f"Successfully logged in as {self.user_info.get('username', 'Unknown')}")

    def logout_user(self):
        """Logout user"""
        self.auth_token = None
        self.user_info = None
        self.update_auth_ui()
        QMessageBox.information(self, "Logged Out", "Successfully logged out")

    def update_auth_ui(self):
        """Update authentication UI elements"""
        if hasattr(self, 'auth_status_label'):
            if self.auth_token:
                self.auth_status_label.setText("Authenticated")
                self.auth_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.login_button.setEnabled(False)
                self.logout_button.setEnabled(True)
            else:
                self.auth_status_label.setText("Not Authenticated")
                self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
                self.login_button.setEnabled(True)
                self.logout_button.setEnabled(False)

    def test_server_connection(self):
        """Test connection to Flask server"""
        server_url = self.server_url_edit.text()
        try:
            response = requests.get(f"{server_url}/api/health", timeout=5)
            if response.status_code == 200:
                QMessageBox.information(self, "Connection Test", "Successfully connected to server!")
            else:
                QMessageBox.warning(self, "Connection Test", f"Server responded with status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Test", f"Failed to connect to server:\n{str(e)}")

    def _create_clearance_settings_group(self):
        group = QGroupBox("Default Clearance Settings")
        layout = QGridLayout(group)
        
        headers = ["Description", "Clearance (mm)", "Line Width"]
        for i, h in enumerate(headers):
            layout.addWidget(QLabel(h), 0, i, Qt.AlignmentFlag.AlignLeft if i==0 else Qt.AlignmentFlag.AlignCenter)

        rows_data = {
            "Courtyard Clearance": ["0.5", "0.1"],
            "Silkscreen Clearance": ["0.2", "0.12"],
        }
        for row_idx, (label, values) in enumerate(rows_data.items(), 1):
            layout.addWidget(QLabel(label + ":"), row_idx, 0)
            layout.addWidget(QLineEdit(values[0]), row_idx, 1)
            layout.addWidget(QLineEdit(values[1]), row_idx, 2)
        return group

    def _create_layer_settings_group(self):
        group = QGroupBox("Default Layer Settings")
        layout = QFormLayout(group)

        assembly_layout = QHBoxLayout()
        assembly_layout.addWidget(QLabel("Line Width:"))
        assembly_layout.addWidget(QLineEdit("0.1"))
        layout.addRow("Assembly:", assembly_layout)

        return group

    def _create_3d_settings_group(self):
        group = QGroupBox("3D Body Settings")
        layout = QFormLayout(group)
        
        path_layout = QHBoxLayout()
        self.step_path_edit = QLineEdit()
        self.step_path_edit.setPlaceholderText("Select a default folder for STEP models...")
        self.step_path_edit.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_for_step_path)
        
        path_layout.addWidget(self.step_path_edit)
        path_layout.addWidget(browse_button)
        layout.addRow("Default STEP Model Path:", path_layout)
        return group
        
    def go_to_generator(self, component_type, option_name):
        page_widget = self.generator_pages.get((component_type, option_name))
        if page_widget:
            page_widget.set_output_path(self.current_script_path)
            self.stacked_widget.setCurrentWidget(page_widget)
        else:
            QMessageBox.information(self, "Not Implemented", f"The generator for '{option_name}' is not yet available.")

    def go_to_settings(self):
        self.stacked_widget.setCurrentIndex(self.settings_page_index)
        for button in self.button_group:
            button.setChecked(False)

    def browse_for_script_path(self, script_type):
        """Browse for script output path for specific tool type"""
        current_path = self.script_paths.get(script_type, os.path.expanduser("~"))
        directory = QFileDialog.getExistingDirectory(
            self, f"Select {script_type.title()} Script Output Folder", current_path
        )
        if directory:
            self.script_paths[script_type] = directory
            
            if script_type == 'altium':
                self.altium_path_edit.setText(directory)
                self.current_script_path = directory
            elif script_type == 'allegro':
                self.allegro_path_edit.setText(directory)
            elif script_type == 'pads':
                self.pads_path_edit.setText(directory)
            elif script_type == 'xpedition':
                self.xpedition_path_edit.setText(directory)
            
            for page in self.generator_pages.values():
                page.set_script_paths(self.script_paths)
            
            QMessageBox.information(
                self, "Path Set", 
                f"{script_type.title()} script output path has been set to:\n{directory}"
            )

    def browse_for_step_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Default STEP Model Folder")
        if directory:
            self.step_path_edit.setText(directory)

# --- Application Entry Point ---
if __name__ == "__main__":
    if not os.path.exists("images"):
        os.makedirs("images")
        print("Created 'images' directory. Please add placeholder SVG images for the best experience.")
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

## 2. Modified Flask Web Application

Now, let's update the Flask application to handle the PySide6 integration:

```python
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import subprocess
import threading
import json
import os
import jwt
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///license_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string'  # Change this in production

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

class LicenseServer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    server_type = db.Column(db.String(50), nullable=False)  # cadence, mentor, altium
    command = db.Column(db.Text, nullable=False)
    total_licenses = db.Column(db.Integer, default=0)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class CustomApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    license_number = db.Column(db.String(50), nullable=False, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class AppUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('custom_app.id'))
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='inactive')
    permission = db.Column(db.String(20), default='allow')  # allow/deny

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(45))
    user = db.relationship('User', backref='activity_logs')

class LicenseUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('license_server.id'))
    username = db.Column(db.String(80))
    device_name = db.Column(db.String(100))
    in_time = db.Column(db.DateTime)
    out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')

# Updated FootprintDatabase with package-wise tables
class FootprintDatabase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    package_type = db.Column(db.String(50), nullable=False)  # DiscreteN, Sot23N, etc.
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    specifications = db.Column(db.Text)  # JSON string of all parameters
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    description = db.Column(db.Text)

# Package-wise tables
class DiscreteNFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    airgap = db.Column(db.Float)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DiscreteFFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    fillet_radius = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    airgap = db.Column(db.Float)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Sot23NFootprint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), nullable=False)
    footprint_name = db.Column(db.String(100), nullable=False)
    body_length = db.Column(db.Float)
    body_width = db.Column(db.Float)
    body_height = db.Column(db.Float)
    pitch = db.Column(db.Float)
    pad_length = db.Column(db.Float)
    pad_width = db.Column(db.Float)
    mask_expansion = db.Column(db.Float)
    paste_expansion = db.Column(db.Float)
    pin_count = db.Column(db.Integer, default=3)
    user_created = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class FootprintTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_name = db.Column(db.String(100), nullable=False)
    widget_name = db.Column(db.String(100), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class DailyLicenseUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('license_server.id'))
    server_type = db.Column(db.String(50))  # cadence, mentor, altium
    username = db.Column(db.String(80))
    device_name = db.Column(db.String(100))
    first_in_time = db.Column(db.DateTime)
    last_out_time = db.Column(db.DateTime)
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    total_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class MyAppsDailyUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('custom_app.id'))
    username = db.Column(db.String(80))
    email = db.Column(db.String(120))
    first_in_time = db.Column(db.DateTime)
    last_out_time = db.Column(db.DateTime)
    usage_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    total_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer TOKEN
            except IndexError:
                return jsonify({'message': 'Token format invalid'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            current_user_obj = User.query.filter_by(id=current_user_id).first()
            if not current_user_obj:
                return jsonify({'message': 'Token is invalid'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_user_obj, *args, **kwargs)
    return decorated

def log_activity(action):
    if current_user.is_authenticated:
        important_actions = [
            'logged in', 'logged out', 'Updated user', 'Created new user', 
            'Deleted user', 'Added new app', 'Server', 'Updated user permission'
        ]
        
        if any(keyword in action for keyword in important_actions):
            log = ActivityLog(
                user_id=current_user.id,
                action=action,
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()

# Package type to table mapping
PACKAGE_TABLE_MAP = {
    'DiscreteN': DiscreteNFootprint,
    'DiscreteF': DiscreteFFootprint,
    'Sot23N': Sot23NFootprint,
    # Add more mappings as you implement other package types
}

# Background task functions (keeping existing ones)
def run_terminal_command(command, server_id):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        parse_license_data(result.stdout, server_id)
    except subprocess.TimeoutExpired:
        print(f"Command timeout for server {server_id}")
    except Exception as e:
        print(f"Error running command for server {server_id}: {e}")

def parse_license_data(output, server_id):
    lines = output.split('\n')
    for line in lines:
        if 'user:' in line.lower():
            pass

def save_daily_usage():
    """Save daily usage data for all license servers and apps"""
    today = datetime.now(timezone.utc).date()
    
    for server in LicenseServer.query.filter_by(is_enabled=True).all():
        usage_records = LicenseUsage.query.filter_by(server_id=server.id).all()
        
        for usage in usage_records:
            if usage.in_time and usage.in_time.date() == today:
                daily_record = DailyLicenseUsage.query.filter_by(
                    server_id=server.id,
                    username=usage.username,
                    usage_date=today
                ).first()
                
                if not daily_record:
                    daily_record = DailyLicenseUsage(
                        server_id=server.id,
                        server_type=server.server_type,
                        username=usage.username,
                        device_name=usage.device_name,
                        first_in_time=usage.in_time,
                        usage_date=today
                    )
                    db.session.add(daily_record)
                
                if usage.out_time:
                    daily_record.last_out_time = usage.out_time
                    if daily_record.first_in_time:
                        hours = (usage.out_time - daily_record.first_in_time).total_seconds() / 3600
                        daily_record.total_hours = hours
    
    for app in CustomApp.query.all():
        app_users = AppUser.query.filter_by(app_id=app.id, status='active').all()
        
        for user in app_users:
            if user.in_time and user.in_time.date() == today:
                daily_record = MyAppsDailyUsage.query.filter_by(
                    app_id=app.id,
                    username=user.username,
                    usage_date=today
                ).first()
                
                if not daily_record:
                    daily_record = MyAppsDailyUsage(
                        app_id=app.id,
                        username=user.username,
                        email=user.email,
                        first_in_time=user.in_time,
                        usage_date=today
                    )
                    db.session.add(daily_record)
                
                if user.out_time:
                    daily_record.last_out_time = user.out_time
                    if daily_record.first_in_time:
                        hours = (user.out_time - daily_record.first_in_time).total_seconds() / 3600
                        daily_record.total_hours = hours
    
    db.session.commit()

def start_background_monitoring():
    def monitor_licenses():
        while True:
            with app.app_context():
                try:
                    servers = LicenseServer.query.filter_by(is_enabled=True).all()
                    threads = []
                    
                    for server in servers:
                        thread = threading.Thread(target=run_terminal_command, args=(server.command, server.id))
                        thread.daemon = True
                        thread.start()
                        threads.append(thread)
                    
                    for thread in threads:
                        thread.join()
                    
                    save_daily_usage()
                    
                except Exception as e:
                    print(f"Error in background monitoring: {e}")
                
                threading.Event().wait(300)
    
    monitor_thread = threading.Thread(target=monitor_licenses)
    monitor_thread.daemon = True
    monitor_thread.start()

# API Routes for PySide6 Integration
@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Flask server is running'}), 200

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password) and user.is_active:
        # Generate JWT token
        token_data = {
            'user_id': user.id,
            'username': user.username,
            'exp': datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours
        }
        token = jwt.encode(token_data, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin
            }
        }), 200
    else:
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

@app.route('/api/footprint/add', methods=['POST'])
@token_required
def add_footprint_api(current_user_api):
    try:
        data = request.get_json()
        
        package_type = data.get('package_type')
        part_number = data.get('part_number')
        footprint_name = data.get('footprint_name')
        specifications = data.get('specifications', {})
        user_created = data.get('user_created', current_user_api.username)
        
        if not package_type or not part_number or not footprint_name:
            return jsonify({
                'status': 'error', 
                'message': 'package_type, part_number, and footprint_name are required'
            }), 400
        
        # Save to main FootprintDatabase table
        footprint = FootprintDatabase(
            package_type=package_type,
            part_number=part_number,
            footprint_name=footprint_name,
            specifications=json.dumps(specifications),
            user_created=user_created
        )
        db.session.add(footprint)
        
        # Save to package-specific table if it exists
        if package_type in PACKAGE_TABLE_MAP:
            PackageTable = PACKAGE_TABLE_MAP[package_type]
            
            # Create package-specific record
            package_record = PackageTable(
                part_number=part_number,
                footprint_name=footprint_name,
                user_created=user_created
            )
            
            # Set package-specific attributes
            for key, value in specifications.items():
                if hasattr(package_record, key) and value:
                    try:
                        # Convert to appropriate type
                        if key in ['pin_count']:
                            setattr(package_record, key, int(value))
                        elif key in ['body_length', 'body_width', 'body_height', 'pad_length', 
                                   'pad_width', 'mask_expansion', 'paste_expansion', 'airgap',
                                   'pitch', 'fillet_radius']:
                            setattr(package_record, key, float(value))
                        else:
                            setattr(package_record, key, str(value))
                    except (ValueError, TypeError):
                        continue
            
            db.session.add(package_record)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Footprint data saved successfully',
            'footprint_id': footprint.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to save footprint data: {str(e)}'
        }), 500

@app.route('/api/footprint/list')
@token_required
def list_footprints_api(current_user_api):
    try:
        package_type = request.args.get('package_type')
        
        query = FootprintDatabase.query
        if package_type:
            query = query.filter_by(package_type=package_type)
        
        footprints = query.order_by(FootprintDatabase.created_at.desc()).all()
        
        result = []
        for fp in footprints:
            result.append({
                'id': fp.id,
                'package_type': fp.package_type,
                'part_number': fp.part_number,
                'footprint_name': fp.footprint_name,
                'specifications': json.loads(fp.specifications) if fp.specifications else {},
                'user_created': fp.user_created,
                'created_at': fp.created_at.isoformat()
            })
        
        return jsonify({
            'status': 'success',
            'footprints': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve footprints: {str(e)}'
        }), 500

# Existing web routes (keeping all existing ones)
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            log_activity(f"User {username} logged in")
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    log_activity(f"User {current_user.username} logged out")
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        cadence_servers = LicenseServer.query.filter_by(server_type='cadence', is_enabled=True).count()
        mentor_servers = LicenseServer.query.filter_by(server_type='mentor', is_enabled=True).count()
        altium_servers = LicenseServer.query.filter_by(server_type='altium', is_enabled=True).count()
        
        try:
            custom_apps = CustomApp.query.count()
        except Exception as e:
            if "no such column" in str(e).lower():
                flash('Database needs updating. Please run the migration script.', 'warning')
                custom_apps = 0
            else:
                raise e
        
        active_users = AppUser.query.filter_by(status='active').count()
        total_footprints = FootprintDatabase.query.count()
        
        log_activity("Accessed dashboard")
        
        return render_template('dashboard.html', 
                             cadence_servers=cadence_servers,
                             mentor_servers=mentor_servers,
                             altium_servers=altium_servers,
                             custom_apps=custom_apps,
                             active_users=active_users,
                             total_footprints=total_footprints)
                             
    except Exception as e:
        if "no such column" in str(e).lower():
            flash('Database schema is outdated. Please run: python migrate_database.py', 'error')
            return render_template('dashboard.html', 
                                 cadence_servers=0,
                                 mentor_servers=0,
                                 altium_servers=0,
                                 custom_apps=0,
                                 active_users=0,
                                 total_footprints=0)
        else:
            raise e

@app.route('/footprint')
@login_required
def footprint_database():
    footprints = FootprintDatabase.query.all()
    table_widgets = FootprintTable.query.filter_by(is_visible=True).all()
    
    # Statistics
    total_footprints = len(footprints)
    package_stats = {}
    user_stats = {}
    
    for fp in footprints:
        if fp.package_type:
            package_stats[fp.package_type] = package_stats.get(fp.package_type, 0) + 1
        if fp.user_created:
            user_stats[fp.user_created] = user_stats.get(fp.user_created, 0) + 1
    
    return render_template('footprint.html', 
                         footprints=footprints,
                         table_widgets=table_widgets,
                         total_footprints=total_footprints,
                         package_stats=package_stats,
                         user_stats=user_stats)

@app.route('/footprint/package/<package_type>')
@login_required
def footprint_by_package(package_type):
    """View footprints by package type"""
    footprints = FootprintDatabase.query.filter_by(package_type=package_type).all()
    
    # Get package-specific data if available
    package_data = []
    if package_type in PACKAGE_TABLE_MAP:
        PackageTable = PACKAGE_TABLE_MAP[package_type]
        package_data = PackageTable.query.all()
    
    return render_template('footprint_package.html', 
                         package_type=package_type,
                         footprints=footprints,
                         package_data=package_data)

# Keep all other existing routes...
# [Include all the other routes from the original Flask app]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
        
        # Check if license_number column exists before querying
        try:
            apps_without_license = CustomApp.query.filter_by(license_number='').all()
            for app in apps_without_license:
                app.license_number = f"LIC-{app.id:04d}"
            
            if apps_without_license:
                db.session.commit()
                print(f"Updated {len(apps_without_license)} apps with default license numbers")
        except Exception as e:
            if "no such column" in str(e):
                print("Database schema needs updating. Please run: python migrate_database.py")
                print("Or delete license_manager.db to start fresh.")
            else:
                print(f"Database error: {e}")
    
    # Start background monitoring
    start_background_monitoring()
    
    # Run the app on local network
    app.run(host='0.0.0.0', port=5000, debug=True)
```

## 3. HTML Template for Package-wise Footprint View

Create `templates/footprint_package.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ package_type }} Footprints - License Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container-fluid">
        <h1>{{ package_type }} Footprints</h1>
        
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>Package Statistics</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Total {{ package_type }} Footprints:</strong> {{ footprints|length }}</p>
                        <a href="{{ url_for('footprint_database') }}" class="btn btn-secondary">Back to All Footprints</a>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>{{ package_type }} Footprint Details</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Part Number</th>
                                        <th>Footprint Name</th>
                                        <th>User Created</th>
                                        <th>Created Date</th>
                                        <th>Specifications</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for footprint in footprints %}
                                    <tr>
                                        <td>{{ footprint.part_number }}</td>
                                        <td>{{ footprint.footprint_name }}</td>
                                        <td>{{ footprint.user_created }}</td>
                                        <td>{{ footprint.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                                        <td>
                                            <button class="btn btn-sm btn-info" type="button" data-bs-toggle="collapse" 
                                                    data-bs-target="#specs-{{ footprint.id }}" aria-expanded="false">
                                                View Specs
                                            </button>
                                            <div class="collapse" id="specs-{{ footprint.id }}">
                                                <div class="card card-body mt-2">
                                                    <pre>{{ footprint.specifications }}</pre>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## 4. Required Dependencies

Add these to your requirements.txt:

```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Werkzeug==2.3.7
PyJWT==2.8.0
requests==2.31.0
PySide6==6.5.2
qtawesome==1.2.3
```

## Key Features Implemented:

1. **Authentication Integration**: Login dialog in PySide6 app with JWT token authentication
2. **Data Submission**: PySide6 app sends footprint data directly to Flask API
3. **Package-wise Database**: Separate tables for different package types
4. **Token-based Security**: JWT tokens for API authentication
5. **Health Check**: API endpoint to test server connectivity
6. **Database Removal**: Removed SQLite database from PySide6 app

## Usage:

1. Run the Flask server: `python flask_app.py`
2. Run the PySide6 app: `python pyside6_app.py`
3. Login through Settings > Account in the PySide6 app
4. Generate footprints - they'll be saved to the Flask server automatically

The integration allows your PySide6 application to work seamlessly with the Flask web server for data management while keeping the local script generation functionality intact.
