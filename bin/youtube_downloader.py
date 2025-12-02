#!/usr/bin/env python3
# bin/youtube_downloader.py
import sys
import os

# Add the src directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

# ===== SETUP QUIET LOGGING FIRST (BEFORE OTHER IMPORTS) =====
from src.utils.logging_config import setup_gui_logging
setup_gui_logging()
# =============================================================

# Now import logging for this module
import logging

# Initialize the core logger
logger = logging.getLogger("youtube_downloader")
logger.info("Starting YouTube Downloader application")

def main():
    """Main entry point"""
    try:
        # Import utilities
        from src.utils.logging_utils import get_logger
        from src.utils.environment import env
        
        # Switch to using the custom logger
        logger = get_logger("youtube_downloader")
       
        # Now import integration
        from src.integration import create_enhanced_application
       
        # Start the application
        logger.info("Starting YouTube Playlist Downloader")
        app = create_enhanced_application()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()