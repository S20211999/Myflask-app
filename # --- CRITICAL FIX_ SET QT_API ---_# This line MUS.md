
I'll help you create individual database tables for each package type with columns that map to the specific input fields. Here's the updated database structure:

## Updated Database Initialization

```python
def init_database(self):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Discrete packages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DiscreteN (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'DiscreteN',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pad_length REAL,
            pad_width REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            airgap REAL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DiscreteF (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'DiscreteF',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pad_length REAL,
            pad_width REAL,
            fillet_radius REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            airgap REAL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    # SOT-23 packages tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sot23N (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'Sot23N',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            pin_count INTEGER DEFAULT 3,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sot23NMPE (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'Sot23NMPE',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            mp_expansion REAL,
            pin_count INTEGER DEFAULT 3,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sot23F (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'Sot23F',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            fillet_radius REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            pin_count INTEGER DEFAULT 3,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Sot23FMPE (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'Sot23FMPE',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            fillet_radius REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            mp_expansion REAL,
            pin_count INTEGER DEFAULT 3,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    # TO Package tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TOPackageN (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'TOPackageN',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            tab_length REAL,
            tab_width REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            pin_count INTEGER,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    # Continue with other package types...
    # Dual Side packages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DualSideN (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_number TEXT NOT NULL,
            footprint_name TEXT,
            component_type TEXT DEFAULT 'DualSideN',
            body_length REAL,
            body_width REAL,
            body_height REAL,
            pitch REAL,
            pad_length REAL,
            pad_width REAL,
            row_spacing REAL,
            mask_expansion REAL,
            paste_expansion REAL,
            pin_count INTEGER,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            altium_script_path TEXT,
            allegro_script_path TEXT,
            pads_script_path TEXT,
            xpedition_script_path TEXT
        )''')
    
    # Add more tables for other package types as needed...
    
    conn.commit()
    conn.close()
```

## Updated BaseGeneratorPage Class

```python
class BaseGeneratorPage(QWidget):
    """
    A base class that encapsulates generation AND file-saving logic.
    Each page saves to its specific database table.
    """
    generationFinalized = Signal(dict, str)  # Add table_name parameter
    
    def __init__(self, table_name, parent=None):
        super().__init__(parent)
        self.table_name = table_name  # Store the table name for this page
        # ... rest of initialization code ...
    
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
                
                # Emit with table name
                self.generationFinalized.emit(data, self.table_name)
            else:
                QMessageBox.critical(self, "Generation Failed", "Failed to generate any scripts:\n\n" + "\n".join(errors))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred during the process:\n\n{e}")
```

## Updated Specific Generator Classes

```python
class DiscreteN(BaseGeneratorPage):
    """Generator page for discrete normal packages"""
    
    def __init__(self, parent=None):
        super().__init__("DiscreteN", parent)  # Pass table name
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

class DiscreteF(BaseGeneratorPage):
    """Generator page for discrete fillet packages"""
    
    def __init__(self, parent=None):
        super().__init__("DiscreteF", parent)
        self.input_fields = {
            "Part Number": QLineEdit(),
            "Footprint Name": QLineEdit(),
            "Body Length (mm)": QLineEdit(),
            "Body Width (mm)": QLineEdit(),
            "Body Height (mm)": QLineEdit(),
            "Pad Length (mm)": QLineEdit(),
            "Pad Width (mm)": QLineEdit(),
            "Fillet Radius (mm)": QLineEdit(),
            "Mask Expansion (mm)": QLineEdit(),
            "Paste Expansion (mm)": QLineEdit(),
            "Airgap (mm)": QLineEdit(),
        }
        for label, field in self.input_fields.items():
            self.form_layout.addRow(label, field)

class Sot23N(BaseGeneratorPage):
    """Generator page for SOT-23 normal packages"""
    
    def __init__(self, parent=None):
        super().__init__("Sot23N", parent)
        self.input_fields = {
            "Part Number": QLineEdit(),
            "Footprint Name": QLineEdit(),
            "Body Length (mm)": QLineEdit(),
            "Body Width (mm)": QLineEdit(),
            "Body Height (mm)": QLineEdit(),
            "Pitch (mm)": QLineEdit(),
            "Pad Length (mm)": QLineEdit(),
            "Pad Width (mm)": QLineEdit(),
            "Mask Expansion (mm)": QLineEdit(),
            "Paste Expansion (mm)": QLineEdit(),
            "Pin Count": QLineEdit(),
        }
        for label, field in self.input_fields.items():
            self.form_layout.addRow(label, field)
        
        # Set default pin count
        self.input_fields["Pin Count"].setText("3")
```

