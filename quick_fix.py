
import sys
import os
from decimal import Decimal, ROUND_HALF_UP
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QComboBox, QTextEdit, QMessageBox, QGroupBox,
                             QRadioButton, QButtonGroup, QGridLayout, QTabWidget,
                             QFileDialog, QCheckBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def to_decimal(value):
    """Convert value to Decimal safely"""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except:
        return Decimal('0')


class IPCCalculator:
    """IPC-7351 Land Pattern Calculator - Altium Compatible"""
    
    # IPC-7351B Tolerance values (in mm) - Exactly as Altium uses
    TOLERANCES = {
        'A': {'JT': Decimal('0.55'), 'JH': Decimal('0.45'), 'JS': Decimal('0.05')},  # Maximum (Least density)
        'B': {'JT': Decimal('0.35'), 'JH': Decimal('0.35'), 'JS': Decimal('0.05')},  # Nominal (Moderate density)
        'C': {'JT': Decimal('0.15'), 'JH': Decimal('0.25'), 'JS': Decimal('0.01')}   # Minimum (Most density)
    }
    
    @staticmethod
    def calculate_land_pattern(L_min, L_max, T_min, T_max, W_min, W_max, 
                               ipc_class='B', F=None, P=None):
        """
        Calculate land pattern dimensions based on IPC-7351B (Altium method)
        
        Parameters:
        - L_min, L_max: Lead span (toe-to-toe) min/max (mm)
        - T_min, T_max: Terminal/lead length min/max (mm)
        - W_min, W_max: Terminal/lead width min/max (mm)
        - ipc_class: 'A', 'B', or 'C'
        - F: Fabrication tolerance (default 0.05mm)
        - P: Placement tolerance (default 0.05mm)
        
        Returns: dict with Zmax, Gmin, Xmax, pad_length, pad_width
        """
        # Default tolerances as per IPC-7351B
        if F is None:
            F = Decimal('0.05')
        if P is None:
            P = Decimal('0.05')
            
        # Get J tolerances for selected class
        tol = IPCCalculator.TOLERANCES[ipc_class]
        JT = tol['JT']
        JH = tol['JH']
        JS = tol['JS']
        
        # Convert all inputs to Decimal
        L_min = to_decimal(str(L_min))
        L_max = to_decimal(str(L_max))
        T_min = to_decimal(str(T_min))
        T_max = to_decimal(str(T_max))
        W_min = to_decimal(str(W_min))
        W_max = to_decimal(str(W_max))
        F = to_decimal(str(F))
        P = to_decimal(str(P))
        
        # Calculate component tolerances (half of range)
        CL = (L_max - L_min) / Decimal('2')
        CT = (T_max - T_min) / Decimal('2')
        CW = (W_max - W_min) / Decimal('2')
        
        # IPC-7351B Formulas (exactly as Altium implements)
        # Zmax: Courtyard toe-to-toe dimension
        Zmax = L_min + Decimal('2') * T_max + Decimal('2') * JT + (CL**2 + (Decimal('2')*CT)**2 + P**2).sqrt()
        
        # Gmin: Gap between pads
        Gmin = L_max - Decimal('2') * T_min - Decimal('2') * JH - (CL**2 + (Decimal('2')*CT)**2 + F**2).sqrt()
        
        # Xmax: Pad width
        Xmax = W_min + Decimal('2') * JS + (CW**2 + P**2 + F**2).sqrt()
        
        # Calculate individual pad dimensions
        pad_length = (Zmax - Gmin) / Decimal('2')
        pad_width = Xmax
        
        return {
            'Zmax': Zmax.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            'Gmin': Gmin.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            'Xmax': Xmax.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            'pad_length': pad_length.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP),
            'pad_width': pad_width.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)
        }


