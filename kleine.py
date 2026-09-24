import os
import time
import threading
import requests
from flask import Flask
from bs4 import BeautifulSoup

# Inicijalizacija Flask aplikacije za hosting
app = Flask(__name__)

# Preuzimanje poverljivih podataka iz Environment varijabli
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SEARCH_URL = "https://www.kleinanzeigen.de/s-fahrraeder/herren/93326/preis:200:650/fully/k0c217l6231r100+fahrraeder.art_s:herren"
CHECK_INTERVAL = 600  # 10 minuta
seen_ads = set()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

@app.route('/')
def home():
    return "Bot je aktivan i prati oglase na Kleinanzeigen-u!"

def send_telegram_notification(title, price, link, img_url):
    """Slanje obaveštenja na Telegram sa slikom ili kao tekst."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Greška: TELEGRAM_BOT_TOKEN ili TELEGRAM_CHAT_ID nisu postavljeni u okruženju!")
        return

    caption = (
        f"<b>🔔 Novi oglas na Kleinanzeigen!</b>\n\n"
        f"<b>Naslov:</b> {title}\n"
        f"<b>Cena:</b> {price}\n"
        f"<b>Link:</b> <a href='{link}'>Otvori oglas</a>"
    )

    if img_url and img_url.startswith("http"):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": img_url, "caption": caption, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": caption, "parse_mode": "HTML"}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Greška pri slanju na Telegram: {e}")

def check_kleinanzeigen(is_first_run=False):
    print("Proveravam nove oglase na Kleinanzeigen...")
    try:
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"Greška pri pristupu sajtu. Status kod: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        articles = soup.find_all("article", attrs={"data-adid": True})

        if len(articles) == 0:
            print("UPOZORENJE: 0 oglasa pronađeno.")
            return

        for article in articles:
            try:
                ad_id = article.get("data-adid")
                if not ad_id or ad_id in seen_ads:
                    continue

                # 1. PRONALAŽENJE LINKA I NASLOVA
                # Kleinanzeigen uglavnom drži naslov unutar h2 -> a ili klase .ellipsis / .text-module-title
                link_element = (
                    article.find("a", class_="ellipsis") or 
                    article.find("h2") or 
                    article.select_one("a[href*='/s-anzeige/']")
                )

                if not link_element:
                    continue  # Preskoči ako nije pravi oglas (reklama/baner)

                # Ako je unutar h2 našao <h2><a>Naslov</a></h2>
                if link_element.name == "h2" and link_element.find("a"):
                    link_element = link_element.find("a")

                title = link_element.text.strip()
                href = link_element.get("href") or article.get("data-href")

                if not href or not title:
                    continue  # Preskačemo prazne oglase / reklame

                link = "https://www.kleinanzeigen.de" + href if href.startswith("/") else href

                # 2. PRONALAŽENJE CENE
                price_element = (
                    article.find("p", class_="aditem-main--middle--price-shipping--price") or 
                    article.find("p", class_="text-title3") or
                    article.select_one(".aditem-main--middle--price-shipping")
                )
                
                price = price_element.text.strip() if price_element else "Nije navedeno"
                # Čišćenje duplih razmaka u ceni ako ih ima
                price = " ".join(price.split())

                # 3. PRONALAŽENJE SLIKE
                img_element = article.find("img")
                img_url = None
                if img_element:
                    # Nekada je slika u src, a nekada u data-src (lazy-loading)
                    img_url = img_element.get("src") or img_element.get("data-src")

                seen_ads.add(ad_id)

                if is_first_run:
                    continue

                send_telegram_notification(title, price, link, img_url)
                print(f"Poslat nov oglas: {title} ({price})")

            except Exception as e:
                print(f"Greška pri obradi pojedinačnog oglasa: {e}")
                continue

    except Exception as e:
        print(f"Greška pri mrežnom zahtevu: {e}")

def run_bot():
    print("Pokrećem prvu proveru...")
    check_kleinanzeigen(is_first_run=True)
    print(f"Učitano {len(seen_ads)} postojećih oglasa.")

    while True:
        time.sleep(CHECK_INTERVAL)
        check_kleinanzeigen(is_first_run=False)

# Pokretanje bota u pozadinskom nitu (background thread)
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)