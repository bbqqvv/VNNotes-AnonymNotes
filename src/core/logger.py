import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logging(app_name="VNNotes"):
    """
    Sets up the application logging infrastructure.
    Uses RotatingFileHandler to manage log file sizes.
    Stores logs in the user's app data directory.
    """
    # 1. Determine Log Directory (User Data)
    if sys.platform == 'win32':
        app_data = os.getenv('APPDATA')
        log_dir = os.path.join(app_data, app_name, 'logs')
    else:
        log_dir = os.path.expanduser(f'~/.{app_name.lower()}/logs')
        
    os.makedirs(log_dir, exist_ok=True)
    
    # 2. Define Log File Path
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{app_name}_{timestamp}.log")
    
    # 3. Configure Root Logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) # Capture everything, filter handlers later
    
    # 4. Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 5. File Handler (Rotating)
    # Max size: 5MB, Backup count: 3
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 6. Console Handler (for Dev)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) # Less noise in console
    console_handler.setFormatter(formatter)
    
    # 7. Add Handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info("="*60)
    logging.info(f"{app_name} Session Started")
    logging.info(f"Log File: {log_file}")
    logging.info("="*60)
    
    return log_file
