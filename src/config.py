"""Configuration management."""

import yaml
from pathlib import Path
from typing import Dict, Any

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\n"
                "Copy config.example.yaml to config.yaml and edit it."
            )
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    def get(self, key: str, default=None):
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    @property
    def sabnzbd_url(self) -> str:
        return self.get('sabnzbd.url', 'http://localhost:8080')
    
    @property
    def sabnzbd_api_key(self) -> str:
        return self.get('sabnzbd.api_key', '')
    
    @property
    def tv_path(self) -> Path:
        return Path(self.get('paths.tv_shows', ''))
    
    @property
    def movies_path(self) -> Path:
        return Path(self.get('paths.movies', ''))
    
    @property
    def backup_path(self) -> Path:
        return Path(self.get('paths.backup', ''))
    
    @property
    def database_path(self) -> Path:
        return Path(self.get('paths.database', './data/medialibrary.db'))
    
    @property
    def min_resolution(self) -> int:
        return self.get('quality.min_resolution', 1080)

config = Config()
