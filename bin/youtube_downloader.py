#!/usr/bin/env python3
# bin/youtube_downloader.py
import sys
import os
import logging

# Add the src directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
sys.path.insert(0, project_root)

# Set up basic logging first (minimal setup to allow modules to log)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Initialize the core logger
logger = logging.getLogger("youtube_downloader")
logger.info("Starting YouTube Downloader application")

def main():
    """Main entry point"""
    try:
        # First, import the logging utilities
        from src.utils.logging_utils import setup_logging, get_logger
       
        # Now we can import and use our modules that might log
        from src.utils.environment import env
       
        # Set up full logging configuration
        setup_logging(
            logs_dir="logs",
            log_level=env.get("YOUTUBE_LOG_LEVEL", "INFO"),
            log_file="youtube_downloader.log"
        )
        
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