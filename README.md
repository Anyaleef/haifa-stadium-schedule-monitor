# Haifa Stadium Alert Bot ![Status](https://img.shields.io/badge/status-active-brightgreen)

Personal Python automation project that monitors the Haifa Stadium schedule, detects newly published games, and sends Telegram alerts for schedule updates and game-day reminders.

## Live alerts

Join the Telegram announcement channel to receive stadium schedule updates and game-day reminders:
[Join the Haifa Stadium Alerts channel](YOUR_TELEGRAM_INVITE_LINK)

## Why I built this

I live near Haifa Stadium, where game-day traffic can cause significant congestion and make leaving the area by car difficult.
Instead of manually checking the stadium website every day, this project monitors the schedule automatically and sends notifications when new games are published or when a game is taking place that day.

## What it does

- Checks the official Haifa Stadium (aka סמי עופר) schedule page once per day
- Extracts structured game information, including date, kickoff time, and teams
- Compares the current schedule with the previously stored schedule
- Sends a Telegram alert when new games are published
- Sends a reminder on the morning of each game day
- Prevents duplicate game-day reminders
- Runs automatically using GitHub Actions

## Tech stack

- Python
- Requests
- BeautifulSoup
- Telegram Bot API
- GitHub Actions

## How it works

The script downloads the Haifa Stadium schedule page and uses BeautifulSoup to extract the listed games.
Each game is stored with its date, kickoff time, teams, and competition information. The current schedule is compared with the previously saved schedule in `state.json`.
If new games are detected, the bot sends a Telegram update listing them.
On each daily run, the script also checks whether a game is taking place that day. If so, it sends a morning reminder and records that the reminder was already sent to prevent duplicates.

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
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"
```
Run the script:
```bash
python monitor.py
```

## Automation

The project uses GitHub Actions to run the monitor once per day in the `Asia/Jerusalem` timezone.
The workflow can also be triggered manually from the GitHub Actions tab for testing.

## Project structure

```text
haifa-stadium-schedule-monitor/
│
├── monitor.py
├── requirements.txt
├── state.json
├── README.md
└── .github/
    └── workflows/
        └── daily-check.yml
```

## Notifications

The bot sends two types of Telegram notifications:
- 🟢 Schedule update when one or more new games are published
- 🔴 Game-day reminder on the morning of a scheduled game
