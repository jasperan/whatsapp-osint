import logging
import colorlog
import sys
from pathlib import Path

from .private_files import create_private_file, make_private_dir

def setup_logging(log_level="INFO", log_dir="logs"):
    """Sets up the logging configuration."""

    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    make_private_dir(log_path)

    log_file = log_path / "whatsapp_beacon.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicates
    if root_logger.handlers:
        root_logger.handlers = []

    # Console Handler with Colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File Handler
    create_private_file(log_file)
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    return logging.getLogger("WhatsAppBeacon")
