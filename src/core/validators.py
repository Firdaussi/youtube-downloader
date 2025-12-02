import os
import logging
import time
from typing import List, Optional
import re
from src.utils.logging_utils import get_logger

# Get module logger
logger = get_logger(__name__)

class OptimizedYouTubeCookieValidator:
    """Optimized validator with caching for YouTube cookies"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.YouTubeCookieValidator")
        self.errors: List[str] = []
        self.required_cookies = {"SID", "HSID", "SAPISID"}
        
        # Add cache for validation results
        self._validation_cache = {}  # {(method, file_path): (is_valid, timestamp)}
        self._cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        
        self.logger.debug("Optimized YouTube cookie validator initialized")
    
    def validate(self, method: str, file_path: Optional[str] = None, 
                skip_for_quick_mode: bool = False) -> bool:
        """Validate cookies with caching and quick mode option"""
        self.errors.clear()
        
        if skip_for_quick_mode:
            self.logger.debug("Skipping validation for quick mode")
            return True
        
        if method == 'none':
            self.logger.debug("Cookie method 'none' selected, no validation needed")
            return True
        
        # Check cache first
        cache_key = (method, file_path)
        if cache_key in self._validation_cache:
            is_valid, timestamp = self._validation_cache[cache_key]
            
            # Check if cache is still valid
            if time.time() - timestamp < self._cache_ttl:
                self.logger.debug(f"Using cached validation result for {method}: {is_valid}")
                return is_valid
                
            # Cache expired, remove it
            del self._validation_cache[cache_key]
        
        # For browser methods, we assume they're valid if the browser exists
        if method != 'file':
            self.logger.debug(f"Using browser cookie method: {method}, assuming valid")
            self._validation_cache[cache_key] = (True, time.time())
            return True
        
        # Validate file method
        if not file_path:
            self.errors.append("Cookie file path not provided")
            self.logger.warning("Cookie file path not provided")
            self._validation_cache[cache_key] = (False, time.time())
            return False
            
        result = self._validate_cookie_file(file_path)
        
        # Cache the result
        self._validation_cache[cache_key] = (result, time.time())
        return result
    
    def _validate_cookie_file(self, file_path: str) -> bool:
        """Validate cookie file with minimal checks"""
        self.logger.debug(f"Validating cookie file: {file_path}")
        
        if not os.path.exists(file_path):
            self.errors.append(f"Cookie file not found: {file_path}")
            self.logger.warning(f"Cookie file not found: {file_path}")
            return False
        
        if os.path.getsize(file_path) == 0:
            self.errors.append("Cookie file is empty")
            self.logger.warning("Cookie file is empty")
            return False
        
        # Simplified validation - just check if the file contains youtube.com
        try:
            # Read first few KB to check for YouTube cookies
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(4096)  # Read first 4KB
                
            if 'youtube.com' not in sample:
                self.errors.append("Cookie file does not appear to contain YouTube cookies")
                self.logger.warning("Cookie file doesn't contain YouTube cookies")
                return False
                
            self.logger.debug("Cookie file appears to contain YouTube cookies")
            return True
            
        except Exception as e:
            self.errors.append(f"Could not read cookie file: {e}")
            self.logger.error(f"Could not read cookie file: {e}")
            return False
            
    def get_validation_errors(self) -> List[str]:
        """Get validation error messages"""
        if self.errors:
            self.logger.debug(f"Returning {len(self.errors)} validation errors")
        return self.errors.copy()


class YouTubeCookieValidator:
    """Validates YouTube cookies for authentication"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.YouTubeCookieValidator")
        self.errors: List[str] = []
        self.required_cookies = {"SID", "HSID", "SAPISID"}
        self.logger.debug("YouTube cookie validator initialized")
    
    def validate(self, method: str, file_path: Optional[str] = None, 
                skip_for_quick_mode: bool = False) -> bool:
        """Validate cookies based on method and optional file path"""
        self.errors.clear()
        
        if skip_for_quick_mode:
            self.logger.debug("Skipping full validation for quick mode")
            if method == 'file' and file_path:
                # Minimal validation for quick mode
                if not os.path.exists(file_path):
                    self.errors.append(f"Cookie file not found: {file_path}")
                    return False
                # Just check if the file exists and isn't empty
                if os.path.getsize(file_path) == 0:
                    self.errors.append("Cookie file is empty")
                    return False
                return True
            return True
        
        if method == 'none':
            self.logger.debug("Cookie method 'none' selected, no validation needed")
            return True
        
        if method == 'file':
            if not file_path:
                self.errors.append("Cookie file path not provided")
                self.logger.warning("Cookie file path not provided")
                return False
            return self._validate_cookie_file(file_path)
        
        # For browser methods, we assume they're valid if the browser exists
        self.logger.debug(f"Using browser cookie method: {method}, assuming valid")
        return True
    
    def get_validation_errors(self) -> List[str]:
        """Get validation error messages"""
        if self.errors:
            self.logger.debug(f"Returning {len(self.errors)} validation errors")
        return self.errors.copy()
    
    def _validate_cookie_file(self, file_path: str) -> bool:
        """Validate cookie file contents"""
        self.logger.debug(f"Validating cookie file: {file_path}")
        
        if not os.path.exists(file_path):
            self.errors.append(f"Cookie file not found: {file_path}")
            self.logger.warning(f"Cookie file not found: {file_path}")
            return False
        
        if os.path.getsize(file_path) == 0:
            self.errors.append("Cookie file is empty")
            self.logger.warning("Cookie file is empty")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            self.logger.debug(f"Successfully read cookie file with {len(lines)} lines")
        except Exception as e:
            self.errors.append(f"Could not read cookie file: {e}")
            self.logger.error(f"Could not read cookie file: {e}")
            return False
        
        youtube_cookies = [line for line in lines if "youtube.com" in line]
        if not youtube_cookies:
            self.errors.append("Cookie file does not contain YouTube cookies")
            self.logger.warning("Cookie file does not contain YouTube cookies")
            return False
        
        self.logger.debug(f"Found {len(youtube_cookies)} YouTube cookies")
        
        # Check for required cookies
        present = set()
        for line in youtube_cookies:
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                name = parts[5]
                present.add(name)
        
        missing = self.required_cookies - present
        if missing:
            error_msg = f"Missing required cookies: {', '.join(missing)}"
            self.errors.append(error_msg)
            self.logger.warning(error_msg)
            return False
        
        self.logger.debug("Cookie validation successful")
        return True