## Updated MainWindow Save Method

```python
def handle_save_to_database(self, data, table_name):
    """Receives data and table name, saves to the specific table"""
    try:
        self.save_footprint_to_db(data, table_name)
        print(f"Successfully saved {data['footprint_name']} to {table_name} table.")
    except Exception as e:
        QMessageBox.critical(self, "Database Error", f"The script files were saved, but a database error occurred:\n\n{e}")

def save_footprint_to_db(self, data, table_name):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    # Build column names and values based on input data
    columns = ["part_number", "footprint_name", "component_type"]
    values = [
        data.get('part_number', 'N/A'),
        data.get('footprint_name', 'N/A'),
        table_name
    ]
    
    # Add script paths
    part_number = data.get('part_number', 'N/A')
    columns.extend(["altium_script_path", "allegro_script_path", "pads_script_path", "xpedition_script_path"])
    values.extend([
        os.path.join(self.script_paths['altium'], f"{part_number}_altium.txt"),
        os.path.join(self.script_paths['allegro'], f"{part_number}_allegro.scr"),
        os.path.join(self.script_paths['pads'], f"{part_number}_pads.asc"),
        os.path.join(self.script_paths['xpedition'], f"{part_number}_xpedition.scr")
    ])
    
    # Add dimension fields based on input data
    dimension_mapping = {
        'body_length': 'body_length',
        'body_width': 'body_width', 
        'body_height': 'body_height',
        'pad_length': 'pad_length',
        'pad_width': 'pad_width',
        'mask_expansion': 'mask_expansion',
        'paste_expansion': 'paste_expansion',
        'airgap': 'airgap',
        'pitch': 'pitch',
        'fillet_radius': 'fillet_radius',
        'mp_expansion': 'mp_expansion',
        'pin_count': 'pin_count',
        'tab_length': 'tab_length',
        'tab_width': 'tab_width',
        'row_spacing': 'row_spacing'
    }
    
    for data_key, db_column in dimension_mapping.items():
        if data_key in data and data[data_key]:
            try:
                # Convert to float for numeric fields, except pin_count
                if db_column == 'pin_count':
                    columns.append(db_column)
                    values.append(int(data[data_key]))
                else:
                    columns.append(db_column)
                    values.append(float(data[data_key]))
            except (ValueError, TypeError):
                pass  # Skip invalid numeric values
    
    # Build the SQL query dynamically
    placeholders = ', '.join(['?' for _ in values])
    column_names = ', '.join(columns)
    
    query = f'''
        INSERT INTO {table_name} ({column_names})
        VALUES ({placeholders})
    '''
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
```

## Update Generator Page Connection

```python
for (comp_type, opt_name), PageClass in page_map.items():
    page_instance = PageClass()
    page_instance.generationFinalized.connect(self.handle_save_to_database)
    page_instance.set_script_paths(self.script_paths)
    self.stacked_widget.addWidget(page_instance)
    self.generator_pages[(comp_type, opt_name)] = page_instance
```

## Key Features:

1. **Individual Tables**: Each package type has its own table (DiscreteN, DiscreteF, Sot23N, etc.)
2. **Specific Columns**: Each table has columns that match the input fields for that package type
3. **Dynamic Insertion**: The save method dynamically builds SQL queries based on available data
4. **Type Safety**: Numeric fields are properly converted to REAL/INTEGER types
5. **Script Path Tracking**: Each record stores paths to all 4 generated scripts
6. **Flexible Schema**: Easy to add new package types and their specific fields

This structure allows you to have dedicated tables for each package type with columns that exactly match the input parameters for that specific footprint generator.
