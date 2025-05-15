# interfaces.py - Abstract interfaces using Python's Protocol

from typing import Protocol, List, Optional, Dict, Any
from models import DownloadConfig, HistoryEntry, DownloadProgress, PlaylistInfo


class ConfigurationRepository(Protocol):
    """Interface for configuration storage"""
    
    def load_config(self) -> DownloadConfig:
        """Load configuration from storage"""
        ...
    
    def save_config(self, config: DownloadConfig) -> None:
        """Save configuration to storage"""
        ...


class HistoryRepository(Protocol):
    """Interface for download history storage"""
    
    def save_entry(self, entry: HistoryEntry) -> None:
        """Save a history entry"""
        ...
    
    def load_history(self) -> List[HistoryEntry]:
        """Load all history entries"""
        ...
    
    def clear_history(self) -> None:
        """Clear all history"""
        ...
        
    def find_by_playlist_id(self, playlist_id: str) -> Optional[HistoryEntry]:
        """Find a history entry by playlist ID"""
        ...


class CookieValidator(Protocol):
    """Interface for cookie validation"""
    
    def validate(self, method: str, file_path: Optional[str] = None) -> bool:
        """Validate cookies based on method and optional file path"""
        ...
    
    def get_validation_errors(self) -> List[str]:
        """Get validation error messages"""
        ...


class PlaylistDownloader(Protocol):
    """Interface for playlist downloading"""
    
    def download(self, playlist_id: str, config: DownloadConfig, 
                progress_callback: Optional['ProgressListener'] = None) -> None:
        """Download a playlist"""
        ...
    
    def get_playlist_info(self, playlist_id: str) -> PlaylistInfo:
        """Get playlist metadata"""
        ...
        
    def pause(self) -> None:
        """Pause the download"""
        ...
        
    def resume(self) -> None:
        """Resume the download"""
        ...


class ProgressListener(Protocol):
    """Interface for progress updates"""
    
    def on_progress(self, progress: DownloadProgress) -> None:
        """Called when download progress updates"""
        ...
    
    def on_download_start(self, playlist_id: str) -> None:
        """Called when a download starts"""
        ...
    
    def on_download_complete(self, playlist_id: str) -> None:
        """Called when a download completes"""
        ...
    
    def on_download_error(self, playlist_id: str, error: str) -> None:
        """Called when a download encounters an error"""
        ...


class QualityFormatter(Protocol):
    """Interface for format string generation"""
    
    def get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for given quality"""
        ...


class FileNameSanitizer(Protocol):
    """Interface for filename sanitization"""
    
    def sanitize(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        ...