# downloader.py - Optimized downloader implementation

import os
import time
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
import re
from pathlib import Path
from datetime import datetime
import json
import csv

from src.data.models import (
    DownloadConfig, PlaylistInfo, DownloadProgress, 
    DownloadStatus
)
from src.core.interfaces import ProgressListener


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
        
        # For progress throttling
        self._last_progress_time = 0
    
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
        
        # Check if this is quick mode
        quick_mode = getattr(config, 'quick_mode', False)
        
        while attempts < config.retry_count:
            if self.pause_requested:
                self._handle_pause(playlist_id, progress_callback)
            
            # Check for cancellation
            if hasattr(self, '_force_cancel') and self._force_cancel:
                self.logger.info(f"Download cancelled: {playlist_id}")
                if progress_callback:
                    progress_callback.on_progress(DownloadProgress(
                        playlist_id=playlist_id,
                        status=DownloadStatus.FAILED,
                        progress=0,
                        speed=0,
                        eta=0,
                        current_file="",
                        message="Download cancelled"
                    ))
                return  # Exit early without raising exception

            try:
                # Check for duplicates if enabled and not in quick mode
                if config.check_duplicates and not quick_mode:
                    # Use is_duplicate method if available
                    if hasattr(self.history_repository, 'is_duplicate'):
                        is_duplicate = self.history_repository.is_duplicate(playlist_id)
                    else:
                        # Fall back to old method
                        existing = self.history_repository.find_by_playlist_id(playlist_id)
                        is_duplicate = existing is not None
                        
                    if is_duplicate:
                        self.logger.info(f"Skipping duplicate: {playlist_id}")
                        if progress_callback:
                            progress_callback.on_download_complete(playlist_id)
                        return
                
                # Get playlist info - use minimal mode if configured or in quick mode
                skip_metadata = getattr(config, 'skip_metadata', False) or quick_mode
                playlist_info = self.get_playlist_info(playlist_id, minimal=skip_metadata)
                
                # Create download directory
                playlist_folder = self._create_playlist_folder(
                    config.download_directory, 
                    playlist_info.title
                )
                
                # Create marker file (only in normal mode)
                if not quick_mode:
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


    def download_quick(self, playlist_id: str, config: DownloadConfig,
                    progress_callback: Optional[ProgressListener] = None) -> None:
        """Optimized download method that still gets playlist title and artist info"""
        self.current_download = playlist_id
        
        try:
            # Skip duplicate checking, but we'll still fetch info for the title and metadata
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            
            # Notify listener about download start
            if progress_callback:
                progress_callback.on_download_start(playlist_id)
                progress_callback.on_progress(DownloadProgress(
                    playlist_id=playlist_id,
                    status=DownloadStatus.DOWNLOADING,
                    progress=0,
                    speed=0,
                    eta=0,
                    current_file="",
                    message=f"Starting quick download for {playlist_id} (getting info)"
                ))
            
            # Get minimal playlist info - enough to get the title and basic metadata
            ydl_opts = {
                'quiet': True,
                'extract_flat': 'in_playlist',  # We need entry info for metadata
                'skip_download': True,
                'playlist_items': '0:10',  # Get info for first 10 videos at most for speed
            }
            
            playlist_title = f"Playlist_{playlist_id}"  # Default fallback title
            playlist_entries = []  # Default empty entries list
            
            try:
                # Quick extraction for title and first few entries
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(playlist_url, download=False)
                    if info:
                        if 'title' in info:
                            raw_title = info.get('title')
                            # Sanitize the title
                            playlist_title = self.filename_sanitizer._sanitize_filename_component(raw_title)
                            self.logger.debug(f"Got playlist title: {playlist_title}")
                        
                        # Get entries for metadata
                        if 'entries' in info:
                            playlist_entries = info.get('entries', [])
            except Exception as e:
                # If title extraction fails, just use the ID
                self.logger.warning(f"Couldn't get playlist info, using ID: {e}")
            
            # Create download directory with the title we got
            download_folder = os.path.join(config.download_directory, playlist_title)
            os.makedirs(download_folder, exist_ok=True)
            
            # Create a playlist info object with what we have
            playlist_info = PlaylistInfo(
                id=playlist_id,
                title=playlist_title,
                url=playlist_url,
                total_tracks=len(playlist_entries),
                entries=playlist_entries
            )
            
            # Generate metadata files
            self._generate_playlist_metadata_file(playlist_info, download_folder, config)
            
            # Download directly with optimized options
            self._download_playlist_quick(playlist_info, download_folder, config, progress_callback)
            
            # Save to history in the background
            try:
                self.history_repository.save_entry({
                    'playlist_id': playlist_id,
                    'playlist_title': playlist_title,
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat(),
                    'download_path': download_folder
                })
            except Exception as e:
                self.logger.error(f"Failed to save history: {e}")
            
            if progress_callback:
                progress_callback.on_download_complete(playlist_id)
                
        except Exception as e:
            if progress_callback:
                progress_callback.on_download_error(playlist_id, str(e))
            raise
    
    def force_stop(self) -> None:
        """Forcefully stop any active downloads"""
        self.logger.info("Force stopping any active yt-dlp processes")
        
        # Set a flag to track cancellation
        self._force_cancel = True
        
        # Try to terminate any active subprocess
        # yt-dlp usually spawns ffmpeg or other processes that need to be killed
        try:
            import psutil
            import os
            import signal
            
            # Get our process and its children
            current_process = psutil.Process(os.getpid())
            
            # Look for yt-dlp or ffmpeg processes among the children
            for child in current_process.children(recursive=True):
                try:
                    child_name = child.name().lower()
                    if 'yt-dlp' in child_name or 'ffmpeg' in child_name or 'youtube-dl' in child_name:
                        self.logger.info(f"Terminating child process: {child.pid} ({child_name})")
                        child.terminate()
                except:
                    pass
        except Exception as e:
            self.logger.error(f"Error trying to terminate processes: {e}")
        
        # If the current download is active, we need to handle that
        if self.current_download:
            self.logger.info(f"Marking current download as cancelled: {self.current_download}")
            self.current_download = None
        
    def get_playlist_info(self, playlist_id: str, minimal: bool = False) -> PlaylistInfo:
        """Get playlist metadata with lazy fetching option"""
        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        
        if minimal:
            # For quick downloads, don't fetch full metadata
            return PlaylistInfo(
                id=playlist_id,
                title=f"Playlist_{playlist_id}",  # Use placeholder title
                url=playlist_url,
                total_tracks=0,  # Unknown without fetching
                entries=[]  # No entries for minimal info
            )
        
        # Original implementation for standard downloads
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
    
    def _generate_playlist_metadata_file(self, playlist_info: PlaylistInfo, folder_path: str, config: DownloadConfig) -> None:
        """Generate a metadata file with playlist details and artist information"""
        self.logger.info(f"Generating metadata file for playlist: {playlist_info.title}")
        
        try:
            # Get more detailed information if not already available
            detailed_info = playlist_info

            # print(detailed_info)
            
            # If entries are empty or minimal, try to get more info
            if not detailed_info.entries or len(detailed_info.entries) == 0:
                try:
                    # Try to get more detailed info but don't fail the whole download if it doesn't work
                    ydl_opts = {
                        'quiet': True,
                        'extract_flat': 'in_playlist',
                        'skip_download': True,
                    }
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(detailed_info.url, download=False)
                        if info and 'entries' in info:
                            detailed_info.entries = info.get('entries', [])
                            # Update total tracks count
                            detailed_info.total_tracks = len(detailed_info.entries)
                except Exception as e:
                    self.logger.warning(f"Could not get detailed playlist info for metadata: {e}")
            
            # Prepare metadata
            metadata = {
                "playlist_id": detailed_info.id,
                "playlist_title": detailed_info.title,
                "playlist_url": detailed_info.url,
                "total_tracks": detailed_info.total_tracks,
                "extraction_date": datetime.now().isoformat(),
                "videos": []
            }
            
            # Channel/uploader information (extracted from first video if available)
            channel_info = {}
            
            # Process entries for artist/uploader info and video details
            for i, entry in enumerate(detailed_info.entries):
                video_info = {
                    "position": i + 1,
                    "title": entry.get('title', 'Unknown Title'),
                    "id": entry.get('id', 'Unknown ID'),
                    "url": f"https://www.youtube.com/watch?v={entry.get('id')}" 
                        if entry.get('id') else 'Unknown URL'
                }
                
                # Extract uploader/channel info
                if 'channel' in entry:
                    video_info['channel'] = entry.get('channel', 'Unknown Channel')
                if 'uploader' in entry:
                    video_info['uploader'] = entry.get('uploader', 'Unknown Uploader')
                if 'uploader_id' in entry:
                    video_info['uploader_id'] = entry.get('uploader_id', 'Unknown Uploader ID')
                if 'channel_id' in entry:
                    video_info['channel_id'] = entry.get('channel_id', 'Unknown Channel ID')
                if 'channel_url' in entry:
                    video_info['channel_url'] = entry.get('channel_url', '')
                
                # Get duration if available
                if 'duration' in entry:
                    duration = entry.get('duration')
                    if duration:
                        minutes, seconds = divmod(int(duration), 60)
                        hours, minutes = divmod(minutes, 60)
                        if hours > 0:
                            video_info['duration'] = f"{hours}:{minutes:02d}:{seconds:02d}"
                        else:
                            video_info['duration'] = f"{minutes}:{seconds:02d}"
                
                # Add to videos list
                metadata['videos'].append(video_info)
                
                # Capture channel info from first video if not already set
                if not channel_info and i == 0:
                    channel_info = {
                        'channel': video_info.get('channel', 'Unknown Channel'),
                        'uploader': video_info.get('uploader', 'Unknown Uploader'),
                        'channel_id': video_info.get('channel_id', ''),
                        'channel_url': video_info.get('channel_url', '')
                    }
            
            # Add channel info to main metadata
            metadata.update(channel_info)
            
            # Generate JSON metadata file
            json_path = os.path.join(folder_path, "playlist_metadata.json")
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(metadata, json_file, indent=2, ensure_ascii=False)
            
            # Generate CSV file for easy importing into other tools
            csv_path = os.path.join(folder_path, "playlist_tracks.csv")
            with open(csv_path, 'w', encoding='utf-8', newline='') as csv_file:
                # Define CSV columns
                fieldnames = ['position', 'title', 'id', 'url', 'channel', 'uploader', 'duration']
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                
                writer.writeheader()
                for video in metadata['videos']:
                    # Create a row with only the fields we want in the CSV
                    row = {field: video.get(field, '') for field in fieldnames if field in video}
                    writer.writerow(row)
            
            # Create a simple README text file with basic info
            readme_path = os.path.join(folder_path, "README.txt")
            with open(readme_path, 'w', encoding='utf-8') as readme_file:
                readme_file.write(f"Playlist: {detailed_info.title}\n")
                readme_file.write(f"URL: {detailed_info.url}\n")
                if 'channel' in channel_info:
                    readme_file.write(f"Channel: {channel_info['channel']}\n")
                if 'uploader' in channel_info:
                    readme_file.write(f"Uploader: {channel_info['uploader']}\n")
                if 'channel_url' in channel_info and channel_info['channel_url']:
                    readme_file.write(f"Channel URL: {channel_info['channel_url']}\n")
                readme_file.write(f"Total Tracks: {detailed_info.total_tracks}\n")
                readme_file.write(f"Downloaded on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                readme_file.write("This folder contains:\n")
                readme_file.write("- Video files downloaded from the playlist\n")
                readme_file.write("- playlist_metadata.json: Complete playlist metadata in JSON format\n")
                readme_file.write("- playlist_tracks.csv: Track listing in CSV format for importing\n")
            
            self.logger.info(f"Created metadata files in {folder_path}")
            
        except Exception as e:
            # Don't fail the download if metadata generation fails
            self.logger.error(f"Error generating metadata files: {e}")
        
    def _download_playlist(self, playlist_info: PlaylistInfo, 
                        folder: str, config: DownloadConfig,
                        progress_callback: Optional[ProgressListener] = None) -> None:
        """Download the playlist with optimized options and generate metadata"""
        if progress_callback:
            progress_callback.on_download_start(playlist_info.id)
        
        # Ensure folder exists and all parent directories
        os.makedirs(folder, exist_ok=True)
        
        # Generate metadata file before starting download
        self._generate_playlist_metadata_file(playlist_info, folder, config)
        
        output_template = os.path.join(folder, config.output_template)

        # Verify template contains the folder path
        if folder not in output_template:
            self.logger.error(f"CRITICAL ERROR: Folder path missing from output template!")
            self.logger.error(f"Folder: {folder}")
            self.logger.error(f"Template: {output_template}")
            # Fix template directly
            output_template = os.path.normpath(folder + '/' + '%(playlist_index)02d-%(title)s.%(ext)s')
            self.logger.info(f"Attempting to fix template: {output_template}")

        # Log what we're doing
        self.logger.info(f"Using output template: {output_template}")
        
        # Prepare download options with improved settings
        ydl_opts = {
            'format': self.quality_formatter.get_format_string(
                config.default_quality.value
            ),
            'quiet': False,
            'noplaylist': False,
            'outtmpl': output_template,
            # Add more efficient options:
            'merge_output_format': config.preferred_format,
            'sleep_interval': 1,  # Sleep between requests to avoid rate limiting
            'max_sleep_interval': 5,
            'sleep_interval_requests': 3,
            'ignoreerrors': config.auto_retry_failed,  # Skip errors if auto retry is enabled
            'geo_bypass': True  # Try to bypass geo-restrictions
        }
        
        # Add postprocessing if enabled
        if config.use_postprocessing:
            ydl_opts['merge_output_format'] = config.preferred_format
        
        # Add progress hook with throttling
        if progress_callback:
            def progress_hook(d):
                # Check for cancellation
                if hasattr(self, '_force_cancel') and self._force_cancel:
                    self.logger.debug("Progress hook detected cancellation")
                    raise Exception("Download cancelled by user")
                
                # Use throttling to reduce UI updates
                current_time = time.time()
                
                # Only update UI every 0.5 seconds (or when status changes)
                if (hasattr(self, '_last_progress_time') and 
                    current_time - self._last_progress_time < 0.5 and
                    d.get('status') == 'downloading'):
                    return
                
                # Update last progress time
                self._last_progress_time = current_time
                
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
                # For quick mode, skip info extraction
                if getattr(config, 'quick_mode', False) or getattr(config, 'skip_metadata', False):
                    # Go directly to download
                    result = ydl.download([playlist_info.url])
                else:
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
                raise

    def _download_playlist_quick(self, playlist_info: PlaylistInfo,
                              folder: str, config: DownloadConfig,
                              progress_callback: Optional[ProgressListener]) -> None:
        """Optimized download implementation with minimal overhead"""
        if progress_callback:
            progress_callback.on_download_start(playlist_info.id)
        
        # Ensure folder exists
        os.makedirs(folder, exist_ok=True)
        
        output_template = os.path.join(folder, config.output_template)
        
        # Prepare download options with minimal settings
        ydl_opts = {
            'format': self.quality_formatter.get_format_string(
                config.default_quality.value
            ),
            'quiet': False,
            'noplaylist': False,
            'outtmpl': output_template,
            'ignoreerrors': True,  # Skip errors for quicker processing
            'merge_output_format': config.preferred_format,
            'nocheckcertificate': True,  # Skip certificate validation
            'geo_bypass': True,  # Try to bypass geo-restrictions
            'sleep_interval': 0  # No sleep between requests
        }

        # Add progress hook with throttling
        if progress_callback:
            def progress_hook(d):
                # Use throttling logic here (only update UI every 0.5 seconds)
                current_time = time.time()
                
                # Only update every 0.5 seconds for downloading status
                if (hasattr(self, '_last_progress_time') and 
                    current_time - self._last_progress_time < 0.5 and
                    d.get('status') == 'downloading'):
                    return
                
                # Update last progress time
                self._last_progress_time = current_time
                
                try:
                    status = d.get('status', '')
                    filename = d.get('filename', 'unknown file')
                    current_file = os.path.basename(filename) if filename else 'unknown'
                    
                    if status == 'downloading':
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
                except Exception as hook_error:
                    self.logger.error(f"Error in progress hook: {hook_error}")
                    
            ydl_opts['progress_hooks'] = [progress_hook]
        
        # Add cookies if configured, with minimal validation
        if config.cookie_method != 'none' and config.cookie_method == 'file':
            if config.cookie_file and os.path.exists(config.cookie_file):
                ydl_opts['cookiefile'] = config.cookie_file
        elif config.cookie_method != 'none':
            # For browser cookies
            ydl_opts['cookiesfrombrowser'] = (config.cookie_method, None, None, None)
        
        # Download
        with YoutubeDL(ydl_opts) as ydl:
            try:
                # Go directly to download, skip extraction step
                result = ydl.download([playlist_info.url])
                self.logger.info(f"Quick download result: {result}")
            except Exception as e:
                self.logger.error(f"Download error: {e}")
                raise
    
    def _handle_progress(self, d: Dict[str, Any], playlist_id: str,
                        callback: ProgressListener) -> None:
        """Handle progress updates from yt-dlp with throttling"""
        # Current time for throttling
        current_time = time.time()
        
        # Only update UI every 0.5 seconds unless status changes
        if hasattr(self, '_last_progress_time') and current_time - self._last_progress_time < 0.5:
            # If status is 'finished', always update regardless of time
            if d.get('status') != 'finished':
                return
        
        # Update last progress time
        self._last_progress_time = current_time
        
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