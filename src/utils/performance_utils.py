# src/utils/performance_utils.py

import time
import threading
import logging
from typing import Callable, Optional, Dict, Any, TypeVar, Generic
from functools import wraps

# Get a logger for this module
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')

class Throttler:
    """Throttles function calls to limit execution frequency"""
    
    def __init__(self, min_interval: float = 0.25):
        """
        Initialize throttler
        
        Args:
            min_interval: Minimum time between executions in seconds
        """
        self.min_interval = min_interval
        self.last_call_time = 0
        self.lock = threading.RLock()
        self.last_result = None
        self.pending_call = False
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to throttle function calls"""
        @wraps(func)
        def wrapped(*args, **kwargs):
            current_time = time.time()
            
            with self.lock:
                # If enough time has passed since last call
                if current_time - self.last_call_time >= self.min_interval:
                    # Execute immediately
                    self.last_call_time = current_time
                    self.last_result = func(*args, **kwargs)
                    self.pending_call = False
                else:
                    # Mark that we have a pending call
                    self.pending_call = True
            
            return self.last_result
            
        return wrapped
    
    def execute_pending(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function now if there's a pending call"""
        with self.lock:
            if self.pending_call:
                self.last_call_time = time.time()
                self.last_result = func(*args, **kwargs)
                self.pending_call = False
                return self.last_result
            return None


class Debouncer(Generic[T]):
    """Debounces function calls to delay execution until input stabilizes"""
    
    def __init__(self, delay: float = 0.5):
        """
        Initialize debouncer
        
        Args:
            delay: Delay time in seconds before executing the function
        """
        self.delay = delay
        self.timer: Optional[threading.Timer] = None
        self.lock = threading.RLock()
        self.last_args = None
        self.last_kwargs = None
        self.last_call_time = 0
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., None]:
        """Decorator to debounce function calls"""
        @wraps(func)
        def wrapped(*args, **kwargs):
            with self.lock:
                self.last_args = args
                self.last_kwargs = kwargs
                self.last_call_time = time.time()
                
                # Cancel previous timer if it exists
                if self.timer:
                    self.timer.cancel()
                
                # Schedule new timer
                self.timer = threading.Timer(
                    self.delay,
                    self._execute_func,
                    args=[func]
                )
                self.timer.daemon = True
                self.timer.start()
                
            # Return None immediately
            return None
            
        return wrapped
    
    def _execute_func(self, func: Callable[..., T]) -> T:
        """Execute the function with the most recent arguments"""
        with self.lock:
            args = self.last_args
            kwargs = self.last_kwargs
            self.timer = None
        
        if args is not None:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in debounced function: {e}")
                return None
        return None


class BatchProcessor:
    """Processes items in batches rather than individually"""
    
    def __init__(self, processor_func: Callable[[list], Any], batch_size: int = 10, 
                 max_wait: float = 1.0):
        """
        Initialize batch processor
        
        Args:
            processor_func: Function to process a batch of items
            batch_size: Maximum number of items to process at once
            max_wait: Maximum time to wait before processing an incomplete batch
        """
        self.processor_func = processor_func
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.items = []
        self.lock = threading.RLock()
        self.timer: Optional[threading.Timer] = None
        self.last_process_time = time.time()
    
    def add_item(self, item: Any) -> bool:
        """
        Add an item to the batch
        
        Returns:
            True if batch was processed, False otherwise
        """
        with self.lock:
            self.items.append(item)
            
            # Cancel existing timer if any
            if self.timer:
                self.timer.cancel()
                self.timer = None
            
            # Process immediately if batch is full
            if len(self.items) >= self.batch_size:
                return self._process_batch()
            
            # Schedule processing after max_wait
            self.timer = threading.Timer(self.max_wait, self._timed_process)
            self.timer.daemon = True
            self.timer.start()
            
            return False
    
    def _timed_process(self) -> None:
        """Process batch after timer expires"""
        with self.lock:
            self._process_batch()
    
    def _process_batch(self) -> bool:
        """Process current batch of items"""
        with self.lock:
            if not self.items:
                return False
                
            # Get current batch and clear the queue
            current_batch = self.items.copy()
            self.items.clear()
            self.last_process_time = time.time()
            
            # Cancel timer if it exists
            if self.timer:
                self.timer.cancel()
                self.timer = None
        
        # Process the batch outside the lock
        try:
            self.processor_func(current_batch)
            return True
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return False
    
    def flush(self) -> bool:
        """Force processing of current items"""
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
                
            return self._process_batch()


