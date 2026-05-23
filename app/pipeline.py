import os
import asyncio
from app.utils.logger import get_logger
import app.utils.secure_store as secure_store
import app.utils.config_manager as config_manager
import app.utils.gas_client as gas_client
import app.core.preprocessor as preprocessor
import app.core.queue_db as queue_db
import app.core.classifier as classifier
import app.core.validator as validator
from app.providers.gemini import GeminiProvider

logger = get_logger("Pipeline")

class COAPipeline:
    """Orchestrates the entire document parsing, validation, and sync pipeline."""
    
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback # Callback to notify frontend UI
        self.provider = GeminiProvider()
        self.is_running = False
        
    def scan_and_enqueue(self, folder_path: str) -> int:
        """Scan folder for PDF/image files and add them as Pending tasks in SQLite."""
        if not os.path.isdir(folder_path):
            logger.error(f"Provided path is not a valid folder: {folder_path}")
            return 0
            
        supported_exts = (".pdf", ".png", ".jpg", ".jpeg")
        added_count = 0
        
        logger.info(f"Scanning folder: {folder_path}")
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_exts):
                    file_path = os.path.join(root, file)
                    file_name = file
                    
                    try:
                        # 1. Calculate file hash to prevent double work
                        file_hash = preprocessor.calculate_sha256(file_path)
                        # 2. Add to SQLite DB
                        if queue_db.add_task(file_path, file_hash, file_name):
                            added_count += 1
                    except Exception as e:
                        logger.error(f"Error enqueuing file {file}: {e}")
                        
        logger.info(f"Scan complete. Enqueued {added_count} new tasks.")
        return added_count

    async def run_pipeline(self):
        """Asynchronously run the extraction pipeline for all Pending tasks."""
        if self.is_running:
            logger.warning("Pipeline is already running.")
            return
            
        self.is_running = True
        logger.info("Starting COA Parser Pipeline processing run...")
        
        try:
            # 1. Load Configurations
            config = config_manager.load_config()
            gas_url = config.get("gas_web_app_url", "")
            std_rules = config.get("standardization_rules", {})
            
            # 2. Get API Key
            api_key = secure_store.get_api_key()
            if not api_key:
                logger.error("No Gemini API Key found in secure storage. Pipeline halted.")
                if self.progress_callback:
                    self.progress_callback("error", "API Key is missing. Please set it in Settings.")
                return
                
            # 3. Initialize Provider
            if not self.provider.initialize(api_key):
                logger.error("Failed to authenticate Gemini API Key.")
                if self.progress_callback:
                    self.progress_callback("error", "Invalid API Key. Please verify in settings.")
                return
                
            # 4. Process Loop
            tasks = queue_db.get_all_tasks()
            pending_tasks = [t for t in tasks if t["status"] == "Pending"]
            
            if not pending_tasks:
                logger.info("No Pending tasks to process.")
                if self.progress_callback:
                    self.progress_callback("finished", "No pending files found to process.")
                return
                
            total = len(pending_tasks)
            for idx, task in enumerate(pending_tasks):
                if not self.is_running:
                    logger.info("Pipeline cancelled by user.")
                    break
                    
                file_path = task["file_path"]
                file_name = task["file_name"]
                file_hash = task["file_hash"]
                
                logger.info(f"[{idx+1}/{total}] Processing: {file_name}")
                if self.progress_callback:
                    self.progress_callback("progress", f"Processing {file_name} ({idx+1}/{total})...", task["id"])
                
                # Step 1: Update SQLite to Processing
                queue_db.update_task_status(file_path, "Processing")
                
                try:
                    # Step 2: Check Google Sheets Cloud Cache
                    cloud_data = None
                    if gas_url:
                        # Run requests in thread pool to prevent blocking loop
                        loop = asyncio.get_event_loop()
                        cloud_data = await loop.run_in_executor(
                            None, gas_client.check_cloud_cache, gas_url, file_hash
                        )
                        
                    if cloud_data:
                        # Cache hit! Save straight to DB as Completed
                        # We save it as Completed because it is already a verified record from colleagues
                        queue_db.update_task_status(
                            file_path, 
                            "Completed", 
                            extracted_data=cloud_data, 
                            validation_errors=[]
                        )
                        logger.info(f"Cache hit. Completed task: {file_name}")
                        continue
                        
                    # Step 3: Cloud Cache Miss -> Preprocess (render pages & compress)
                    # Run CPU-bound fitz conversions in thread pool
                    loop = asyncio.get_event_loop()
                    base64_images = await loop.run_in_executor(
                        None, preprocessor.preprocess_file, file_path
                    )
                    
                    # Step 4: Classify Document
                    doc_type = await loop.run_in_executor(
                        None, classifier.classify_coa_document, self.provider, base64_images
                    )
                    
                    if doc_type != "COA":
                        logger.warning(f"File {file_name} classified as {doc_type}, not a COA. Skipping.")
                        queue_db.update_task_status(
                            file_path, 
                            "Failed", 
                            validation_errors=[f"Invalid document type. Classified as {doc_type}"]
                        )
                        continue
                        
                    # Step 5: AI Field Extraction
                    raw_data = await loop.run_in_executor(
                        None, self.provider.extract_coa_fields, base64_images, validator.COA_EXTRACTION_SCHEMA
                    )
                    
                    # Step 6: Local Standardization & Validation Check
                    std_data, warnings = validator.validate_and_standardize_fields(raw_data, std_rules)
                    
                    # Step 7: Save to SQLite Queue as ReviewNeeded
                    queue_db.update_task_status(
                        file_path, 
                        "ReviewNeeded", 
                        extracted_data=std_data, 
                        validation_errors=warnings
                    )
                    
                    logger.info(f"Extraction successful for {file_name}. Review warnings: {warnings}")
                    
                except Exception as e:
                    logger.error(f"Error executing pipeline for {file_name}: {e}")
                    queue_db.update_task_status(
                        file_path, 
                        "Failed", 
                        validation_errors=[f"Extraction failed: {str(e)}"]
                    )
                    
                # Small cooldown to play nice with rate limits
                await asyncio.sleep(0.5)
                
            if self.progress_callback:
                self.progress_callback("finished", "Processing completed. Ready for review.")
                
        finally:
            self.is_running = False

    def cancel_pipeline(self):
        """Stop the running pipeline execution."""
        if self.is_running:
            logger.info("Requesting pipeline cancellation...")
            self.is_running = False
