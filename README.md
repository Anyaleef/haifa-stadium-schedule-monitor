# Haifa Stadium Alert Bot ![Status](https://img.shields.io/badge/status-active-brightgreen) ![Use](https://img.shields.io/badge/use-personal%20project-blue)

A personal Python automation project that tracks publicly available Haifa Stadium game schedule information and sends Telegram alerts when relevant schedule information changes.

> [!CAUTION]
> **Disclaimer:** This is an independent, unofficial community project and is not affiliated with or endorsed by Sammy Ofer Stadium.
## Disclaimer

This is an independent, unofficial, private project and is not affiliated with, endorsed by, or operated by Haifa Stadium or Sammy Ofer Stadium.

## Why I built this

Game days at Haifa Stadium can cause significant traffic congestion and road delays in the surrounding area.
Instead of manually checking the stadium website, this project monitors the schedule automatically and sends useful updates through Telegram.

## Live alerts

Join the private Telegram community to receive Haifa Stadium schedule updates, changes, and game-day reminders:
[Haifa Stadium Alerts community](https://t.me/+a9wMn-xBOO81YzBk)

The community is private, and join requests are reviewed before access is granted.
> This is an independent, unofficial community project and is not affiliated with or endorsed by Sammy Ofer Stadium.

## Features

- Checks the official Haifa Stadium schedule page once per day
- Parses individual games into structured data: competition, teams, date, and kickoff time
- Detects newly published games 
- Detects changes to an existing game's date or kickoff time
- Detects future games that disappear from the published schedule, while ignoring removals on or after the scheduled game date
- Handles games whose kickoff time has not yet been published 
- Sends a reminder on the day of a scheduled game
- Sends a Telegram warning if the website cannot be read or parsed correctly
- Stores the latest schedule and a small event history in `state.json`
- Runs automatically using GitHub Actions

## Tech stack

- Python 3.12
- Requests
- BeautifulSoup
- Telegram Bot API
- GitHub Actions

## How it works

The monitor retrieves publicly available game schedule information and converts each listed game into structured data.

Each game is identified using the two teams and the competition name, while its date and kickoff time are treated as details that may change.
On each run, the latest schedule is compared with the previously saved state. The monitor can detect newly added games, changes to existing games, and future games that are no longer listed.

The current state and a limited history of detected events are stored locally for comparison with future runs.

## Telegram notifications

The bot sends different notifications depending on what changed:
- 🟢 New game added
- 🟡 Existing game date or kickoff time changed 
- ⚠️ Future game removed from the published schedule 
- 🔴 Game-day reminder
- 🚨 Monitoring/parsing failure

## Environment variables

The Telegram credentials are not stored in the code.
They are provided through environment variables and configured as GitHub Actions secrets:
```Text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Running locally

Install dependencies:

```bash
pip install -r requirements.txt
```

#### Windows PowerShell

```powershell
$env:TELEGRAM_BOT_TOKEN="your_bot_token"
$env:TELEGRAM_CHAT_ID="your_chat_id"

python monitor.py
```

#### macOS / Linux

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

python monitor.py
```

## Automation

GitHub Actions runs the monitor automatically once per day. The workflow can also be triggered manually from the Actions tab.
The workflow commits changes to `state.json` back to the repository so that each future run can compare the current schedule with the previously observed state.

If the monitor encounters an unexpected error, it attempts to send a Telegram failure notification and then exits with an error so the GitHub Actions run is visibly marked as failed.

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

## Limitations

The parser depends on the structure and wording of the official stadium website.
Significant changes to the site's HTML or schedule format may require an update to the parser.
The monitor is designed to fail visibly rather than silently accept an empty or unreadable schedule.

A competition-name change is treated as a different game identity. In that case, the monitor may report the previous entry as removed and the updated entry as newly added.

## License

This project is licensed under the MIT License.
The MIT License applies only to the original source code in this repository.
Third-party names, trademarks, website content, and other third-party materials remain the property of their respective owners.
