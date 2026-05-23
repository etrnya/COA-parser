import re
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("Validator")

# JSON Schema definition to guide Gemini's extraction format
COA_EXTRACTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "product_raw": { "type": "STRING", "description": "The chemical or product name exactly as printed on the COA." },
        "brand_raw": { "type": "STRING", "description": "The manufacturer or brand name of the chemical (e.g. Sigma-Aldrich, Merck, Alfa Aesar, USP)." },
        "batch_no": { "type": "STRING", "description": "The batch or lot identifier number." },
        "expiry_raw": { "type": "STRING", "description": "The expiry date or retest date text exactly as printed." },
        "purity_raw": { "type": "STRING", "description": "The purity percentage or assay value text exactly as printed." },
        "amount_raw": { "type": "STRING", "description": "The packaging volume, mass, or amount exactly as printed (e.g. 100g, 50ml, 1x10mg)." },
        "cas_no_raw": { "type": "STRING", "description": "The Chemical Abstracts Service (CAS) Registry Number exactly as printed." },
        "mw_raw": { "type": "STRING", "description": "The molecular weight (MW) or formula weight exactly as printed." },
        "storage_raw": { "type": "STRING", "description": "The storage temperature or storage condition text exactly as printed." },
        
        "product_std_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "brand_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "batch_no_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "expiry_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "purity_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "amount_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "cas_no_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "mw_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        "storage_raw_confidence": { "type": "STRING", "enum": ["high", "medium", "low"] },
        
        "traceability": {
            "type": "OBJECT",
            "properties": {
                "product_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the product name was found." },
                "brand_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the brand was found." },
                "batch_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the batch number was found." },
                "expiry_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the expiry date was found." },
                "purity_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the purity was found." },
                "amount_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the amount was found." },
                "cas_no_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the CAS number was found." },
                "mw_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the molecular weight was found." },
                "storage_source": { "type": "STRING", "description": "Snippet of text and page number indicating where the storage was found." }
            },
            "required": ["product_source", "brand_source", "batch_source", "expiry_source", "purity_source", "amount_source", "cas_no_source", "mw_source", "storage_source"]
        }
    },
    "required": [
        "product_raw", "brand_raw", "batch_no", "expiry_raw", "purity_raw", "amount_raw", "cas_no_raw", "mw_raw", "storage_raw",
        "product_std_confidence", "brand_raw_confidence", "batch_no_confidence", "expiry_raw_confidence", "purity_raw_confidence", "amount_raw_confidence", "cas_no_raw_confidence", "mw_raw_confidence", "storage_raw_confidence",
        "traceability"
    ]
}

