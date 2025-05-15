# main.py - Fixed main entry point

import logging
import os
from logging.handlers import RotatingFileHandler

# Import fixed implementations - replace the originals with our fixed versions
# NOTE: You'll need to rename these files to remove the "_full_fix" suffix when using them
from repositories import JsonConfigurationRepository, JsonHistoryRepository
from validators import YouTubeCookieValidator, FileNameSanitizer, QualityFormatter
from downloader import YouTubePlaylistDownloader
from download_service import DownloadService
from presenters import DownloadPresenter, HistoryPresenter, SettingsPresenter
from gui import YouTubeDownloaderApp


def setup_logging():
    """Configure application logging"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/youtube_downloader.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger


def create_application():
    """Create application with dependency injection"""
    # Setup logging
    logger = setup_logging()
    logger.info("Starting YouTube Playlist Downloader")
    
    # Create repositories
    config_repository = JsonConfigurationRepository()
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