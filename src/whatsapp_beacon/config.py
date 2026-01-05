import os
import yaml
import argparse
from pathlib import Path

class Config:
    def __init__(self, config_file='config.yaml'):
        self.config = self._load_defaults()
        if os.path.exists(config_file):
            self.config.update(self._load_from_file(config_file))
        self._update_from_env()

    def _load_defaults(self):
        return {
            'username': '',
            'language': 'en',
            'excel': False,
            'headless': False,
            'split_char': '-',
            'browser': 'chrome',
            'log_level': 'INFO',
            'data_dir': 'data'
        }

    def _load_from_file(self, filepath):
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            return {}

    def _update_from_env(self):
        # Optional: Load from env vars if needed, e.g., WHATSAPP_USERNAME
        pass

    def update_from_args(self, args):
        """Update config with command line arguments if they are provided (not None)."""
        arg_dict = vars(args)
        for key, value in arg_dict.items():
            if value is not None:
                self.config[key] = value

    def get(self, key):
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
    def log_level(self): return self.config.get('log_level')
