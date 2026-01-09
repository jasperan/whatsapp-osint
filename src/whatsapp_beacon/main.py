import argparse
import sys
from .config import Config
from .beacon import WhatsAppBeacon
from .logger import setup_logging

def main():
    parser = argparse.ArgumentParser(description="WhatsApp OSINT Tracker")
    parser.add_argument('-u', '--username', help='Username to track')
    parser.add_argument('-l', '--language', help='Language code (en, es, etc.)')
    parser.add_argument('-e', '--excel', help="Export DB to Excel", action='store_true')
    parser.add_argument('--headless', help="Run in headless mode", action='store_true')
    parser.add_argument('--config', help="Path to config file", default='config.yaml')

    args = parser.parse_args()

    # Load configuration
    config = Config(config_file=args.config)
    config.update_from_args(args)

    # Setup Logging
    setup_logging(log_level=config.log_level)

    # Check requirements
    if not config.username:
        print("Error: Username is required. Set it in config.yaml or use --username.")
        parser.print_help()
        sys.exit(1)

    # Run Beacon
    beacon = WhatsAppBeacon(config)
    beacon.run()

if __name__ == '__main__':
    main()
