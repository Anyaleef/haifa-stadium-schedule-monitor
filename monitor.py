import json
import os
import re
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo
from copy import deepcopy

import requests
from bs4 import BeautifulSoup

# CONSTANTS
URL = "https://www.haifa-stadium.co.il/%D7%9C%D7%95%D7%97_%D7%94%D7%9E%D7%A9%D7%97%D7%A7%D7%99%D7%9D_%D7%91%D7%90%D7%A6%D7%98%D7%93%D7%99%D7%95%D7%9F/"
STATE_FILE = "state.json"
MAX_HISTORY_ENTRIES = 100

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")

DATE_PATTERN = re.compile(
    r"\b(\d{2}/\d{2}/(?:\d{2}|\d{4}))\b"
)

TIME_PATTERN = re.compile(
    r"^\d{1,2}:\d{2}$"
)

# WEBSITE PARSING
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

    # remove page elements unrelated to the game schedule
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
        "display": date_object.strftime("%d.%m.%Y"),
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

def normalize_text(text):
    return re.sub(r"\s+", " ", text.strip().lower())

def game_id(game):
    """
    Identifies a game independently of its time.
    If the stadium changes the kickoff time or date, it's still recognized it as the same game.
    """

    return (
        f"{normalize_text(game['team1'])}|"
        f"{normalize_text(game['team2'])}|"
        f"{normalize_text(game['competition'])}"
    )

def find_changes(old_game, new_game):
    changes = {}

    for field in ["date", "time"]:
        if old_game.get(field) != new_game.get(field):
            changes[field] = {
                "old": old_game.get(field),
                "new": new_game.get(field),
            }

    return changes


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE, "r", encoding="utf-8") as file:
        state = json.load(file)

    state.setdefault("games", [])
    state.setdefault("reminders_sent", [])
    state.setdefault("history", [])

    return state


def save_state(state):
    state["history"] = state.get("history", [])[-MAX_HISTORY_ENTRIES:]
    with open(STATE_FILE, "w", encoding="utf-8") as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
        )


def add_history(state, event_type, **data):
    event = {
        "detected_at": datetime.now(
            ISRAEL_TZ
        ).isoformat(timespec="seconds"),
        "type": event_type,
        **data,
    }

    state.setdefault("history", []).append(event)



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
    count = len(games)

    if count == 1:
        intro = "נוסף משחק חדש ללוח:"
    else:
        intro = f"נוספו {count} משחקים חדשים ללוח:"

    message = (
        "🟢 <b>עדכון לוח המשחקים</b>\n\n"
        f"{intro}\n"
    )

    for number, game in enumerate(games, start=1):
        time = game["time"] or "שעה טרם פורסמה"

        message += (
            f"\n<b>{number}. "
            f"{escape(game['team1'])} נגד "
            f"{escape(game['team2'])}</b>\n"
            f"🏆 {escape(game['competition'])}\n"
            f"📅 {escape(game['display_date'])}\n"
            f"🕗 {escape(time)}\n"
        )

    message += (
            "\n🔗 <a href=\""
            + URL
            + "\">לוח המשחקים באתר סמי עופר</a>"
    )

    return message


def format_changed_games_message(changed_games):
    message = "🟡 <b>שינוי בלוח המשחקים</b>\n"

    for number, item in enumerate(changed_games, start=1):
        old_game = item["old"]
        new_game = item["new"]
        changes = item["changes"]

        old_time = old_game["time"] or "שעה טרם פורסמה"
        new_time = new_game["time"] or "שעה טרם פורסמה"

        message += (
            f"\n<b>{number}. "
            f"{escape(new_game['team1'])} נגד "
            f"{escape(new_game['team2'])}</b>\n"
            f"🏆 {escape(new_game['competition'])}\n"
        )

        if "date" in changes:
            message += (
                f"📅 {escape(old_game['display_date'])} → "
                f"<b>{escape(new_game['display_date'])}</b>\n"
            )
        else:
            message += f"📅 {escape(new_game['display_date'])}\n"

        if "time" in changes:
            message += (
                f"🕗 {escape(old_time)} → "
                f"<b>{escape(new_time)}</b>\n"
            )
        else:
            message += f"🕗 {escape(new_time)}\n"

    return message


def format_removed_games_message(games):
    message = (
        "⚠️ <b>שינוי בלוח המשחקים</b>\n\n"
        "המשחקים הבאים אינם מופיעים עוד בלוח באתר:\n"
    )

    for number, game in enumerate(games, start=1):
        time = game["time"] or "שעה טרם פורסמה"

        message += (
            f"\n<b>{number}. "
            f"{escape(game['team1'])} נגד "
            f"{escape(game['team2'])}</b>\n"
            f"🏆 {escape(game['competition'])}\n"
            f"📅 {escape(game['display_date'])}\n"
            f"🕗 {escape(time)}\n"
        )

    message += (
        "\n<i>הסרה מהאתר אינה בהכרח מעידה "
        "על ביטול המשחק.</i>"
    )

    return message


def format_failure_message(error):
    error_text = str(error)

    if len(error_text) > 500:
        error_text = error_text[:500] + "..."

    return (
        "🚨 <b>עמכם הסליחה</b>\n\n"
        "עלתה שגיאה בניסיון קריאת לוח המשחקים.\n"
        "ייתכן שמבנה האתר השתנה או שהאתר אינו זמין כרגע.\n\n"
        "אנו בודקים כעת את מקור התקלה ופועלים לטפל בה בהקדם.\n\n"
        f"<code>{escape(error_text)}</code>"
    )


def format_today_reminder(game):
    date = escape(game["display_date"])
    team1 = escape(game["team1"])
    team2 = escape(game["team2"])

    if game["time"]:
        time = escape(game["time"])
    else:
        time = "שעה טרם פורסמה"

    return (
        "🔴 <b>תזכורת למשחק היום</b>\n\n"
        f"<b>{team1} נגד {team2}</b>\n\n"
        f"🏆 {escape(game['competition'])}\n"
        f"📅 {date}\n"
        f"🕗 {time}\n"
        "📍 אצטדיון סמי עופר\n\n"
        "מומלץ להיערך לעומסי תנועה באזור."
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

    # First run: save current schedule as baseline
    if state is None:
        state = {
            "games": current_games,
            "reminders_sent": [],
            "history": [],
        }

        add_history(
            state,
            "baseline_created",
            games_detected=len(current_games),
        )

        save_state(state)

        print(
            f"Initial baseline saved with "
            f"{len(current_games)} games."
        )

    else:
        previous_games = state.get("games", [])

        previous_index = {
            game_id(game): game
            for game in previous_games
        }

        current_index = {
            game_id(game): game
            for game in current_games
        }

        previous_ids = set(previous_index)
        current_ids = set(current_index)

        # ----- New games -----

        new_ids = current_ids - previous_ids

        new_games = [
            current_index[game_key]
            for game_key in new_ids
        ]

        new_games.sort(
            key=lambda game: game["date"]
        )

        if new_games:
            send_telegram_message(
                format_new_games_message(new_games)
            )

            for game in new_games:
                add_history(
                    state,
                    "game_added",
                    game=deepcopy(game),
                )

            print(
                f"Sent new-game notification for "
                f"{len(new_games)} game(s)."
            )

        else:
            print("No new games detected.")

        # ----- Changed games -----

        changed_games = []

        for game_key in current_ids & previous_ids:
            old_game = previous_index[game_key]
            new_game = current_index[game_key]

            changes = find_changes(
                old_game,
                new_game,
            )

            if changes:
                changed_games.append(
                    {
                        "old": old_game,
                        "new": new_game,
                        "changes": changes,
                    }
                )

        changed_games.sort(
            key=lambda item: item["new"]["date"]
        )

        if changed_games:
            send_telegram_message(
                format_changed_games_message(
                    changed_games
                )
            )

            for item in changed_games:
                add_history(
                    state,
                    "game_changed",
                    before=deepcopy(item["old"]),
                    after=deepcopy(item["new"]),
                    changes=deepcopy(
                        item["changes"]
                    ),
                )

            print(
                f"Detected {len(changed_games)} "
                f"changed game(s)."
            )

        else:
            print("No game changes detected.")

        # ----- Removed games -----

        today = datetime.now(
            ISRAEL_TZ
        ).date().isoformat()

        removed_ids = previous_ids - current_ids

        removed_games = [
            previous_index[game_key]
            for game_key in removed_ids
            if previous_index[game_key]["date"] > today
        ]

        removed_games.sort(
            key=lambda game: game["date"]
        )

        if removed_games:
            send_telegram_message(
                format_removed_games_message(
                    removed_games
                )
            )

            for game in removed_games:
                add_history(
                    state,
                    "game_removed",
                    game=deepcopy(game),
                )

            print(
                f"Detected {len(removed_games)} "
                f"removed future game(s)."
            )

        else:
            print("No future games were removed.")

        # Always update stored schedule
        state["games"] = current_games

        save_state(state)

    # ----- Today's reminder -----

    today = datetime.now(
        ISRAEL_TZ
    ).date().isoformat()

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
                f"{game['team1']} vs "
                f"{game['team2']}."
            )
            continue

        send_telegram_message(
            format_today_reminder(game)
        )

        reminders_sent.add(reminder_id)

        state["reminders_sent"] = list(
            reminders_sent
        )

        add_history(
            state,
            "game_day_reminder_sent",
            game=deepcopy(game),
        )

        save_state(state)

        print(
            f"Sent today's reminder for "
            f"{game['team1']} vs "
            f"{game['team2']}."
        )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(f"Monitor failed: {error}")

        try:
            send_telegram_message(
                format_failure_message(error)
            )
        except Exception as telegram_error:
            print(
                "Could not send Telegram failure alert: "
                f"{telegram_error}"
            )

        raise