def parse_date(date_str: str) -> datetime:
    """Attempt to parse a date string using common formats in COAs."""
    if not date_str or date_str.strip().upper() == "N/A":
        return None
        
    cleaned = date_str.strip().replace(",", " ").replace(".", " ").replace("-", " ").replace("/", " ")
    # Compress multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Try formats
    formats = [
        "%Y %m %d",      # 2027 08 22
        "%d %b %Y",      # 22 Aug 2027 or 22 August 2027
        "%b %d %Y",      # Aug 22 2027
        "%B %d %Y",      # August 22 2027
        "%m %d %Y",      # 08 22 2027
        "%Y %b %d",      # 2027 Aug 22
        "%Y %B %d",      # 2027 August 22
        "%d %B %Y",      # 22 August 2027
        "%Y%m%d",        # 20270822
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
            
    # Try backup standard ISO parses directly on original string
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
            
    # Try parsing month names manually (e.g. "August 2027" without day)
    # If no day is found, assume the 1st or end of month, but let's try to extract month + year
    year_match = re.search(r'\b(20\d{2})\b', date_str)
    if year_match:
        year = int(year_match.group(1))
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        for name, num in months.items():
            if name in date_str.lower():
                # Check if day is also present
                day_match = re.search(r'\b(\d{1,2})\b', date_str.replace(str(year), ""))
                day = int(day_match.group(1)) if day_match else 1
                return datetime(year, num, day)
                
    return None

def validate_and_standardize_fields(extracted_data: dict, rules: dict) -> tuple:
    """
    Standardize the raw fields extracted by Gemini and perform range validation.
    
    Args:
        extracted_data: Raw JSON payload returned by Gemini.
        rules: Standardization rules dictionary from config.json.
        
    Returns:
        tuple: (standardized_data_dict, warnings_list)
    """
    warnings = []
    std_data = extracted_data.copy()
    
    # 1. Product Name Standardization (Title Case / UPPER / lower)
    product_raw = extracted_data.get("product_raw", "N/A").strip()
    name_fmt = rules.get("name_format", "Title Case")
    
    if product_raw == "N/A":
        std_data["product_std"] = "N/A"
        warnings.append("Missing Product Name (Raw was N/A).")
    else:
        if name_fmt == "Title Case":
            std_data["product_std"] = product_raw.title()
        elif name_fmt == "UPPERCASE":
            std_data["product_std"] = product_raw.upper()
        elif name_fmt == "lowercase":
            std_data["product_std"] = product_raw.lower()
        else:
            std_data["product_std"] = product_raw
            
    # 2. Expiry Date Standardization (Format to YYYY/M/D or similar)
    expiry_raw = extracted_data.get("expiry_raw", "N/A").strip()
    target_date_format = rules.get("date_format", "YYYY/M/D")
    
    if expiry_raw == "N/A":
        std_data["expiry_std"] = "N/A"
        warnings.append("Missing Expiry Date (Raw was N/A).")
    else:
        parsed_dt = parse_date(expiry_raw)
        if parsed_dt:
            # Map YYYY/M/D format to Python strftime
            if target_date_format == "YYYY/M/D":
                std_data["expiry_std"] = f"{parsed_dt.year}/{parsed_dt.month}/{parsed_dt.day}"
            elif target_date_format == "YYYY-MM-DD":
                std_data["expiry_std"] = parsed_dt.strftime("%Y-%m-%d")
            elif target_date_format == "YYYY/MM/DD":
                std_data["expiry_std"] = parsed_dt.strftime("%Y/%m/%d")
            else:
                std_data["expiry_std"] = f"{parsed_dt.year}/{parsed_dt.month}/{parsed_dt.day}"
                
            # Date Range check
            today = datetime.now()
            years_diff = (parsed_dt - today).days / 365.25
            if parsed_dt < today:
                warnings.append(f"Expired standard: Expiry date ({std_data['expiry_std']}) is in the past.")
            elif years_diff > 20:
                warnings.append(f"Suspicious expiry date: Expiry date ({std_data['expiry_std']}) is more than 20 years in the future.")
        else:
            std_data["expiry_std"] = expiry_raw
            warnings.append(f"Unable to parse expiry date: '{expiry_raw}'. Check format manually.")

    # 3. Purity Standardization ([Value] %)
    purity_raw = extracted_data.get("purity_raw", "N/A").strip()
    if purity_raw == "N/A":
        std_data["purity_std"] = "N/A"
        warnings.append("Missing Purity (Raw was N/A).")
    else:
        # Extract digits/decimals (including optional space/percentage)
        match = re.search(r'(\d+(?:\.\d+)?)', purity_raw)
        if match:
            val = float(match.group(1))
            std_data["purity_std"] = f"{val} %"
            
            # Purity Range Check (0% - 100%)
            if val < 0.0 or val > 100.0:
                warnings.append(f"Invalid purity value range: {val}% (must be 0-100%).")
        else:
            std_data["purity_std"] = purity_raw
            warnings.append(f"Unable to extract purity numerical value from: '{purity_raw}'.")

    # 4. Storage Condition Standardization (-20°C / 4°C / RT)
    storage_raw = extracted_data.get("storage_raw", "N/A").strip()
    temp_mappings = rules.get("temp_mappings", {})
    
    if storage_raw == "N/A":
        std_data["storage_std"] = "RT"
        warnings.append("Missing Storage Condition (Raw was N/A). Defaulted to RT.")
    else:
        matched_temp = None
        for std_temp, keywords in temp_mappings.items():
            for kw in keywords:
                # Case-insensitive substring match
                if kw.lower() in storage_raw.lower():
                    matched_temp = std_temp
                    break
            if matched_temp:
                break
                
        if matched_temp:
            std_data["storage_std"] = matched_temp
        else:
            # Fallback to RT and issue a review warning
            std_data["storage_std"] = "RT"
            warnings.append(f"Storage condition '{storage_raw}' could not be matched. Defaulted to RT.")

    # 5. Brand Name Standardization
    brand_raw = extracted_data.get("brand_raw", "N/A").strip()
    if brand_raw == "N/A":
        std_data["brand_std"] = "N/A"
        warnings.append("Missing Brand Name (Raw was N/A).")
    else:
        std_data["brand_std"] = re.sub(r'\s+', ' ', brand_raw).title()

    # 6. Amount Standardization
    amount_raw = extracted_data.get("amount_raw", "N/A").strip()
    if amount_raw == "N/A":
        std_data["amount_std"] = "N/A"
        warnings.append("Missing Packaging Amount (Raw was N/A).")
    else:
        clean_amount = amount_raw.lower().strip()
        clean_amount = re.sub(r'(\d+)\s*(g|ml|mg|l|kg|ul)\b', r'\1 \2', clean_amount)
        # Normalize uppercase/lowercase units
        clean_amount = clean_amount.replace("ml", "mL").replace("ul", "uL").replace("l ", "L ").replace("kg", "kg").replace("mg", "mg").replace("g ", "g ")
        std_data["amount_std"] = clean_amount

    # 7. CAS Number Standardization
    cas_raw = extracted_data.get("cas_no_raw", "N/A").strip()
    if cas_raw == "N/A":
        std_data["cas_no_std"] = "N/A"
        warnings.append("Missing CAS Number (Raw was N/A).")
    else:
        match = re.search(r'(\b\d{2,7}-\d{2}-\d\b)', cas_raw)
        if match:
            std_data["cas_no_std"] = match.group(1)
        else:
            cleaned_cas = re.sub(r'[^0-9\-]', '', cas_raw)
            if re.match(r'^\d{2,7}-\d{2}-\d$', cleaned_cas):
                std_data["cas_no_std"] = cleaned_cas
            else:
                std_data["cas_no_std"] = cas_raw
                warnings.append(f"Invalid or non-standard CAS Number format: '{cas_raw}'.")

    # 8. Molecular Weight Standardization
    mw_raw = extracted_data.get("mw_raw", "N/A").strip()
    if mw_raw == "N/A":
        std_data["mw_std"] = "N/A"
        warnings.append("Missing Molecular Weight (Raw was N/A).")
    else:
        match = re.search(r'(\d+(?:\.\d+)?)', mw_raw)
        if match:
            val = float(match.group(1))
            std_data["mw_std"] = f"{val} g/mol"
        else:
            std_data["mw_std"] = mw_raw
            warnings.append(f"Unable to extract numerical Molecular Weight from: '{mw_raw}'.")

    # 9. Check AI Confidence Warnings
    confidence_keys = [
        ("product_std_confidence", "Product Name"),
        ("brand_raw_confidence", "Brand"),
        ("batch_no_confidence", "Batch No"),
        ("expiry_raw_confidence", "Expiry Date"),
        ("purity_raw_confidence", "Purity"),
        ("amount_raw_confidence", "Packaging Amount"),
        ("cas_no_raw_confidence", "CAS Number"),
        ("mw_raw_confidence", "Molecular Weight"),
        ("storage_raw_confidence", "Storage Condition")
    ]
    for key, field_name in confidence_keys:
        conf = extracted_data.get(key, "high")
        if conf == "low":
            warnings.append(f"Low AI confidence score during extraction of {field_name}.")

    return std_data, warnings