class FileNameSanitizer:
    """Sanitizes filenames for filesystem safety"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.FileNameSanitizer")
        
        # Cache to avoid sanitizing same strings repeatedly
        self._sanitize_cache = {}
        self._cache_size_limit = 1000  # Limit cache size to prevent memory issues
        
        self.logger.debug("Filename sanitizer initialized with caching")
    
    def sanitize(self, filename: str) -> str:
        """Sanitize a filename (not a path) for filesystem safety"""
        # Check if this is in cache
        if filename in self._sanitize_cache:
            return self._sanitize_cache[filename]
            
        # Check if this is a path - if so, handle differently
        if os.path.sep in filename:
            self.logger.debug(f"Sanitizing path: {filename}")
            # This is likely a path, not just a filename
            # Split path into components and sanitize each filename component
            # while preserving the path structure
            path_parts = filename.split(os.path.sep)
            sanitized_parts = []
            
            # Process each part of the path, preserving empty parts for absolute paths
            for i, part in enumerate(path_parts):
                # Skip empty parts at the beginning (for absolute paths)
                if i == 0 and not part and os.path.sep == '/':
                    sanitized_parts.append('')
                    continue
                    
                # Skip empty parts that might result from consecutive separators
                if not part:
                    continue
                    
                # Sanitize the part if it's not empty
                sanitized_part = self._sanitize_filename_component(part)
                sanitized_parts.append(sanitized_part)
                
            # Rejoin the path with appropriate separators
            result = os.path.sep.join(sanitized_parts)
            
            # Prune cache if needed
            if len(self._sanitize_cache) >= self._cache_size_limit:
                # Use a simple LRU-like strategy - clear half the cache
                keys_to_remove = list(self._sanitize_cache.keys())[:self._cache_size_limit // 2]
                for key in keys_to_remove:
                    del self._sanitize_cache[key]
                    
            # Cache the result
            self._sanitize_cache[filename] = result
            
            self.logger.debug(f"Sanitized path result: {result}")
            return result
        else:
            # This is just a filename, sanitize directly
            self.logger.debug(f"Sanitizing filename: {filename}")
            result = self._sanitize_filename_component(filename)
            
            # Cache the result
            if len(self._sanitize_cache) < self._cache_size_limit:
                self._sanitize_cache[filename] = result
                
            self.logger.debug(f"Sanitized filename result: {result}")
            return result
            
    def _sanitize_filename_component(self, component: str) -> str:
        """Sanitize a single filename component (not a path)"""
        # Remove invalid characters, but NOT path separators
        invalid_chars = r'\\*?:"<>|'  # Note: removed / from the invalid chars list
        sanitized = re.sub(f'[{re.escape(invalid_chars)}]', "_", component)
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Limit length
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            max_name_length = 200 - len(ext)
            sanitized = name[:max_name_length] + ext
            
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed"
            
        return sanitized


class QualityFormatter:
    """Generates yt-dlp format strings for different qualities"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.QualityFormatter")
        
        self.format_strings = {
            # More flexible format strings that don't require specific codecs
            'best': 'bestvideo+bestaudio/best',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
            'audio_only': 'bestaudio/best'
        }
        
        # Cache for custom format strings
        self._custom_format_cache = {}
        
        self.logger.debug("Quality formatter initialized with format cache")
    
    def get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for given quality"""
        # Check if quality has a predefined format
        if quality in self.format_strings:
            return self.format_strings[quality]
            
        # Check if we have a cached custom format
        if quality in self._custom_format_cache:
            return self._custom_format_cache[quality]
            
        # Generate custom format string
        # Basic pattern: match resolution and get best audio
        custom_format = None
        
        # Try to interpret quality as a resolution
        resolution_match = re.match(r'(\d+)p', quality)
        if resolution_match:
            height = resolution_match.group(1)
            custom_format = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
            self._custom_format_cache[quality] = custom_format
            return custom_format
            
        # Fallback to best if no match
        self.logger.warning(f"Unknown quality '{quality}', using 'best' instead")
        return self.format_strings['best']