class ProgressThrottler:
    """Specialized throttler for download progress updates"""
    
    def __init__(self, base_interval: float = 0.25, dynamic_throttling: bool = True):
        """
        Initialize progress throttler
        
        Args:
            base_interval: Base minimum time between updates in seconds
            dynamic_throttling: Whether to adjust throttling based on progress speed
        """
        self.base_interval = base_interval
        self.dynamic_throttling = dynamic_throttling
        self.last_update_time: Dict[str, float] = {}
        self.update_counts: Dict[str, int] = {}
        self.lock = threading.RLock()
        
        # For dynamic throttling
        self.progress_history: Dict[str, list] = {}
        self.last_progress: Dict[str, float] = {}
        
        # For status change detection
        self.last_status: Dict[str, str] = {}
        self.last_message: Dict[str, str] = {}
        
        logger.debug("ProgressThrottler initialized")
    
    def should_update(self, playlist_id: str, progress: float, 
                     status: Optional[str] = None, message: Optional[str] = None,
                     current_time: Optional[float] = None) -> bool:
        """
        Determine if a progress update should be processed
        
        Args:
            playlist_id: Identifier for the download
            progress: Current progress percentage (0-100)
            status: Current status (if status changes, always update)
            message: Current message (if message changes, always update)
            current_time: Current time (defaults to time.time())
            
        Returns:
            True if update should be processed, False otherwise
        """
        if current_time is None:
            current_time = time.time()
        
        with self.lock:
            # Initialize tracking for new downloads
            if playlist_id not in self.last_update_time:
                self.last_update_time[playlist_id] = 0
                self.update_counts[playlist_id] = 0
                self.progress_history[playlist_id] = []
                self.last_progress[playlist_id] = 0
                self.last_status[playlist_id] = ""
                self.last_message[playlist_id] = ""
            
            # Always update if status changes
            if status is not None and status != self.last_status[playlist_id]:
                self._track_update(playlist_id, progress, current_time, status, message)
                return True
                
            # Always update if message changes significantly
            if message is not None and message != self.last_message[playlist_id]:
                # Check if it's actually a meaningful change (not just ETA updates)
                if (not self.last_message[playlist_id].startswith("Downloading:") or 
                    not message.startswith("Downloading:")):
                    self._track_update(playlist_id, progress, current_time, status, message)
                    return True
            
            # Always update for the first 5 updates to get initial progress
            if self.update_counts[playlist_id] < 5:
                self._track_update(playlist_id, progress, current_time, status, message)
                return True
            
            # Calculate time since last update
            time_since_last = current_time - self.last_update_time[playlist_id]
            
            # Determine interval based on progress change rate
            interval = self._get_dynamic_interval(playlist_id, progress)
            
            # Check if enough time has passed
            if time_since_last >= interval:
                self._track_update(playlist_id, progress, current_time, status, message)
                return True
                
            # Always update if progress is complete (100%)
            if progress >= 100 and self.last_progress[playlist_id] < 100:
                self._track_update(playlist_id, progress, current_time, status, message)
                return True
                
            # Always update if progress has changed significantly
            if abs(progress - self.last_progress[playlist_id]) > 10:
                self._track_update(playlist_id, progress, current_time, status, message)
                return True
                
            return False
    
    def _track_update(self, playlist_id: str, progress: float, current_time: float,
                     status: Optional[str] = None, message: Optional[str] = None) -> None:
        """Track an update for dynamic throttling"""
        with self.lock:
            self.last_update_time[playlist_id] = current_time
            self.update_counts[playlist_id] += 1
            
            # Store progress history (last 5 points)
            self.progress_history[playlist_id].append((current_time, progress))
            if len(self.progress_history[playlist_id]) > 5:
                self.progress_history[playlist_id].pop(0)
                
            self.last_progress[playlist_id] = progress
            
            # Update status and message if provided
            if status is not None:
                self.last_status[playlist_id] = status
            if message is not None:
                self.last_message[playlist_id] = message
    
    def _get_dynamic_interval(self, playlist_id: str, current_progress: float) -> float:
        """Calculate dynamic update interval based on progress change rate"""
        if not self.dynamic_throttling:
            return self.base_interval
            
        with self.lock:
            history = self.progress_history[playlist_id]
            if len(history) < 2:
                return self.base_interval
            
            # Calculate progress change rate (percent per second)
            first_time, first_progress = history[0]
            last_time, last_progress = history[-1]
            time_diff = last_time - first_time
            
            if time_diff <= 0:
                return self.base_interval
                
            progress_diff = last_progress - first_progress
            change_rate = abs(progress_diff / time_diff)
            
            # Adjust interval based on change rate
            if change_rate < 0.5:  # Very slow progress
                return min(2.0, self.base_interval * 4)  # Up to 2 seconds
            elif change_rate < 2.0:  # Moderate progress
                return self.base_interval * 2  # Double base interval
            elif change_rate > 10.0:  # Very fast progress
                return max(0.1, self.base_interval / 2)  # At least 0.1 seconds
            
            # Adjust based on current progress
            if current_progress > 95:
                # Speed up updates near completion
                return max(0.1, self.base_interval / 2)
            
            return self.base_interval  # Default case
    
    def reset(self, playlist_id: Optional[str] = None) -> None:
        """Reset throttling state"""
        with self.lock:
            if playlist_id is None:
                # Reset all
                self.last_update_time.clear()
                self.update_counts.clear()
                self.progress_history.clear()
                self.last_progress.clear()
                self.last_status.clear()
                self.last_message.clear()
                logger.debug("Reset all throttling state")
            elif playlist_id in self.last_update_time:
                # Reset specific download
                del self.last_update_time[playlist_id]
                del self.update_counts[playlist_id]
                del self.progress_history[playlist_id]
                del self.last_progress[playlist_id]
                
                # Also clean up status and message tracking
                if playlist_id in self.last_status:
                    del self.last_status[playlist_id]
                if playlist_id in self.last_message:
                    del self.last_message[playlist_id]
                logger.debug(f"Reset throttling state for {playlist_id}")
