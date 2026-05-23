import os
import threading
import asyncio
import webview
from app.utils.logger import get_logger, register_ui_logger
import app.utils.secure_store as secure_store
import app.utils.config_manager as config_manager
import app.utils.gas_client as gas_client
import app.core.queue_db as queue_db
import app.core.preprocessor as preprocessor
from app.exporters.excel import export_to_excel
from app.pipeline import COAPipeline

logger = get_logger("Bridge")

class WebviewBridge:
    """IPC Bridge exposing Python backend functions directly to the webview JS window."""
    
    def __init__(self):
        self._window = None # Set after window creation
        self._pipeline = None
        self._async_loop = None
        
    def set_window(self, window):
        self._window = window
        # Register a logger handler to send real-time python logs to the UI console log panel!
        register_ui_logger(self.log_to_frontend)
        
    def set_loop(self, loop):
        self._async_loop = loop
        self._pipeline = COAPipeline(progress_callback=self.pipeline_progress_callback)

    def _parse_string_arg(self, args) -> str:
        """Parse a single string argument, reconstructing it if it was unpacked by pywebview."""
        if not args:
            return ""
        # If it is a tuple/list wrapping a string (e.g. from dialogs)
        target = args[0]
        if isinstance(target, (list, tuple)) and len(target) > 0:
            target = target[0]
            
        if isinstance(target, str):
            if len(args) == 1:
                return target
            # If all args are single character strings, join them
            if all(isinstance(x, str) and len(x) == 1 for x in args):
                return "".join(args)
            return target
        return str(target)

    def log_to_frontend(self, message: str):
        """Invoke a JS function to append logs to the UI log console."""
        if self._window:
            # Escape backslashes, quotes, and newlines for JS execution
            safe_msg = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            self._window.evaluate_js(f"if (window.appendLog) {{ window.appendLog(\"{safe_msg}\"); }}")

    def pipeline_progress_callback(self, status: str, message: str, task_id: int = None):
        """Callback to push pipeline status changes to the frontend UI."""
        if self._window:
            safe_msg = message.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            js_code = f"if (window.onPipelineProgress) {{ window.onPipelineProgress('{status}', '{safe_msg}', {task_id or 'null'}); }}"
            self._window.evaluate_js(js_code)

    # ==========================================================================
    # API ENDPOINTS EXPOSED TO JAVASCRIPT
    # ==========================================================================

    def select_folder(self) -> str:
        """Open a native OS directory selection dialog."""
        logger.info("Opening folder selection dialog...")
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            folder_path = result[0]
            logger.info(f"User selected folder: {folder_path}")
            return folder_path
        return ""

    def select_excel_save_path(self) -> str:
        """Open a native OS save file dialog for the Excel summary report."""
        logger.info("Opening save file dialog...")
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, 
            file_types=("Excel Files (*.xlsx)", "CSV Files (*.csv)"),
            save_filename="summary.xlsx"
        )
        if result:
            save_path = result[0]
            logger.info(f"User selected export path: {save_path}")
            return save_path
        return ""

    def save_api_key(self, *args) -> dict:
        """Encrypt and save the user's Gemini API Key."""
        api_key = self._parse_string_arg(args)
        success = secure_store.save_api_key(api_key.strip())
        return {"status": "success" if success else "error"}

    def get_api_key_masked(self) -> str:
        """Return a masked representation of the key if it exists in secure store."""
        key = secure_store.get_api_key()
        if key:
            # Mask the key for UI safety: show first 4 and last 4, middle masked
            if len(key) > 8:
                return f"{key[:4]}****************{key[-4:]}"
            return "****************"
        return ""

    def get_config(self) -> dict:
        """Return current configuration dict."""
        return config_manager.load_config()

    def save_config(self, config_data: dict) -> dict:
        """Save settings dictionary to config.json."""
        success = config_manager.save_config(config_data)
        return {"status": "success" if success else "error"}

    def start_pipeline(self, *args) -> dict:
        """Scan a folder for files, queue them in SQLite, and run the pipeline."""
        folder_path = self._parse_string_arg(args)
        if not folder_path or not os.path.exists(folder_path):
            return {"status": "error", "message": "Invalid folder path."}
            
        # Scan and add files
        count = self._pipeline.scan_and_enqueue(folder_path)
        
        # Run pipeline in background event loop thread
        if count > 0 or len(queue_db.get_all_tasks()) > 0:
            asyncio.run_coroutine_threadsafe(self._pipeline.run_pipeline(), self._async_loop)
            return {"status": "success", "count": count}
        else:
            return {"status": "empty", "message": "No supported PDF or image files found in folder."}

    def cancel_pipeline(self) -> dict:
        """Request the pipeline execution to stop."""
        self._pipeline.cancel_pipeline()
        return {"status": "success"}

    def get_tasks(self) -> list:
        """Return all tasks from SQLite database."""
        return queue_db.get_all_tasks()

    def delete_task(self, *args) -> dict:
        """Delete a task by its file path from SQLite."""
        file_path = self._parse_string_arg(args)
        success = queue_db.delete_task(file_path)
        return {"status": "success" if success else "error"}

    def clear_queue(self) -> dict:
        """Truncate the tasks table."""
        success = queue_db.clear_queue()
        return {"status": "success" if success else "error"}

    def get_document_pages_b64(self, *args) -> list:
        """
        On-the-fly rendering/preprocessing of a COA file for frontend display.
        Returns a list of base64 JPEG page strings.
        """
        file_path = self._parse_string_arg(args)
        if not os.path.exists(file_path):
            logger.error(f"Cannot render pages. File not found: {file_path}")
            return []
            
        try:
            # We can use our preprocessor to convert PDF or image into base64 page views
            pages = preprocessor.preprocess_file(file_path)
            return pages
        except Exception as e:
            logger.error(f"Failed to render document preview pages: {e}")
            return []

    def verify_and_complete_task(self, *args) -> dict:
        """
        Save human-reviewed fields, mark status as Completed, and async sync to Google Sheets.
        """
        if not args:
            return {"status": "error", "message": "No arguments provided."}
            
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            file_path = args[0]
            edited_data = args[1]
        else:
            # Reconstruct from unpacked args
            edited_data = args[-1] if isinstance(args[-1], dict) else {}
            file_path = "".join(args[:-1]) if len(args) > 1 else ""
            
        logger.info(f"Human verified task: {os.path.basename(file_path)}")
        
        # 1. Update status locally
        success = queue_db.update_task_status(
            file_path, 
            status="Completed", 
            extracted_data=edited_data, 
            validation_errors=[]
        )
        
        if success:
            task = queue_db.get_task_by_path(file_path)
            if task:
                # 2. Get GAS Web App URL from config
                config = config_manager.load_config()
                gas_url = config.get("gas_web_app_url", "")
                
                # 3. Synchronize to Google Sheets (Non-blocking background thread)
                if gas_url:
                    def sync_worker():
                        gas_client.sync_entry_to_cloud(
                            gas_url, 
                            task["file_hash"], 
                            task["file_name"], 
                            edited_data
                        )
                    threading.Thread(target=sync_worker, daemon=True).start()
                    
            return {"status": "success"}
        return {"status": "error", "message": "Failed to update record in SQLite queue."}

    def export_summary_report(self, *args) -> dict:
        """Export all Completed tasks into Excel summary."""
        try:
            output_path = self._parse_string_arg(args)
            tasks = queue_db.get_all_tasks()
            completed_tasks = [t for t in tasks if t["status"] == "Completed"]
            
            if not completed_tasks:
                return {"status": "error", "message": "沒有已完成 (人工校對) 的數據可供匯出。"}
                
            config = config_manager.load_config()
            fields_order = config.get("fields_order", [])
            fields_visibility = config.get("fields_visibility", {})
            column_headers = config.get("column_headers", {})
            
            success = export_to_excel(
                completed_tasks, 
                output_path, 
                fields_order, 
                fields_visibility,
                column_headers
            )
            if success:
                return {"status": "success"}
            else:
                return {"status": "error", "message": "Excel 寫入失敗，請確認檔案是否被其他程式開啟。"}
        except Exception as e:
            logger.error(f"Failed to export summary report: {e}")
            return {"status": "error", "message": f"匯出異常：{str(e)}"}
