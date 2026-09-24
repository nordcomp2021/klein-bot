import time
import os
import threading
import requests
from flask import Flask
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- FLASK SERVER (Za besplatan Render Web Service) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot je aktivan i prati oglase!"

# --- PODEŠAVANJA ---
SEARCH_URL = "https://www.kleinanzeigen.de/s-fahrraeder/herren/93326/preis:200:650/fully/k0c217l6231r100+fahrraeder.art_s:herren"
TELEGRAM_BOT_TOKEN = "8688931289:AAEY4gIT7rO-CY85WLM_t8EQPnI5KZ7gK2U"
TELEGRAM_CHAT_ID = "8846679847"

CHECK_INTERVAL = 600  # 10 minuta
seen_ads = set()

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

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

def check_kleinanzeigen(driver, is_first_run=False):
    print("Proveravam nove oglase na Kleinanzeigen...")
    try:
        driver.get(SEARCH_URL)
        time.sleep(4)
        articles = driver.find_elements(By.CSS_SELECTOR, "article.aditem")

        for article in articles:
            try:
                ad_id = article.get_attribute("data-adid")
                if not ad_id:
                    continue

                if ad_id not in seen_ads:
                    title_element = article.find_element(By.CSS_SELECTOR, "h2.text-module-header a")
                    title = title_element.text
                    link = title_element.get_attribute("href")

                    try:
                        price = article.find_element(By.CSS_SELECTOR, "p.aditem-main--middle--price-shipping--price").text
                    except:
                        price = "Nije navedeno"

                    try:
                        img_element = article.find_element(By.CSS_SELECTOR, ".imagebox img")
                        img_url = img_element.get_attribute("src")
                    except:
                        img_url = None

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
        print("Pokrećem Selenium driver...")
        driver = setup_driver()
        print("Bot je pokrenut u pozadini...")
        check_kleinanzeigen(driver, is_first_run=True)
        print(f"Učitano {len(seen_ads)} postojećih oglasa.")

        while True:
            time.sleep(CHECK_INTERVAL)
            check_kleinanzeigen(driver, is_first_run=False)
    except Exception as e:
        import traceback
        print(f"KRITIČNA GREŠKA u run_bot: {e}")
        traceback.print_exc()

# Pokrećemo bota u zasebnoj niti (thread)
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
