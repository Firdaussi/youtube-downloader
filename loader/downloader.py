# downloader.py - Core YouTube downloader implementation

import os
import time
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
from datetime import datetime

from models import (
    DownloadConfig, PlaylistInfo, DownloadProgress, 
    DownloadStatus, HistoryEntry
)
from interfaces import (
    PlaylistDownloader, ProgressListener, QualityFormatter,
    FileNameSanitizer, HistoryRepository
)
from validators import YouTubeCookieValidator, FileNameSanitizer as DefaultFileNameSanitizer


class YouTubePlaylistDownloader:
    """Core YouTube playlist downloader implementation"""
    
    def __init__(self, 
                 quality_formatter: QualityFormatter,
                 filename_sanitizer: FileNameSanitizer,
                 cookie_validator: YouTubeCookieValidator,
                 history_repository: HistoryRepository,
                 logger: logging.Logger):
        self.quality_formatter = quality_formatter
        self.filename_sanitizer = filename_sanitizer
        self.cookie_validator = cookie_validator
        self.history_repository = history_repository
        self.logger = logger
        self.pause_requested = False
        self.current_download: Optional[str] = None
    
    def download(self, playlist_id: str, config: DownloadConfig,
                progress_callback: Optional[ProgressListener] = None) -> None:
        """Download a playlist"""
        self.current_download = playlist_id
        attempts = 0
        
        while attempts < config.retry_count:
            if self.pause_requested:
                self._handle_pause(playlist_id, progress_callback)
            
            try:
                # Check for duplicates if enabled
                if config.check_duplicates:
                    existing = self.history_repository.find_by_playlist_id(playlist_id)
                    if existing:
                        self.logger.info(f"Skipping duplicate: {playlist_id}")
                        if progress_callback:
                            progress_callback.on_download_complete(playlist_id)
                        return
                
                # Get playlist info
                playlist_info = self.get_playlist_info(playlist_id)
                
                # Create download directory
                playlist_folder = self._create_playlist_folder(
                    config.download_directory, 
                    playlist_info.title
                )
                
                # Create marker file
                self._create_marker_file(playlist_folder, playlist_id)
                
                # Download playlist
                self._download_playlist(
                    playlist_info, 
                    playlist_folder, 
                    config, 
                    progress_callback
                )
                
                # Save to history
                history_entry = HistoryEntry(
                    playlist_id=playlist_id,
                    playlist_title=playlist_info.title,
                    status='completed',
                    timestamp=datetime.now(),
                    download_path=playlist_folder
                )
                self.history_repository.save_entry(history_entry)
                
                if progress_callback:
                    progress_callback.on_download_complete(playlist_id)
                
                return  # Success
                
            except Exception as e:
                attempts += 1
                error_msg = str(e)
                self.logger.error(f"Attempt {attempts} failed for {playlist_id}: {error_msg}")
                
                # Check for specific YouTube bot detection error
                if "Sign in to confirm you're not a bot" in error_msg:
                    special_error = (
                        "YouTube bot detection triggered. Please:\n"
                        "1. Go to Settings tab and set up cookie authentication\n"
                        "2. Either use a browser cookie method or export cookies.txt from your browser\n"
                        "3. Make sure you're logged in to YouTube in the browser you export cookies from\n"
                        "4. Save settings and try again"
                    )
                    if progress_callback:
                        progress_callback.on_progress(DownloadProgress(
                            playlist_id=playlist_id,
                            status=DownloadStatus.FAILED,
                            progress=0,
                            speed=0,
                            eta=0,
                            current_file="",
                            message=special_error
                        ))
                
                if attempts >= config.retry_count:
                    # Save failed entry to history
                    history_entry = HistoryEntry(
                        playlist_id=playlist_id,
                        playlist_title=getattr(playlist_info, 'title', playlist_id) if 'playlist_info' in locals() else playlist_id,
                        status='failed',
                        timestamp=datetime.now(),
                        download_path=config.download_directory
                    )
                    self.history_repository.save_entry(history_entry)
                    
                    if progress_callback:
                        progress_callback.on_download_error(playlist_id, str(e))
                    raise
                
                time.sleep(2)  # Wait before retry
    
    def get_playlist_info(self, playlist_id: str) -> PlaylistInfo:
        """Get playlist metadata"""
        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
        
        return PlaylistInfo(
            id=playlist_id,
            title=self.filename_sanitizer.sanitize(
                info.get('title', f'Playlist_{playlist_id}')
            ),
            url=playlist_url,
            total_tracks=len(info.get('entries', [])),
            entries=info.get('entries', [])
        )
    
    def pause(self) -> None:
        """Pause the download"""
        self.pause_requested = True
    
    def resume(self) -> None:
        """Resume the download"""
        self.pause_requested = False
    
    def _handle_pause(self, playlist_id: str, 
                     progress_callback: Optional[ProgressListener]) -> None:
        """Handle pause request"""
        self.logger.info(f"Download paused for {playlist_id}")
        while self.pause_requested:
            if progress_callback:
                progress = DownloadProgress(
                    playlist_id=playlist_id,
                    status=DownloadStatus.PAUSED,
                    progress=0,
                    speed=0,
                    eta=0,
                    current_file="",
                    message="Download paused"
                )
                progress_callback.on_progress(progress)
            time.sleep(0.5)
        self.logger.info(f"Resuming download for {playlist_id}")
    
    def _create_playlist_folder(self, base_dir: str, playlist_title: str) -> str:
        """Create folder for playlist"""
        folder_path = os.path.join(base_dir, playlist_title)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
    
    def _create_marker_file(self, folder: str, playlist_id: str) -> None:
        """Create marker file for playlist"""
        marker_path = os.path.join(folder, playlist_id)
        with open(marker_path, 'w') as f:
            pass
    
    def _download_playlist(self, playlist_info: PlaylistInfo, 
                          folder: str, config: DownloadConfig,
                          progress_callback: Optional[ProgressListener]) -> None:
        """Download the playlist"""
        if progress_callback:
            progress_callback.on_download_start(playlist_info.id)
        
        # Prepare download options
        ydl_opts = {
            'format': self.quality_formatter.get_format_string(
                config.default_quality.value
            ),
            'quiet': False,
            'noplaylist': False,
            'outtmpl': os.path.join(folder, '%(playlist_index)02d - %(title).200s.%(ext)s'),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        # Add progress hook
        if progress_callback:
            def progress_hook(d):
                self._handle_progress(d, playlist_info.id, progress_callback)
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # Add cookies if configured
        if config.cookie_method != 'none':
            self._add_cookie_config(ydl_opts, config)
        
        # Add bandwidth limit
        if config.bandwidth_limit != "0":
            ydl_opts['ratelimit'] = config.bandwidth_limit
        
        # Download
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([playlist_info.url])
    
    def _handle_progress(self, d: Dict[str, Any], playlist_id: str,
                        callback: ProgressListener) -> None:
        """Handle progress updates from yt-dlp"""
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            
            progress = 0
            if total_bytes > 0:
                progress = (downloaded_bytes / total_bytes) * 100
            
            filename = os.path.basename(d.get('filename', ''))
            
            progress_update = DownloadProgress(
                playlist_id=playlist_id,
                status=DownloadStatus.DOWNLOADING,
                progress=progress,
                speed=speed,
                eta=eta,
                current_file=filename,
                message=f"Downloading: {filename}"
            )
            callback.on_progress(progress_update)
        
        elif d['status'] == 'finished':
            filename = os.path.basename(d.get('filename', ''))
            progress_update = DownloadProgress(
                playlist_id=playlist_id,
                status=DownloadStatus.DOWNLOADING,
                progress=100,
                speed=0,
                eta=0,
                current_file=filename,
                message=f"Processing: {filename}"
            )
            callback.on_progress(progress_update)
    
    def _add_cookie_config(self, ydl_opts: Dict, config: DownloadConfig) -> None:
        """Add cookie configuration to yt-dlp options"""
        if config.cookie_method == 'file':
            if config.cookie_file and os.path.exists(config.cookie_file):
                # Use 'cookiefile' parameter for yt-dlp (this is critical)
                ydl_opts['cookies'] = config.cookie_file
                self.logger.info(f"Using cookie file: {config.cookie_file}")
            else:
                self.logger.warning(f"Cookie file not found or not set: {config.cookie_file}")
        elif config.cookie_method != 'none':
            # For browser cookies
            ydl_opts['cookiesfrombrowser'] = (config.cookie_method, None, None, None)
            self.logger.info(f"Using cookies from browser: {config.cookie_method}")
            
        # Add additional yt-dlp options that help with bot detection
        ydl_opts.update({
            'sleep_interval': 1,  # Sleep between requests to avoid rate limiting
            'max_sleep_interval': 5,
            'sleep_interval_requests': 3,  # Number of requests between sleeps
            'ignoreerrors': False,  # Don't ignore errors
            'geo_bypass': True,  # Try to bypass geo-restrictions
        })