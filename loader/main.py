# main_env.py - Main entry point with environment variable support

import logging
import os
from logging.handlers import RotatingFileHandler

# Import environment module first to ensure variables are loaded
from environment import env

# Import repositories
from repositories import JsonHistoryRepository
from env_config import EnvironmentConfigRepository

# Import validators and utilities
from validators import YouTubeCookieValidator, FileNameSanitizer, QualityFormatter

# Import core components
from downloader import YouTubePlaylistDownloader
from download_service import DownloadService
from presenters import DownloadPresenter, HistoryPresenter, SettingsPresenter
from gui import YouTubeDownloaderApp


def setup_logging():
    """Configure application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory from environment or fallback
    logs_dir = env.get("YOUTUBE_LOGS_DIR", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Log level from environment or fallback to INFO
    log_level_name = env.get("YOUTUBE_LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler with rotation
    log_file = os.path.join(logs_dir, "youtube_downloader.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger


def create_application():
    """Create application with dependency injection"""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting YouTube Playlist Downloader")
    
    # Show environment info
    logger.info(f"Using environment settings")
    logger.info(f"Download directory: {env.get('YOUTUBE_DOWNLOAD_DIR', 'Not set')}")
    logger.info(f"Cookie method: {env.get('YOUTUBE_COOKIE_METHOD', 'Not set')}")
    
    # Create repositories - use environment config
    config_repository = EnvironmentConfigRepository()
    history_repository = JsonHistoryRepository()
    
    # Create validators and utilities
    cookie_validator = YouTubeCookieValidator()
    filename_sanitizer = FileNameSanitizer()
    quality_formatter = QualityFormatter()
    
    # Create downloader
    youtube_downloader = YouTubePlaylistDownloader(
        quality_formatter=quality_formatter,
        filename_sanitizer=filename_sanitizer,
        cookie_validator=cookie_validator,
        history_repository=history_repository,
        logger=logger.getChild('Downloader')
    )
    
    # Create download service
    download_service = DownloadService(
        downloader=youtube_downloader,
        history_repository=history_repository,
        cookie_validator=cookie_validator,
        logger=logger.getChild('DownloadService')
    )
    
    # Create presenters
    download_presenter = DownloadPresenter(
        download_service=download_service,
        config_repository=config_repository,
        history_repository=history_repository,
        logger=logger.getChild('DownloadPresenter')
    )
    
    history_presenter = HistoryPresenter(
        history_repository=history_repository
    )
    
    settings_presenter = SettingsPresenter(
        config_repository=config_repository,
        cookie_validator=cookie_validator
    )
    
    # Create application
    app = YouTubeDownloaderApp(
        download_presenter=download_presenter,
        history_presenter=history_presenter,
        settings_presenter=settings_presenter
    )
    
    return app


def main():
    """Main entry point"""
    try:
        app = create_application()
        app.mainloop()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()