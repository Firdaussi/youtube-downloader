# repositories.py - Concrete implementations of repository interfaces

import json
import os
from typing import List, Optional
from datetime import datetime
from models import DownloadConfig, HistoryEntry, DownloadQuality


class JsonConfigurationRepository:
    """JSON file-based configuration storage"""
    
    def __init__(self, config_file: str = "downloader_config.json"):
        self.config_file = config_file
    
    def load_config(self) -> DownloadConfig:
        """Load configuration from JSON file"""
        default_config = DownloadConfig()
        
        if not os.path.exists(self.config_file):
            self.save_config(default_config)
            return default_config
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                # Convert quality string to enum if present
                if 'default_quality' in data:
                    data['default_quality'] = DownloadQuality(data['default_quality'])
                return DownloadConfig(**data)
        except Exception:
            return default_config
    
    def save_config(self, config: DownloadConfig) -> None:
        """Save configuration to JSON file"""
        data = {
            'download_directory': config.download_directory,
            'max_concurrent_downloads': config.max_concurrent_downloads,
            'default_quality': config.default_quality.value,
            'retry_count': config.retry_count,
            'auto_retry_failed': config.auto_retry_failed,
            'check_duplicates': config.check_duplicates,
            'bandwidth_limit': config.bandwidth_limit,
            'cookie_method': config.cookie_method,
            'cookie_file': config.cookie_file
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)


class JsonHistoryRepository:
    """JSON file-based history storage"""
    
    def __init__(self, history_file: str = "download_history.json"):
        self.history_file = history_file
    
    def save_entry(self, entry: HistoryEntry) -> None:
        """Save a history entry to file"""
        history = self.load_history()
        
        # Convert to dict for JSON serialization
        entry_dict = {
            'playlist_id': entry.playlist_id,
            'playlist_title': entry.playlist_title,
            'status': entry.status,
            'timestamp': entry.timestamp.isoformat(),
            'download_path': entry.download_path
        }
        
        # Remove any existing entries with the same ID and status
        history = [e for e in history if not (
            isinstance(e, dict) and 
            e.get('playlist_id') == entry.playlist_id and 
            e.get('status') == entry.status
        )]
        
        history.append(entry_dict)
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def load_history(self) -> List[HistoryEntry]:
        """Load all history entries from file"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
                
            entries = []
            for item in data:
                # Handle both dict and HistoryEntry objects
                if isinstance(item, dict):
                    entry = HistoryEntry(
                        playlist_id=item['playlist_id'],
                        playlist_title=item['playlist_title'],
                        status=item['status'],
                        timestamp=datetime.fromisoformat(item['timestamp']),
                        download_path=item['download_path']
                    )
                    entries.append(entry)
                else:
                    entries.append(item)
            
            return entries
        except Exception:
            return []
    
    def clear_history(self) -> None:
        """Clear all history"""
        with open(self.history_file, 'w') as f:
            json.dump([], f)
    
    def find_by_playlist_id(self, playlist_id: str) -> Optional[HistoryEntry]:
        """Find a history entry by playlist ID"""
        history = self.load_history()
        for entry in history:
            if entry.playlist_id == playlist_id and entry.status == 'completed':
                return entry
        return None