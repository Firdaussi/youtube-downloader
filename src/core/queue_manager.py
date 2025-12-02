import time
import logging
from typing import List, Optional, Dict
from src.data.models import QueueItem, DownloadResult, DownloadStatus
from src.utils.logging_utils import get_logger

# Get module logger
logger = get_logger(__name__)

class DownloadQueue:
    """Optimized download queue with priority support and faster lookups"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.DownloadQueue")
        self.queue: List[QueueItem] = []
        self.completed: List[DownloadResult] = []
        self.failed: List[DownloadResult] = []
        
        # Add dictionaries for O(1) lookups
        self.completed_ids = set()  # Use set for O(1) lookup
        self.failed_ids = set()     # Use set for O(1) lookup
        self.queue_ids = set()      # Track IDs in queue
        
        self.logger.debug("Optimized download queue initialized")
    
    def add_playlist(self, playlist_id: str, priority: int = 0) -> None:
        """Add a playlist to the queue with duplicate prevention"""
        # Check if already in the queue (O(1) lookup)
        if playlist_id in self.queue_ids:
            self.logger.debug(f"Playlist already in queue: {playlist_id}, skipping")
            return
            
        # Create queue item
        item = QueueItem(
            playlist_id=playlist_id,
            priority=priority,
            added_time=time.time()
        )
        
        # Add to queue and tracking set
        self.queue.append(item)
        self.queue_ids.add(playlist_id)
        
        self._sort_queue()
        self.logger.debug(f"Added playlist to queue: {playlist_id} (priority: {priority})")
    
    def get_next(self) -> Optional[QueueItem]:
        """Get the next item from the queue with efficient tracking"""
        if not self.queue:
            self.logger.debug("Queue is empty, no next item")
            return None
            
        item = self.queue.pop(0)
        
        # Remove from tracking set
        if item.playlist_id in self.queue_ids:
            self.queue_ids.remove(item.playlist_id)
            
        self.logger.debug(f"Retrieved next item from queue: {item.playlist_id}")
        return item
    
    def mark_completed(self, playlist_id: str, info: Dict) -> None:
        """Mark a download as completed with efficient tracking"""
        # Already completed? Skip
        if playlist_id in self.completed_ids:
            return
            
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.COMPLETED,
            info=info
        )
        
        self.completed.append(result)
        self.completed_ids.add(playlist_id)  # Add to set for O(1) lookup
        
        # If it was in failed list, remove it
        if playlist_id in self.failed_ids:
            # Update list (less frequent operation)
            self.failed = [r for r in self.failed if r.playlist_id != playlist_id]
            self.failed_ids.remove(playlist_id)
            
        self.logger.debug(f"Marked playlist as completed: {playlist_id}")
    
    def mark_failed(self, playlist_id: str, error: str) -> None:
        """Mark a download as failed with efficient tracking"""
        # Already failed? Update the error message
        if playlist_id in self.failed_ids:
            for item in self.failed:
                if item.playlist_id == playlist_id:
                    item.error = error
                    self.logger.debug(f"Updated error for failed playlist: {playlist_id}")
                    return
        
        # Create new failed result
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.FAILED,
            info={},
            error=error
        )
        
        self.failed.append(result)
        self.failed_ids.add(playlist_id)  # Add to set for O(1) lookup
        
        self.logger.debug(f"Marked playlist as failed: {playlist_id}, error: {error[:100]}...")
    
    def get_failed_ids(self) -> List[str]:
        """Get list of failed playlist IDs efficiently"""
        # Just convert set to list - more efficient than extracting from objects
        return list(self.failed_ids)
    
    def is_duplicate(self, playlist_id: str) -> bool:
        """Efficiently check if a playlist is already processed"""
        return playlist_id in self.completed_ids
    
    def clear_failed(self) -> None:
        """Clear the failed list efficiently"""
        count = len(self.failed)
        self.failed.clear()
        self.failed_ids.clear()  # Clear the set too
        self.logger.debug(f"Cleared {count} failed items")
    
    def clear_completed(self) -> None:
        """Clear the completed list efficiently"""
        count = len(self.completed)
        self.completed.clear()
        self.completed_ids.clear()  # Clear the set too
        self.logger.debug(f"Cleared {count} completed items")
    
    def clear_all(self) -> None:
        """Reset the entire queue efficiently"""
        pending_count = len(self.queue)
        completed_count = len(self.completed)
        failed_count = len(self.failed)
        
        self.queue.clear()
        self.completed.clear()
        self.failed.clear()
        
        # Clear sets too
        self.queue_ids.clear()
        self.completed_ids.clear()
        self.failed_ids.clear()
        
        self.logger.debug(f"Reset queue: cleared {pending_count} pending, {completed_count} completed, {failed_count} failed items")
    
    def _sort_queue(self) -> None:
        """Sort queue by priority and added time"""
        if len(self.queue) <= 1:
            return  # No need to sort single item
            
        self.queue.sort(key=lambda x: (-x.priority, x.added_time))
        self.logger.debug("Queue sorted by priority and added time")
    
    @property
    def pending_count(self) -> int:
        return len(self.queue)
    
    @property
    def completed_count(self) -> int:
        return len(self.completed)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed)