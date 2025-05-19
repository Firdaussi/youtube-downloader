# presenters.py - Presenter layer for handling UI interactions

import logging
from typing import List, Optional, Callable

from src.data.models import DownloadConfig, DownloadProgress, HistoryEntry
from src.core.interfaces import (
    ConfigurationRepository, HistoryRepository, ProgressListener
)
from src.core.download_service import DownloadService
from src.utils.logging_utils import get_logger

class DownloadPresenter(ProgressListener):
    """Presenter for download tab functionality"""
    
    def __init__(self,
                 download_service: DownloadService,
                 config_repository: ConfigurationRepository,
                 history_repository: HistoryRepository,
                 logger: Optional[logging.Logger] = None):
        # Use provided logger or get one based on module name
        self.logger = logger or get_logger(f"{__name__}.DownloadPresenter")
        
        self.download_service = download_service
        self.config_repository = config_repository
        self.history_repository = history_repository
        
        # UI callbacks
        self.on_progress_callback: Optional[Callable[[DownloadProgress], None]] = None
        self.on_status_change_callback: Optional[Callable[[str], None]] = None
        self.on_playlist_complete_callback: Optional[Callable[[str], None]] = None
        self.on_playlist_failed_callback: Optional[Callable[[str, str], None]] = None
        self.on_all_complete_callback: Optional[Callable[[], None]] = None
    
    def load_config(self) -> DownloadConfig:
        """Load configuration"""
        return self.config_repository.load_config()
    
    def save_config(self, config: DownloadConfig) -> None:
        """Save configuration"""
        self.config_repository.save_config(config)
    
    def start_downloads(self, playlist_ids: List[str]) -> bool:
        """Start downloading playlists"""
        if not playlist_ids:
            self._update_status("No playlist IDs provided")
            return False
        
        config = self.load_config()
        self._update_status("Starting downloads...")
        
        success = self.download_service.start_downloads(
            playlist_ids, config, self
        )
        
        if not success:
            self._update_status("Failed to start downloads. Check your settings.")
            return False
        
        return True
    
    def pause_downloads(self) -> None:
        """Pause downloads"""
        self.download_service.pause_downloads()
        self._update_status("Downloads paused")
    
    def resume_downloads(self) -> None:
        """Resume downloads"""
        self.download_service.resume_downloads()
        self._update_status("Downloads resumed")
    
    def stop_downloads(self) -> None:
        """Stop downloads"""
        self.download_service.stop_downloads()
        self._update_status("Downloads cancelled")
        
        # Manually trigger UI reset since we're not going through the normal completion flow
        if self.on_all_complete_callback:
            self.on_all_complete_callback()
    
    def get_queue_status(self):
        """Get current queue status"""
        return self.download_service.get_queue_status()
    
    # ProgressListener implementation
    def on_progress(self, progress: DownloadProgress) -> None:
        """Handle progress updates"""
        if self.on_progress_callback:
            self.on_progress_callback(progress)
    
    def on_download_start(self, playlist_id: str) -> None:
        """Handle download start"""
        self._update_status(f"Starting download: {playlist_id}")
    
    def on_download_complete(self, playlist_id: str) -> None:
        """Handle download completion"""
        if self.on_playlist_complete_callback:
            self.on_playlist_complete_callback(playlist_id)
        self._update_status(f"Completed: {playlist_id}")
    
    def on_download_error(self, playlist_id: str, error: str) -> None:
        """Handle download error"""
        if self.on_playlist_failed_callback:
            self.on_playlist_failed_callback(playlist_id, error)
        self._update_status(f"Failed: {playlist_id} - {error}")
    
    def _update_status(self, message: str) -> None:
        """Update status message"""
        self.logger.info(message)
        if self.on_status_change_callback:
            self.on_status_change_callback(message)

    def on_all_downloads_complete(self) -> None:
        """Handle all downloads completion"""
        self._update_status("All downloads completed")
        if self.on_all_complete_callback:
            self.on_all_complete_callback()


class HistoryPresenter:
    """Presenter for history tab functionality"""
    
    def __init__(self, history_repository: HistoryRepository):
        self.history_repository = history_repository
        self.logger = get_logger(f"{__name__}.HistoryPresenter")
    
    def get_history(self) -> List[HistoryEntry]:
        """Get download history"""
        try:
            return self.history_repository.load_history()
        except Exception as e:
            self.logger.error(f"Error loading history: {e}")
            return []
    
    def clear_history(self) -> None:
        """Clear download history"""
        try:
            self.history_repository.clear_history()
            self.logger.info("Download history cleared")
        except Exception as e:
            self.logger.error(f"Error clearing history: {e}")
    
    def format_history_entry(self, entry: HistoryEntry) -> tuple:
        """Format history entry for display"""
        return (
            entry.playlist_id,
            entry.playlist_title,
            entry.status,
            entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            entry.download_path
        )


class SettingsPresenter:
    """Presenter for settings tab functionality"""
    
    def __init__(self, 
                 config_repository: ConfigurationRepository,
                 cookie_validator):
        self.config_repository = config_repository
        self.cookie_validator = cookie_validator
        self.logger = get_logger(f"{__name__}.SettingsPresenter")
    
    def load_config(self) -> DownloadConfig:
        """Load configuration"""
        try:
            return self.config_repository.load_config()
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return DownloadConfig()
    
    def save_config(self, config: DownloadConfig) -> bool:
        """Save configuration"""
        # Validate cookies before saving
        if not self.cookie_validator.validate(config.cookie_method, config.cookie_file):
            self.logger.warning("Cookie validation failed")
            return False
        
        try:
            self.config_repository.save_config(config)
            self.logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def validate_cookies(self, method: str, file_path: Optional[str]) -> tuple[bool, List[str]]:
        """Validate cookie settings"""
        is_valid = self.cookie_validator.validate(method, file_path)
        errors = self.cookie_validator.get_validation_errors()
        
        if not is_valid:
            self.logger.warning(f"Cookie validation failed: {', '.join(errors)}")
        
        return is_valid, errors