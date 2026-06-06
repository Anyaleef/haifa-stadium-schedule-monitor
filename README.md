# Haifa Stadium Alert

Personal Python automation project that monitors the Haifa Stadium schedule page and sends an alert when new game information is published.


## Status

![Status](https://img.shields.io/badge/status-ongoing-red)


## Why I built this

I live near Haifa Stadium, and on game days the traffic around the area can be a real headache.
Therefore, instead of manually checking the stadium website every day, this project automates the process and notifies me when the schedule page changes.

## What it does

- Checks the official Haifa Stadium (aka סמי עופר) schedule page once per day
- Extracts and cleans the page text
- Creates a hash of the page content
- Compares the current hash with the previous saved hash
- Sends a Telegram notification if a change is detected
- Runs automatically using GitHub Actions

## Tech stack

- Python
- Requests
- BeautifulSoup
- Telegram Bot API
- GitHub Actions

## How it works

The script downloads the stadium schedule page and extracts the visible text.  
It then creates a SHA-256 hash of the cleaned text and compares it with the hash saved from the previous run.

If the hash is different, the script assumes the page was updated and sends a Telegram alert.

## Environment variables

The Telegram credentials are not stored in the code.
They are stored as GitHub Actions secrets:
```Text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Running locally

Install dependencies:
```bash
pip install -r requirements.txt
```
Set the environment variables:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```
Run the script:
```bash
python monitor.py
```

## Automation

The project uses GitHub Actions to run the monitor once per day.
The workflow can also be triggered manually from the GitHub Actions tab.

## Notes

This project detects meaningful page changes rather than parsing each game individually.
A future improvement will be considered, and could extract structured game data such as date, teams, and event time.
