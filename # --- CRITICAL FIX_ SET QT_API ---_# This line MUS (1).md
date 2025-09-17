

# \# --- CRITICAL FIX: SET QT_API ---

# This line MUST be at the very top, before any other imports.

import os
os.environ['QT_API'] = 'pyside6'

# --- END FIX ---

import sys
import sqlite3
import qtawesome
import json

# Add these imports after the existing imports

import struct
import json
import math
from PySide6.QtCore import (Qt, QSize, Signal, QPoint) \# Signal is the equivalent of pyqtSignal
from PySide6.QtWidgets import (
QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,QComboBox,QGroupBox,QCheckBox,
QPushButton, QStackedWidget, QLabel, QLineEdit, QGridLayout,QTabWidget,
QFrame, QScrollArea, QSizePolicy, QFileDialog, QMessageBox, QFormLayout,
QTextEdit, QButtonGroup \# <-- ADD QButtonGroup HERE
)
from PySide6.QtGui import QPixmap, QIcon, QMouseEvent, QClipboard, QFontDatabase \# <-- ADD QFontDatabase
from PySide6.QtSvgWidgets import QSvgWidget

# --- Constants ---

DATABASE_FILE = "footprint_data.db"
DEFAULT_SCRIPT_PATH = os.path.join(os.path.expanduser("~"), "generated_scripts")

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
A base class that encapsulates generation AND file-saving logic.
Each page is a self-sufficient unit.
"""
\# Signal is now simpler: just sends the data for the database
generationFinalized = Signal(dict)
def __init__(self, parent=None):
super().__init__(parent)
self.output_path = ""
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
\# Use QSvgWidget for sharp vector graphics rendering
self.image_label = QSvgWidget()
self.image_label.setMinimumSize(250, 300)
self.image_label.setStyleSheet("background-color: \#232730; border-radius: 8px;")
right_panel_layout.addWidget(self.image_label)
layout.addLayout(right_panel_layout, 0, 1)
layout.setColumnStretch(1, 1)
button_layout = QHBoxLayout()
self.generate_button = QPushButton("Generate Script")
self.generate_button.setObjectName("GenerateButton")
self.generate_button.setCursor(Qt.PointingHandCursor)
self.generate_button.clicked.connect(self._on_generate_clicked)
button_layout.addWidget(self.generate_button)
button_layout.addStretch()
layout.addLayout(button_layout, 2, 0, 1, 2)
def _on_generate_clicked(self):
"""Workflow: Collect, validate, generate, save file, display, and emit."""
data = self.collect_data()
if not data.get("part_number") or not data.get("footprint_name"):
QMessageBox.warning(self, "Input Error", "Part Number and Footprint Name are required.")
return
try:
\# 1. Let the specific page create the script
script_content, filename = self.generate_script(data, self.output_path)

            # 3. Save the script to the file system FROM THIS CLASS
            self._write_script_to_file(filename, script_content)
            
            # 4. Show a success message for the file save part
            QMessageBox.information(self, "File Saved", f"Script '{filename}' has been saved successfully to:\n{self.output_path}")
            # 5. Emit the data for MainWindow to save to the database
            self.generationFinalized.emit(data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during the process:\n\n{e}")
    def _write_script_to_file(self, filename, script_content):
        """Internal helper to write the script file to the configured output path."""
        if not self.output_path:
            raise ValueError("Output path has not been set.")
        
        # Check if directory exists, if not, create it
        os.makedirs(self.output_path, exist_ok=True)
        
        output_filepath = os.path.join(self.output_path, filename)
        with open(output_filepath, "w") as f:
            f.write(script_content)
    def generate_script(self, data, path):
        """Abstract method - subclasses MUST implement this."""
        raise NotImplementedError("Each generator page must implement generate_script and return a (script, filename) tuple.")
    def set_output_path(self, path):
        self.output_path = path
    def set_initial_values(self, title, footprint_name):
        self.title_label.setText(title)
        for field in self.input_fields.values():
            field.clear()
        if "Footprint Name" in self.input_fields:
            self.input_fields["Footprint Name"].setText(footprint_name)
    def collect_data(self):
        return {k.replace(" ", "_").lower().replace("(mm)", "").strip(): v.text() for k, v in self.input_fields.items()}
    
# --- Specific Generator Page Implementations ---

class DiscreteN(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):

        super().__init__(parent)
        self.input_fields = {
            "Part Number": QLineEdit(),
            "Footprint Name": QLineEdit(),
            "Body Length (mm)": QLineEdit(),
            "Body Width (mm)": QLineEdit(),
            "body height (mm)": QLineEdit(),
            "pad Length (mm)": QLineEdit(),
            "pad Width (mm)": QLineEdit(),
            "mask expansion (mm)": QLineEdit(),
            "paste expansion (mm)": QLineEdit(),
            "airgap (mm)": QLineEdit(),
        }
        for label, field in self.input_fields.items():
            self.form_layout.addRow(label, field)
        
        # Load the SVG vector image directly into the widget for sharp rendering
        self.image_label.load("generator_resistor_chip.svg")
    def generate_script(self, data, path):
"""Generate Ultra Librarian-style footprint and save as .txt file."""
try:
part_number = data.get('Part Number', '')
footprint_name = data.get('Footprint Name', '')
body_l = float(data.get('Body Length (mm)', ))
body_w = float(data.get('Body Width (mm)', ))
pad_l = float(data.get('pad Length (mm)', ))
pad_w = float(data.get('pad Width (mm)', ))
mask_expansion = float(data.get('mask expansion (mm)', ))
paste_expansion = float(data.get('paste expansion (mm)', ))
airgap = float(data.get('airgap (mm)', ))
except (ValueError, TypeError):
raise ValueError("All dimensions must be valid numbers.")
\# Convert mm to Ultra Librarian ASCII units (1 mm = 3937.007874 units)
def mm_to_ul(val):
return round(val / 0.000254)
pad_offset = (body_l - pad_l) / 2
pad_x = mm_to_ul(pad_offset)
pad_y = 0
pad_w_ul = mm_to_ul(pad_w)
pad_l_ul = mm_to_ul(pad_l)
\# Helper functions
\# Predefined outlines and shapes (static from reference)
\# Generate script
script = f"""\# Created by Footprint Generator

