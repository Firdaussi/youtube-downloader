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
        
        self.logger.debug("Download service initialized")
    
    def start_downloads(self, 
                       playlist_ids: List[str], 
                       config: DownloadConfig,
                       progress_listener: Optional[ProgressListener] = None) -> bool:
        """Start downloading playlists"""
        if self.is_downloading:
            self.logger.warning("Download already in progress, ignoring request")
            return False
        
        # Validate cookies first
        if not self.cookie_validator.validate(config.cookie_method, config.cookie_file):
            errors = self.cookie_validator.get_validation_errors()
            self.logger.error(f"Cookie validation failed: {errors}")
            return False
        
        self.is_downloading = True
        self.logger.info(f"Starting downloads for {len(playlist_ids)} playlists")
        
        # Add playlists to queue
        for playlist_id in playlist_ids:
            self.download_queue.add_playlist(playlist_id)
            self.logger.debug(f"Added playlist to queue: {playlist_id}")
        
        # Start processing queue
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_downloads)
        self.logger.info(f"Created thread pool with {config.max_concurrent_downloads} workers")
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
        """Process downloads from the queue"""
        self.logger.debug("Starting queue processor")
        
        # Start a background thread to process the queue
        def queue_processor():
            try:
                self.logger.debug("Queue processor thread started")
                while self.is_downloading:
                    # Get next playlist from queue
                    next_item = self.download_queue.get_next()
                    if not next_item:
                        # Check if there are still active downloads
                        if not self.active_downloads:
                            self.logger.info("Queue empty and no active downloads, completing")
                            self._on_all_downloads_complete(config, progress_listener)
                            break
                        # Wait for active downloads to complete
                        time.sleep(1)
                        continue
                    
                    # Wait if we're at max concurrent downloads
                    while (len(self.active_downloads) >= config.max_concurrent_downloads and 
                           self.is_downloading):
                        # Remove completed downloads
                        completed_ids = []
                        for playlist_id, future in list(self.active_downloads.items()):
                            if future.done():
                                self.logger.debug(f"Download completed: {playlist_id}")
                                completed_ids.append(playlist_id)
                        
                        for playlist_id in completed_ids:
                            del self.active_downloads[playlist_id]
                        
                        if len(self.active_downloads) >= config.max_concurrent_downloads:
                            time.sleep(0.5)
                    
                    # Break loop if downloads were stopped
                    if not self.is_downloading:
                        self.logger.debug("Download stopped, breaking queue processor loop")
                        break
                    
                    # Start download
                    playlist_id = next_item.playlist_id
                    self.logger.info(f"Starting download for playlist: {playlist_id}")
                    future = self.executor.submit(
                        self._download_with_handling,
                        playlist_id,
                        config,
                        progress_listener
                    )
                    self.active_downloads[playlist_id] = future
            
            except Exception as e:
                self.logger.error(f"Error in queue processor: {e}", exc_info=True)
                self.is_downloading = False
        
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