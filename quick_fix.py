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
        # Look for DigiKey-specific description in distributor rows
        distributor_rows = soup.find_all("tr", class_=re.compile(r'distributor|dist-row|row'))
        
        for row in distributor_rows:
            row_text = row.get_text().lower()
            
            # Check if this row contains DigiKey
            if 'digikey' in row_text or 'digi-key' in row_text:
                # Look for description cell in this row
                desc_cell = row.find("td", class_=re.compile(r'description|desc|part-desc', re.I))
                
                if desc_cell:
                    desc_text = desc_cell.get_text(strip=True)
                    # Clean up the description
                    desc_text = desc_text.replace(mpn, "").strip()
                    
                    # Check if it matches DigiKey format (all caps, technical specs)
                    if desc_text and len(desc_text) > 5 and desc_text.isupper():
                        meta["digikey_description"] = desc_text
                        break
        
        # Alternative: Look for DigiKey description in data attributes
        if not meta["digikey_description"]:
            digikey_sections = soup.find_all("div", attrs={"data-distributor": re.compile(r'digikey', re.I)})
            for section in digikey_sections:
                desc_elem = section.find(class_=re.compile(r'description', re.I))
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if desc_text and desc_text.isupper():
                        meta["digikey_description"] = desc_text
                        break
                        
    except Exception as e:
        print(f"Error extracting DigiKey description: {e}")
        pass

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
        distributor_rows = soup.find_all("tr", class_=re.compile(r'distributor|dist-row|row'))
        
        for row in distributor_rows:
            row_text = row.get_text().lower()
            
            if 'digikey' in row_text or 'digi-key' in row_text:
                stock_patterns = [
                    r'stock[:\s]+(\d[\d,]*)',
                    r'in\s+stock[:\s]+(\d[\d,]*)',
                    r'qty[:\s]+(\d[\d,]*)',
                    r'(\d[\d,]+)\s+in\s+stock',
                    r'available[:\s]+(\d[\d,]*)'
                ]
                
                for pattern in stock_patterns:
                    stock_match = re.search(pattern, row_text, re.I)
                    if stock_match:
                        stock_value = stock_match.group(1).replace(",", "")
                        meta["stock"] = int(stock_value)
                        break
                
                if meta["stock"] > 0:
                    break
                    
    except Exception as e:
        print(f"Error extracting DigiKey stock: {e}")
        pass

    return meta

