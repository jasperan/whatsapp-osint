# WhatsApp OSINT Tool

## TikTok Tutorial (Spanish)

https://user-images.githubusercontent.com/20752424/222984331-4928e06d-7da1-4521-8f2a-37cbb2a4f0cc.mp4

Video credits go to [linkfydev](https://www.instagram.com/linkfydev/) (thanks for the awesome explanation).

## Example

![example](./img/doc1.PNG?raw=true)

Welcome to the first WhatsApp OSINT tool. This was developed in early 2019 but I decided to restart the project now for fun. 

# How to Install

First, install requirements:

```
pip install -r requirements.txt
```

- You will need chromedriver, or you can modify the code and use GeckoDriver or any other drivers for Selenium.
- You will need a GUI to execute the code since it interacts with web.whatsapp.com to get statuses
- Replace the name in the file with whichever name you want to track

# How to Run

```
python3 whatsappbeacon.py --username <username_to_track> --language "<language_code>"
```

where language_code is either 'en' or 'es' for English and Spanish languages. Future language support will be added.

# Credits

This tool was developed by myself in my free time. It's a tool that demonstrates the power of Selenium and web scraping. I don't endorse using this tool for stalking people or any other fraudulent purposes. If you have suggestions on how to expand or improve the functionality, please submit a PR and I'll gladly review changes

[jasperan](https://github.com/jasperan)
