# repositories.py - Fixed repository implementations

import json
import os
from typing import List, Optional, Dict, Any, Union
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
    """JSON file-based history storage with improved serialization"""
    
    def __init__(self, history_file: str = "download_history.json"):
        self.history_file = history_file
    
    def save_entry(self, entry: Union[HistoryEntry, Dict[str, Any]]) -> None:
        """Save a history entry to file, handles both HistoryEntry objects and dicts"""
        history = self.load_history_as_dicts()
        
        # Convert to dict for JSON serialization if not already a dict
        if isinstance(entry, HistoryEntry):
            entry_dict = {
                'playlist_id': entry.playlist_id,
                'playlist_title': entry.playlist_title,
                'status': entry.status,
                'timestamp': entry.timestamp.isoformat() if hasattr(entry.timestamp, 'isoformat') else entry.timestamp,
                'download_path': entry.download_path
            }
        else:
            # Already a dict, make sure timestamp is a string
            entry_dict = dict(entry)  # Make a copy to avoid modifying the original
            if 'timestamp' in entry_dict and hasattr(entry_dict['timestamp'], 'isoformat'):
                entry_dict['timestamp'] = entry_dict['timestamp'].isoformat()
        
        # Remove any existing entries with the same ID 
        history = [e for e in history if e.get('playlist_id') != entry_dict.get('playlist_id')]
        
        # Add the new entry
        history.append(entry_dict)
        
        # Save to file
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def load_history(self) -> List[HistoryEntry]:
        """Load history entries as HistoryEntry objects"""
        history_dicts = self.load_history_as_dicts()
        
        entries = []
        for item in history_dicts:
            try:
                # Convert timestamp string to datetime
                if isinstance(item.get('timestamp'), str):
                    timestamp = datetime.fromisoformat(item['timestamp'])
                else:
                    timestamp = datetime.now()  # Fallback
                
                entry = HistoryEntry(
                    playlist_id=item['playlist_id'],
                    playlist_title=item['playlist_title'],
                    status=item['status'],
                    timestamp=timestamp,
                    download_path=item['download_path']
                )
                entries.append(entry)
            except Exception as e:
                print(f"Error converting history entry: {e}")
                # Skip invalid entries
                continue
        
        return entries
    
    def load_history_as_dicts(self) -> List[Dict[str, Any]]:
        """Load raw history entries as dictionaries"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history file: {e}")
            return []
    
    def clear_history(self) -> None:
        """Clear all history"""
        with open(self.history_file, 'w') as f:
            json.dump([], f)
    
    def find_by_playlist_id(self, playlist_id: str) -> Optional[HistoryEntry]:
        """Find a history entry by playlist ID"""
        for entry in self.load_history():
            if entry.playlist_id == playlist_id and entry.status == 'completed':
                return entry
        return None