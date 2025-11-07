def detail(self, mpn: str, manufacturer: str) -> dict:
    """Extract component details - DigiKey description only"""
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

    # Extract ONLY DigiKey description from distributor table
    try:
        # Find all table rows that might contain distributor info
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            # Get all text in this row
            row_text = row.get_text()
            
            # Check if this row mentions DigiKey
            if 'DigiKey' in row_text or 'DISTI # 497-' in row_text:
                # Find all td cells in this row
                cells = row.find_all("td")
                
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    
                    # Look for pattern like "IC MCU 32BIT 512KB FLASH"
                    # DigiKey descriptions start with "IC" and are in specific format
                    if cell_text.startswith("IC ") and len(cell_text) > 10:
                        # Extract just the description part (before "Min Qty" or other details)
                        description = cell_text.split("Min Qty")[0].strip()
                        description = description.split("Lead time")[0].strip()
                        description = description.split("Container")[0].strip()
                        description = description.split("RoHS")[0].strip()
                        
                        meta["digikey_description"] = description
                        break
                
                if meta["digikey_description"]:
                    break
                    
    except Exception as e:
        print(f"Error extracting DigiKey description: {e}")

    # Extract from Part Data Attributes table (keep other fields)
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
                elif field_name in ["Part Package Code", "Size Code", "Package Description", "Package Code"]:
                    if not meta["package_code"]:
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
                elif field_name in ["Height", "Package Height", "Seated Height-Max"]:
                    height_match = re.search(r'(\d+(?:\.\d+)?)', field_value)
                    if height_match:
                        meta["height_mm"] = float(height_match.group(1))
                elif field_name in ["Number of Pins", "Number of Terminals", "Pin Count"]:
                    terminal_match = re.search(r'(\d+)', field_value)
                    if terminal_match:
                        meta["num_terminals"] = int(terminal_match.group(1))
                elif "Operating Temperature" in field_name or "Temperature Range" in field_name:
                    if "Max" in field_name:
                        temp_match = re.search(r'(-?\d+(?:\.\d+)?)', field_value)
                        if temp_match:
                            meta["temp_max"] = temp_match.group(1)
                    elif "Min" in field_name:
                        temp_match = re.search(r'(-?\d+(?:\.\d+)?)', field_value)
                        if temp_match:
                            meta["temp_min"] = temp_match.group(1)
                    else:
                        temp_matches = re.findall(r'(-?\d+(?:\.\d+)?)', field_value)
                        if len(temp_matches) >= 2:
                            meta["temp_min"] = temp_matches[0]
                            meta["temp_max"] = temp_matches[1]

        except Exception:
            continue

    # Extract datasheet link
    datasheet_patterns = [
        soup.find("a", href=re.compile(r'.*datasheet.*', re.I)),
        soup.find("a", href=re.compile(r'.*\.pdf$', re.I)),
        soup.find("a", string=re.compile(r'datasheet', re.I))
    ]
    
    for datasheet_link in datasheet_patterns:
        if datasheet_link and datasheet_link.get("href"):
            href = datasheet_link["href"]
            if href.startswith("http"):
                meta["datasheet_url"] = href
                break

    # Extract DigiKey stock
    try:
        all_rows = soup.find_all("tr")
        
        for row in all_rows:
            row_text = row.get_text()
            
            if 'DigiKey' in row_text or 'DISTI # 497-' in row_text:
                # Look for stock number pattern
                stock_match = re.search(r'(\d{1,6})\s+In Stock', row_text, re.I)
                if stock_match:
                    meta["stock"] = int(stock_match.group(1))
                    break
                    
    except Exception as e:
        print(f"Error extracting DigiKey stock: {e}")

    return meta
