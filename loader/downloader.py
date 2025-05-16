# downloader_fixed.py - Fixed downloader implementation

import os
import time
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
import re
from pathlib import Path
from datetime import datetime

from models import (
    DownloadConfig, PlaylistInfo, DownloadProgress, 
    DownloadStatus
)
from interfaces import (
    PlaylistDownloader, ProgressListener, QualityFormatter,
    FileNameSanitizer, HistoryRepository
)


class YouTubePlaylistDownloader:
    """Core YouTube playlist downloader implementation"""
    
    def __init__(self, 
                 quality_formatter,
                 filename_sanitizer,
                 cookie_validator,
                 history_repository,
                 logger):
        self.quality_formatter = quality_formatter
        self.filename_sanitizer = filename_sanitizer
        self.cookie_validator = cookie_validator
        self.history_repository = history_repository
        self.logger = logger
        self.pause_requested = False
        self.current_download = None
    
    @staticmethod
    def sanitize_filepath(filepath):
        """
        Thoroughly sanitize a file path to ensure it's valid across all platforms.
        - Replaces invalid characters
        - Handles path length limitations
        - Normalizes path separators
        """
        # Get directory and filename
        directory, filename = os.path.split(filepath)
        
        # Create Path object to normalize path separators
        directory_path = Path(directory)
        
        # Ensure directory exists
        os.makedirs(directory_path, exist_ok=True)
        
        # Replace invalid characters in filename with underscores
        # This is more thorough than most sanitization functions
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # Limit filename length (Windows has a 260 character path limitation)
        max_filename_length = 100  # Conservative limit
        if len(filename) > max_filename_length:
            base, ext = os.path.splitext(filename)
            truncated_base = base[:max_filename_length - len(ext) - 3]  # Leave room for "..." and extension
            filename = f"{truncated_base}...{ext}"
        
        # Recombine directory and sanitized filename
        sanitized_path = os.path.join(str(directory_path), filename)
        
        return sanitized_path
    
    def download(self, playlist_id: str, config: DownloadConfig,
                progress_callback: Optional[ProgressListener] = None) -> None:
        """Download a playlist"""
        self.current_download = playlist_id
        attempts = 0
        playlist_info = None
        
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
                
                # Save to history - use dict instead of HistoryEntry
                history_dict = {
                    'playlist_id': playlist_id,
                    'playlist_title': playlist_info.title,
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'download_path': playlist_folder
                }
                
                # Use history_repository directly with a dict
                try:
                    # Create dict-based history
                    self.history_repository.save_entry({
                        'playlist_id': playlist_id,
                        'playlist_title': playlist_info.title,
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat(),
                        'download_path': playlist_folder
                    })
                except Exception as e:
                    self.logger.error(f"Failed to save history: {e}")
                
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
                    # Save failed entry to history using dict
                    try:
                        self.history_repository.save_entry({
                            'playlist_id': playlist_id,
                            'playlist_title': getattr(playlist_info, 'title', playlist_id) if playlist_info else playlist_id,
                            'status': 'failed',
                            'timestamp': datetime.now().isoformat(),
                            'download_path': config.download_directory
                        })
                    except Exception as history_err:
                        self.logger.error(f"Failed to save history: {history_err}")
                    
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
        
        # Get the raw title from info
        raw_title = info.get('title', f'Playlist_{playlist_id}')
        
        # Only sanitize the title, not any path components
        sanitized_title = self.filename_sanitizer._sanitize_filename_component(raw_title)
        
        return PlaylistInfo(
            id=playlist_id,
            title=sanitized_title,
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
        # Do NOT sanitize the base_dir as it's a path
        # Only sanitize the playlist_title which is a folder name
        sanitized_title = self.filename_sanitizer._sanitize_filename_component(playlist_title)
        folder_path = os.path.join(base_dir, sanitized_title)
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
        
        # Ensure folder exists and all parent directories
        os.makedirs(folder, exist_ok=True)
        
        output_template = os.path.join(folder, config.output_template)

        # Verify template contains the folder path - Add this debugging check
        if folder not in output_template:
            self.logger.error(f"CRITICAL ERROR: Folder path missing from output template!")
            self.logger.error(f"Folder: {folder}")
            self.logger.error(f"Template: {output_template}")
            # Even attempt to fix it directly
            output_template = os.path.normpath(folder + '/' + '%(playlist_index)02d-%(title)s.%(ext)s')
            self.logger.info(f"Attempting to fix template: {output_template}")

        # Log what we're doing
        self.logger.info(f"Using output template: {output_template}")
        
        # Prepare download options with minimal settings
        ydl_opts = {
            'format': self.quality_formatter.get_format_string(
                config.default_quality.value
            ),
            'quiet': False,
            'noplaylist': False,
            'outtmpl': output_template,
            #'restrictfilenames': True,  # This is important to avoid invalid characters
        }

        # Add postprocessing if enabled
        if config.use_postprocessing:
            ydl_opts['merge_output_format'] = config.preferred_format
        
        # Add progress hook
        if progress_callback:
            def progress_hook(d):
                try:
                    status = d.get('status', '')
                    filename = d.get('filename', 'unknown file')
                    
                    # Create a safe version of current_file for display
                    current_file = os.path.basename(filename) if filename else 'unknown'
                    
                    if status == 'downloading':
                        # Safely calculate progress
                        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0) 
                        downloaded_bytes = d.get('downloaded_bytes', 0)
                        progress = (downloaded_bytes / total_bytes) * 100 if total_bytes else 0
                        
                        self._handle_progress(d, playlist_info.id, progress_callback)
                        
                    elif status == 'finished':
                        progress_update = DownloadProgress(
                            playlist_id=playlist_info.id,
                            status=DownloadStatus.DOWNLOADING,
                            progress=100,
                            speed=0,
                            eta=0,
                            current_file=current_file,
                            message=f"Processing: {current_file}"
                        )
                        progress_callback.on_progress(progress_update)
                        
                    elif status == 'error':
                        error_msg = d.get('error', 'Unknown error')
                        progress_update = DownloadProgress(
                            playlist_id=playlist_info.id,
                            status=DownloadStatus.FAILED,
                            progress=0,
                            speed=0,
                            eta=0,
                            current_file="",
                            message=f"Error: {error_msg}"
                        )
                        progress_callback.on_progress(progress_update)
                        
                except Exception as hook_error:
                    self.logger.error(f"Error in progress hook: {hook_error}")
                    # Don't crash on hook errors
                    
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # Add cookies if configured
        if config.cookie_method != 'none':
            self._add_cookie_config(ydl_opts, config)
        
        # For debugging
        self.logger.info(f"Download options: {ydl_opts}")
        
        # Download
        with YoutubeDL(ydl_opts) as ydl:
            try:
                # First try to extract info only to verify URL works
                try:
                    self.logger.info(f"Extracting playlist info for {playlist_info.url}")
                    ydl.extract_info(playlist_info.url, download=False)
                except Exception as info_error:
                    self.logger.error(f"Info extraction error: {info_error}")
                    # Continue anyway - sometimes the info extraction fails but download works
                
                # Proceed with download
                result = ydl.download([playlist_info.url])
                self.logger.info(f"Download result: {result}")
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Download error: {error_msg}")
                
                # Try to provide more helpful error information
                if "'filepath'" in error_msg:
                    self.logger.error(f"This is a filepath error '{config.download_directory}'. Check folder permissions and path length.")
                    self.logger.error(f"Error Message: {error_msg}")
                    self.logger.error(f"Attempted to use template: {config.output_template}")
                    # Try to get the current filename being processed if available
                    current_filename = "unknown"
                    if 'progress_hooks' in ydl_opts and ydl_opts['progress_hooks']:
                        # This is a best-effort attempt to get the current filename
                        # It may not always work depending on when the error occurred
                        hook_data = getattr(ydl_opts['progress_hooks'][0], 'last_data', {})
                        current_filename = hook_data.get('filename', 'unknown')
                    self.logger.error(f"Current file being downloaded: {current_filename}")
                    
                    # Try to test write permissions
                    try:
                        test_path = os.path.join(folder, "write_test.txt")
                        with open(test_path, 'w') as f:
                            f.write("test")
                        os.remove(test_path)
                        self.logger.info("Write permission test: PASSED")
                    except Exception as perm_e:
                        self.logger.error(f"Write permission error: {perm_e}")
                        
                    # Test with different file extensions
                    for ext in ['.mp4', '.webm', '.mkv']:
                        try:
                            test_video_path = os.path.join(folder, f"test_video{ext}")
                            with open(test_video_path, 'wb') as f:
                                f.write(b'test')
                            self.logger.info(f"Test file created successfully with extension: {ext}")
                            os.remove(test_video_path)
                        except Exception as test_e:
                            self.logger.error(f"Failed to create test file with extension {ext}: {test_e}")
                            
                    # Test path components
                    path_components = folder.split(os.path.sep)
                    for i in range(1, len(path_components) + 1):
                        test_path = os.path.sep.join(path_components[:i])
                        if test_path:  # Skip empty path components
                            try:
                                if os.path.exists(test_path):
                                    access_read = os.access(test_path, os.R_OK)
                                    access_write = os.access(test_path, os.W_OK)
                                    access_exec = os.access(test_path, os.X_OK)
                                    self.logger.info(f"Path component {test_path}: exists={True}, read={access_read}, write={access_write}, execute={access_exec}")
                                else:
                                    self.logger.error(f"Path component does not exist: {test_path}")
                            except Exception as path_e:
                                self.logger.error(f"Error checking path component {test_path}: {path_e}")
                
                raise

    def _handle_progress(self, d: Dict[str, Any], playlist_id: str,
                        callback: ProgressListener) -> None:
        """Handle progress updates from yt-dlp with improved error handling"""
        try:
            if d['status'] == 'downloading':
                # Safe retrieval of values with fallbacks
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded_bytes = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                
                progress = 0
                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                
                # Safely get filename
                filename = "unknown.mp4"
                if 'filename' in d:
                    try:
                        filename = os.path.basename(d.get('filename', ''))
                    except:
                        pass
                
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
                # Safely get filename
                filename = "unknown.mp4"
                if 'filename' in d:
                    try:
                        filename = os.path.basename(d.get('filename', ''))
                    except:
                        pass
                    
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
                
            # Handle error status
            elif d['status'] == 'error':
                error_msg = d.get('error', 'Unknown error')
                self.logger.error(f"Download error in progress hook: {error_msg}")
                
                progress_update = DownloadProgress(
                    playlist_id=playlist_id,
                    status=DownloadStatus.FAILED,
                    progress=0,
                    speed=0,
                    eta=0,
                    current_file="",
                    message=f"Error: {error_msg}"
                )
                callback.on_progress(progress_update)
        
        except Exception as e:
            # Log the error but don't crash
            self.logger.error(f"Error in progress handler: {e}")
            # Try to notify about the error
            try:
                callback.on_progress(DownloadProgress(
                    playlist_id=playlist_id,
                    status=DownloadStatus.DOWNLOADING,
                    progress=0,
                    speed=0,
                    eta=0,
                    current_file="",
                    message=f"Progress update error: {str(e)}"
                ))
            except:
                pass  # If even the error notification fails, just continue
    
    def _add_cookie_config(self, ydl_opts: Dict, config: DownloadConfig) -> None:
        """Add cookie configuration to yt-dlp options"""
        if config.cookie_method == 'file':
            if config.cookie_file and os.path.exists(config.cookie_file):
                # Use 'cookiefile' parameter - this is correct for the Python API!
                ydl_opts['cookiefile'] = config.cookie_file
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