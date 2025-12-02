# src/utils/logging_utils.py

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# Flag to track if logging has been configured
_logging_configured = False

def setup_logging(logs_dir: str = "logs", 
                 log_level: str = "INFO", 
                 log_file: str = "youtube_downloader.log",
                 max_size_mb: int = 10,
                 backup_count: int = 5,
                 force: bool = False) -> logging.Logger:
    """
    Configure application logging
    
    Args:
        logs_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Name of the log file
        max_size_mb: Maximum size of log file in megabytes before rotation
        backup_count: Number of backup files to keep
        force: Force reconfiguration even if already configured
        
    Returns:
        Configured logger instance
    """
    global _logging_configured
    
    # If logging is already configured (e.g., by logging_config), don't reconfigure
    if _logging_configured and not force:
        return logging.getLogger()
    
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # Get log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates when called multiple times
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Create file handler with rotation
    log_path = os.path.join(logs_dir, log_file)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_size_mb * 1024 * 1024,  # Convert MB to bytes
        backupCount=backup_count
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Log startup message
    root_logger.info(f"Logging configured with level {log_level} to {log_path}")
    
    _logging_configured = True
    
    return root_logger

def get_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name and optional level
    
    Args:
        name: Logger name
        log_level: Optional specific log level for this logger
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    if log_level:
        numeric_level = getattr(logging, log_level.upper(), None)
        if numeric_level:
            logger.setLevel(numeric_level)
            
    return logger

def configure_module_logging(module_name: str, log_level: str = "INFO") -> None:
    """
    Configure logging for a specific module
    
    Args:
        module_name: Name of the module
        log_level: Logging level for the module
    """
    logger = logging.getLogger(module_name)
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)