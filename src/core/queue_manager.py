import time
import logging
from typing import List, Optional, Dict
from src.data.models import QueueItem, DownloadResult, DownloadStatus
from src.utils.logging_utils import get_logger

# Get module logger
logger = get_logger(__name__)

class DownloadQueue:
    """Manages download queue with priority support"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.DownloadQueue")
        self.queue: List[QueueItem] = []
        self.completed: List[DownloadResult] = []
        self.failed: List[DownloadResult] = []
        self.logger.debug("Download queue initialized")
    
    def add_playlist(self, playlist_id: str, priority: int = 0) -> None:
        """Add a playlist to the queue"""
        item = QueueItem(
            playlist_id=playlist_id,
            priority=priority,
            added_time=time.time()
        )
        self.queue.append(item)
        self._sort_queue()
        self.logger.debug(f"Added playlist to queue: {playlist_id} (priority: {priority})")
    
    def get_next(self) -> Optional[QueueItem]:
        """Get the next item from the queue"""
        if self.queue:
            item = self.queue.pop(0)
            self.logger.debug(f"Retrieved next item from queue: {item.playlist_id}")
            return item
        self.logger.debug("Queue is empty, no next item")
        return None
    
    def mark_completed(self, playlist_id: str, info: Dict) -> None:
        """Mark a download as completed"""
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.COMPLETED,
            info=info
        )
        self.completed.append(result)
        self.logger.debug(f"Marked playlist as completed: {playlist_id}")
    
    def mark_failed(self, playlist_id: str, error: str) -> None:
        """Mark a download as failed"""
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.FAILED,
            info={},
            error=error
        )
        self.failed.append(result)
        self.logger.debug(f"Marked playlist as failed: {playlist_id}, error: {error[:100]}...")
    
    def get_failed_ids(self) -> List[str]:
        """Get list of failed playlist IDs"""
        failed_ids = [item.playlist_id for item in self.failed]
        self.logger.debug(f"Retrieved {len(failed_ids)} failed playlist IDs")
        return failed_ids
    
    def clear_failed(self) -> None:
        """Clear the failed list"""
        count = len(self.failed)
        self.failed.clear()
        self.logger.debug(f"Cleared {count} failed items")
    
    def clear_completed(self) -> None:
        """Clear the completed list"""
        count = len(self.completed)
        self.completed.clear()
        self.logger.debug(f"Cleared {count} completed items")
    
    def reset(self) -> None:
        """Reset the entire queue"""
        pending_count = len(self.queue)
        completed_count = len(self.completed)
        failed_count = len(self.failed)
        
        self.queue.clear()
        self.completed.clear()
        self.failed.clear()
        
        self.logger.debug(f"Reset queue: cleared {pending_count} pending, {completed_count} completed, {failed_count} failed items")
    
    def _sort_queue(self) -> None:
        """Sort queue by priority and added time"""
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