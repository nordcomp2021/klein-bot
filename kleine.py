import time
import os
import threading
import requests
from flask import Flask
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot je aktivan i prati oglase!"

SEARCH_URL = "https://www.kleinanzeigen.de/s-fahrraeder/herren/93326/preis:200:650/fully/k0c217l6231r100+fahrraeder.art_s:herren"
TELEGRAM_BOT_TOKEN = "8688931289:AAEY4gIT7rO-CY85WLM_t8EQPnI5KZ7gK2U"
TELEGRAM_CHAT_ID = "8846679847"

CHECK_INTERVAL = 600
seen_ads = set()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def send_telegram_notification(title, price, link, img_url):
    caption = f"<b>Novi oglas na Kleinanzeigen!</b>\n\n" \
              f"<b>Naslov:</b> {title}\n" \
              f"<b>Cena:</b> {price}\n" \
              f"<b>Link:</b> {link}"

    if img_url and img_url.startswith("http"):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": img_url, "caption": caption, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "HTML"}

    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Greška pri slanju na Telegram: {e}")

def check_kleinanzeigen(is_first_run=False):
    print("Proveravam nove oglase na Kleinanzeigen...")
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.find_all("article", attrs={"data-adid": True})

        if len(articles) == 0:
            print("UPOZORENJE: 0 oglasa pronađeno, čuvam HTML za debug...")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)

        for article in articles:
            try:
                ad_id = article.get("data-adid")
                if not ad_id or ad_id in seen_ads:
                    continue

                href = article.get("data-href")
                link = "https://www.kleinanzeigen.de" + href if href else SEARCH_URL

                title_element = article.find("a", class_="ellipsis")
                title = title_element.text.strip() if title_element else "Bez naslova"

                price_element = article.find("p", class_="text-title3")
                price = price_element.text.strip() if price_element else "Nije navedeno"

                img_element = article.find("img")
                img_url = img_element.get("src") if img_element else None

                seen_ads.add(ad_id)

                if is_first_run:
                    continue

                send_telegram_notification(title, price, link, img_url)
                print(f"Poslat nov oglas: {title}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"Greška pri otvaranju stranice: {e}")

def run_bot():
    try:
        print("Pokrećem prvu proveru...")
        check_kleinanzeigen(is_first_run=True)
        print(f"Učitano {len(seen_ads)} postojećih oglasa.")

        while True:
            time.sleep(CHECK_INTERVAL)
            check_kleinanzeigen(is_first_run=False)
    except Exception as e:
        import traceback
        print(f"KRITIČNA GREŠKA u run_bot: {e}")
        traceback.print_exc()

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)