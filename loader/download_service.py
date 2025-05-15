# download_service.py - Main service orchestrating downloads

import logging
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Optional, Dict, Set

from models import DownloadConfig
from interfaces import (
    PlaylistDownloader, HistoryRepository, 
    ProgressListener, CookieValidator
)
from queue_manager import DownloadQueue


class DownloadService:
    """Service that orchestrates playlist downloads"""
    
    def __init__(self,
                 downloader: PlaylistDownloader,
                 history_repository: HistoryRepository,
                 cookie_validator: CookieValidator,
                 logger: logging.Logger):
        self.downloader = downloader
        self.history_repository = history_repository
        self.cookie_validator = cookie_validator
        self.logger = logger
        self.download_queue = DownloadQueue()
        self.active_downloads: Dict[str, Future] = {}
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_downloading = False
    
    def start_downloads(self, 
                       playlist_ids: List[str], 
                       config: DownloadConfig,
                       progress_listener: Optional[ProgressListener] = None) -> bool:
        """Start downloading playlists"""
        if self.is_downloading:
            return False
        
        # Validate cookies first
        if not self.cookie_validator.validate(config.cookie_method, config.cookie_file):
            errors = self.cookie_validator.get_validation_errors()
            self.logger.error(f"Cookie validation failed: {errors}")
            return False
        
        self.is_downloading = True
        
        # Add playlists to queue
        for playlist_id in playlist_ids:
            self.download_queue.add_playlist(playlist_id)
        
        # Start processing queue
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_downloads)
        self._process_queue(config, progress_listener)
        
        return True
    
    def stop_downloads(self) -> None:
        """Stop all downloads"""
        self.is_downloading = False
        
        # Cancel active downloads
        for future in self.active_downloads.values():
            future.cancel()
        
        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None
        
        self.active_downloads.clear()
    
    def pause_downloads(self) -> None:
        """Pause all active downloads"""
        self.downloader.pause()
    
    def resume_downloads(self) -> None:
        """Resume paused downloads"""
        self.downloader.resume()
    
    def get_queue_status(self) -> Dict[str, int]:
        """Get current queue status"""
        return {
            'pending': self.download_queue.pending_count,
            'completed': self.download_queue.completed_count,
            'failed': self.download_queue.failed_count,
            'active': len(self.active_downloads)
        }
    
    def retry_failed(self, 
                    config: DownloadConfig,
                    progress_listener: Optional[ProgressListener] = None) -> None:
        """Retry failed downloads"""
        failed_ids = self.download_queue.get_failed_ids()
        self.download_queue.clear_failed()
        
        for playlist_id in failed_ids:
            self.download_queue.add_playlist(playlist_id)
        
        self._process_queue(config, progress_listener)
    
    def _process_queue(self, 
                      config: DownloadConfig,
                      progress_listener: Optional[ProgressListener]) -> None:
        """Process downloads from the queue"""
        # Start a background thread to process the queue
        def queue_processor():
            try:
                while self.is_downloading:
                    # Get next playlist from queue
                    next_item = self.download_queue.get_next()
                    if not next_item:
                        # Check if there are still active downloads
                        if not self.active_downloads:
                            self._on_all_downloads_complete(config, progress_listener)
                            break
                        # Wait for active downloads to complete
                        time.sleep(1)
                        continue
                    
                    # Wait if we're at max concurrent downloads
                    while (len(self.active_downloads) >= config.max_concurrent_downloads and 
                           self.is_downloading):
                        # Remove completed downloads
                        completed_ids: Set[str] = set()
                        for playlist_id, future in self.active_downloads.items():
                            if future.done():
                                completed_ids.add(playlist_id)
                        
                        for playlist_id in completed_ids:
                            del self.active_downloads[playlist_id]
                        
                        if len(self.active_downloads) >= config.max_concurrent_downloads:
                            time.sleep(0.5)
                    
                    # Break loop if downloads were stopped
                    if not self.is_downloading:
                        break
                    
                    # Start download
                    future = self.executor.submit(
                        self._download_with_handling,
                        next_item.playlist_id,
                        config,
                        progress_listener
                    )
                    self.active_downloads[next_item.playlist_id] = future
            
            except Exception as e:
                self.logger.error(f"Error in queue processor: {e}", exc_info=True)
                self.is_downloading = False
        
        # Start queue processor in a separate thread
        processor_thread = ThreadPoolExecutor(max_workers=1)
        processor_thread.submit(queue_processor)
    
    def _download_with_handling(self,
                               playlist_id: str,
                               config: DownloadConfig,
                               progress_listener: Optional[ProgressListener]) -> None:
        """Download with error handling"""
        try:
            # Call the downloader
            self.downloader.download(playlist_id, config, progress_listener)
            
            # Mark as completed with serializable data
            self.download_queue.mark_completed(
                playlist_id, 
                {
                    'status': 'completed', 
                    'path': config.download_directory,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to download {playlist_id}: {e}")
            
            # Ensure error message is serializable
            error_msg = str(e)
            
            # Mark as failed with serializable data
            self.download_queue.mark_failed(playlist_id, error_msg)
            
            # Notify progress listener if available
            if progress_listener:
                progress_listener.on_download_error(playlist_id, error_msg)
                
        finally:
            # Remove from active downloads
            if playlist_id in self.active_downloads:
                del self.active_downloads[playlist_id]
    
    def _on_all_downloads_complete(self, 
                                  config: DownloadConfig,
                                  progress_listener: Optional[ProgressListener]) -> None:
        """Handle completion of all downloads"""
        self.is_downloading = False
        
        # Auto-retry failed if enabled
        if config.auto_retry_failed and self.download_queue.failed_count > 0:
            self.logger.info(f"Auto-retrying {self.download_queue.failed_count} failed downloads")
            self.retry_failed(config, progress_listener)
        else:
            # Shutdown executor
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
            
            # Log summary
            status = self.get_queue_status()
            self.logger.info(
                f"Downloads complete. Completed: {status['completed']}, "
                f"Failed: {status['failed']}"
            )