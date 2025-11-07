
"""
BOM Data Extractor - Component Information Extraction Tool
Extracts technical specifications without pricing data
"""

from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.cell import MergedCell
import sys, re, json, time, urllib.parse, math, os, chardet
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QToolBar,
    QFileDialog, QTableWidget, QTableWidgetItem, QComboBox, QLabel,
    QSpinBox, QTextEdit, QMessageBox, QTabWidget, QProgressBar,
    QSplitter, QDialog, QListWidget, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QAction, QFont, QPalette, QPixmap, QIcon

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BASE_SEARCH = "https://www.findchips.com/search/"
BASE_DETAIL = "https://www.findchips.com/detail/{mpn}/{mfg}"


def apply_dark_green_theme(app):
    """Apply dark green theme to the entire application"""
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(25, 35, 25))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 255, 100))
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 45, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 55, 45))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 255, 100))
    palette.setColor(QPalette.ColorRole.Button, QColor(35, 55, 35))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 255, 100))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 150, 50))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, QColor(100, 255, 150))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(100, 100, 100))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 100, 100))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(100, 100, 100))

    app.setPalette(palette)

    app.setStyleSheet("""
        QMainWindow {
            background-color: rgb(25, 35, 25);
            color: rgb(0, 255, 100);
        }
        QToolBar {
            background-color: rgb(35, 45, 35);
            border: 1px solid rgb(0, 150, 50);
            spacing: 3px;
        }
        QPushButton, QToolButton {
            background-color: rgb(35, 55, 35);
            color: rgb(0, 255, 100);
            border: 2px solid rgb(0, 150, 50);
            border-radius: 5px;
            padding: 5px 10px;
            font-weight: bold;
        }
        QPushButton:hover, QToolButton:hover {
            background-color: rgb(0, 150, 50);
            color: white;
        }
        QComboBox {
            background-color: rgb(35, 45, 35);
            color: rgb(0, 255, 100);
            border: 2px solid rgb(0, 150, 50);
            border-radius: 3px;
            padding: 2px 5px;
        }
        QSpinBox {
            background-color: rgb(35, 45, 35);
            color: rgb(0, 255, 100);
            border: 2px solid rgb(0, 150, 50);
            border-radius: 3px;
        }
        QLabel {
            color: rgb(0, 255, 100);
            font-weight: bold;
        }
        QTabBar::tab {
            background-color: rgb(35, 45, 35);
            color: rgb(0, 255, 100);
            border: 2px solid rgb(0, 150, 50);
            padding: 8px 15px;
            margin: 2px;
        }
        QTabBar::tab:selected {
            background-color: rgb(0, 150, 50);
            color: white;
        }
        QProgressBar {
            background-color: rgb(35, 45, 35);
            border: 2px solid rgb(0, 150, 50);
            border-radius: 5px;
            color: white;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: rgb(0, 200, 50);
            border-radius: 3px;
        }
        QListWidget {
            background-color: white;
            color: black;
            border: 2px solid rgb(0, 150, 50);
        }
    """)


def filter_search_results(mpn: str, search_results: list[dict]) -> list[dict]:
    """Filter search results: exact matches first, then first partial match"""
    exact_matches = []
    partial_matches = []
    mpn_lower = mpn.strip().lower()

    for result in search_results:
        result_mpn = result["mpn"].strip().lower()
        if result_mpn == mpn_lower:
            exact_matches.append(result)
        else:
            partial_matches.append(result)

    if exact_matches:
        return exact_matches
    elif partial_matches:
        return partial_matches[:1]
    else:
        return []


def detect_file_encoding(file_path: str) -> str:
    """Detect the encoding of a file"""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            return result['encoding'] or 'utf-8'
    except Exception:
        return 'utf-8'


def detect_csv_delimiter(file_path: str, encoding: str = 'utf-8') -> str:
    """Detect CSV delimiter"""
    delimiters = [',', ';', '\t', '|']
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(1024)

        delimiter_scores = {}
        for delim in delimiters:
            lines = sample.split('\n')[:3]
            scores = []
            for line in lines:
                if line.strip():
                    scores.append(line.count(delim))
            if scores and max(scores) > 0:
                delimiter_scores[delim] = max(scores)

        if delimiter_scores:
            return max(delimiter_scores.items(), key=lambda x: x[1])[0]
        return ','
    except Exception:
        return ','


