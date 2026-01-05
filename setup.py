from setuptools import setup, find_packages

setup(
    name="whatsapp-beacon",
    version="2.0.0",
    description="WhatsApp OSINT Tracker",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "selenium",
        "openpyxl",
        "keyboard",
        "webdriver-manager",
        "pyyaml",
        "colorlog",
    ],
    entry_points={
        "console_scripts": [
            "whatsapp-beacon=whatsapp_beacon.main:main",
        ],
    },
)
