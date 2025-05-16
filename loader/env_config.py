# env_config.py - Environment-based configuration repository

import json
import os
from typing import Dict, Any
from models import DownloadConfig, DownloadQuality
from interfaces import ConfigurationRepository
from environment import env

class EnvironmentConfigRepository(ConfigurationRepository):
    """Configuration repository that uses environment variables with file fallback"""
    
    def __init__(self, config_file: str = "downloader_config.json"):
        self.config_file = config_file
    
    def load_config(self) -> DownloadConfig:
        """Load configuration from environment variables with fallback to file"""
        # Load from file first as fallback
        file_config = self._load_from_file()
        
        # Create config from environment variables
        config = DownloadConfig(
            # System paths
            download_directory=env.get("YOUTUBE_DOWNLOAD_DIR", file_config.download_directory),
            
            # Performance settings
            max_concurrent_downloads=env.get_int("YOUTUBE_MAX_CONCURRENT", file_config.max_concurrent_downloads),
            bandwidth_limit=env.get("YOUTUBE_BANDWIDTH_LIMIT", file_config.bandwidth_limit),
            
            # Quality settings
            default_quality=DownloadQuality(
                env.get("YOUTUBE_DEFAULT_QUALITY", file_config.default_quality.value)
            ),
            
            # Cookie settings
            cookie_method=env.get("YOUTUBE_COOKIE_METHOD", file_config.cookie_method),
            cookie_file=env.get("YOUTUBE_COOKIE_FILE", file_config.cookie_file),
            
            # Retry settings
            retry_count=env.get_int("YOUTUBE_RETRY_COUNT", file_config.retry_count),
            auto_retry_failed=env.get_bool("YOUTUBE_AUTO_RETRY", file_config.auto_retry_failed),
            
            # Other settings
            check_duplicates=env.get_bool("YOUTUBE_CHECK_DUPLICATES", file_config.check_duplicates),
            
            # Output settings (new)
            output_template=env.get("YOUTUBE_OUTPUT_TEMPLATE", file_config.output_template),
            create_playlist_folder=env.get_bool("YOUTUBE_CREATE_PLAYLIST_FOLDER", file_config.create_playlist_folder),
            sanitize_filenames=env.get_bool("YOUTUBE_SANITIZE_FILENAMES", file_config.sanitize_filenames),
            preferred_format=env.get("YOUTUBE_PREFERRED_FORMAT", file_config.preferred_format),
            use_postprocessing=env.get_bool("YOUTUBE_USE_POSTPROCESSING", file_config.use_postprocessing)
        )
        
        return config
    
    def save_config(self, config: DownloadConfig) -> None:
        """Save configuration to file (environment variables cannot be saved)"""
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
            
            # Output settings
            'output_template': config.output_template,
            'create_playlist_folder': config.create_playlist_folder,
            'sanitize_filenames': config.sanitize_filenames,
            'preferred_format': config.preferred_format,
            'use_postprocessing': config.use_postprocessing
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_from_file(self) -> DownloadConfig:
        """Load configuration from file as fallback"""
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