# models.py - Domain models and data structures

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DownloadQuality(Enum):
    BEST = "best"
    HD_1080P = "1080p"
    HD_720P = "720p"
    SD_480P = "480p"
    AUDIO_ONLY = "audio_only"


@dataclass
class DownloadConfig:
    download_directory: str = "/mnt/m/Library/Youtube"
    max_concurrent_downloads: int = 1
    default_quality: DownloadQuality = DownloadQuality.BEST
    retry_count: int = 3
    auto_retry_failed: bool = True
    check_duplicates: bool = True
    bandwidth_limit: str = "0"
    cookie_method: str = "none"
    cookie_file: str = ""


@dataclass
class PlaylistInfo:
    id: str
    title: str
    url: str
    total_tracks: int
    entries: list


@dataclass
class DownloadProgress:
    playlist_id: str
    status: DownloadStatus
    progress: float
    speed: float
    eta: int
    current_file: str
    message: str


@dataclass
class HistoryEntry:
    playlist_id: str
    playlist_title: str
    status: str
    timestamp: datetime
    download_path: str


@dataclass
class QueueItem:
    playlist_id: str
    priority: int
    added_time: float
    
    
@dataclass
class DownloadResult:
    playlist_id: str
    status: DownloadStatus
    info: Dict[str, Any]
    error: Optional[str] = None