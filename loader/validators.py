# validators.py - Validation implementations

import os
from typing import List, Optional
import re


class YouTubeCookieValidator:
    """Validates YouTube cookies for authentication"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.required_cookies = {"SID", "HSID", "SAPISID"}
    
    def validate(self, method: str, file_path: Optional[str] = None) -> bool:
        """Validate cookies based on method and optional file path"""
        self.errors.clear()
        
        if method == 'none':
            return True
        
        if method == 'file':
            if not file_path:
                self.errors.append("Cookie file path not provided")
                return False
            return self._validate_cookie_file(file_path)
        
        # For browser methods, we assume they're valid if the browser exists
        return True
    
    def get_validation_errors(self) -> List[str]:
        """Get validation error messages"""
        return self.errors.copy()
    
    def _validate_cookie_file(self, file_path: str) -> bool:
        """Validate cookie file contents"""
        if not os.path.exists(file_path):
            self.errors.append(f"Cookie file not found: {file_path}")
            return False
        
        if os.path.getsize(file_path) == 0:
            self.errors.append("Cookie file is empty")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            self.errors.append(f"Could not read cookie file: {e}")
            return False
        
        youtube_cookies = [line for line in lines if "youtube.com" in line]
        if not youtube_cookies:
            self.errors.append("Cookie file does not contain YouTube cookies")
            return False
        
        # Check for required cookies
        present = set()
        for line in youtube_cookies:
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                name = parts[5]
                present.add(name)
        
        missing = self.required_cookies - present
        if missing:
            self.errors.append(f"Missing required cookies: {', '.join(missing)}")
            return False
        
        return True


class FileNameSanitizer:
    """Sanitizes filenames for filesystem safety"""
    
    def sanitize(self, filename: str) -> str:
        """Remove invalid characters from filename"""
        # Remove invalid characters
        sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized


class QualityFormatter:
    """Generates yt-dlp format strings for different qualities"""
    
    def __init__(self):
        self.format_strings = {
            'best': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            '1080p': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            '720p': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
            '480p': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best',
            'audio_only': 'bestaudio[ext=m4a]/bestaudio'
        }
    
    def get_format_string(self, quality: str) -> str:
        """Get yt-dlp format string for given quality"""
        return self.format_strings.get(quality, self.format_strings['best'])