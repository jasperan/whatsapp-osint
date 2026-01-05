# 🕵️‍♂️ WhatsApp Beacon (OSINT Tracker)

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)

**WhatsApp Beacon** is a powerful, cross-platform OSINT tool designed to track the online status of WhatsApp users. It leverages Selenium and Web WhatsApp to monitor connectivity patterns and generate detailed logs and reports.

> **Disclaimer**: This tool is for educational and research purposes only. Do not use it for stalking or any illegal activities.

---

## ✨ Features

- **Cross-Platform**: Works seamlessly on Windows, Linux, and macOS.
- **Automated Driver Management**: No need to manually download `chromedriver`.
- **Headless Mode**: Run in the background without a visible browser window.
- **Detailed Logging**: Tracks online/offline events with precision.
- **Data Export**: Export session logs to Excel for analysis.
- **Configurable**: Use CLI arguments or a simple `config.yaml` file.
- **Resilient**: Handles network interruptions and browser restarts.

---

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jasperan/whatsapp-osint.git
   cd whatsapp-osint
   ```

2. **Install dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

You can run the tracker using command-line arguments or the configuration file.

### Quick Start

```bash
python3 -m src.whatsapp_beacon.main -u "John Doe"
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-u`, `--username` | The exact WhatsApp username (as saved in your contacts) to track. | Required |
| `-l`, `--language` | Language code of your WhatsApp Web interface (e.g., `en`, `es`, `fr`). | `en` |
| `-e`, `--excel` | Export database logs to an Excel file on startup. | `False` |
| `--headless` | Run in headless mode (no browser window). | `False` |
| `--config` | Path to a custom configuration file. | `config.yaml` |

### Examples

**Track a user with Spanish WhatsApp Web in Headless mode:**
```bash
python3 -m src.whatsapp_beacon.main -u "Maria" -l es --headless
```

**Export data to Excel:**
```bash
python3 -m src.whatsapp_beacon.main -u "John Doe" -e
```

---

## ⚙️ Configuration

You can permanently set your preferences in `config.yaml`:

```yaml
username: "Target Name"
language: "en"
headless: false
excel: false
browser: "chrome"
log_level: "INFO"
data_dir: "data"
```

---

## 📊 Output

- **Logs**: Saved to `logs/whatsapp_beacon.log` and displayed in the console.
- **Database**: All sessions are stored in `data/victims_logs.db`.
- **Excel**: Exported reports are saved as `History_wp.xlsx` (configurable path in code).

---

## 🤖 Headless Mode & Authentication

When running in **Headless Mode** for the first time:
1. The tool will attempt to log in.
2. If not authenticated, it will save a screenshot of the QR code to `qrcode.png`.
3. Open `qrcode.png` and scan it with your phone's WhatsApp.
4. The tool will detect the login and proceed.

*Note: It is easier to run once in non-headless mode to authenticate, as the session is saved in `data/chrome_profile`.*

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🙌 Credits

Original concept developed in 2019. Revamped in 2025 for better performance and usability.