class FindchipsClient:
    def __init__(self, timeout=15):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT})
        self.timeout = timeout

    def get(self, url):
        return self.s.get(url, timeout=self.timeout)

    def search(self, mpn: str) -> list[dict]:
        """Extract MPN and manufacturer from search page"""
        url = BASE_SEARCH + urllib.parse.quote(mpn)
        r = self.get(url)
        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.content, "html.parser")
        rows = soup.find_all("tr", class_="row")
        results = []

        for row in rows:
            try:
                mfg = (row.get("data-mfr") or row.get("data-manufacturer") or "").strip()
                result_mpn = (row.get("data-mfrpartnumber") or "").strip()
                if not mfg or not result_mpn:
                    continue

                results.append({
                    "mpn": result_mpn,
                    "manufacturer": mfg
                })
            except Exception:
                continue

        # Remove duplicates
        seen = set()
        unique_results = []
        for item in results:
            key = (item["mpn"].lower(), item["manufacturer"].lower())
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        return unique_results

    def detail(self, mpn: str, manufacturer: str) -> dict:
        """Extract component details from detail page"""
        url = BASE_DETAIL.format(
            mpn=urllib.parse.quote(mpn),
            mfg=urllib.parse.quote(manufacturer.replace(' ', '-'))
        )
        r = self.get(url)
        if r.status_code != 200:
            return {}

        html = r.text
        meta = {
            "life_cycle_code": None,
            "package_code": None,
            "length_mm": None,
            "width_mm": None,
            "height_mm": None,
            "lead_time": None,
            "num_terminals": None,
            "digikey_description": None,
            "temp_min": None,
            "temp_max": None,
            "datasheet_url": None,
            "stock": 0
        }

        soup = BeautifulSoup(html, "html.parser")

        # Extract from Part Data Attributes table
        data_rows = soup.find_all("tr", class_="data-row")
        for row in data_rows:
            try:
                field_cell = row.find("td", class_="field-cell")
                main_cell = row.find("td", class_="main-part-cell")

                if field_cell and main_cell:
                    field_name = field_cell.get_text(strip=True)
                    field_value = main_cell.get_text(strip=True)

                    if field_name == "Part Life Cycle Code":
                        meta["life_cycle_code"] = field_value
                    elif field_name in ["Part Package Code", "Size Code", "Package Description"]:
                        meta["package_code"] = field_value
                    elif field_name == "Factory Lead Time":
                        meta["lead_time"] = field_value
                    elif field_name in ["Length", "Package Length"]:
                        length_match = re.search(r'(\d+(?:\.\d+)?)', field_value)
                        if length_match:
                            meta["length_mm"] = float(length_match.group(1))
                    elif field_name in ["Width", "Package Width"]:
                        width_match = re.search(r'(\d+(?:\.\d+)?)', field_value)
                        if width_match:
                            meta["width_mm"] = float(width_match.group(1))
                    elif field_name in ["Height", "Package Height"]:
                        height_match = re.search(r'(\d+(?:\.\d+)?)', field_value)
                        if height_match:
                            meta["height_mm"] = float(height_match.group(1))
                    elif field_name in ["Number of Pins", "Number of Terminals", "Pin Count"]:
                        terminal_match = re.search(r'(\d+)', field_value)
                        if terminal_match:
                            meta["num_terminals"] = int(terminal_match.group(1))
                    elif field_name in ["Description", "Part Description"]:
                        meta["digikey_description"] = field_value
                    elif "Operating Temperature" in field_name or "Temperature Range" in field_name:
                        # Try to extract min and max temperatures
                        temp_match = re.findall(r'(-?\d+(?:\.\d+)?)\s*Â°?C', field_value)
                        if len(temp_match) >= 2:
                            meta["temp_min"] = temp_match[0]
                            meta["temp_max"] = temp_match[1]
                        elif len(temp_match) == 1:
                            if "min" in field_name.lower():
                                meta["temp_min"] = temp_match[0]
                            elif "max" in field_name.lower():
                                meta["temp_max"] = temp_match[0]

            except Exception:
                continue

        # Extract datasheet link
        datasheet_link = soup.find("a", href=re.compile(r'.*datasheet.*', re.I))
        if datasheet_link and datasheet_link.get("href"):
            meta["datasheet_url"] = datasheet_link["href"]

        # Extract stock information
        try:
            stock_section = soup.find("div", class_="stock-summary") or soup.find("span", class_="stock")
            if stock_section:
                stock_text = stock_section.get_text()
                stock_match = re.search(r'(\d[\d,]*)', stock_text)
                if stock_match:
                    meta["stock"] = int(stock_match.group(1).replace(",", ""))
        except Exception:
            pass

        return meta