class AltiumScriptGenerator:
    """Generate Altium footprint scripts compatible with IPC-7351B"""
    
    SCALE = Decimal('39.37')  # mm to mils conversion factor
    
    @staticmethod
    def generate_ipc_footprint_name(package_type, data, pin_count):
        """Generate IPC-7351B compliant footprint name"""
        
        pitch = to_decimal(data.get('pitch', '1.27'))
        pitch_str = str(int(pitch * Decimal('100')))  # Convert to 100ths of mm
        
        if package_type in ['SOP', 'SOIC']:
            # SOIC127P600X390X150-8N
            lead_span = to_decimal(data.get('L_max', '6.0'))
            body_width = to_decimal(data.get('body_width', '3.9'))
            height = to_decimal(data.get('height', '1.5'))
            
            lead_span_str = str(int(lead_span * Decimal('100')))
            body_width_str = str(int(body_width * Decimal('100')))
            height_str = str(int(height * Decimal('100')))
            
            # Suffix based on body width
            if body_width < Decimal('5.0'):
                suffix = 'N'
            elif body_width < Decimal('7.5'):
                suffix = 'M'
            else:
                suffix = 'W'
            
            return f"SOIC{pitch_str}P{lead_span_str}X{body_width_str}X{height_str}-{pin_count}{suffix}"
        
        elif package_type == 'QFP':
            # QFP80P1200X1200X160-32N
            lead_span = to_decimal(data.get('L_max', '9.0'))
            height = to_decimal(data.get('height', '1.6'))
            
            lead_span_str = str(int(lead_span * Decimal('100')))
            height_str = str(int(height * Decimal('100')))
            
            return f"QFP{pitch_str}P{lead_span_str}X{lead_span_str}X{height_str}-{pin_count}N"
        
        elif package_type == 'QFN':
            # QFN50P500X500X100-33N (includes thermal pad)
            body_size = to_decimal(data.get('body_size', '5.0'))
            height = to_decimal(data.get('height', '1.0'))
            has_thermal_pad = data.get('has_thermal_pad', True)
            
            body_size_str = str(int(body_size * Decimal('100')))
            height_str = str(int(height * Decimal('100')))
            
            total_pins = pin_count + 1 if has_thermal_pad else pin_count
            
            return f"QFN{pitch_str}P{body_size_str}X{body_size_str}X{height_str}-{total_pins}N"
        
        elif package_type == 'BGA':
            # BGA80CP10X10_800X800X150
            rows = int(data.get('rows', 10))
            columns = int(data.get('columns', 10))
            body_size = to_decimal(data.get('body_size', '8.0'))
            height = to_decimal(data.get('height', '1.5'))
            
            body_size_str = str(int(body_size * Decimal('100')))
            height_str = str(int(height * Decimal('100')))
            
            return f"BGA{pitch_str}CP{rows}X{columns}_{body_size_str}X{body_size_str}X{height_str}"
        
        return f"{package_type}_{pin_count}"
    
    @staticmethod
    def generate_sop_soic_script(data, ipc_class, use_datasheet=False):
        """Generate SOP/SOIC footprint script"""
        lines = []
        
        footprint_base_name = data.get('footprint_name', 'SOIC')
        pin_count = int(data.get('pin_count', 8))
        pitch = to_decimal(data.get('pitch', '1.27'))
        body_length = to_decimal(data.get('body_length', '4.9'))
        body_width = to_decimal(data.get('body_width', '3.9'))
        
        # Generate IPC name
        ipc_name = AltiumScriptGenerator.generate_ipc_footprint_name(footprint_base_name, data, pin_count)
        footprint_name = f"{ipc_name}_Datasheet" if use_datasheet else f"{ipc_name}_IPC{ipc_class}"
        
        if use_datasheet:
            pad_length = to_decimal(data.get('datasheet_pad_length', '1.5'))
            pad_width = to_decimal(data.get('datasheet_pad_width', '0.6'))
            pad_spacing = to_decimal(data.get('datasheet_pad_spacing', '4.4'))
        else:
            L_min = to_decimal(data.get('L_min', '5.8'))
            L_max = to_decimal(data.get('L_max', '6.2'))
            T_min = to_decimal(data.get('T_min', '0.4'))
            T_max = to_decimal(data.get('T_max', '1.27'))
            W_min = to_decimal(data.get('W_min', '0.31'))
            W_max = to_decimal(data.get('W_max', '0.51'))
            
            land = IPCCalculator.calculate_land_pattern(L_min, L_max, T_min, T_max, W_min, W_max, ipc_class)
            pad_length = land['pad_length']
            pad_width = land['pad_width']
            pad_spacing = land['Gmin']
        
        lines.append("StartFootprints\n")
        lines.append(f"Footprint (Name \"{footprint_name}\")\n")
        
        # Constants
        line_width = Decimal('0.05') * AltiumScriptGenerator.SCALE
        silk_width = Decimal('0.15') * AltiumScriptGenerator.SCALE
        courtyard_width = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_mask = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_paste = Decimal('0.0')
        
        # Body outline
        half_length = body_length / Decimal('2')
        half_width = body_width / Decimal('2')
        
        body_corners = [
            (-half_length, half_width), (half_length, half_width),
            (half_length, -half_width), (-half_length, -half_width),
            (-half_length, half_width)
        ]
        
        for i in range(len(body_corners) - 1):
            x1, y1 = body_corners[i]
            x2, y2 = body_corners[i + 1]
            lines.append(f"Line (Width {line_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        # Pin1 chamfer
        chamfer = Decimal('0.5')
        lines.append(f"Line (Width {line_width}) (Start {-half_length*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (End {(-half_length+chamfer)*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        lines.append(f"Line (Width {line_width}) (Start {-half_length*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (End {-half_length*AltiumScriptGenerator.SCALE}, {(half_width-chamfer)*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        # Pads
        pins_per_side = pin_count // 2
        start_y = (pins_per_side - 1) * pitch / Decimal('2')
        
        for i in range(pins_per_side):
            pin_num = i + 1
            y_pos = start_y - i * pitch
            x_pos = -pad_spacing / Decimal('2') - pad_length / Decimal('2')
            
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
        
        for i in range(pins_per_side):
            pin_num = pin_count - i
            y_pos = start_y - i * pitch
            x_pos = pad_spacing / Decimal('2') + pad_length / Decimal('2')
            
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
        
        # Silkscreen
        silk_gap = Decimal('0.15')
        pad_edge = pad_spacing / Decimal('2') - pad_length / Decimal('2') - silk_gap
        
        if pad_edge > Decimal('0'):
            lines.append(f"Line (Width {silk_width}) (Start {-half_length*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (End {-pad_edge*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
            lines.append(f"Line (Width {silk_width}) (Start {pad_edge*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (End {half_length*AltiumScriptGenerator.SCALE}, {half_width*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
            lines.append(f"Line (Width {silk_width}) (Start {-half_length*AltiumScriptGenerator.SCALE}, {-half_width*AltiumScriptGenerator.SCALE}) (End {-pad_edge*AltiumScriptGenerator.SCALE}, {-half_width*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
            lines.append(f"Line (Width {silk_width}) (Start {pad_edge*AltiumScriptGenerator.SCALE}, {-half_width*AltiumScriptGenerator.SCALE}) (End {half_length*AltiumScriptGenerator.SCALE}, {-half_width*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        # Courtyard
        courtyard_expansion = Decimal('0.25')
        pad_outer_x = pad_spacing / Decimal('2') + pad_length
        pad_outer_y = start_y + pad_width / Decimal('2')
        courtyard_x = max(pad_outer_x, half_length) + courtyard_expansion
        courtyard_y = max(pad_outer_y, half_width) + courtyard_expansion
        
        courtyard_corners = [
            (-courtyard_x, courtyard_y), (courtyard_x, courtyard_y),
            (courtyard_x, -courtyard_y), (-courtyard_x, -courtyard_y),
            (-courtyard_x, courtyard_y)
        ]
        
        for i in range(len(courtyard_corners) - 1):
            x1, y1 = courtyard_corners[i]
            x2, y2 = courtyard_corners[i + 1]
            lines.append(f"Line (Width {courtyard_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical15)")
        
        lines.append("EndFootprint")
        lines.append("EndFootprints")
        return '\n'.join(lines)
    
    @staticmethod
    def generate_qfp_script(data, ipc_class, use_datasheet=False):
        """Generate QFP footprint script"""
        lines = []
        
        footprint_base_name = data.get('footprint_name', 'QFP')
        pin_count = int(data.get('pin_count', 32))
        pitch = to_decimal(data.get('pitch', '0.8'))
        body_size = to_decimal(data.get('body_size', '7.0'))
        
        ipc_name = AltiumScriptGenerator.generate_ipc_footprint_name(footprint_base_name, data, pin_count)
        footprint_name = f"{ipc_name}_Datasheet" if use_datasheet else f"{ipc_name}_IPC{ipc_class}"
        
        if use_datasheet:
            pad_length = to_decimal(data.get('datasheet_pad_length', '1.5'))
            pad_width = to_decimal(data.get('datasheet_pad_width', '0.45'))
            pad_spacing = to_decimal(data.get('datasheet_pad_spacing', '6.4'))
        else:
            L_min = to_decimal(data.get('L_min', '8.8'))
            L_max = to_decimal(data.get('L_max', '9.2'))
            T_min = to_decimal(data.get('T_min', '0.45'))
            T_max = to_decimal(data.get('T_max', '0.75'))
            W_min = to_decimal(data.get('W_min', '0.27'))
            W_max = to_decimal(data.get('W_max', '0.37'))
            
            land = IPCCalculator.calculate_land_pattern(L_min, L_max, T_min, T_max, W_min, W_max, ipc_class)
            pad_length = land['pad_length']
            pad_width = land['pad_width']
            pad_spacing = land['Gmin']
        
        lines.append("StartFootprints\n")
        lines.append(f"Footprint (Name \"{footprint_name}\")\n")
        
        line_width = Decimal('0.05') * AltiumScriptGenerator.SCALE
        silk_width = Decimal('0.15') * AltiumScriptGenerator.SCALE
        courtyard_width = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_mask = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_paste = Decimal('0.0')
        
        half_body = body_size / Decimal('2')
        
        body_corners = [
            (-half_body, half_body), (half_body, half_body),
            (half_body, -half_body), (-half_body, -half_body),
            (-half_body, half_body)
        ]
        
        for i in range(len(body_corners) - 1):
            x1, y1 = body_corners[i]
            x2, y2 = body_corners[i + 1]
            lines.append(f"Line (Width {line_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        chamfer = Decimal('0.7')
        lines.append(f"Line (Width {line_width}) (Start {-half_body*AltiumScriptGenerator.SCALE}, {(half_body-chamfer)*AltiumScriptGenerator.SCALE}) (End {(-half_body+chamfer)*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        pins_per_side = pin_count // 4
        pin_num = 1
        
        # Top side (left to right)
        start_x = -(pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = start_x + i * pitch
            y_pos = pad_spacing / Decimal('2') + pad_length / Decimal('2')
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 90) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        # Right side (top to bottom)
        start_y = (pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = pad_spacing / Decimal('2') + pad_length / Decimal('2')
            y_pos = start_y - i * pitch
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        # Bottom side (right to left)
        start_x = (pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = start_x - i * pitch
            y_pos = -(pad_spacing / Decimal('2') + pad_length / Decimal('2'))
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 90) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        # Left side (bottom to top)
        start_y = -(pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = -(pad_spacing / Decimal('2') + pad_length / Decimal('2'))
            y_pos = start_y + i * pitch
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        # Silkscreen
        top_bottom_pad_extent = pad_width / Decimal('2') + Decimal('0.15')
        left_right_pad_extent = pad_width / Decimal('2') + Decimal('0.15')
        top_left_pad_x = -(pins_per_side - 1) * pitch / Decimal('2')
        top_right_pad_x = (pins_per_side - 1) * pitch / Decimal('2')
        right_top_pad_y = (pins_per_side - 1) * pitch / Decimal('2')
        right_bottom_pad_y = -(pins_per_side - 1) * pitch / Decimal('2')
        
        if top_left_pad_x - top_bottom_pad_extent > -half_body:
            lines.append(f"Line (Width {silk_width}) (Start {-half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {(top_left_pad_x-top_bottom_pad_extent)*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        if top_right_pad_x + top_bottom_pad_extent < half_body:
            lines.append(f"Line (Width {silk_width}) (Start {(top_right_pad_x+top_bottom_pad_extent)*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        if right_top_pad_y + left_right_pad_extent < half_body:
            lines.append(f"Line (Width {silk_width}) (Start {half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {half_body*AltiumScriptGenerator.SCALE}, {(right_top_pad_y+left_right_pad_extent)*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        if right_bottom_pad_y - left_right_pad_extent > -half_body:
            lines.append(f"Line (Width {silk_width}) (Start {half_body*AltiumScriptGenerator.SCALE}, {(right_bottom_pad_y-left_right_pad_extent)*AltiumScriptGenerator.SCALE}) (End {half_body*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        if top_right_pad_x + top_bottom_pad_extent < half_body:
            lines.append(f"Line (Width {silk_width}) (Start {half_body*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (End {(top_right_pad_x+top_bottom_pad_extent)*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        if top_left_pad_x - top_bottom_pad_extent > -half_body:
            lines.append(f"Line (Width {silk_width}) (Start {(top_left_pad_x-top_bottom_pad_extent)*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (End {-half_body*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        if right_bottom_pad_y - left_right_pad_extent > -half_body:
            lines.append(f"Line (Width {silk_width}) (Start {-half_body*AltiumScriptGenerator.SCALE}, {-half_body*AltiumScriptGenerator.SCALE}) (End {-half_body*AltiumScriptGenerator.SCALE}, {(right_bottom_pad_y-left_right_pad_extent)*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        chamfer_clearance = chamfer + Decimal('0.15')
        if right_top_pad_y + left_right_pad_extent < half_body - chamfer_clearance:
            lines.append(f"Line (Width {silk_width}) (Start {-half_body*AltiumScriptGenerator.SCALE}, {(right_top_pad_y+left_right_pad_extent)*AltiumScriptGenerator.SCALE}) (End {-half_body*AltiumScriptGenerator.SCALE}, {(half_body-chamfer_clearance)*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        pin1_dot_radius = Decimal('0.3')
        pin1_arc_width = Decimal('0.15') * AltiumScriptGenerator.SCALE
        pin1_dot_x = -half_body + Decimal('0.6')
        pin1_dot_y = half_body - Decimal('0.6')
        lines.append(f"Arc (Width {pin1_arc_width}) (Location {pin1_dot_x*AltiumScriptGenerator.SCALE}, {pin1_dot_y*AltiumScriptGenerator.SCALE}) (Radius {pin1_dot_radius*AltiumScriptGenerator.SCALE}) (StartAngle 0) (EndAngle 360) (Layer TopOverlay)")
        
        # Courtyard
        courtyard_expansion = Decimal('0.25')
        pad_outer_edge = pad_spacing / Decimal('2') + pad_length
        outermost = max(half_body, pad_outer_edge)
        courtyard_size = outermost + courtyard_expansion
        
        courtyard_corners = [
            (-courtyard_size, courtyard_size), (courtyard_size, courtyard_size),
            (courtyard_size, -courtyard_size), (-courtyard_size, -courtyard_size),
            (-courtyard_size, courtyard_size)
        ]
        
        for i in range(len(courtyard_corners) - 1):
            x1, y1 = courtyard_corners[i]
            x2, y2 = courtyard_corners[i + 1]
            lines.append(f"Line (Width {courtyard_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical15)")
        
        lines.append("EndFootprint")
        lines.append("EndFootprints")
        return '\n'.join(lines)
    
    @staticmethod
    def generate_qfn_script(data, ipc_class, use_datasheet=False):
        """Generate QFN footprint script"""
        lines = []
        
        footprint_base_name = data.get('footprint_name', 'QFN')
        pin_count = int(data.get('pin_count', 32))
        pitch = to_decimal(data.get('pitch', '0.5'))
        body_size = to_decimal(data.get('body_size', '5.0'))
        has_thermal_pad = data.get('has_thermal_pad', True)
        thermal_pad_size = to_decimal(data.get('thermal_pad_size', '3.3'))
        
        ipc_name = AltiumScriptGenerator.generate_ipc_footprint_name(footprint_base_name, data, pin_count)
        footprint_name = f"{ipc_name}_Datasheet" if use_datasheet else f"{ipc_name}_IPC{ipc_class}"
        
        if use_datasheet:
            pad_length = to_decimal(data.get('datasheet_pad_length', '0.8'))
            pad_width = to_decimal(data.get('datasheet_pad_width', '0.3'))
            pad_spacing = to_decimal(data.get('datasheet_pad_spacing', '4.1'))
        else:
            L_min = to_decimal(data.get('L_min', '4.9'))
            L_max = to_decimal(data.get('L_max', '5.1'))
            T_min = to_decimal(data.get('T_min', '0.2'))
            T_max = to_decimal(data.get('T_max', '0.4'))
            W_min = to_decimal(data.get('W_min', '0.2'))
            W_max = to_decimal(data.get('W_max', '0.3'))
            
            land = IPCCalculator.calculate_land_pattern(L_min, L_max, T_min, T_max, W_min, W_max, ipc_class)
            pad_length = land['pad_length']
            pad_width = land['pad_width']
            pad_spacing = land['Gmin']
        
        lines.append("StartFootprints\n")
        lines.append(f"Footprint (Name \"{footprint_name}\")\n")
        
        line_width = Decimal('0.05') * AltiumScriptGenerator.SCALE
        silk_width = Decimal('0.15') * AltiumScriptGenerator.SCALE
        courtyard_width = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_mask = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_paste = Decimal('0.0')
        
        half_body = body_size / Decimal('2')
        
        body_corners = [
            (-half_body, half_body), (half_body, half_body),
            (half_body, -half_body), (-half_body, -half_body),
            (-half_body, half_body)
        ]
        
        for i in range(len(body_corners) - 1):
            x1, y1 = body_corners[i]
            x2, y2 = body_corners[i + 1]
            lines.append(f"Line (Width {line_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        pin1_radius = Decimal('0.3')
        arc_width = Decimal('0.05') * AltiumScriptGenerator.SCALE
        pin1_x = -half_body + Decimal('0.5')
        pin1_y = half_body - Decimal('0.5')
        lines.append(f"Arc (Width {arc_width}) (Location {pin1_x*AltiumScriptGenerator.SCALE}, {pin1_y*AltiumScriptGenerator.SCALE}) (Radius {pin1_radius*AltiumScriptGenerator.SCALE}) (StartAngle 0) (EndAngle 360) (Layer Mechanical13)")
        
        pins_per_side = pin_count // 4
        pin_num = 1
        
        # Same pad generation as QFP (counter-clockwise)
        start_x = -(pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = start_x + i * pitch
            y_pos = pad_spacing / Decimal('2') + pad_length / Decimal('2')
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 90) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        start_y = (pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = pad_spacing / Decimal('2') + pad_length / Decimal('2')
            y_pos = start_y - i * pitch
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        start_x = (pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = start_x - i * pitch
            y_pos = -(pad_spacing / Decimal('2') + pad_length / Decimal('2'))
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 90) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        start_y = -(pins_per_side - 1) * pitch / Decimal('2')
        for i in range(pins_per_side):
            x_pos = -(pad_spacing / Decimal('2') + pad_length / Decimal('2'))
            y_pos = start_y + i * pitch
            lines.append(f"Pad (Name \"{pin_num}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
            lines.append(f"PadShape (Size {pad_length*AltiumScriptGenerator.SCALE}, {pad_width*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
            pin_num += 1
        
        # Thermal pad
        if has_thermal_pad:
            thermal_expand_paste = -Decimal('0.1') * AltiumScriptGenerator.SCALE
            lines.append(f"Pad (Name \"{pin_num}\") (Location 0, 0) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {thermal_expand_paste})")
            lines.append(f"PadShape (Size {thermal_pad_size*AltiumScriptGenerator.SCALE}, {thermal_pad_size*AltiumScriptGenerator.SCALE}) (Shape Rectangular) (Layer Top)")
            lines.append("EndPad")
        
        # Silkscreen L-marks
        silk_gap = Decimal('0.2')
        top_bottom_pad_extent = pad_width / Decimal('2') + silk_gap
        top_left_pad_x = -(pins_per_side - 1) * pitch / Decimal('2')
        top_right_pad_x = (pins_per_side - 1) * pitch / Decimal('2')
        corner_length = Decimal('1.5')
        
        if top_left_pad_x - top_bottom_pad_extent > -half_body:
            tl_h_end = min(-half_body + corner_length, top_left_pad_x - top_bottom_pad_extent)
            lines.append(f"Line (Width {silk_width}) (Start {-half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {tl_h_end*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        if top_right_pad_x + top_bottom_pad_extent < half_body:
            tr_h_start = max(half_body - corner_length, top_right_pad_x + top_bottom_pad_extent)
            lines.append(f"Line (Width {silk_width}) (Start {tr_h_start*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        # Pin 1 triangle
        triangle_size = Decimal('0.6')
        triangle_offset = Decimal('0.2')
        tri_x = -half_body - triangle_offset
        lines.append(f"Line (Width {silk_width}) (Start {tri_x*AltiumScriptGenerator.SCALE}, {(half_body+Decimal('0.3'))*AltiumScriptGenerator.SCALE}) (End {(tri_x-triangle_size)*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        lines.append(f"Line (Width {silk_width}) (Start {(tri_x-triangle_size)*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (End {tri_x*AltiumScriptGenerator.SCALE}, {(half_body-Decimal('0.3'))*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        lines.append(f"Line (Width {silk_width}) (Start {tri_x*AltiumScriptGenerator.SCALE}, {(half_body-Decimal('0.3'))*AltiumScriptGenerator.SCALE}) (End {tri_x*AltiumScriptGenerator.SCALE}, {(half_body+Decimal('0.3'))*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        # Courtyard
        courtyard_expansion = Decimal('0.25')
        pad_outer_edge = pad_spacing / Decimal('2') + pad_length
        thermal_outer = thermal_pad_size / Decimal('2') if has_thermal_pad else Decimal('0')
        outermost = max(half_body, pad_outer_edge, thermal_outer)
        courtyard_size = outermost + courtyard_expansion
        
        courtyard_corners = [
            (-courtyard_size, courtyard_size), (courtyard_size, courtyard_size),
            (courtyard_size, -courtyard_size), (-courtyard_size, -courtyard_size),
            (-courtyard_size, courtyard_size)
        ]
        
        for i in range(len(courtyard_corners) - 1):
            x1, y1 = courtyard_corners[i]
            x2, y2 = courtyard_corners[i + 1]
            lines.append(f"Line (Width {courtyard_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical15)")
        
        lines.append("EndFootprint")
        lines.append("EndFootprints")
        return '\n'.join(lines)
    
    @staticmethod
    def generate_bga_script(data, ipc_class, use_datasheet=False):
        """Generate BGA footprint script"""
        lines = []
        
        footprint_base_name = data.get('footprint_name', 'BGA')
        rows = int(data.get('rows', 10))
        columns = int(data.get('columns', 10))
        pitch = to_decimal(data.get('pitch', '0.8'))
        ball_diameter = to_decimal(data.get('ball_diameter', '0.4'))
        body_size = to_decimal(data.get('body_size', '8.0'))
        
        ipc_name = AltiumScriptGenerator.generate_ipc_footprint_name(footprint_base_name, data, rows * columns)
        footprint_name = f"{ipc_name}_Datasheet" if use_datasheet else f"{ipc_name}_IPC{ipc_class}"
        
        if use_datasheet:
            pad_diameter = to_decimal(data.get('datasheet_pad_diameter', '0.35'))
        else:
            pad_size_factors = {'A': Decimal('1.0'), 'B': Decimal('0.8'), 'C': Decimal('0.6')}
            pad_diameter = ball_diameter * pad_size_factors[ipc_class]
        
        lines.append("StartFootprints\n")
        lines.append(f"Footprint (Name \"{footprint_name}\")\n")
        
        line_width = Decimal('0.05') * AltiumScriptGenerator.SCALE
        silk_width = Decimal('0.2') * AltiumScriptGenerator.SCALE
        arc_width = Decimal('0.1') * AltiumScriptGenerator.SCALE
        courtyard_width = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_mask = Decimal('0.1') * AltiumScriptGenerator.SCALE
        expand_paste = Decimal('0.0')
        
        half_body = body_size / Decimal('2')
        
        body_corners = [
            (-half_body, half_body), (half_body, half_body),
            (half_body, -half_body), (-half_body, -half_body),
            (-half_body, half_body)
        ]
        
        for i in range(len(body_corners) - 1):
            x1, y1 = body_corners[i]
            x2, y2 = body_corners[i + 1]
            lines.append(f"Line (Width {line_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical13)")
        
        pin1_radius = Decimal('0.5')
        lines.append(f"Arc (Width {arc_width}) (Location {-half_body*AltiumScriptGenerator.SCALE}, {half_body*AltiumScriptGenerator.SCALE}) (Radius {pin1_radius*AltiumScriptGenerator.SCALE}) (StartAngle 0) (EndAngle 360) (Layer TopOverlay)")
        
        silk_inset = Decimal('0.3')
        silk_size = half_body - silk_inset
        
        lines.append(f"Line (Width {silk_width}) (Start {-silk_size*AltiumScriptGenerator.SCALE}, {-silk_size*AltiumScriptGenerator.SCALE}) (End {silk_size*AltiumScriptGenerator.SCALE}, {-silk_size*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        lines.append(f"Line (Width {silk_width}) (Start {silk_size*AltiumScriptGenerator.SCALE}, {-silk_size*AltiumScriptGenerator.SCALE}) (End {silk_size*AltiumScriptGenerator.SCALE}, {silk_size*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        lines.append(f"Line (Width {silk_width}) (Start {silk_size*AltiumScriptGenerator.SCALE}, {silk_size*AltiumScriptGenerator.SCALE}) (End {-silk_size*AltiumScriptGenerator.SCALE}, {silk_size*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        lines.append(f"Line (Width {silk_width}) (Start {-silk_size*AltiumScriptGenerator.SCALE}, {silk_size*AltiumScriptGenerator.SCALE}) (End {-silk_size*AltiumScriptGenerator.SCALE}, {-silk_size*AltiumScriptGenerator.SCALE}) (Layer TopOverlay)")
        
        start_x = -(columns - 1) * pitch / Decimal('2')
        start_y = (rows - 1) * pitch / Decimal('2')
        row_labels = 'ABCDEFGHJKLMNPRTUVWY'
        
        for row in range(rows):
            for col in range(columns):
                x_pos = start_x + col * pitch
                y_pos = start_y - row * pitch
                pin_name = f"{row_labels[row]}{col+1}"
                
                lines.append(f"Pad (Name \"{pin_name}\") (Location {x_pos*AltiumScriptGenerator.SCALE}, {y_pos*AltiumScriptGenerator.SCALE}) (Surface True) (Rotation 0) (ExpandMask {expand_mask}) (ExpandPaste {expand_paste})")
                lines.append(f"PadShape (Size {pad_diameter*AltiumScriptGenerator.SCALE}, {pad_diameter*AltiumScriptGenerator.SCALE}) (Shape Rounded) (Layer Top)")
                lines.append("EndPad")
        
        courtyard_expansion = Decimal('0.5')
        ball_outer_x = abs(start_x) + (columns - 1) * pitch / Decimal('2') + pad_diameter / Decimal('2')
        ball_outer_y = abs(start_y) + pad_diameter / Decimal('2')
        outermost = max(half_body, ball_outer_x, ball_outer_y)
        courtyard_size = outermost + courtyard_expansion
        
        courtyard_corners = [
            (-courtyard_size, courtyard_size), (courtyard_size, courtyard_size),
            (courtyard_size, -courtyard_size), (-courtyard_size, -courtyard_size),
            (-courtyard_size, courtyard_size)
        ]
        
        for i in range(len(courtyard_corners) - 1):
            x1, y1 = courtyard_corners[i]
            x2, y2 = courtyard_corners[i + 1]
            lines.append(f"Line (Width {courtyard_width}) (Start {x1*AltiumScriptGenerator.SCALE}, {y1*AltiumScriptGenerator.SCALE}) (End {x2*AltiumScriptGenerator.SCALE}, {y2*AltiumScriptGenerator.SCALE}) (Layer Mechanical15)")
        
        lines.append("EndFootprint")
        lines.append("EndFootprints")
        return '\n'.join(lines)


class PackageInputWidget(QWidget):
    """Base widget for package-specific inputs"""
    
    def __init__(self, package_type, parent=None):
        super().__init__(parent)
        self.package_type = package_type
        self.inputs = {}
        self.main_window = None  # Store reference to main window
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Land pattern source selection
        source_group = QGroupBox("Land Pattern Source")
        source_layout = QVBoxLayout()
        
        self.pattern_source_group = QButtonGroup(self)
        
        self.use_ipc_radio = QRadioButton("Use IPC-7351 Calculations")
        self.use_ipc_radio.setChecked(True)
        self.use_ipc_radio.toggled.connect(self.toggle_input_mode)
        self.pattern_source_group.addButton(self.use_ipc_radio)
        source_layout.addWidget(self.use_ipc_radio)
        
        self.use_datasheet_radio = QRadioButton("Use Datasheet Recommended Values")
        self.pattern_source_group.addButton(self.use_datasheet_radio)
        source_layout.addWidget(self.use_datasheet_radio)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # Common parameters
        common_group = QGroupBox("Common Parameters")
        common_layout = QGridLayout()
        
        row = 0
        common_layout.addWidget(QLabel("Footprint Name:"), row, 0)
        self.inputs['footprint_name'] = QLineEdit(f"{self.package_type}_8")
        common_layout.addWidget(self.inputs['footprint_name'], row, 1)
        
        row += 1
        common_layout.addWidget(QLabel("Pin Count:"), row, 0)
        self.inputs['pin_count'] = QLineEdit("8" if self.package_type != "BGA" else "100")
        common_layout.addWidget(self.inputs['pin_count'], row, 1)
        
        row += 1
        common_layout.addWidget(QLabel("Pitch (mm):"), row, 0)
        pitch_default = {"SOP": "1.27", "SOIC": "1.27", "QFP": "0.8", "QFN": "0.5", "BGA": "0.8"}
        self.inputs['pitch'] = QLineEdit(pitch_default.get(self.package_type, "1.27"))
        common_layout.addWidget(self.inputs['pitch'], row, 1)
        
        common_group.setLayout(common_layout)
        layout.addWidget(common_group)
        
        # IPC calculation parameters
        self.ipc_params_widget = QWidget()
        self.add_ipc_parameters(self.ipc_params_widget)
        layout.addWidget(self.ipc_params_widget)
        
        # Datasheet parameters
        self.datasheet_params_widget = QWidget()
        self.add_datasheet_parameters(self.datasheet_params_widget)
        self.datasheet_params_widget.setVisible(False)
        layout.addWidget(self.datasheet_params_widget)
        
        # IPC Class selection (only for IPC mode)
        self.ipc_class_widget = QGroupBox("IPC-7351 Land Pattern Class")
        ipc_layout = QVBoxLayout()
        
        self.ipc_group = QButtonGroup(self)
        for ipc_class, desc in [("A", "Maximum (Low Density)"), 
                                 ("B", "Nominal (Moderate Density)"), 
                                 ("C", "Minimum (High Density)")]:
            rb = QRadioButton(f"Class {ipc_class}: {desc}")
            rb.setProperty("ipc_class", ipc_class)
            self.ipc_group.addButton(rb)
            ipc_layout.addWidget(rb)
            if ipc_class == "B":
                rb.setChecked(True)
        
        self.ipc_class_widget.setLayout(ipc_layout)
        layout.addWidget(self.ipc_class_widget)
        
        # Generate buttons
        self.generate_single_btn = QPushButton("Generate Selected Pattern")
        self.generate_single_btn.clicked.connect(self.generate_single)
        layout.addWidget(self.generate_single_btn)
        
        self.generate_all_btn = QPushButton("Generate Datasheet + All IPC Classes (4 variants)")
        self.generate_all_btn.clicked.connect(self.generate_all_variants)
        layout.addWidget(self.generate_all_btn)
        
        layout.addStretch()
    
    def set_main_window(self, main_window):
        """Set reference to main window"""
        self.main_window = main_window
    
    def toggle_input_mode(self):
        """Toggle between IPC and datasheet input modes"""
        use_ipc = self.use_ipc_radio.isChecked()
        self.ipc_params_widget.setVisible(use_ipc)
        self.ipc_class_widget.setVisible(use_ipc)
        self.datasheet_params_widget.setVisible(not use_ipc)
    
    def add_ipc_parameters(self, parent):
        """Add IPC calculation parameters"""
        layout = QVBoxLayout(parent)
        
        if self.package_type in ["SOP", "SOIC", "QFP", "QFN"]:
            dims_group = QGroupBox("Component Dimensions for IPC Calculation (mm)")
            dims_layout = QGridLayout()
            
            row = 0
            dims_layout.addWidget(QLabel("Lead Span Min (L_min):"), row, 0)
            self.inputs['L_min'] = QLineEdit("5.8")
            dims_layout.addWidget(self.inputs['L_min'], row, 1)
            
            dims_layout.addWidget(QLabel("Lead Span Max (L_max):"), row, 2)
            self.inputs['L_max'] = QLineEdit("6.2")
            dims_layout.addWidget(self.inputs['L_max'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Lead Length Min (T_min):"), row, 0)
            self.inputs['T_min'] = QLineEdit("0.4")
            dims_layout.addWidget(self.inputs['T_min'], row, 1)
            
            dims_layout.addWidget(QLabel("Lead Length Max (T_max):"), row, 2)
            self.inputs['T_max'] = QLineEdit("1.27")
            dims_layout.addWidget(self.inputs['T_max'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Lead Width Min (W_min):"), row, 0)
            self.inputs['W_min'] = QLineEdit("0.31")
            dims_layout.addWidget(self.inputs['W_min'], row, 1)
            
            dims_layout.addWidget(QLabel("Lead Width Max (W_max):"), row, 2)
            self.inputs['W_max'] = QLineEdit("0.51")
            dims_layout.addWidget(self.inputs['W_max'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Body Length/Size:"), row, 0)
            body_key = 'body_size' if self.package_type in ['QFP', 'QFN'] else 'body_length'
            self.inputs[body_key] = QLineEdit("5.0")
            dims_layout.addWidget(self.inputs[body_key], row, 1)
            
            if self.package_type in ['SOP', 'SOIC']:
                dims_layout.addWidget(QLabel("Body Width:"), row, 2)
                self.inputs['body_width'] = QLineEdit("4.0")
                dims_layout.addWidget(self.inputs['body_width'], row, 3)
            
            dims_group.setLayout(dims_layout)
            layout.addWidget(dims_group)
        
        elif self.package_type == "BGA":
            dims_group = QGroupBox("BGA Dimensions (mm)")
            dims_layout = QGridLayout()
            
            row = 0
            dims_layout.addWidget(QLabel("Rows:"), row, 0)
            self.inputs['rows'] = QLineEdit("10")
            dims_layout.addWidget(self.inputs['rows'], row, 1)
            
            dims_layout.addWidget(QLabel("Columns:"), row, 2)
            self.inputs['columns'] = QLineEdit("10")
            dims_layout.addWidget(self.inputs['columns'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Ball Diameter:"), row, 0)
            self.inputs['ball_diameter'] = QLineEdit("0.4")
            dims_layout.addWidget(self.inputs['ball_diameter'], row, 1)
            
            dims_layout.addWidget(QLabel("Body Size:"), row, 2)
            self.inputs['body_size'] = QLineEdit("8.0")
            dims_layout.addWidget(self.inputs['body_size'], row, 3)
            
            dims_group.setLayout(dims_layout)
            layout.addWidget(dims_group)
    
    def add_datasheet_parameters(self, parent):
        """Add datasheet recommended parameters"""
        layout = QVBoxLayout(parent)
        
        dims_group = QGroupBox("Datasheet Recommended Land Pattern (mm)")
        dims_layout = QGridLayout()
        
        if self.package_type in ["SOP", "SOIC", "QFP", "QFN"]:
            row = 0
            dims_layout.addWidget(QLabel("Pad Length (Y):"), row, 0)
            self.inputs['datasheet_pad_length'] = QLineEdit("1.5")
            dims_layout.addWidget(self.inputs['datasheet_pad_length'], row, 1)
            
            dims_layout.addWidget(QLabel("Pad Width (X):"), row, 2)
            self.inputs['datasheet_pad_width'] = QLineEdit("0.6")
            dims_layout.addWidget(self.inputs['datasheet_pad_width'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Pad Spacing (G):"), row, 0)
            self.inputs['datasheet_pad_spacing'] = QLineEdit("4.4")
            dims_layout.addWidget(self.inputs['datasheet_pad_spacing'], row, 1)
            
            row += 1
            dims_layout.addWidget(QLabel("Body Length/Size:"), row, 0)
            body_key = 'body_size_ds' if self.package_type in ['QFP', 'QFN'] else 'body_length_ds'
            self.inputs[body_key] = QLineEdit("5.0")
            dims_layout.addWidget(self.inputs[body_key], row, 1)
            
            if self.package_type in ['SOP', 'SOIC']:
                dims_layout.addWidget(QLabel("Body Width:"), row, 2)
                self.inputs['body_width_ds'] = QLineEdit("4.0")
                dims_layout.addWidget(self.inputs['body_width_ds'], row, 3)
        
        elif self.package_type == "BGA":
            row = 0
            dims_layout.addWidget(QLabel("Pad Diameter:"), row, 0)
            self.inputs['datasheet_pad_diameter'] = QLineEdit("0.35")
            dims_layout.addWidget(self.inputs['datasheet_pad_diameter'], row, 1)
            
            dims_layout.addWidget(QLabel("Rows:"), row, 2)
            self.inputs['rows_ds'] = QLineEdit("10")
            dims_layout.addWidget(self.inputs['rows_ds'], row, 3)
            
            row += 1
            dims_layout.addWidget(QLabel("Columns:"), row, 0)
            self.inputs['columns_ds'] = QLineEdit("10")
            dims_layout.addWidget(self.inputs['columns_ds'], row, 1)
            
            dims_layout.addWidget(QLabel("Body Size:"), row, 2)
            self.inputs['body_size_ds'] = QLineEdit("8.0")
            dims_layout.addWidget(self.inputs['body_size_ds'], row, 3)
        
        dims_group.setLayout(dims_layout)
        layout.addWidget(dims_group)
    
    def get_data(self):
        """Collect all input data"""
        data = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, QLineEdit):
                data[key] = widget.text()
            elif isinstance(widget, QCheckBox):
                data[key] = widget.isChecked()
        return data
    
    def get_selected_ipc_class(self):
        """Get selected IPC class"""
        for button in self.ipc_group.buttons():
            if button.isChecked():
                return button.property("ipc_class")
        return "B"
    
    def is_datasheet_mode(self):
        """Check if datasheet mode is selected"""
        return self.use_datasheet_radio.isChecked()
    
    def generate_single(self):
        """Generate single footprint"""
        if self.main_window:
            self.main_window.generate_script()
    
    def generate_all_variants(self):
        """Generate all variants (datasheet + IPC A, B, C)"""
        if self.main_window:
            self.main_window.generate_all_variants()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IPC Footprint Generator - Datasheet + IPC Classes")
        self.setGeometry(100, 100, 1000, 750)
        
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # Left side: Package selection and inputs
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Title
        title = QLabel("IPC-7351 Footprint Generator")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title)
        
        subtitle = QLabel("Supports Datasheet Recommendations & IPC Classes A/B/C")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(subtitle)
        
        # Package type selection
        
        # Input tabs
        self.input_tabs = QTabWidget()
        self.package_widgets = {}
        
        for pkg in ["SOP", "SOIC", "QFP", "QFN", "BGA"]:
            widget = PackageInputWidget(pkg)
            widget.set_main_window(self)  # Set reference to main window
            self.package_widgets[pkg] = widget
            self.input_tabs.addTab(widget, pkg)
        
        left_layout.addWidget(self.input_tabs)
        
        main_layout.addWidget(left_widget, 1)
        
        # Right side: Script output
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        output_label = QLabel("Generated Altium Script:")
        output_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        right_layout.addWidget(output_label)
        
        self.script_output = QTextEdit()
        self.script_output.setFont(QFont("Courier New", 9))
        self.script_output.setReadOnly(True)
        right_layout.addWidget(self.script_output)
        
        # Save button
        self.save_btn = QPushButton("Save Script to File")
        self.save_btn.clicked.connect(self.save_script)
        right_layout.addWidget(self.save_btn)
        
        main_layout.addWidget(right_widget, 1)
    
    def switch_package(self):
        """Switch to the selected package tab"""
        sender = self.sender()
        package = sender.property("package")
        
        for i in range(self.input_tabs.count()):
            if self.input_tabs.tabText(i) == package:
                self.input_tabs.setCurrentIndex(i)
                break
    
    def generate_script(self):
        """Generate script for selected configuration"""
        current_widget = self.input_tabs.currentWidget()
        package_type = current_widget.package_type
        data = current_widget.get_data()
        use_datasheet = current_widget.is_datasheet_mode()
        ipc_class = current_widget.get_selected_ipc_class()
        
        try:
            if package_type in ["SOP", "SOIC"]:
                script = AltiumScriptGenerator.generate_sop_soic_script(data, ipc_class, use_datasheet)
            elif package_type == "QFP":
                script = AltiumScriptGenerator.generate_qfp_script(data, ipc_class, use_datasheet)
            elif package_type == "QFN":
                script = AltiumScriptGenerator.generate_qfn_script(data, ipc_class, use_datasheet)
            elif package_type == "BGA":
                script = AltiumScriptGenerator.generate_bga_script(data, ipc_class, use_datasheet)
            else:
                script = "Package type not implemented yet."
            
            self.script_output.setPlainText(script)
            
            if use_datasheet:
                QMessageBox.information(self, "Success", f"Generated {package_type} footprint using Datasheet values")
            else:
                QMessageBox.information(self, "Success", f"Generated {package_type} footprint with IPC Class {ipc_class}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate script:\n{str(e)}")
    
    def generate_all_variants(self):
        """Generate all variants: datasheet + IPC A, B, C"""
        current_widget = self.input_tabs.currentWidget()
        package_type = current_widget.package_type
        data = current_widget.get_data()
        
        all_scripts = []
        
        # Generate datasheet version
        try:
            if package_type in ["SOP", "SOIC"]:
                script = AltiumScriptGenerator.generate_sop_soic_script(data, 'B', use_datasheet=True)
            elif package_type == "QFP":
                script = AltiumScriptGenerator.generate_qfp_script(data, 'B', use_datasheet=True)
            elif package_type == "QFN":
                script = AltiumScriptGenerator.generate_qfn_script(data, 'B', use_datasheet=True)
            elif package_type == "BGA":
                script = AltiumScriptGenerator.generate_bga_script(data, 'B', use_datasheet=True)
            
            all_scripts.append(f"; ===== DATASHEET RECOMMENDED =====\n{script}\n\n")
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to generate Datasheet version:\n{str(e)}")
        
        # Generate IPC classes
        for ipc_class in ['A', 'B', 'C']:
            try:
                if package_type in ["SOP", "SOIC"]:
                    script = AltiumScriptGenerator.generate_sop_soic_script(data, ipc_class, use_datasheet=False)
                elif package_type == "QFP":
                    script = AltiumScriptGenerator.generate_qfp_script(data, ipc_class, use_datasheet=False)
                elif package_type == "QFN":
                    script = AltiumScriptGenerator.generate_qfn_script(data, ipc_class, use_datasheet=False)
                elif package_type == "BGA":
                    script = AltiumScriptGenerator.generate_bga_script(data, ipc_class, use_datasheet=False)
                
                all_scripts.append(f"; ===== IPC CLASS {ipc_class} =====\n{script}\n\n")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to generate IPC Class {ipc_class}:\n{str(e)}")
                return
        
        combined_script = '\n'.join(all_scripts)
        self.script_output.setPlainText(combined_script)
        QMessageBox.information(self, "Success", 
                               f"Generated {package_type} footprints:\n" +
                               "- Datasheet Recommended\n" +
                               "- IPC Class A (Maximum)\n" +
                               "- IPC Class B (Nominal)\n" +
                               "- IPC Class C (Minimum)")
    
    def save_script(self):
        """Save the generated script to a text file"""
        script = self.script_output.toPlainText()
        
        if not script or script.strip() == "":
            QMessageBox.warning(self, "Warning", "No script to save. Generate a footprint first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Altium Script", "", "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(script)
                QMessageBox.information(self, "Success", f"Script saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