# Part Number: {part_number}

# Footprint: {footprint_name}

StartFootprints
Footprint (Name "{footprint_name}")
Pad (Name "1") (Location -{pad_x}, {pad_y}) (Surface True) (Rotation 0) (ExpandMask 0) (ExpandPaste 0)
PadShape (Size {pad_w_ul}, {pad_l_ul}) (Shape Rectangular) (Layer Top)
EndPad
Pad (Name "2") (Location {pad_x}, {pad_y}) (Surface True) (Rotation 0) (ExpandMask 0) (ExpandPaste 0)
PadShape (Size {pad_w_ul}, {pad_l_ul}) (Shape Rectangular) (Layer Top)
EndPad
Polygon (PointCount 4) (Type KeepOut) (Layer KeepOutLayer)
EndPolygon
Polygon (PointCount 4) (Type KeepOut) (Layer TopLayer)
EndPolygon
Polygon (PointCount 4) (Layer Mechanical15)
Point (-67.5, -38.5)
Point (-67.5, 38.5)
Point (67.5, 38.5)
Point (67.5, -38.5)
EndPolygon
Text (Location -75, -25) (Height 50) (Width 3) (Rotation 0) (Layer TopOverlay) (Value "RefDes")
Text (Location -87.5, -25) (Height 50) (Width 3) (Rotation 0) (Layer TopOverlay) (Value "REFDES")
Text (Location -87.5, -25) (Height 50) (Width 3) (Rotation 0) (Layer Mechanical13) (Value "RefDes2")
Arc (Width 0) (Radius 0) (Location -30.5, 0) (StartAngle 0) (EndAngle 360) (Layer Mechanical13)
Step (Name {footprint_name}.step)
EndFootprint
EndFootprints
"""
\# Save to .txt file
full_path = os.path.join(path, f"{part_number}.txt")
with open(full_path, "w") as f:
f.write(script)
return script, f"{part_number}.txt"

class DiscreteF(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DiscreteFMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class Sot23N(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class Sot23NMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class Sot23F(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class Sot23FMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class TOPackageN(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class TOPackageNMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class TOPackageF(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class TOPackageFMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideN(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideNMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideF(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideFMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideTN(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideTNMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideTF(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)
class DualSideTFMPE(BaseGeneratorPage):
"""Generator page for chip resistors with its own script logic and file format."""
def __init__(self, parent=None):
super().__init__(parent)

# --- Main Application Window ---

class MainWindow(QMainWindow):
"""The main window that orchestrates all pages and database interactions."""
\# Map component categories to a default image to show when the page is first opened.
DEFAULT_CATEGORY_IMAGE_MAP = {
"Discrete": "images/Chip2PinSM.svg",
"Sot-23": "images/SOT23.svg",  \# Example: Add sot_package.svg to images/
"Sot-143": "images/SOT143.svg",  \# Example: Add sot_143.svg to images/, etc.
"TO Package": "images/DPAK.svg",  \# Example: Add to_package.svg to images/
"Dual Side": "images/SOIC.svg",  \# etc.
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
\# Pre-load font lists so they are available as instance attributes.
\# This must be done before create_main_content() is called.
self.system_fonts = QFontDatabase.families()
self.stroke_fonts = ["Default", "Sans Serif", "Serif"]

        if not os.path.exists(DEFAULT_SCRIPT_PATH):
            os.makedirs(DEFAULT_SCRIPT_PATH)
            
        self.current_script_path = DEFAULT_SCRIPT_PATH
        self.init_database()
        
        # --- FIX IS HERE ---
        # Rename 'self.central_widget' to avoid name collision with QMainWindow's methods.
        central_container = QWidget()
        self.main_layout = QHBoxLayout(central_container) # The layout is applied to the container.
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # This is the line that was causing the error. Now it works correctly.
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
    def init_database(self):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS DiscreteN (
                id INTEGER PRIMARY KEY AUTOINCREMENT, part_number TEXT NOT NULL,
                footprint_name TEXT, component_type TEXT, dimensions_json TEXT
            )''')
        conn.commit()
        conn.close()
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
            # Add more mappings as needed for other component types/options
            }
        for (comp_type, opt_name), PageClass in page_map.items():
            page_instance = PageClass()
            page_instance.generationFinalized.connect(self.handle_save_to_database)
            page_instance.set_output_path(self.current_script_path)
            self.stacked_widget.addWidget(page_instance)
            self.generator_pages[(comp_type, opt_name)] = page_instance
    def handle_save_to_database(self, data):
        """Receives data and saves it to the database. File saving is done by the page."""
        try:
            self.save_footprint_to_db(data)
            print(f"Successfully saved metadata for {data['footprint_name']} to database.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"The script file was saved, but a database error occurred:\n\n{e}")
    def save_footprint_to_db(self, data):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        footprint_name = data.get('footprint_name', 'N/A')
        cursor.execute('''
            INSERT INTO footprints (part_number, footprint_name, component_type, dimensions_json)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('part_number', 'N/A'),
            footprint_name,
            footprint_name.split('_')[0],
            json.dumps(data)
        ))
        conn.commit()
        conn.close()
    def get_sidebar_options(self):
        return {
            "Home": "fa5s.home",  # 🏠 Home Dashboard
            "Discrete": "fa5s.sliders-h",  # 🔩 Discrete component like resistor
            "Sot-23": "fa5s.microchip",  # 🧩 Small Outline Transistor
            "Sot-143": "fa5s.satellite",  # 🛰️ Close representation (unique package)
            "TO Package": "fa5s.battery-half",  # 🔋 Power-related packages
            "Dual Side": "fa5s.clone",  # 🧿 Symmetric layout idea
            "Dual with thermal": "fa5s.fire",  # 🔥 For thermal pad
            "QF Package": "fa5s.shapes",  # 🔳 QFP packages
            "QF with thermal": "fa5s.thermometer-half",  # 🌡️ Thermal-aware QFP
            "QFN TWO ROW": "fa5s.border-style",
            "Connectors": "fa5s.plug",  # 🔌 Connectors
            "Crystals": "fa5s.icicles",  # ❄️ (symbolic for crystal oscillators)
            "BGA Package": "fa5s.th",  # ⬛ Ball Grid Array (use ‘th’ or ‘grip-lines’)
        }
    def create_home_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        top_bar_layout = QHBoxLayout()
        title = QLabel("Dashboard"); title.setObjectName("HomePageTitle")
        top_bar_layout.addWidget(title); top_bar_layout.addStretch()
        settings_button = QPushButton()
        settings_button.setIcon(qtawesome.icon('fa5s.cog', color='#d0d0d0'))
        settings_button.setIconSize(QSize(24, 24)); settings_button.setFixedSize(40, 40)
        settings_button.setCursor(Qt.PointingHandCursor); settings_button.clicked.connect(self.go_to_settings)
        top_bar_layout.addWidget(settings_button)
        layout.addLayout(top_bar_layout, 0, 0, 1, 4)
        card1 = self.create_dashboard_card("Total Footprints", "1,204", "fa5s.database")
        card2 = self.create_dashboard_card("Scripts Generated", "89", "fa5s.file-code")
        card3 = self.create_dashboard_card("Last Generated", "IC-SOIC-8", "fa5s.clock")
        layout.addWidget(card1, 1, 0); layout.addWidget(card2, 1, 1); layout.addWidget(card3, 1, 2)
        layout.setRowStretch(2, 1)
        return page
    def create_dashboard_card(self, title_text, value_text, icon_name):
        card = QFrame(); card.setObjectName("DashboardCard"); card_layout = QVBoxLayout(card)
        title_label = QLabel(title_text); title_label.setStyleSheet("font-size: 11pt; color: #a0a0a0;")
        value_layout = QHBoxLayout()
        icon_label = QLabel(); icon_label.setPixmap(qtawesome.icon(icon_name, color='#5d9afc').pixmap(QSize(32, 32)))
        value_label = QLabel(value_text); value_label.setStyleSheet("font-size: 20pt; font-weight: bold;")
        value_layout.addWidget(icon_label); value_layout.addWidget(value_label); value_layout.addStretch()
        card_layout.addWidget(title_label); card_layout.addLayout(value_layout)
        return card
    def create_component_page(self, component_type):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        title = QLabel(f"{component_type} Footprint")
        title.setObjectName("PageTitle")
        # Increase font size
        font = title.font()
        font.setPointSize(36)  # 🔧 Increase this value for larger font
        font.setBold(True)     # Optional
        title.setFont(font)
        layout.addWidget(title, 0, 0, 1, 2)
        
        # Use QSvgWidget for the main image display
        image_label = QSvgWidget()
        image_label.setMinimumSize(400, 400)
        image_label.setStyleSheet("background-color:#232730; border-radius:8px;")
        # Look up the default image for this component category, with a fallback.
        default_svg = self.DEFAULT_CATEGORY_IMAGE_MAP.get(component_type)
        # Attempt to load the specific SVG; if it fails, load the ultimate fallback.
        image_label.load(default_svg) 
            # Load a default SVG
        
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
        # --- Image Mapping for Component Types and Options ---
        IMAGE_MAP = {
            ("Discrete", "Discrete Narmal"): "generator_resistor_chip.svg",
            ("Discrete", "Discrete Fillet-Shape"): "images/placeholder_C.svg",
            ("Sot-23", "Tantalum A"): "images/tantalum_a.svg",
            ("Sot-23", "Tantalum B"): "images/tantalum_b.svg",
            # Add more mappings as needed for other component types/options
        }
        # Use SVG paths for placeholder images
                
        for i, option_text in enumerate(component_options):
            option_label = ClickableLabel(option_text)
            option_label.setFixedWidth(300)
            image_path = IMAGE_MAP.get((component_type, option_text))
            # Capture image_path and option_text as default arguments
            option_label.singleClicked.connect(lambda checked=True, p=image_path:image_label.load(default_svg))
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
        tab_widget.addTab(self._create_Default_settings_tab(), "Default Settings")
        tab_widget.addTab(self._create_placeholder_tab("Account"), "Account")
        container_layout.addWidget(tab_widget)
        return page_widget
    def _create_Default_settings_tab(self):
        tab_widget = QWidget()
        main_layout = QVBoxLayout(tab_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setSpacing(15)
        group = QGroupBox("Default Clearance Settings")
        path_layout = QGridLayout(group)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.current_script_path)
        self.path_edit.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_for_path)
        path_layout.addWidget(QLabel("Altium Script Output Path:"))
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_button)
        main_layout.addLayout(path_layout)
        main_layout.addWidget(self._create_clearance_settings_group())
        main_layout.addWidget(self._create_layer_settings_group())
        main_layout.addWidget(self._create_3d_settings_group())
        return tab_widget
    
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
        # Assembly Row
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
    def _create_placeholder_tab(self, name):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(f"{name} settings will be configured here.")
        label.setStyleSheet("font-size: 14pt; color: #808080;")
        layout.addWidget(label)
        return widget
        
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
    def browse_for_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.current_script_path)
        if directory:
            self.current_script_path = directory
            self.path_edit.setText(self.current_script_path)
            for page in self.generator_pages.values():
                page.set_output_path(self.current_script_path)
            QMessageBox.information(self, "Path Set", f"Script output path has been set to:\n{directory}")
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
    sys.exit(app.exec())   add 3 more output script path in the settings - allegro,pads, xpedition and 3 sepate script and it map with its output path if select generate script button it will generate 4 defferent script at same time
    I'll help you add support for 4 different script output formats (Altium, Allegro, PADS, and Xpedition) with separate output paths and simultaneous script generation. Here are the key modifications:

## Modified Settings Section

```python
def _create_Default_settings_tab(self):
    tab_widget = QWidget()
    main_layout = QVBoxLayout(tab_widget)
    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    main_layout.setSpacing(15)

    # Script Output Paths Group
    paths_group = QGroupBox("Script Output Paths")
    paths_layout = QGridLayout(paths_group)
    
    # Initialize default paths if they don't exist
    if not hasattr(self, 'script_paths'):
        self.script_paths = {
            'altium': self.current_script_path,
            'allegro': os.path.join(os.path.expanduser("~"), "allegro_scripts"),
            'pads': os.path.join(os.path.expanduser("~"), "pads_scripts"),
            'xpedition': os.path.join(os.path.expanduser("~"), "xpedition_scripts")
        }
        # Create directories if they don't exist
        for path in self.script_paths.values():
            os.makedirs(path, exist_ok=True)
    
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
```


## Updated Browse Methods

```python
def browse_for_script_path(self, script_type):
    """Browse for script output path for specific tool type"""
    current_path = self.script_paths.get(script_type, os.path.expanduser("~"))
    directory = QFileDialog.getExistingDirectory(
        self, f"Select {script_type.title()} Script Output Folder", current_path
    )
    if directory:
        self.script_paths[script_type] = directory
        
        # Update the corresponding UI field
        if script_type == 'altium':
            self.altium_path_edit.setText(directory)
            self.current_script_path = directory  # Keep backward compatibility
        elif script_type == 'allegro':
            self.allegro_path_edit.setText(directory)
        elif script_type == 'pads':
            self.pads_path_edit.setText(directory)
        elif script_type == 'xpedition':
            self.xpedition_path_edit.setText(directory)
        
        # Update all generator pages
        for page in self.generator_pages.values():
            page.set_script_paths(self.script_paths)
        
        QMessageBox.information(
            self, "Path Set", 
            f"{script_type.title()} script output path has been set to:\n{directory}"
        )

# Remove the old browse_for_path method and replace with this updated version
def browse_for_path(self):
    """Legacy method - redirects to Altium path for backward compatibility"""
    self.browse_for_script_path('altium')
```


## Updated BaseGeneratorPage Class

```python
class BaseGeneratorPage(QWidget):
    """
    A base class that encapsulates generation AND file-saving logic.
    Each page is a self-sufficient unit that generates scripts for all 4 tools.
    """
    generationFinalized = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize paths for all 4 script types
        self.script_paths = {
            'altium': DEFAULT_SCRIPT_PATH,
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
        """Generate scripts for all 4 tools simultaneously"""
        data = self.collect_data()
        if not data.get("part_number") or not data.get("footprint_name"):
            QMessageBox.warning(self, "Input Error", "Part Number and Footprint Name are required.")
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
            
            # Show results
            if generated_files:
                success_msg = "Successfully generated scripts:\n\n" + "\n".join(generated_files)
                if errors:
                    success_msg += f"\n\nErrors encountered:\n" + "\n".join(errors)
                QMessageBox.information(self, "Scripts Generated", success_msg)
                self.generationFinalized.emit(data)
            else:
                QMessageBox.critical(self, "Generation Failed", "Failed to generate any scripts:\n\n" + "\n".join(errors))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during the process:\n\n{e}")

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
        
    # Keep backward compatibility
    def set_output_path(self, path):
        """Legacy method for backward compatibility"""
        self.script_paths['altium'] = path

    def collect_data(self):
        return {k.replace(" ", "_").lower().replace("(mm)", "").strip(): v.text() for k, v in self.input_fields.items()}
```


## Updated DiscreteN Class with Multi-Tool Support

```python
class DiscreteN(BaseGeneratorPage):
    """Generator page for chip resistors with multi-tool script generation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.input_fields = {
            "Part Number": QLineEdit(),
            "Footprint Name": QLineEdit(),
            "Body Length (mm)": QLineEdit(),
            "Body Width (mm)": QLineEdit(),
            "body height (mm)": QLineEdit(),
            "pad Length (mm)": QLineEdit(),
            "pad Width (mm)": QLineEdit(),
            "mask expansion (mm)": QLineEdit(),
            "paste expansion (mm)": QLineEdit(),
            "airgap (mm)": QLineEdit(),
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
```


## Update MainWindow Initialization

```python
def __init__(self):
    super().__init__()
    self.setWindowTitle("Modern UI Footprint Generator")
    self.setGeometry(100, 100, 1000, 600)
    
    self.system_fonts = QFontDatabase.families()
    self.stroke_fonts = ["Default", "Sans Serif", "Serif"]
    
    # Initialize script paths for all tools
    self.script_paths = {
        'altium': DEFAULT_SCRIPT_PATH,
        'allegro': os.path.join(os.path.expanduser("~"), "allegro_scripts"),
        'pads': os.path.join(os.path.expanduser("~"), "pads_scripts"),
        'xpedition': os.path.join(os.path.expanduser("~"), "xpedition_scripts")
    }
    
    # Create directories if they don't exist
    for path in self.script_paths.values():
        os.makedirs(path, exist_ok=True)
    
    self.current_script_path = self.script_paths['altium']  # Backward compatibility
    
    self.init_database()
    
    central_container = QWidget()
    self.main_layout = QHBoxLayout(central_container)
    self.main_layout.setContentsMargins(0, 0, 0, 0)
    self.main_layout.setSpacing(0)
    
    self.setCentralWidget(central_container)
    
    self.create_sidebar()
    self.create_main_content()
    self.load_stylesheet("style.qss")
```


## Update Generator Page Creation

```python
for (comp_type, opt_name), PageClass in page_map.items():
    page_instance = PageClass()
    page_instance.generationFinalized.connect(self.handle_save_to_database)
    page_instance.set_script_paths(self.script_paths)  # Set all paths
    self.stacked_widget.addWidget(page_instance)
    self.generator_pages[(comp_type, opt_name)] = page_instance
```


## Key Features Added:

1. **4 Separate Output Paths**: Each tool (Altium, Allegro, PADS, Xpedition) has its own configurable output directory
2. **Simultaneous Generation**: One click generates all 4 script formats at once
3. **Tool-Specific Formats**: Each script uses the appropriate syntax for its target tool
4. **Individual Browse Buttons**: Separate path selection for each tool
5. **Error Handling**: Shows which scripts succeeded/failed during generation
6. **Backward Compatibility**: Maintains existing Altium-focused functionality

The button now reads "Generate All Scripts" and will create 4 different files simultaneously when clicked, each in their respective output directories.