class JSONStorage:
    """JSON-based storage for component data"""
    def __init__(self, path="bom_data_extractor.json"):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON data: {e}")
                return {}
        return {}

    def _save(self):
        try:
            if os.path.exists(self.path):
                backup_path = f"{self.path}.backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                os.rename(self.path, backup_path)

            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving JSON data: {e}")
            backup_path = f"{self.path}.backup"
            if os.path.exists(backup_path):
                os.rename(backup_path, self.path)

    def upsert_component(self, mpn, manufacturer, **kwargs):
        """Insert or update component data"""
        if mpn not in self.data:
            self.data[mpn] = {}

        if manufacturer not in self.data[mpn]:
            self.data[mpn][manufacturer] = {}

        # Update component data
        component_data = {
            "manufacturer": manufacturer,
            "life_cycle_code": kwargs.get("life_cycle_code"),
            "package_code": kwargs.get("package_code"),
            "length_mm": kwargs.get("length_mm"),
            "width_mm": kwargs.get("width_mm"),
            "height_mm": kwargs.get("height_mm"),
            "lead_time": kwargs.get("lead_time"),
            "stock": kwargs.get("stock", 0),
            "num_terminals": kwargs.get("num_terminals"),
            "digikey_description": kwargs.get("digikey_description"),
            "temp_min": kwargs.get("temp_min"),
            "temp_max": kwargs.get("temp_max"),
            "datasheet_url": kwargs.get("datasheet_url"),
            "part_type": kwargs.get("part_type"),
            "scraped_date": datetime.now().isoformat()
        }

        self.data[mpn][manufacturer].update(component_data)
        self._save()

    def get_component_data(self, mpn):
        """Get all data for a specific MPN"""
        if mpn not in self.data:
            return []

        components = []
        for manufacturer, comp_data in self.data[mpn].items():
            components.append({
                "manufacturer": manufacturer,
                **comp_data
            })

        return components

    def get_best_component(self, mpn):
        """Get the best/most complete component data for MPN"""
        components = self.get_component_data(mpn)
        if not components:
            return None

        # Prefer components with more complete data
        def completeness_score(comp):
            score = 0
            for key, value in comp.items():
                if value is not None and value != "" and value != 0:
                    score += 1
            return score

        return max(components, key=completeness_score)

    def is_data_fresh(self, mpn, hours=6):
        """Check if MPN data is fresh"""
        if mpn not in self.data:
            return False

        for manufacturer_data in self.data[mpn].values():
            scraped_date_str = manufacturer_data.get("scraped_date")
            if scraped_date_str:
                try:
                    scraped_date = datetime.fromisoformat(scraped_date_str)
                    time_diff = datetime.now() - scraped_date
                    if time_diff < timedelta(hours=hours):
                        return True
                except Exception:
                    continue
        return False


