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

    def __getattr__(self, name: str) -> Any:
        # Expose every known config key (e.g. ``config.username``) as a
        # read-only attribute backed by the merged settings dict. ``__getattr__``
        # only fires for names not found via normal lookup, so ``self.config``
        # and real methods are unaffected. Unknown names still raise AttributeError.
        config = self.__dict__.get('config', {})
        if name in config:
            return config[name]
        raise AttributeError(name)
