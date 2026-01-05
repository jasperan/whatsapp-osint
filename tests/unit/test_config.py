import pytest
import yaml
from argparse import Namespace
from src.whatsapp_beacon.config import Config

class TestConfig:
    def test_default_values(self):
        config = Config(config_file="nonexistent.yaml")
        assert config.language == 'en'
        assert config.headless is False
        assert config.browser == 'chrome'

    def test_load_from_file(self, tmp_path):
        config_file = tmp_path / "test_config.yaml"
        data = {
            'username': 'TestUser',
            'language': 'es',
            'headless': True
        }
        with open(config_file, 'w') as f:
            yaml.dump(data, f)

        config = Config(config_file=str(config_file))
        assert config.username == 'TestUser'
        assert config.language == 'es'
        assert config.headless is True

    def test_args_override_file(self):
        # Use argparse Namespace which vars() works on correctly for this purpose
        args = Namespace(
            username='OverrideUser',
            language=None, # Should not override
            excel=True,
            headless=None
        )

        config = Config(config_file="nonexistent.yaml")
        config.update_from_args(args)

        assert config.username == 'OverrideUser'
        assert config.language == 'en' # Default remains
        assert config.excel is True