class ScrapeThread(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    done = pyqtSignal()

    def __init__(self, mpns, storage: JSONStorage):
        super().__init__()
        self.mpns = mpns
        self.storage = storage
        self.client = FindchipsClient()
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
        self.log.emit("Scraping cancelled by user")

    def run(self):
        total = len(self.mpns)
        fresh_count = 0
        scraped_count = 0

        for i, mpn in enumerate(self.mpns):
            if self.cancelled:
                self.log.emit("Scraping process was cancelled")
                self.done.emit()
                return

            try:
                if self.storage.is_data_fresh(mpn, hours=6):
                    self.log.emit(f"Using cached data for {mpn}")
                    fresh_count += 1
                    self.progress.emit(int((i + 1) * 100 / total))
                    continue

                self.log.emit(f"Scraping {mpn}")

                search_results = self.client.search(mpn)
                if not search_results:
                    self.log.emit(f"No manufacturers found for {mpn}")
                    self.progress.emit(int((i + 1) * 100 / total))
                    time.sleep(0.1)
                    continue

                filtered_results = filter_search_results(mpn, search_results)
                if not filtered_results:
                    self.log.emit(f"No suitable matches found for {mpn}")
                    self.progress.emit(int((i + 1) * 100 / total))
                    time.sleep(0.1)
                    continue

                self.log.emit(f"Found {len(filtered_results)} matches for {mpn}")

                for result in filtered_results:
                    if self.cancelled:
                        self.log.emit("Scraping process was cancelled")
                        self.done.emit()
                        return

                    result_mpn = result["mpn"]
                    manufacturer = result["manufacturer"]

                    is_exact = result_mpn.strip().lower() == mpn.strip().lower()
                    part_type = "Precise Match" if is_exact else "Alternate Parts"

                    self.log.emit(f"Getting details: {result_mpn} / {manufacturer}")

                    detail_data = self.client.detail(result_mpn, manufacturer)

                    self.storage.upsert_component(
                        mpn=mpn,
                        manufacturer=manufacturer,
                        **detail_data,
                        part_type=part_type
                    )

                scraped_count += 1
                self.log.emit(f"Completed: {mpn}")

            except Exception as e:
                self.log.emit(f"Error processing {mpn}: {e}")

            self.progress.emit(int((i + 1) * 100 / total))
            time.sleep(0.1)

        self.log.emit(f"Scraping completed - Cached: {fresh_count}, Scraped: {scraped_count}")
        self.done.emit()


class RobustBOMLoader:
    """Enhanced BOM file loader"""

    @staticmethod
    def load_bom_file(file_path: str) -> pd.DataFrame:
        file_ext = os.path.splitext(file_path)[1].lower()

        try:
            if file_ext == '.csv':
                return RobustBOMLoader._load_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                return RobustBOMLoader._load_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            raise Exception(f"Failed to load BOM file: {str(e)}")

    @staticmethod
    def _load_csv(file_path: str) -> pd.DataFrame:
        encoding = detect_file_encoding(file_path)
        delimiter = detect_csv_delimiter(file_path, encoding)

        encodings_to_try = [encoding, 'utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']

        for enc in encodings_to_try:
            try:
                df = pd.read_csv(
                    file_path, 
                    delimiter=delimiter, 
                    encoding=enc,
                    engine='python',
                    on_bad_lines='skip',
                    dtype=str
                )

                if df.empty:
                    raise ValueError("CSV file is empty")

                if len(df.columns) < 2:
                    raise ValueError("CSV file must have at least 2 columns")

                df.columns = df.columns.str.strip()
                return df

            except UnicodeDecodeError:
                continue
            except Exception as e:
                if enc == encodings_to_try[-1]:
                    raise Exception(f"Failed to read CSV: {str(e)}")
                continue

        raise Exception("Could not read CSV file with any supported encoding")

    @staticmethod
    def _load_excel(file_path: str) -> pd.DataFrame:
        try:
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            if len(sheet_names) == 0:
                raise ValueError("Excel file contains no worksheets")

            selected_sheet = sheet_names[0]

            df = pd.read_excel(
                file_path,
                sheet_name=selected_sheet,
                dtype=str,
                engine='openpyxl'
            )

            if df.empty:
                raise ValueError("Excel sheet is empty")

            if len(df.columns) < 2:
                raise ValueError("Excel sheet must have at least 2 columns")

            df.columns = df.columns.str.strip()
            df = df.dropna(how='all')

            return df

        except Exception as e:
            raise Exception(f"Failed to read Excel file: {str(e)}")


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOM Data Extractor V1.0 - Â© 2025 Sienna ECAD Technologies")

        logo_path = resource_path("bomlogo.ico")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.resize(1250, 750)
        self.storage = JSONStorage()
        self.client = FindchipsClient()
        self._manufacturer_overrides = {}

        self._build_ui()
        self._apply_white_backgrounds()
        self.bom_df = None
        self.loader = RobustBOMLoader()

    def _build_ui(self):
        tb = QToolBar()
        self.addToolBar(tb)

        act_open = QAction("Upload BOM", self)
        act_open.triggered.connect(self.on_open)
        tb.addAction(act_open)
        tb.addSeparator()

        act_fetch = QAction("Fetch Data", self)
        act_fetch.triggered.connect(self.on_fetch)
        tb.addAction(act_fetch)
        tb.addSeparator()

        act_export = QAction("Export to Excel", self)
        act_export.triggered.connect(self.on_export)
        tb.addAction(act_export)

        top = QHBoxLayout()

        # MPN Column
        mpn_layout = QHBoxLayout()
        mpn_layout.addWidget(QLabel("MPN Column:"))
        self.cmb_mpn = QComboBox()
        self.cmb_mpn.setMinimumWidth(200)
        mpn_layout.addWidget(self.cmb_mpn)
        top.addLayout(mpn_layout)

        # QTY Column
        qty_layout = QHBoxLayout()
        qty_layout.addWidget(QLabel("QTY Column:"))
        self.cmb_qty = QComboBox()
        self.cmb_qty.setMinimumWidth(200)
        qty_layout.addWidget(self.cmb_qty)
        top.addLayout(qty_layout)

        # Logo
        img_label = QLabel()
        pixmap_path = "SiennaLogo.png"
        if os.path.exists(pixmap_path):
            pixmap = QPixmap(pixmap_path)
            img_label.setPixmap(pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation))
        top.addWidget(img_label)
        top.setAlignment(Qt.AlignmentFlag.AlignRight)

        topw = QWidget()
        topw.setLayout(top)

        self.tabs = QTabWidget()
        self.tbl_results = QTableWidget()
        self.tbl_details = QTableWidget()
        self.tabs.addTab(self.tbl_results, "BOM Results")
        self.tabs.addTab(self.tbl_details, "Component Details")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)

        progress_layout = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setVisible(False)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.on_cancel_scraping)

        progress_layout.addWidget(self.progress)
        progress_layout.addWidget(self.cancel_btn)
        progress_widget = QWidget()
        progress_widget.setLayout(progress_layout)

        spl = QSplitter(Qt.Orientation.Vertical)
        spl.addWidget(self.tabs)
        spl.addWidget(self.log)
        spl.setStretchFactor(0, 3)
        spl.setStretchFactor(1, 1)

        root = QVBoxLayout()
        root.addWidget(topw)
        root.addWidget(progress_widget)
        root.addWidget(spl)
        cw = QWidget()
        cw.setLayout(root)
        self.setCentralWidget(cw)

    def on_cancel_scraping(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("Cancelling...")

    def _apply_white_backgrounds(self):
        table_style = """
            QTableWidget {
                background-color: white;
                color: black;
                border: 2px solid rgb(0, 150, 50);
                selection-background-color: rgb(0, 150, 50);
                selection-color: white;
            }
            QHeaderView::section:horizontal {
                background-color: rgb(0, 150, 50);
                color: white;
                padding: 5px;
                border: 1px solid rgb(200, 200, 200);
                font-weight: bold;
            }
            QHeaderView::section:vertical {
                background-color: white;
                color: black;
                padding: 3px;
                border: 1px solid rgb(200, 200, 200);
            }
        """

        self.log.setStyleSheet("background-color: white; color: black; border: 2px solid rgb(0, 150, 50);")
        self.tbl_results.setStyleSheet(table_style)
        self.tbl_details.setStyleSheet(table_style)

    def log_msg(self, m):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {m}")

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open BOM", 
            "", 
            "Excel (*.xlsx *.xls);;CSV (*.csv);;All Files (*.*)"
        )
        if not path:
            return

        try:
            self.log_msg(f"Loading file: {os.path.basename(path)}")
            self.bom_df = self.loader.load_bom_file(path)

            self.cmb_mpn.clear()
            self.cmb_qty.clear()
            cols = list(self.bom_df.columns)
            self.cmb_mpn.addItems(cols)
            self.cmb_qty.addItems(cols)

            self._auto_detect_columns(cols)
            self.show_bom(self.bom_df)
            self.log_msg(f"Successfully loaded BOM with {len(self.bom_df)} rows")

        except Exception as e:
            QMessageBox.critical(self, "Error Loading BOM", str(e))
            self.log_msg(f"Error loading BOM: {str(e)}")

    def _auto_detect_columns(self, columns):
        mpn_patterns = ['mpn', 'part', 'partno', 'part_no', 'part number']
        qty_patterns = ['qty', 'quantity']

        for i, col in enumerate(columns):
            col_lower = col.lower().strip()
            if any(pattern in col_lower for pattern in mpn_patterns):
                self.cmb_mpn.setCurrentIndex(i)
                break

        for i, col in enumerate(columns):
            col_lower = col.lower().strip()
            if any(pattern in col_lower for pattern in qty_patterns):
                self.cmb_qty.setCurrentIndex(i)
                break

    def show_bom(self, df):
        self.tbl_results.setRowCount(len(df))
        self.tbl_results.setColumnCount(len(df.columns))
        self.tbl_results.setHorizontalHeaderLabels(list(df.columns))
        for r in range(len(df)):
            for c in range(len(df.columns)):
                val = df.iloc[r, c]
                display_val = str(val) if pd.notna(val) else ""
                self.tbl_results.setItem(r, c, QTableWidgetItem(display_val))

    def on_fetch(self):
        if self.bom_df is None:
            QMessageBox.warning(self, "Warning", "Upload BOM first")
            return

        mpn_col = self.cmb_mpn.currentText()
        if not mpn_col:
            QMessageBox.warning(self, "Warning", "Select MPN column")
            return

        mpns = []
        for val in self.bom_df[mpn_col].dropna().astype(str).str.strip().unique():
            if val and val.lower() != 'nan':
                mpns.append(val)

        if not mpns:
            QMessageBox.warning(self, "Warning", "No valid MPNs found")
            return

        fresh_mpns = [mpn for mpn in mpns if self.storage.is_data_fresh(mpn, hours=6)]
        stale_mpns = [mpn for mpn in mpns if not self.storage.is_data_fresh(mpn, hours=6)]

        self.log_msg(f"Starting fetch for {len(mpns)} unique MPNs")
        self.log_msg(f"Fresh data: {len(fresh_mpns)} MPNs, Will scrape: {len(stale_mpns)} MPNs")

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("Cancel")

        self.worker = ScrapeThread(mpns, self.storage)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log_msg)
        self.worker.done.connect(self.on_scrape_done)
        self.worker.start()

    def on_scrape_done(self):
        self.progress.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.log_msg("Processing completed")
        self.populate_results()
        self.populate_details()

    def populate_results(self):
        """Populate results table with extracted data"""
        if self.bom_df is None:
            return

        mpn_col = self.cmb_mpn.currentText() or self.bom_df.columns[0]
        qty_col = self.cmb_qty.currentText() or self.bom_df.columns[1]
        df = self.bom_df.copy()

        result_cols = [
            "Part Type", "MPN", "Manufacturer", "Part Life Cycle Code", "Package",
            "Size (L*W mm)", "Height", "Lead Time", "In Stock", "Number of Terminals",
            "Digikey Description", "Operating Temperature-Min", "Operating Temperature-Max",
            "Datasheet Link"
        ]

        for col in result_cols:
            df[col] = ""

        for idx, row in df.iterrows():
            mpn_val = row[mpn_col]
            if pd.isna(mpn_val):
                continue
            mpn = str(mpn_val).strip()
            if not mpn or mpn.lower() == 'nan':
                continue

            best = self.storage.get_best_component(mpn)
            if not best:
                continue

            df.at[idx, "Part Type"] = best.get("part_type", "")
            df.at[idx, "MPN"] = mpn
            df.at[idx, "Manufacturer"] = best.get("manufacturer", "")
            df.at[idx, "Part Life Cycle Code"] = best.get("life_cycle_code", "")
            df.at[idx, "Package"] = best.get("package_code", "")

            L = best.get("length_mm")
            W = best.get("width_mm")
            if L is not None or W is not None:
                df.at[idx, "Size (L*W mm)"] = f"{(L or '')}*{(W or '')}"

            H = best.get("height_mm")
            if H is not None:
                df.at[idx, "Height"] = f"{H} mm"

            df.at[idx, "Lead Time"] = best.get("lead_time", "")
            df.at[idx, "In Stock"] = str(best.get("stock", 0))
            df.at[idx, "Number of Terminals"] = str(best.get("num_terminals", ""))
            df.at[idx, "Digikey Description"] = best.get("digikey_description", "")
            df.at[idx, "Operating Temperature-Min"] = best.get("temp_min", "")
            df.at[idx, "Operating Temperature-Max"] = best.get("temp_max", "")
            df.at[idx, "Datasheet Link"] = best.get("datasheet_url", "")

        # Update table
        self.tbl_results.setRowCount(len(df))
        self.tbl_results.setColumnCount(len(df.columns))
        self.tbl_results.setHorizontalHeaderLabels(list(df.columns))

        for r in range(len(df)):
            for c in range(len(df.columns)):
                col_name = df.columns[c]
                val = df.iloc[r, c]
                display_val = str(val) if pd.notna(val) else ""
                it = QTableWidgetItem(display_val)

                if col_name == "In Stock":
                    try:
                        s = int(display_val) if display_val else 0
                    except:
                        s = 0
                    if s == 0:
                        it.setBackground(QColor(255, 200, 200))
                    elif s < 100:
                        it.setBackground(QColor(255, 255, 200))
                    elif s < 1000:
                        it.setBackground(QColor(255, 255, 150))
                    else:
                        it.setBackground(QColor(200, 255, 200))
                    f = QFont()
                    f.setBold(True)
                    it.setFont(f)

                self.tbl_results.setItem(r, c, it)

    def populate_details(self):
        """Populate details table with all available distributor data"""
        if self.bom_df is None:
            return

        mpn_col = self.cmb_mpn.currentText() or self.bom_df.columns[0]
        df = self.bom_df.copy()

        # Add detail columns
        detail_cols = ["Manufacturer", "Part Type", "Life Cycle", "Package", "Size (L*W mm)", 
                      "Height", "Lead Time", "Stock", "Terminals", "Description", 
                      "Temp Min", "Temp Max", "Datasheet"]
        for col in detail_cols:
            df[col] = ""

        for idx, row in df.iterrows():
            mpn_val = row[mpn_col]
            if pd.isna(mpn_val):
                continue
            mpn = str(mpn_val).strip()
            if not mpn or mpn.lower() == 'nan':
                continue

            components = self.storage.get_component_data(mpn)
            if not components:
                continue

            # Aggregate data from all manufacturers
            manufacturers = [c["manufacturer"] for c in components if c.get("manufacturer")]
            df.at[idx, "Manufacturer"] = " | ".join(manufacturers)

            # Use best component for other fields
            best = max(components, key=lambda c: sum(1 for v in c.values() if v))

            df.at[idx, "Part Type"] = best.get("part_type", "")
            df.at[idx, "Life Cycle"] = best.get("life_cycle_code", "")
            df.at[idx, "Package"] = best.get("package_code", "")

            L = best.get("length_mm")
            W = best.get("width_mm")
            if L or W:
                df.at[idx, "Size (L*W mm)"] = f"{(L or '')}*{(W or '')}"

            H = best.get("height_mm")
            if H:
                df.at[idx, "Height"] = f"{H} mm"

            df.at[idx, "Lead Time"] = best.get("lead_time", "")
            df.at[idx, "Stock"] = str(best.get("stock", 0))
            df.at[idx, "Terminals"] = str(best.get("num_terminals", ""))
            df.at[idx, "Description"] = best.get("digikey_description", "")
            df.at[idx, "Temp Min"] = best.get("temp_min", "")
            df.at[idx, "Temp Max"] = best.get("temp_max", "")
            df.at[idx, "Datasheet"] = best.get("datasheet_url", "")

        # Update details table
        self.tbl_details.setRowCount(len(df))
        self.tbl_details.setColumnCount(len(df.columns))
        self.tbl_details.setHorizontalHeaderLabels(list(df.columns))

        for r in range(len(df)):
            for c in range(len(df.columns)):
                val = df.iloc[r, c]
                display_val = str(val) if pd.notna(val) else ""
                self.tbl_details.setItem(r, c, QTableWidgetItem(display_val))

    def on_export(self):
        """Export results to Excel"""
        if self.tbl_results.rowCount() == 0:
            QMessageBox.warning(self, "Warning", "No data to export")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "", "Excel (*.xlsx)")
        if not path:
            return

        try:
            headers = [self.tbl_results.horizontalHeaderItem(i).text() for i in range(self.tbl_results.columnCount())]
            data = []

            for r in range(self.tbl_results.rowCount()):
                row = []
                for c in range(self.tbl_results.columnCount()):
                    it = self.tbl_results.item(r, c)
                    row.append(it.text() if it else "")
                data.append(row)

            df = pd.DataFrame(data, columns=headers)

            wb = Workbook()
            ws = wb.active
            ws.title = "BOM Data"

            # Add data
            for r in dataframe_to_rows(df, index=False, header=True):
                ws.append(r)

            # Style headers
            green_fill = PatternFill(start_color="00962F", end_color="00962F", fill_type="solid")
            white_font = Font(color="FFFFFF", bold=True)

            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col)
                cell.fill = green_fill
                cell.font = white_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Auto-adjust columns
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if not isinstance(cell, MergedCell):
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            wb.save(path)
            self.log_msg(f"Exported to: {path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
            self.log_msg(f"Export failed: {e}")


def run_app():
    app = QApplication(sys.argv)
    apply_dark_green_theme(app)
    w = App()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
