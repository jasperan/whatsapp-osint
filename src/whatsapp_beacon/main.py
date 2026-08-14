import argparse
import sys
from pathlib import Path
from .analytics import AnalyticsDashboard
from .config import Config
from .beacon import WhatsAppBeacon
from .database import Database
from .db_to_excel import export_json
from .logger import setup_logging

def main():
    parser = argparse.ArgumentParser(description="WhatsApp OSINT Tracker")
    parser.add_argument('-u', '--username', help='Username to track')
    parser.add_argument('-l', '--language', help='Language code (en, es, etc.)')
    parser.add_argument('-e', '--excel', help="Export DB to Excel", action='store_true')
    parser.add_argument('--headless', help="Run in headless mode", action='store_true')
    parser.add_argument('--chrome-driver-path', dest='chrome_driver_path',
                        help="Path to chromedriver binary (default: auto-detect)")
    parser.add_argument('--chrome-binary-path', dest='chrome_binary_path',
                        help="Path to the Chrome/Chromium browser binary (default: auto-detect)")
    parser.add_argument('--analytics', help="Generate the analytics dashboard and exit", action='store_true')
    parser.add_argument('--analytics-output', dest='analytics_output', default='analytics/index.html',
                        help="Output path for the analytics dashboard HTML file")
    parser.add_argument('--export-json', dest='export_json', default=None,
                        help="Export sessions and presence signals to a JSON file and exit (no browser needed)")
    parser.add_argument('--last-seen', dest='last_seen', action='store_true',
                        help="Print the latest presence signal per contact and exit (no browser needed)")
    parser.add_argument('--config', help="Path to config file", default='config.yaml')

    args = parser.parse_args()

    config = Config(config_file=args.config)
    config.update_from_args(args)

    setup_logging(log_level=config.log_level)

    if args.analytics:
        db_path = Path(config.data_dir) / 'victims_logs.db'
        dashboard = AnalyticsDashboard(db_path=str(db_path), output_file=args.analytics_output)
        output_path = dashboard.export()
        print(f"Analytics dashboard written to {output_path}")
        sys.exit(0)

    if args.export_json:
        db_path = Path(config.data_dir) / 'victims_logs.db'
        output_path = export_json(db_path=str(db_path), output_path=args.export_json)
        print(f"JSON export written to {output_path}")
        sys.exit(0)

    if args.last_seen:
        db_path = Path(config.data_dir) / 'victims_logs.db'
        latest = Database(db_path=str(db_path)).get_latest_presence_by_user()
        if not latest:
            print("No presence data recorded yet. Run the tracker once to start collecting.")
            sys.exit(0)
        filter_name = (config.username or '').strip()
        for name in sorted(latest):
            if filter_name and name != filter_name:
                continue
            snapshot = latest[name]
            print(f"{name}: {snapshot['status_text']} (observed {snapshot['observed_at']})")
        sys.exit(0)

    if not config.username:
        print("Error: Username is required. Set it in config.yaml or use --username.")
        parser.print_help()
        sys.exit(1)

    beacon = WhatsAppBeacon(config)
    beacon.run()

if __name__ == '__main__':
    main()
