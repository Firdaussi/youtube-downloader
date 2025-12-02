"""
Logging configuration for YouTube Playlist Downloader

This module provides different logging levels for console and file output.
For a windowed application, we keep console output minimal (WARNING and above)
while maintaining detailed file logs for troubleshooting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Default logging levels
CONSOLE_LEVEL = logging.WARNING  # Only warnings and errors to console
FILE_LEVEL = logging.DEBUG       # Everything goes to file

# Log file location
DEFAULT_LOG_FILE = "logs/youtube_downloader.log"


def setup_logging(
    console_level: int = CONSOLE_LEVEL,
    file_level: int = FILE_LEVEL,
    log_file: Optional[str] = None,
    quiet_mode: bool = False
) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        console_level: Logging level for console output (default: WARNING)
        file_level: Logging level for file output (default: DEBUG)
        log_file: Path to log file (default: logs/youtube_downloader.log)
        quiet_mode: If True, disable console output completely
    """
    if log_file is None:
        log_file = DEFAULT_LOG_FILE
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything at root level
    
    # IMPORTANT: Clear ALL existing handlers first
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler - minimal logging (unless quiet mode)
    if not quiet_mode:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'  # Simpler format for console
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Silence noisy third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('yt_dlp').setLevel(logging.WARNING)
    logging.getLogger('yt-dlp').setLevel(logging.WARNING)
    
    # Silence common noisy modules
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # Set the flag in logging_utils to prevent it from reconfiguring
    try:
        import src.utils.logging_utils as logging_utils
        logging_utils._logging_configured = True
    except:
        pass
    
    # Log initial setup message (to file only)
    if not quiet_mode:
        file_only_logger = logging.getLogger(__name__)
        file_only_logger.info(f"Logging configured - Console: {logging.getLevelName(console_level)}, File: {log_file}")


def set_console_level(level: int) -> None:
    """
    Change console logging level at runtime.
    
    Args:
        level: New logging level (logging.DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setLevel(level)


def enable_debug_mode() -> None:
    """Enable debug logging to console (useful for troubleshooting)"""
    set_console_level(logging.DEBUG)
    logging.warning("Debug mode enabled - verbose console output")


def enable_quiet_mode() -> None:
    """Disable all console logging"""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            root_logger.removeHandler(handler)


# Convenience function for getting loggers (maintains compatibility)
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Preset configurations
class LogLevel:
    """Preset logging levels for convenience"""
    SILENT = logging.CRITICAL + 1  # No output
    QUIET = logging.ERROR          # Errors only
    NORMAL = logging.WARNING       # Warnings and errors (default)
    VERBOSE = logging.INFO         # Info, warnings, and errors
    DEBUG = logging.DEBUG          # Everything


# Quick setup functions
def setup_gui_logging(log_file: Optional[str] = None) -> None:
    """
    Setup logging optimized for GUI applications.
    - Console: WARNING level only
    - File: DEBUG level (everything)
    """
    setup_logging(
        console_level=LogLevel.NORMAL,
        file_level=LogLevel.DEBUG,
        log_file=log_file,
        quiet_mode=False
    )


def setup_silent_logging(log_file: Optional[str] = None) -> None:
    """
    Setup logging with no console output (completely silent).
    - Console: None
    - File: DEBUG level (everything)
    """
    setup_logging(
        console_level=LogLevel.SILENT,
        file_level=LogLevel.DEBUG,
        log_file=log_file,
        quiet_mode=True
    )


def setup_debug_logging(log_file: Optional[str] = None) -> None:
    """
    Setup logging for debugging/development.
    - Console: DEBUG level (everything)
    - File: DEBUG level (everything)
    """
    setup_logging(
        console_level=LogLevel.DEBUG,
        file_level=LogLevel.DEBUG,
        log_file=log_file,
        quiet_mode=False
    )