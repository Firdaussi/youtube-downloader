import json
import os
import shutil
import time
from typing import List, Optional, Dict, Any, Union, Set
from datetime import datetime
from src.data.models import DownloadConfig, HistoryEntry, DownloadQuality

class OptimizedJsonHistoryRepository:
    """Optimized JSON file-based history storage with memory caching"""
    
    def __init__(self, history_file: str = "download_history.json"):
        self.history_file = history_file
        self.cache = {}  # In-memory cache
        self.completed_ids = set()  # Fast lookup for duplicates
        self._loaded = False  # Flag to track if we've loaded from file
        
    def _ensure_loaded(self):
        """Ensure history is loaded into memory"""
        if not self._loaded:
            self._load_cache()
            self._loaded = True
            
    def _load_cache(self):
        """Load history into memory cache"""
        if not os.path.exists(self.history_file):
            # Create an empty history file if it doesn't exist
            with open(self.history_file, 'w') as f:
                json.dump([], f)
            return
        
        try:
            with open(self.history_file, 'r') as f:
                content = f.read().strip()
                # Check if file is empty or just whitespace
                if not content:
                    return
                
                raw_entries = json.loads(content)
                
                # Build cache and completed_ids set
                for entry in raw_entries:
                    if 'playlist_id' in entry:
                        self.cache[entry['playlist_id']] = entry
                        if entry.get('status') == 'completed':
                            self.completed_ids.add(entry['playlist_id'])
                            
        except json.JSONDecodeError as e:
            print(f"Error loading history file: {e}")
            self._backup_corrupted_file()
        except Exception as e:
            print(f"Unexpected error loading history file: {e}")
    
    def _backup_corrupted_file(self):
        """Backup corrupted history file"""
        backup_file = f"{self.history_file}.bak.{int(time.time())}"
        try:
            shutil.copy2(self.history_file, backup_file)
            print(f"Corrupted history file backed up to {backup_file}")
        except Exception as be:
            print(f"Failed to backup corrupted history: {be}")
        
        # Create a new empty history file
        with open(self.history_file, 'w') as f:
            json.dump([], f)
        
        # Reset cache and tracking
        self.cache = {}
        self.completed_ids = set()
    
    def save_entry(self, entry: Union[HistoryEntry, Dict[str, Any]]) -> None:
        """Save a history entry to memory cache and file"""
        self._ensure_loaded()
        
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
        
        playlist_id = entry_dict.get('playlist_id')
        if not playlist_id:
            raise ValueError("Entry must have a playlist_id")
            
        # Update cache
        self.cache[playlist_id] = entry_dict
        
        # Update completed_ids tracking
        if entry_dict.get('status') == 'completed':
            self.completed_ids.add(playlist_id)
        elif playlist_id in self.completed_ids and entry_dict.get('status') != 'completed':
            self.completed_ids.remove(playlist_id)
        
        # Write entire cache to file (could be optimized with delayed writing)
        self._save_to_file()
    
    def _save_to_file(self):
        """Save cache to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(list(self.cache.values()), f, indent=2)
        except Exception as e:
            print(f"Error saving history to file: {e}")
    
    def load_history(self) -> List[HistoryEntry]:
        """Load history entries as HistoryEntry objects"""
        self._ensure_loaded()
        
        entries = []
        for item in self.cache.values():
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
    
    def find_by_playlist_id(self, playlist_id: str) -> Optional[HistoryEntry]:
        """Find a history entry by playlist ID with caching"""
        self._ensure_loaded()
        
        # Fast check for completed status
        if playlist_id not in self.completed_ids:
            return None
            
        # Get from cache
        entry_dict = self.cache.get(playlist_id)
        if not entry_dict or entry_dict.get('status') != 'completed':
            return None
            
        try:
            # Convert timestamp string to datetime
            if isinstance(entry_dict.get('timestamp'), str):
                timestamp = datetime.fromisoformat(entry_dict['timestamp'])
            else:
                timestamp = datetime.now()  # Fallback
            
            return HistoryEntry(
                playlist_id=entry_dict['playlist_id'],
                playlist_title=entry_dict['playlist_title'],
                status=entry_dict['status'],
                timestamp=timestamp,
                download_path=entry_dict['download_path']
            )
        except Exception as e:
            print(f"Error converting history entry: {e}")
            return None
    
    def is_duplicate(self, playlist_id: str) -> bool:
        """Fast check if a playlist has been completed"""
        self._ensure_loaded()
        return playlist_id in self.completed_ids
    
    def clear_history(self) -> None:
        """Clear all history"""
        self.cache = {}
        self.completed_ids = set()
        self._save_to_file()


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
                    
                # Handle new performance optimization settings
                if 'quick_mode' not in data:
                    data['quick_mode'] = False
                if 'skip_validation' not in data:
                    data['skip_validation'] = False
                if 'skip_metadata' not in data:
                    data['skip_metadata'] = False
                if 'throttle_progress' not in data:
                    data['throttle_progress'] = True
                if 'cache_lifetime' not in data:
                    data['cache_lifetime'] = 3600
                if 'use_memory_cache' not in data:
                    data['use_memory_cache'] = True
                if 'parallel_downloads' not in data:
                    data['parallel_downloads'] = 0
                
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
            'cookie_file': config.cookie_file,
            'output_template': config.output_template,
            'create_playlist_folder': config.create_playlist_folder,
            'sanitize_filenames': config.sanitize_filenames,
            'preferred_format': config.preferred_format,
            'use_postprocessing': config.use_postprocessing,
            
            # Performance optimization settings
            'quick_mode': getattr(config, 'quick_mode', False),
            'skip_validation': getattr(config, 'skip_validation', False),
            'skip_metadata': getattr(config, 'skip_metadata', False),
            'throttle_progress': getattr(config, 'throttle_progress', True),
            'cache_lifetime': getattr(config, 'cache_lifetime', 3600),
            'use_memory_cache': getattr(config, 'use_memory_cache', True),
            'parallel_downloads': getattr(config, 'parallel_downloads', 0)
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
        """Load raw history entries as dictionaries with improved error handling"""
        if not os.path.exists(self.history_file):
            # Create an empty history file if it doesn't exist
            with open(self.history_file, 'w') as f:
                json.dump([], f)
            return []
        
        try:
            with open(self.history_file, 'r') as f:
                content = f.read().strip()
                # Check if file is empty or just whitespace
                if not content:
                    return []
                
                return json.loads(content)
        except json.JSONDecodeError as e:
            error_msg = f"Error loading history file: {e}"
            print(error_msg)
            
            # Backup corrupted file
            backup_file = f"{self.history_file}.bak.{int(time.time())}"
            try:
                shutil.copy2(self.history_file, backup_file)
                print(f"Corrupted history file backed up to {backup_file}")
            except Exception as be:
                print(f"Failed to backup corrupted history: {be}")
            
            # Create a new empty history file
            with open(self.history_file, 'w') as f:
                json.dump([], f)
            
            return []
        except Exception as e:
            print(f"Unexpected error loading history file: {e}")
            return []

    def find_by_playlist_id(self, playlist_id: str) -> Optional[HistoryEntry]:
        """Find a history entry by playlist ID with error handling"""
        try:
            # For better performance, first try to find it in the raw dicts
            for entry_dict in self.load_history_as_dicts():
                if entry_dict.get('playlist_id') == playlist_id and entry_dict.get('status') == 'completed':
                    # Found a match, convert to HistoryEntry
                    try:
                        # Convert timestamp string to datetime
                        if isinstance(entry_dict.get('timestamp'), str):
                            timestamp = datetime.fromisoformat(entry_dict['timestamp'])
                        else:
                            timestamp = datetime.now()  # Fallback
                        
                        return HistoryEntry(
                            playlist_id=entry_dict['playlist_id'],
                            playlist_title=entry_dict['playlist_title'],
                            status=entry_dict['status'],
                            timestamp=timestamp,
                            download_path=entry_dict['download_path']
                        )
                    except Exception as e:
                        print(f"Error converting history entry: {e}")
                        return None
            
            # Not found
            return None
        except Exception as e:
            print(f"Error searching history: {e}")
            return None
    
    def is_duplicate(self, playlist_id: str) -> bool:
        """Check if a playlist ID is a duplicate (has been completed)"""
        # This is less efficient than the optimized version
        # but provided for backward compatibility
        entry = self.find_by_playlist_id(playlist_id)
        return entry is not None and entry.status == 'completed'
    
    def clear_history(self) -> None:
        """Clear all history"""
        with open(self.history_file, 'w') as f:
            json.dump([], f)