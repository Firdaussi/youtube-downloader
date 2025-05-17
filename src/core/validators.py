import os
import logging
from typing import List, Optional
import re
from src.utils.logging_utils import get_logger

# Get module logger
logger = get_logger(__name__)

class YouTubeCookieValidator:
    """Validates YouTube cookies for authentication"""
    
    def __init__(self):
        # Get class-specific logger
        self.logger = get_logger(f"{__name__}.YouTubeCookieValidator")
        self.errors: List[str] = []
        self.required_cookies = {"SID", "HSID", "SAPISID"}
        self.logger.debug("YouTube cookie validator initialized")
    
    def validate(self, method: str, file_path: Optional[str] = None) -> bool:
        """Validate cookies based on method and optional file path"""
        self.errors.clear()
        
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
        self.logger.debug("Filename sanitizer initialized")
    
    def sanitize(self, filename: str) -> str:
        """Sanitize a filename (not a path) for filesystem safety"""
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
            self.logger.debug(f"Sanitized path result: {result}")
            return result
        else:
            # This is just a filename, sanitize directly
            self.logger.debug(f"Sanitizing filename: {filename}")
            result = self._sanitize_filename_component(filename)
            self.logger.debug(f"Sanitized filename result: {result}")
            return result
            
    def _sanitize_filename_component(self, component: str) -> str:
        """Sanitize a single filename component (not a path)"""
        # Remove invalid characters, but NOT path separators
        invalid_chars = r'\\*?:"<>|'  # Note: removed / from the invalid chars list
        sanitized = re.sub(f'[{re.escape(invalid_chars)}]', "", component)
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 200:
            self.logger.debug(f"Truncating long filename component: {len(component)} chars")
            sanitized = sanitized[:200]
            
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
        self.logger.debug("Quality formatter initialized")
    
    def get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for given quality"""
        if quality not in self.format_strings:
            self.logger.warning(f"Unknown quality '{quality}', using 'best' instead")
            return self.format_strings['best']
            
        self.logger.debug(f"Using format string for quality: {quality}")
        return self.format_strings.get(quality, self.format_strings['best'])