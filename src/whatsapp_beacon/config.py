from pathlib import Path
from typing import Any, Dict

import yaml


class Config:
    def __init__(self, config_file: str = 'config.yaml') -> None:
        self.config: Dict[str, Any] = self._load_defaults()
        if Path(config_file).exists():
            self.config.update(self._load_from_file(config_file))

    def _load_defaults(self) -> Dict[str, Any]:
        return {
            'username': '',
            'language': 'en',
            'excel': False,
            'headless': False,
            'split_char': '-',
            'browser': 'chrome',
            'log_level': 'INFO',
            'data_dir': 'data',
            'chrome_driver_path': None,
            'chrome_binary_path': None
        }

    def _load_from_file(self, filepath: str) -> Dict[str, Any]:
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as e:
            print(f"Warning: Could not load config file: {e}")
            return {}

    def update_from_args(self, args) -> None:
        """Update config with command line arguments if they are provided (not None)."""
        for key, value in vars(args).items():
            if value is not None:
                self.config[key] = value

    def get(self, key: str) -> Any:
        return self.config.get(key)

    @property
    def username(self): return self.config.get('username')

    @property
    def language(self): return self.config.get('language')

    @property
    def excel(self): return self.config.get('excel')

    @property
    def headless(self): return self.config.get('headless')

    @property
    def browser(self): return self.config.get('browser')

    @property
    def data_dir(self): return self.config.get('data_dir')

    @property
    def chrome_driver_path(self): return self.config.get('chrome_driver_path')

    @property
    def chrome_binary_path(self): return self.config.get('chrome_binary_path')

    @property
    def log_level(self): return self.config.get('log_level')
