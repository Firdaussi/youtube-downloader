# main_env.py - Main entry point with environment variable support

import logging
from integration import create_enhanced_application

# Replace the existing main function
def main():
    """Main entry point"""
    try:
        app = create_enhanced_application()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()