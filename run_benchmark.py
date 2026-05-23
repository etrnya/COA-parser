import os
import json
import asyncio
import time
from app.utils.logger import get_logger
import app.utils.secure_store as secure_store
import app.utils.config_manager as config_manager
import app.core.preprocessor as preprocessor
import app.core.validator as validator
from app.providers.gemini import GeminiProvider

logger = get_logger("Benchmark")

async def run_regression_benchmark():
    """Runs a regression test checking extraction accuracy against dataset/expected.json."""
    logger.info("==============================================================")
    logger.info("   AI COA Parser - Regression Accuracy Benchmark Runner       ")
    logger.info("==============================================================")
    
    # 1. Load ground truth
    dataset_dir = "dataset"
    expected_json_path = os.path.join(dataset_dir, "expected.json")
    
    if not os.path.exists(expected_json_path):
        logger.error(f"Expected ground truth dataset not found: {expected_json_path}")
        return
        
    with open(expected_json_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
        
    if not ground_truth:
        logger.warning("Ground truth expected.json is empty. Add entries to benchmark.")
        return
        
    # 2. Get API Key & Initialize Provider
    api_key = secure_store.get_api_key()
    if not api_key:
        logger.error("No Gemini API Key found in secure store. Cannot run benchmark.")
        return
        
    provider = GeminiProvider()
    if not provider.initialize(api_key):
        logger.error("API authentication failed. Check your stored API Key.")
        return
        
    config = config_manager.load_config()
    std_rules = config.get("standardization_rules", {})
    
    total_fields = 0
    passed_fields = 0
    start_time = time.time()
    
    logger.info(f"Loaded {len(ground_truth)} reference files to test.")
    
    for filename, expected_fields in ground_truth.items():
        file_path = os.path.join(dataset_dir, filename)
        if not os.path.exists(file_path):
            logger.warning(f"Benchmark file '{filename}' listed in expected.json does not exist in 'dataset/' directory. Skipping.")
            continue
            
        logger.info(f"\nEvaluating document: {filename}...")
        
        try:
            # Render pages
            pages = preprocessor.preprocess_file(file_path)
            
            # Extract fields
            raw_data = provider.extract_coa_fields(pages, validator.COA_EXTRACTION_SCHEMA)
            std_data, warnings = validator.validate_and_standardize_fields(raw_data, std_rules)
            
            # Compare fields: product_raw, batch_no, expiry_raw, purity_raw, storage_raw
            # Compare fields dynamically based on what is present in expected ground truth
            for field, expected_val in expected_fields.items():
                if field not in std_data:
                    continue
                total_fields += 1
                expected_val_str = str(expected_val).strip()
                extracted_val_str = str(std_data.get(field, "")).strip()
                
                # Check match (case insensitive, strip spacing)
                match = expected_val_str.lower() == extracted_val_str.lower()
                
                if match:
                    passed_fields += 1
                    logger.info(f"  [PASS] {field}: Expected='{expected_val_str}' | Extracted='{extracted_val_str}'")
                else:
                    logger.info(f"  [FAIL] {field}: Expected='{expected_val_str}' | Extracted='{extracted_val_str}'")
                    
        except Exception as e:
            logger.error(f"Error benchmarking file {filename}: {e}")
            
    # Calculate accuracy metrics
    duration = time.time() - start_time
    accuracy = (passed_fields / total_fields * 100) if total_fields > 0 else 0
    
    logger.info("\n==============================================================")
    logger.info("   Benchmark Summary Report")
    logger.info("==============================================================")
    logger.info(f"Total Fields Checked : {total_fields}")
    logger.info(f"Passed Fields        : {passed_fields}")
    logger.info(f"Failed Fields        : {total_fields - passed_fields}")
    logger.info(f"Overall Accuracy     : {accuracy:.2f}%")
    logger.info(f"Execution Duration   : {duration:.2f} seconds")
    logger.info("==============================================================")

if __name__ == "__main__":
    asyncio.run(run_regression_benchmark())
