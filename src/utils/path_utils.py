# src/utils/path_utils.py

import os
import re
import logging
import platform
from pathlib import Path
from typing import Tuple

# Get a logger for this module
logger = logging.getLogger(__name__)

class PathUtils:
    """Centralized utilities for path handling and validation"""
    
    # Constants for path limitations
    MAX_PATH_LENGTH_WINDOWS = 240  # Windows has 260 char limit, leaving buffer
    MAX_PATH_LENGTH_UNIX = 4096  # Most Unix systems
    MAX_FILENAME_LENGTH = 200
    
    @staticmethod
    def get_max_path_length() -> int:
        """Get maximum path length based on platform"""
        if platform.system() == "Windows":
            return PathUtils.MAX_PATH_LENGTH_WINDOWS
        return PathUtils.MAX_PATH_LENGTH_UNIX
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a single filename component (not a path)"""
        # Remove invalid characters for cross-platform compatibility
        invalid_chars = r'\\/*?:"<>|'
        sanitized = re.sub(f'[{re.escape(invalid_chars)}]', "_", filename)
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Limit filename length
        if len(sanitized) > PathUtils.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(sanitized)
            max_name_length = PathUtils.MAX_FILENAME_LENGTH - len(ext)
            sanitized = name[:max_name_length] + ext
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed"
            
        return sanitized
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitize a full path while preserving structure"""
        if not path:
            return ""
            
        # Normalize path separators
        path = os.path.normpath(path)
        
        # Split path into components
        parts = Path(path).parts
        
        # Sanitize each non-drive part
        sanitized_parts = []
        for i, part in enumerate(parts):
            # Skip drive part on Windows (e.g., 'C:')
            if i == 0 and platform.system() == "Windows" and part.endswith(':'):
                sanitized_parts.append(part)
                continue
                
            # Skip root directory
            if part == '/' or part == '\\':
                sanitized_parts.append(part)
                continue
                
            # Sanitize regular part
            sanitized_parts.append(PathUtils.sanitize_filename(part))
            
        # Rebuild path
        sanitized_path = os.path.join(*sanitized_parts) if sanitized_parts else ""
        
        # Handle absolute paths
        if path.startswith(('/', '\\')) or (len(path) > 1 and path[1] == ':'):
            if not sanitized_path.startswith(('/', '\\')) and not (len(sanitized_path) > 1 and sanitized_path[1] == ':'):
                # Restore the leading separator for Unix or drive letter for Windows
                if platform.system() == "Windows" and len(parts) > 0 and parts[0].endswith(':'):
                    sanitized_path = parts[0] + os.sep + sanitized_path
                else:
                    sanitized_path = os.sep + sanitized_path
        
        return sanitized_path
    
    @staticmethod
    def validate_path(path: str) -> Tuple[bool, str]:
        """Validate a path for length and accessibility"""
        if not path:
            return False, "Empty path"
            
        # Normalize path
        try:
            path = os.path.abspath(os.path.normpath(path))
        except Exception as e:
            return False, f"Invalid path format: {e}"
            
        # Check path length
        max_length = PathUtils.get_max_path_length()
        if len(path) > max_length:
            return False, f"Path too long ({len(path)} chars). Maximum is {max_length}."
            
        # Check if drive/root exists
        try:
            drive_or_root = os.path.splitdrive(path)[0]
            if drive_or_root and not os.path.exists(drive_or_root):
                return False, f"Drive or root path does not exist: {drive_or_root}"
        except Exception:
            pass  # Skip if we can't check drive
        
        # All checks passed
        return True, "Path is valid"
    
    @staticmethod
    def ensure_directory(path: str) -> Tuple[bool, str]:
        """Ensure a directory exists, creating it if needed"""
        if not path:
            return False, "Empty path"
            
        try:
            os.makedirs(path, exist_ok=True)
            
            # Verify we can write to the directory
            if not os.access(path, os.W_OK):
                return False, f"Directory exists but is not writable: {path}"
                
            # Try to create a test file to confirm write access
            test_path = os.path.join(path, ".write_test")
            try:
                with open(test_path, 'w') as f:
                    f.write("test")
                os.remove(test_path)
            except Exception as e:
                return False, f"Directory exists but write test failed: {e}"
                
            return True, "Directory is ready"
            
        except Exception as e:
            return False, f"Failed to create directory: {e}"
    
    @staticmethod
    def get_safe_path(base_dir: str, relative_path: str) -> str:
        """Create a safe path by joining base_dir with sanitized relative_path"""
        # Sanitize relative path to prevent directory traversal
        sanitized_rel_path = PathUtils.sanitize_path(relative_path)
        
        # Remove any leading slashes, drive letters, or parent directory references
        sanitized_rel_path = re.sub(r'^[/\\]|^[A-Za-z]:|\.\.', '', sanitized_rel_path)
        
        # Join with base directory
        full_path = os.path.normpath(os.path.join(base_dir, sanitized_rel_path))
        
        # Ensure the joined path starts with base_dir (preventing directory traversal)
        base_abs = os.path.abspath(base_dir)
        if not os.path.commonpath([base_abs, full_path]).startswith(base_abs):
            # If attempting to escape base_dir, return a path in the base_dir
            return os.path.join(base_dir, "INVALID_PATH")
        
        return full_path
    
    @staticmethod
    def resolve_output_path(base_dir: str, playlist_title: str, output_template: str) -> str:
        """Resolve full output path with proper playlist folder handling"""
        # Sanitize playlist title
        safe_title = PathUtils.sanitize_filename(playlist_title)
        
        # Create playlist folder path
        playlist_folder = os.path.join(base_dir, safe_title)
        
        # Validate the path
        valid, message = PathUtils.validate_path(playlist_folder)
        if not valid:
            logger.warning(f"Invalid playlist folder path: {message}")
            # Fall back to base directory with modified name
            safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
            playlist_folder = os.path.join(base_dir, safe_title)
        
        # Add template to create full path
        if '%(playlist_index)' in output_template or '%(title)' in output_template:
            # Template already contains formatting placeholders
            full_path = os.path.join(playlist_folder, output_template)
        else:
            # Add default placeholders if none exist
            full_path = os.path.join(playlist_folder, "%(playlist_index)02d-%(title)s.%(ext)s")
        
        return full_path