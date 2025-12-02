import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Optional, Dict
from datetime import datetime

from src.data.models import DownloadConfig
from src.core.interfaces import (
    PlaylistDownloader, HistoryRepository, 
    ProgressListener, CookieValidator
)
from src.core.queue_manager import DownloadQueue
from src.utils.logging_utils import get_logger

# Get module-specific logger
logger = get_logger(__name__)

class DownloadService:
    """Service that orchestrates playlist downloads"""
    
    def __init__(self,
                 downloader: PlaylistDownloader,
                 history_repository: HistoryRepository,
                 cookie_validator: CookieValidator,
                 logger: Optional[logging.Logger] = None):
        self.downloader = downloader
        self.history_repository = history_repository
        self.cookie_validator = cookie_validator
        # Use provided logger or get a class-specific one
        self.logger = logger or get_logger(f"{__name__}.DownloadService")
        self.download_queue = DownloadQueue()
        self.active_downloads: Dict[str, Future] = {}
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_downloading = False
        self._processor_running = False
        
        self.logger.debug("Download service initialized")
    
    def start_downloads(self, 
                       playlist_ids: List[str], 
                       config: DownloadConfig,
                       progress_listener: Optional[ProgressListener] = None,
                       quick_mode: bool = False) -> bool:
        """Start downloading playlists with optional quick mode"""
        
        # If downloads are already running, just add to the queue
        if self.is_downloading:
            self.logger.info(f"Downloads already running, adding {len(playlist_ids)} playlist(s) to queue")
            for playlist_id in playlist_ids:
                self.download_queue.add_playlist(playlist_id)
                self.logger.debug(f"Added playlist to existing queue: {playlist_id}")
            return True
        
        # Skip cookie validation in quick mode or if explicitly configured
        if not quick_mode and not getattr(config, 'skip_validation', False):
            # Validate cookies with normal validation
            if not self.cookie_validator.validate(config.cookie_method, config.cookie_file):
                errors = self.cookie_validator.get_validation_errors()
                self.logger.error(f"Cookie validation failed: {errors}")
                return False
        else:
            # Minimal cookie validation for quick mode
            if config.cookie_method == 'file' and config.cookie_file:
                if not self.cookie_validator.validate(
                    config.cookie_method, 
                    config.cookie_file, 
                    skip_for_quick_mode=True
                ):
                    self.logger.warning(f"Cookie quick-check failed, but continuing anyway")
        
        self.is_downloading = True
        self.logger.info(f"Starting {'quick ' if quick_mode else ''}downloads for {len(playlist_ids)} playlists")
        
        # Add playlists to queue
        for playlist_id in playlist_ids:
            self.download_queue.add_playlist(playlist_id)
            self.logger.debug(f"Added playlist to queue: {playlist_id}")
        
        # Start processing queue with potentially different concurrency
        max_workers = config.max_concurrent_downloads
        
        # If quick mode or parallel_downloads is set, use higher concurrency
        if quick_mode or config.parallel_downloads > 0:
            additional_workers = config.parallel_downloads if config.parallel_downloads > 0 else 2
            max_workers = min(config.max_concurrent_downloads + additional_workers, 8)
            
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger.info(f"Created thread pool with {max_workers} workers")
        self._process_queue(config, progress_listener)
        
        return True
    
    def stop_downloads(self) -> None:
        """Stop all downloads with extreme prejudice"""
        if not self.is_downloading:
            self.logger.debug("No active downloads to stop")
            return
            
        self.logger.info("Forcefully stopping all downloads")
        self.is_downloading = False
        
        # Cancel active downloads
        for playlist_id, future in list(self.active_downloads.items()):
            self.logger.debug(f"Cancelling download for playlist: {playlist_id}")
            future.cancel()
        
        # Force shutdown all executors
        if self.executor:
            self.logger.debug("Shutting down main executor")
            self.executor.shutdown(wait=False, cancel_futures=True)  # Use cancel_futures if available (Python 3.9+)
            self.executor = None
        
        # Force clear queue and state
        self.download_queue.clear_all()
        self.active_downloads.clear()
        
        # If using yt-dlp directly, we should try to kill any of its processes too
        # This might require storing process IDs/references somewhere
        self.downloader.force_stop()  # We'll need to implement this
        
        self.logger.info("All downloads forcefully stopped")
    
    def add_to_queue(self, playlist_ids: List[str]) -> bool:
        """Add playlists to the queue (works whether downloading or not)"""
        if not playlist_ids:
            return False
            
        for playlist_id in playlist_ids:
            self.download_queue.add_playlist(playlist_id)
            self.logger.debug(f"Added playlist to queue: {playlist_id}")
        
        self.logger.info(f"Added {len(playlist_ids)} playlist(s) to queue")
        return True
    
    def pause_downloads(self) -> None:
        """Pause all active downloads"""
        self.logger.info("Pausing all downloads")
        self.downloader.pause()
    
    def resume_downloads(self) -> None:
        """Resume paused downloads"""
        self.logger.info("Resuming all downloads")
        self.downloader.resume()
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        status = {
            'pending': self.download_queue.pending_count,
            'completed': self.download_queue.completed_count,
            'failed': self.download_queue.failed_count,
            'active': len(self.active_downloads)
        }
        self.logger.debug(f"Queue status: {status}")
        return status
    
    def retry_failed(self, 
                    config: DownloadConfig,
                    progress_listener: Optional[ProgressListener] = None) -> None:
        """Retry failed downloads"""
        failed_ids = self.download_queue.get_failed_ids()
        self.logger.info(f"Retrying {len(failed_ids)} failed downloads")
        
        self.download_queue.clear_failed()
        
        for playlist_id in failed_ids:
            self.download_queue.add_playlist(playlist_id)
            self.logger.debug(f"Re-added failed playlist to queue: {playlist_id}")
        
        self._process_queue(config, progress_listener)
    
    def _process_queue(self, 
                      config: DownloadConfig,
                      progress_listener: Optional[ProgressListener] = None) -> None:
        """Process downloads from the queue with optimized thread management"""
        self.logger.debug("Starting optimized queue processor")
        
        # Start background processor only if not already running
        if self._processor_running:
            self.logger.debug("Queue processor already running")
            return
            
        self._processor_running = True
        
        # Define a more efficient queue processor that better handles concurrency
        def queue_processor():
            try:
                self.logger.debug("Queue processor thread started")
                
                # Track active downloads more efficiently
                active_download_count = 0
                pending_futures = {}  # Map of playlist_id to Future
                
                while self.is_downloading:
                    completed_futures = []
                    
                    # Check for completed downloads
                    for playlist_id, future in list(pending_futures.items()):
                        if future.done():
                            completed_futures.append(playlist_id)
                            active_download_count -= 1
                            
                            # Process completion or error
                            try:
                                future.result()  # This will raise any exceptions from the download
                            except Exception as e:
                                self.logger.error(f"Download failed for {playlist_id}: {e}")
                    
                    # Remove completed downloads from tracking
                    for playlist_id in completed_futures:
                        del pending_futures[playlist_id]
                    
                    # Start new downloads if we have capacity
                    while (active_download_count < config.max_concurrent_downloads and 
                           self.is_downloading):
                        
                        # Get next playlist from queue
                        next_item = self.download_queue.get_next()
                        if not next_item:
                            break  # No more items in queue
                        
                        # Start download
                        playlist_id = next_item.playlist_id
                        self.logger.info(f"Starting download for playlist: {playlist_id}")
                        
                        # Submit task with correct configuration based on mode
                        use_quick_mode = getattr(config, 'quick_mode', False)
                        
                        if use_quick_mode and hasattr(self.downloader, 'download_quick'):
                            # Use optimized quick download if available
                            future = self.executor.submit(
                                self.downloader.download_quick,
                                playlist_id,
                                config,
                                progress_listener
                            )
                        else:
                            # Use standard download method
                            future = self.executor.submit(
                                self._download_with_handling,
                                playlist_id,
                                config,
                                progress_listener
                            )
                        
                        # Track download
                        pending_futures[playlist_id] = future
                        active_download_count += 1
                    
                    # Check if we're done
                    if active_download_count == 0 and self.download_queue.pending_count == 0:
                        if self.is_downloading:
                            self.logger.info("All downloads completed")
                            self._on_all_downloads_complete(config, progress_listener)
                            break
                    
                    # Prevent busy-waiting with a small sleep
                    time.sleep(0.1)
                    
                self._processor_running = False
                self.logger.debug("Queue processor thread finished")
                    
            except Exception as e:
                self.logger.error(f"Error in queue processor: {e}", exc_info=True)
                self.is_downloading = False
                self._processor_running = False
        
        # Start queue processor in a separate thread
        processor_thread = ThreadPoolExecutor(max_workers=1)
        processor_thread.submit(queue_processor)
        self.logger.debug("Queue processor thread submitted")
    
    def _download_with_handling(self,
                            playlist_id: str,
                            config: DownloadConfig,
                            progress_listener: Optional[ProgressListener] = None) -> None:
        """Download with error handling"""
        try:
            # Check if we've been cancelled already
            if not self.is_downloading:
                self.logger.debug(f"Download cancelled before starting: {playlist_id}")
                return
                
            self.logger.debug(f"Starting download handler for playlist: {playlist_id}")
            
            # Check for duplicates if enabled and not in quick mode
            if config.check_duplicates and not getattr(config, 'quick_mode', False):
                # Use is_duplicate method if available (optimized)
                if hasattr(self.history_repository, 'is_duplicate'):
                    is_duplicate = self.history_repository.is_duplicate(playlist_id)
                else:
                    # Fall back to old method
                    existing = self.history_repository.find_by_playlist_id(playlist_id)
                    is_duplicate = existing is not None
                    
                if is_duplicate:
                    self.logger.info(f"Skipping duplicate: {playlist_id}")
                    if progress_listener:
                        progress_listener.on_download_complete(playlist_id)
                    return
            
            # Call the downloader
            self.downloader.download(playlist_id, config, progress_listener)
            
            # Check if we were cancelled during download
            if not self.is_downloading:
                self.logger.debug(f"Download was cancelled during execution: {playlist_id}")
                return
                
            # Mark as completed - ENSURE ALL DATA IS SERIALIZABLE
            completion_info = {
                'status': 'completed', 
                'path': config.download_directory,
                'timestamp': datetime.now().isoformat()
            }
            self.download_queue.mark_completed(playlist_id, completion_info)
            self.logger.info(f"Download completed successfully: {playlist_id}")
            
        except Exception as e:
            # Check if we were cancelled - don't mark as failed if cancelled
            if not self.is_downloading:
                self.logger.debug(f"Download was cancelled after exception: {playlist_id}")
                return
                
            error_msg = str(e)
            self.logger.error(f"Failed to download {playlist_id}: {error_msg}")
            
            # Create a serializable error entry
            self.download_queue.mark_failed(playlist_id, error_msg)
            
            # Notify progress listener
            if progress_listener:
                progress_listener.on_download_error(playlist_id, error_msg)
                    
        finally:
            # Remove from active downloads
            if playlist_id in self.active_downloads:
                try:
                    del self.active_downloads[playlist_id]
                    self.logger.debug(f"Removed from active downloads: {playlist_id}")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up active download: {e}")  
  
    def _on_all_downloads_complete(self, 
                                config: DownloadConfig,
                                progress_listener: Optional[ProgressListener] = None) -> None:
        """Handle completion of all downloads"""
        self.is_downloading = False
        
        # Auto-retry failed if enabled
        if config.auto_retry_failed and self.download_queue.failed_count > 0:
            self.logger.info(f"Auto-retrying {self.download_queue.failed_count} failed downloads")
            self.retry_failed(config, progress_listener)
        else:
            # Shutdown executor
            if self.executor:
                self.logger.debug("Shutting down executor")
                self.executor.shutdown(wait=True)
                self.executor = None
            
            # Log summary
            status = self.get_queue_status()
            self.logger.info(
                f"Downloads complete. Completed: {status['completed']}, "
                f"Failed: {status['failed']}"
            )
            
            # Notify listener about all downloads completing
            if progress_listener:
                progress_listener.on_all_downloads_complete()