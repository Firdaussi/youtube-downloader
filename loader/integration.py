# integration.py - Integration of all improvements

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import logging
from typing import Any, Dict, List, Optional

# Import improvements
from path_utils import PathUtils
from performance_utils import ProgressThrottler, Debouncer
from theme_manager import ThemeManager, Theme
from theme_tab import ThemeTab

# Original imports
from models import DownloadConfig, DownloadProgress, DownloadStatus
from download_service import DownloadService
from downloader import YouTubePlaylistDownloader
from presenters import DownloadPresenter, HistoryPresenter, SettingsPresenter
from gui import YouTubeDownloaderApp, DownloadTab, HistoryTab, SettingsTab

logger = logging.getLogger(__name__)

class EnhancedYouTubeDownloaderApp(YouTubeDownloaderApp):
    """Enhanced version of the YouTube Downloader App with improvements"""
    
    def __init__(self, download_presenter, history_presenter, settings_presenter):
        # Initialize theme manager before the UI
        self.theme_manager = ThemeManager()
        
        # Call parent constructor
        super().__init__(download_presenter, history_presenter, settings_presenter)
        
        # Apply theme
        self.theme_manager.apply_theme(self)
        
        # Add additional UI elements
        self._add_theme_menu()
    
    def create_widgets(self):
        """Override to add theme tab"""
        # Call parent method
        super().create_widgets()
        
        # Add theme tab
        self.theme_tab = ThemeTab(self.notebook, self.theme_manager)
        self.notebook.add(self.theme_tab, text="Theme")
    
    def _add_theme_menu(self):
        """Add theme selection to menu bar"""
        # Create menu bar if not exists
        if not hasattr(self, 'menu_bar'):
            self.menu_bar = tk.Menu(self)
            self.config(menu=self.menu_bar)
        
        # Create theme menu
        theme_menu = tk.Menu(self.menu_bar, tearoff=0)
        
        # Add theme options
        for theme_id in self.theme_manager.get_theme_ids():
            theme = self.theme_manager.themes[theme_id]
            theme_menu.add_command(
                label=theme.name,
                command=lambda tid=theme_id: self.theme_manager.set_current_theme(tid)
            )
        
        # Add theme menu to menu bar
        self.menu_bar.add_cascade(label="Theme", menu=theme_menu)


class EnhancedDownloadTab(DownloadTab):
    """Enhanced version of the Download tab with performance improvements"""
    
    def __init__(self, parent, presenter, **kwargs):
        # Initialize throttlers before parent constructor
        self.progress_throttler = ProgressThrottler(base_interval=0.25)
        self.status_debouncer = Debouncer(delay=0.5)
        
        # Call parent constructor
        super().__init__(parent, presenter, **kwargs)
    
    def update_progress(self, progress: DownloadProgress):
        """Override to throttle progress updates"""
        # Use throttler to determine if we should update
        if self.progress_throttler.should_update(
            progress.playlist_id, 
            progress.progress,
            progress.status.value,
            progress.message
        ):
            # Call parent method to update UI
            super().update_progress(progress)
    
    def update_status(self, message: str):
        """Override to debounce status updates"""
        # Store reference to parent's update_status method
        parent_update = super().update_status
        
        # Use debouncer with explicit method reference
        @self.status_debouncer
        def delayed_update(msg):
            parent_update(msg)  # Call the stored reference
        
        # Queue the update
        delayed_update(message)


class EnhancedYouTubePlaylistDownloader(YouTubePlaylistDownloader):
    """Enhanced version of the playlist downloader with path utilities"""
    
    def _create_playlist_folder(self, base_dir: str, playlist_title: str) -> str:
        """Override to use PathUtils for safer path handling"""
        # Validate base directory
        valid, message = PathUtils.validate_path(base_dir)
        if not valid:
            self.logger.error(f"Invalid base directory: {message}")
            raise ValueError(f"Invalid download directory: {message}")
        
        # Ensure base directory exists
        ensured, message = PathUtils.ensure_directory(base_dir)
        if not ensured:
            self.logger.error(f"Failed to create base directory: {message}")
            raise ValueError(f"Failed to create download directory: {message}")
            
        # Create safe path for playlist folder
        sanitized_title = PathUtils.sanitize_filename(playlist_title)
        folder_path = os.path.join(base_dir, sanitized_title)
        
        # Check if path is too long
        if len(folder_path) > PathUtils.get_max_path_length():
            self.logger.warning(f"Path too long: {folder_path}")
            # Truncate the title if path is too long
            max_title_length = 50
            sanitized_title = sanitized_title[:max_title_length]
            folder_path = os.path.join(base_dir, sanitized_title)
            self.logger.info(f"Using truncated path: {folder_path}")
        
        # Create the directory
        ensured, message = PathUtils.ensure_directory(folder_path)
        if not ensured:
            self.logger.error(f"Failed to create playlist directory: {message}")
            raise ValueError(f"Failed to create playlist directory: {message}")
            
        return folder_path
    
    def sanitize_filepath(self, filepath):
        """Override to use centralized PathUtils"""
        return PathUtils.sanitize_path(filepath)
    
    def get_playlist_info(self, playlist_id: str):
        """Override to include better error handling"""
        try:
            return super().get_playlist_info(playlist_id)
        except Exception as e:
            # Enhance error message with troubleshooting steps
            error_message = str(e)
            if "404" in error_message:
                raise ValueError(
                    f"Playlist not found: {playlist_id}. Please check if the playlist ID is correct "
                    f"and that the playlist is not private or has been deleted."
                )
            elif "Sign in to confirm" in error_message:
                raise ValueError(
                    f"YouTube requires authentication for this playlist. Please configure your "
                    f"cookie settings in the Settings tab."
                )
            else:
                # Re-raise with original error
                raise


def create_enhanced_application():
    """Create enhanced application with all improvements"""
    # Setup logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    
    # Log startup
    logger.info("Starting Enhanced YouTube Playlist Downloader")
    
    # Import original components
    from repositories import JsonHistoryRepository
    from env_config import EnvironmentConfigRepository
    from validators import YouTubeCookieValidator, FileNameSanitizer, QualityFormatter
    
    # Create repositories
    config_repository = EnvironmentConfigRepository()
    history_repository = JsonHistoryRepository()
    
    # Create validators and utilities
    cookie_validator = YouTubeCookieValidator()
    filename_sanitizer = FileNameSanitizer()
    quality_formatter = QualityFormatter()
    
    # Create enhanced downloader
    youtube_downloader = EnhancedYouTubePlaylistDownloader(
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
    
    # Create enhanced application
    app = EnhancedYouTubeDownloaderApp(
        download_presenter=download_presenter,
        history_presenter=history_presenter,
        settings_presenter=settings_presenter
    )
    
    # Override download tab to use enhanced version
    # We need to do this after app creation because YouTubeDownloaderApp 
    # creates its own tabs during initialization
    download_tab = EnhancedDownloadTab(app.notebook, download_presenter)
    app.notebook.forget(0)  # Remove the original tab
    app.notebook.insert(0, download_tab, text="Download")
    app.download_tab = download_tab
    
    return app


if __name__ == "__main__":
    app = create_enhanced_application()
    app.mainloop()