# environment.py - Environment configuration handling

import os
import logging
from typing import Any, Dict, Optional
from pathlib import Path

# Try to import dotenv, with fallback if not installed
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)

class Environment:
    """Manages environment variables with .env file support"""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self._load_environment()
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file if available"""
        if DOTENV_AVAILABLE:
            # Load from .env file if it exists
            env_path = Path(self.env_file)
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                logger.info(f"Loaded environment from {self.env_file}")
            else:
                logger.info(f"Environment file {self.env_file} not found, using system environment")
        else:
            logger.warning("python-dotenv not installed, using system environment only")
            logger.warning("Install with: pip install python-dotenv")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with fallback to default"""
        return os.environ.get(key, default)
    
    def get_path(self, key: str, default: Optional[str] = None) -> Optional[Path]:
        """Get a path from environment variables, ensuring it exists"""
        path_str = self.get(key, default)
        if not path_str:
            return None
            
        path = Path(path_str).expanduser().resolve()
        return path if path.exists() else None
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer environment variable"""
        value = self.get(key)
        try:
            return int(value) if value is not None else default
        except ValueError:
            logger.warning(f"Environment variable {key}={value} is not a valid integer, using default {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean environment variable"""
        value = self.get(key)
        if value is None:
            return default
            
        return value.lower() in ('true', 'yes', '1', 't', 'y')
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables"""
        return dict(os.environ)
    
    def set(self, key: str, value: str) -> None:
        """Set an environment variable"""
        os.environ[key] = value

# Create a global instance
env = Environment()