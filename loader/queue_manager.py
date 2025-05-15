# queue_manager.py - Download queue management

import time
from typing import List, Optional, Dict
from models import QueueItem, DownloadResult, DownloadStatus


class DownloadQueue:
    """Manages download queue with priority support"""
    
    def __init__(self):
        self.queue: List[QueueItem] = []
        self.completed: List[DownloadResult] = []
        self.failed: List[DownloadResult] = []
    
    def add_playlist(self, playlist_id: str, priority: int = 0) -> None:
        """Add a playlist to the queue"""
        item = QueueItem(
            playlist_id=playlist_id,
            priority=priority,
            added_time=time.time()
        )
        self.queue.append(item)
        self._sort_queue()
    
    def get_next(self) -> Optional[QueueItem]:
        """Get the next item from the queue"""
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def mark_completed(self, playlist_id: str, info: Dict) -> None:
        """Mark a download as completed"""
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.COMPLETED,
            info=info
        )
        self.completed.append(result)
    
    def mark_failed(self, playlist_id: str, error: str) -> None:
        """Mark a download as failed"""
        result = DownloadResult(
            playlist_id=playlist_id,
            status=DownloadStatus.FAILED,
            info={},
            error=error
        )
        self.failed.append(result)
    
    def get_failed_ids(self) -> List[str]:
        """Get list of failed playlist IDs"""
        return [item.playlist_id for item in self.failed]
    
    def clear_failed(self) -> None:
        """Clear the failed list"""
        self.failed.clear()
    
    def clear_completed(self) -> None:
        """Clear the completed list"""
        self.completed.clear()
    
    def reset(self) -> None:
        """Reset the entire queue"""
        self.queue.clear()
        self.completed.clear()
        self.failed.clear()
    
    def _sort_queue(self) -> None:
        """Sort queue by priority and added time"""
        self.queue.sort(key=lambda x: (-x.priority, x.added_time))
    
    @property
    def pending_count(self) -> int:
        return len(self.queue)
    
    @property
    def completed_count(self) -> int:
        return len(self.completed)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed)