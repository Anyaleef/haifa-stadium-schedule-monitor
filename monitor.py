import hashlib
import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.haifa-stadium.co.il/%D7%9C%D7%95%D7%97_%D7%94%D7%9E%D7%A9%D7%97%D7%A7%D7%99%D7%9D_%D7%91%D7%90%D7%A6%D7%98%D7%93%D7%99%D7%95%D7%9F/"
HASH_FILE = "last_hash.txt"


def fetch_page_text() -> str:
    response = requests.get(
        URL,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; HaifaStadiumMonitor/1.0)"
        },
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noisy parts that can change without meaning.
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # Focus on the game schedule area if possible.
    start = text.find("לוח המשחקים באצטדיון")
    if start != -1:
        text = text[start:]

    return text.strip()


def calculate_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_old_hash() -> str | None:
    if not os.path.exists(HASH_FILE):
        return None

    with open(HASH_FILE, "r", encoding="utf-8") as file:
        return file.read().strip()


def save_new_hash(new_hash: str) -> None:
    with open(HASH_FILE, "w", encoding="utf-8") as file:
        file.write(new_hash)


def send_telegram_message(message: str) -> None:
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    response = requests.post(
        api_url,
        data={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=20,
    )
    response.raise_for_status()


def main() -> None:
    current_text = fetch_page_text()
    current_hash = calculate_hash(current_text)
    old_hash = read_old_hash()

    if old_hash is None:
        save_new_hash(current_hash)
        print("Initial hash saved. No notification sent.")
        return

    if current_hash != old_hash:
        save_new_hash(current_hash)

        message = (
            "Update detected on the Sami Ofer Stadium game schedule page.\n\n"
            "Check the page:\n"
            f"{URL}"
        )

        send_telegram_message(message)
        print("Change detected. Notification sent.")
    else:
        print("No change detected.")


if __name__ == "__main__":
    main()