import requests
from app.utils.logger import get_logger

logger = get_logger("GASClient")

def check_cloud_cache(gas_url: str, file_hash: str) -> dict:
    """
    Check if a COA with the given SHA256 file hash has already been processed and synced
    to the shared Google Sheet.
    
    Args:
        gas_url: Google Apps Script Web App deployment URL.
        file_hash: SHA256 checksum of the target file.
        
    Returns:
        dict: The parsed data dictionary if found, or None if not found/error.
    """
    if not gas_url:
        return None
        
    try:
        logger.info(f"Checking Google Sheets cloud cache for hash: {file_hash[:10]}...")
        params = {
            "action": "check_cache",
            "hash": file_hash
        }
        # Timeout at 5 seconds for cache checks to avoid slowing down pipeline
        response = requests.get(gas_url, params=params, timeout=5)
        
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("status") == "success" and res_json.get("found") is True:
                logger.info("Cloud cache HIT! Retrieved entry from Google Sheets.")
                return res_json.get("data")
            else:
                logger.info("Cloud cache MISS. Entry not found in Google Sheets.")
        else:
            logger.warning(f"GAS cache query returned status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to query Google Sheets cache (network error/timeout): {e}")
        
    return None

def sync_entry_to_cloud(gas_url: str, file_hash: str, file_name: str, payload: dict) -> bool:
    """
    Sync a processed COA entry to Google Sheets via GAS Web App POST request.
    
    Args:
        gas_url: Google Apps Script Web App deployment URL.
        file_hash: SHA256 checksum of the file.
        file_name: Base filename of the COA.
        payload: Dictionary of parsed fields (raw + standardized values).
        
    Returns:
        bool: True if synced successfully, False otherwise.
    """
    if not gas_url:
        logger.warning("No GAS Web App URL configured. Skipping cloud sync.")
        return False
        
    try:
        logger.info(f"Syncing entry '{file_name}' to Google Sheets...")
        
        # Flatten payload or construct structured sync format
        # Excel exporter maps fields:
        # File Name | Product Raw | Product Std | Batch No | Expiry Raw | Expiry Std | Purity Raw | Purity Std | Storage Raw | Storage Std
        sync_data = {
            "action": "save_entry",
            "hash": file_hash,
            "file_name": file_name,
            "product_raw": payload.get("product_raw", "N/A"),
            "product_std": payload.get("product_std", "N/A"),
            "brand_raw": payload.get("brand_raw", "N/A"),
            "brand_std": payload.get("brand_std", "N/A"),
            "batch_no": payload.get("batch_no", "N/A"),
            "expiry_raw": payload.get("expiry_raw", "N/A"),
            "expiry_std": payload.get("expiry_std", "N/A"),
            "purity_raw": payload.get("purity_raw", "N/A"),
            "purity_std": payload.get("purity_std", "N/A"),
            "amount_raw": payload.get("amount_raw", "N/A"),
            "amount_std": payload.get("amount_std", "N/A"),
            "cas_no_raw": payload.get("cas_no_raw", "N/A"),
            "cas_no_std": payload.get("cas_no_std", "N/A"),
            "mw_raw": payload.get("mw_raw", "N/A"),
            "mw_std": payload.get("mw_std", "N/A"),
            "storage_raw": payload.get("storage_raw", "N/A"),
            "storage_std": payload.get("storage_std", "N/A"),
        }
        
        # Deploying GAS web app might redirect, requests handles redirects (302) by default
        response = requests.post(gas_url, json=sync_data, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            if res_json.get("status") == "success":
                logger.info(f"Successfully synced '{file_name}' to cloud Google Sheet.")
                return True
            else:
                logger.error(f"GAS App returned sync error: {res_json.get('message')}")
        else:
            logger.error(f"GAS Server returned status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to sync entry to cloud: {e}")
        
    return False

# ==============================================================================
# GOOGLE APPS SCRIPT (GAS) CODE TEMPLATE
# ==============================================================================
# The following JavaScript code should be copy-pasted into the Google Sheets
# Extensions -> Apps Script editor, and then deployed as a Web App:
#
# /*
# function doGet(e) {
#   var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
#   var action = e.parameter.action;
#   
#   if (action === "check_cache") {
#     var hash = e.parameter.hash;
#     var data = sheet.getDataRange().getValues();
#     
#     // Row structure: Timestamp | File Name | Hash (Col C) | Product Raw | Product Std | Brand Raw | Brand Std | Batch No | Expiry Raw | Expiry Std | Purity Raw | Purity Std | Amount Raw | Amount Std | CAS Raw | CAS Std | MW Raw | MW Std | Storage Raw | Storage Std
#     for (var i = 1; i < data.length; i++) {
#       if (data[i][2] === hash) {
#         var result = {
#           product_raw: data[i][3],
#           product_std: data[i][4],
#           brand_raw: data[i][5],
#           brand_std: data[i][6],
#           batch_no: data[i][7],
#           expiry_raw: data[i][8],
#           expiry_std: data[i][9],
#           purity_raw: data[i][10],
#           purity_std: data[i][11],
#           amount_raw: data[i][12],
#           amount_std: data[i][13],
#           cas_no_raw: data[i][14],
#           cas_no_std: data[i][15],
#           mw_raw: data[i][16],
#           mw_std: data[i][17],
#           storage_raw: data[i][18],
#           storage_std: data[i][19]
#         };
#         return ContentService.createTextOutput(JSON.stringify({
#           status: "success",
#           found: true,
#           data: result
#         })).setMimeType(ContentService.MimeType.JSON);
#       }
#     }
#     return ContentService.createTextOutput(JSON.stringify({
#       status: "success",
#       found: false
#     })).setMimeType(ContentService.MimeType.JSON);
#   }
#   
#   return ContentService.createTextOutput(JSON.stringify({
#     status: "error",
#     message: "Invalid GET action"
#   })).setMimeType(ContentService.MimeType.JSON);
# }
# 
# function doPost(e) {
#   try {
#     var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
#     
#     // Ensure headers exist
#     if (sheet.getLastRow() === 0) {
#       sheet.appendRow([
#         "Timestamp", "File Name", "SHA256 Hash", 
#         "Product Name (Original)", "Product Name (Standardized)", 
#         "Brand (Original)", "Brand (Standardized)",
#         "Batch No", 
#         "Expiry Date (Original)", "Expiry Date (Standardized)", 
#         "Purity (Original)", "Purity (Standardized)", 
#         "Amount (Original)", "Amount (Standardized)",
#         "CAS Number (Original)", "CAS Number (Standardized)",
#         "Molecular Weight (Original)", "Molecular Weight (Standardized)",
#         "Storage Condition (Original)", "Storage Condition (Standardized)"
#       ]);
#     }
#     
#     var postData = JSON.parse(e.postData.contents);
#     
#     if (postData.action === "save_entry") {
#       var hash = postData.hash;
#       var data = sheet.getDataRange().getValues();
#       
#       // Deduplicate: If hash already exists, update row instead of appending
#       for (var i = 1; i < data.length; i++) {
#         if (data[i][2] === hash) {
#           // Update existing row
#           var rowNum = i + 1;
#           sheet.getRange(rowNum, 1, 1, 20).setValues([[
#             new Date(),
#             postData.file_name,
#             hash,
#             postData.product_raw,
#             postData.product_std,
#             postData.brand_raw,
#             postData.brand_std,
#             postData.batch_no,
#             postData.expiry_raw,
#             postData.expiry_std,
#             postData.purity_raw,
#             postData.purity_std,
#             postData.amount_raw,
#             postData.amount_std,
#             postData.cas_no_raw,
#             postData.cas_no_std,
#             postData.mw_raw,
#             postData.mw_std,
#             postData.storage_raw,
#             postData.storage_std
#           ]]);
#           return ContentService.createTextOutput(JSON.stringify({
#             status: "success",
#             message: "Entry updated successfully"
#           })).setMimeType(ContentService.MimeType.JSON);
#         }
#       }
#       
#       // Else append new row
#       sheet.appendRow([
#         new Date(),
#         postData.file_name,
#         hash,
#         postData.product_raw,
#         postData.product_std,
#         postData.brand_raw,
#         postData.brand_std,
#         postData.batch_no,
#         postData.expiry_raw,
#         postData.expiry_std,
#         postData.purity_raw,
#         postData.purity_std,
#         postData.amount_raw,
#         postData.amount_std,
#         postData.cas_no_raw,
#         postData.cas_no_std,
#         postData.mw_raw,
#         postData.mw_std,
#         postData.storage_raw,
#         postData.storage_std
#       ]);
#       
#       return ContentService.createTextOutput(JSON.stringify({
#         status: "success",
#         message: "Entry appended successfully"
#       })).setMimeType(ContentService.MimeType.JSON);
#     }
#   } catch (err) {
#     return ContentService.createTextOutput(JSON.stringify({
#       status: "error",
#       message: err.toString()
#     })).setMimeType(ContentService.MimeType.JSON);
#   }
# }
# */
