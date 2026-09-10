import json
import os
import re
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


URL = "https://www.haifa-stadium.co.il/%D7%9C%D7%95%D7%97_%D7%94%D7%9E%D7%A9%D7%97%D7%A7%D7%99%D7%9D_%D7%91%D7%90%D7%A6%D7%98%D7%93%D7%99%D7%95%D7%9F/"
STATE_FILE = "state.json"

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

DATE_PATTERN = re.compile(
    r"\b(\d{2}/\d{2}/(?:\d{2}|\d{4}))\b"
)

TIME_PATTERN = re.compile(
    r"^\d{1,2}:\d{2}$"
)


def fetch_page_lines():
    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HaifaStadiumMonitor/1.0)"
        },
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove parts of the page that are irrelevant to the schedule.
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    lines = []

    for text in soup.stripped_strings:
        cleaned = re.sub(r"\s+", " ", text).strip()

        if cleaned:
            lines.append(cleaned)

    return lines


def get_schedule_section(lines):
    """
    Keep only the part of the page containing the game schedule.
    """

    heading = "לוח המשחקים באצטדיון"

    heading_positions = [
        i for i, line in enumerate(lines)
        if line == heading
    ]

    if not heading_positions:
        raise RuntimeError("Could not find the stadium schedule section.")

    # The page contains the heading more than once.
    # The last occurrence is the one directly before the games.
    start = heading_positions[-1] + 1

    end = len(lines)

    for i in range(start, len(lines)):
        if lines[i].startswith("איך מגיעים לאצטדיון"):
            end = i
            break

    return lines[start:end]


def parse_date(date_text):
    match = DATE_PATTERN.search(date_text)

    if not match:
        return None

    date_string = match.group(1)

    if len(date_string.split("/")[-1]) == 2:
        date_object = datetime.strptime(date_string, "%d/%m/%y")
    else:
        date_object = datetime.strptime(date_string, "%d/%m/%Y")

    return {
        "iso": date_object.strftime("%Y-%m-%d"),
        "display": date_object.strftime("%d/%m/%Y"),
    }


def extract_games(schedule_lines):
    games = []

    for i, line in enumerate(schedule_lines):
        parsed_date = parse_date(line)

        if not parsed_date:
            continue

        if i < 2:
            continue

        competition = schedule_lines[i - 2]
        team1 = schedule_lines[i - 1]

        time = None
        team2_index = i + 1

        if i + 1 < len(schedule_lines):
            possible_time = schedule_lines[i + 1]

            if TIME_PATTERN.fullmatch(possible_time):
                time = possible_time
                team2_index = i + 2

        if team2_index >= len(schedule_lines):
            continue

        team2 = schedule_lines[team2_index]

        games.append(
            {
                "date": parsed_date["iso"],
                "display_date": parsed_date["display"],
                "time": time,
                "team1": team1,
                "team2": team2,
                "competition": competition,
            }
        )

    return games


def game_id(game):
    """
    Identifies a game independently of its time.

    If the stadium changes only the kickoff time,
    we still recognize it as the same game.
    """

    return (
        f"{game['date']}|"
        f"{game['team1']}|"
        f"{game['team2']}"
    )


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )


def send_telegram_message(message):
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    api_url = (
        f"https://api.telegram.org/bot"
        f"{bot_token}/sendMessage"
    )

    response = requests.post(
        api_url,
        data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )

    response.raise_for_status()


def format_new_games_message(games):
    message = (
        "🟢 <b>עדכון</b>\n"
        "זוהו משחקים חדשים בלוח:\n"
    )

    for number, game in enumerate(games, start=1):
        time = game["time"] or "שעה טרם פורסמה"

        message += (
            f"\n{number}. {escape(game['display_date'])}\n"
            f"   {escape(time)}\n"
            f"   {escape(game['team1'])} vs "
            f"{escape(game['team2'])}\n"
        )

    return message


def format_today_reminder(game):
    date = escape(game["display_date"])
    team1 = escape(game["team1"])
    team2 = escape(game["team2"])

    if game["time"]:
        time_line = (
            f"היום <b>{date}</b> "
            f"בשעה <b>{escape(game['time'])}</b>"
        )
    else:
        time_line = (
            f"היום <b>{date}</b>\n"
            "שעת המשחק טרם פורסמה"
        )

    return (
        "🔴 <b>תזכורת!</b>\n"
        f"{time_line}\n"
        "יש משחק באצטדיון סמי עופר\n"
        f"{team1} vs {team2}"
    )


def main():
    lines = fetch_page_lines()
    schedule_lines = get_schedule_section(lines)
    current_games = extract_games(schedule_lines)

    print(f"Found {len(current_games)} games.")

    if not current_games:
        raise RuntimeError(
            "No games were detected. "
            "The website structure may have changed."
        )

    state = load_state()

    # First run of the new system:
    # save the existing schedule as the baseline.
    if state is None:
        state = {
            "games": current_games,
            "reminders_sent": [],
        }

        save_state(state)

        print(
            f"Initial baseline saved with "
            f"{len(current_games)} games."
        )

    else:
        previous_ids = {
            game_id(game)
            for game in state.get("games", [])
        }

        new_games = [
            game
            for game in current_games
            if game_id(game) not in previous_ids
        ]

        if new_games:
            send_telegram_message(
                format_new_games_message(new_games)
            )

            print(
                f"Sent new-game notification for "
                f"{len(new_games)} game(s)."
            )

        else:
            print("No new games detected.")

        # Always update stored schedule.
        # This also captures changes to kickoff times.
        state["games"] = current_games

        save_state(state)

    # ----- Today's reminder -----

    today = datetime.now(ISRAEL_TZ).date().isoformat()

    reminders_sent = set(
        state.get("reminders_sent", [])
    )

    todays_games = [
        game
        for game in current_games
        if game["date"] == today
    ]

    for game in todays_games:
        reminder_id = game_id(game)

        if reminder_id in reminders_sent:
            print(
                f"Reminder already sent for "
                f"{game['team1']} vs {game['team2']}."
            )
            continue

        send_telegram_message(
            format_today_reminder(game)
        )

        reminders_sent.add(reminder_id)

        state["reminders_sent"] = list(reminders_sent)

        save_state(state)

        print(
            f"Sent today's reminder for "
            f"{game['team1']} vs {game['team2']}."
        )


if __name__ == "__main__":
    main()