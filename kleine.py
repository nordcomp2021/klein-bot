import re
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
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--window-size=1024,768")
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

        try:
            accept_button = driver.find_element(By.ID, "gdpr-banner-accept")
            accept_button.click()
            print("Cookie banner prihvaćen.")
            time.sleep(2)
        except Exception:
            print("Cookie banner nije pronađen (možda već prihvaćen).")

        ad_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/s-anzeige/']")

        if len(ad_links) == 0:
            print("UPOZORENJE: 0 oglasa pronađeno, čuvam screenshot i HTML za debug...")
            driver.save_screenshot("debug_screenshot.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        seen_ids_this_run = set()

        for link in ad_links:
            try:
                href = link.get_attribute("href")
                if not href or "/s-anzeige/" not in href:
                    continue

                # Izvuci jedinstveni ID oglasa iz linka
                match = re.search(r"/s-anzeige/[^/]+/(\d+)-", href)
                if not match:
                    continue
                ad_id = match.group(1)

                # Preskoči duplikate u istom krugu (isti oglas se ponekad linkuje 2x - slika i naslov)
                if ad_id in seen_ids_this_run:
                    continue
                seen_ids_this_run.add(ad_id)

                if ad_id in seen_ads:
                    continue

                title = link.text.strip()
                if not title:
                    continue

                # Pokušaj da nađeš cenu u blizini linka
                price = "Nije navedeno"
                try:
                    price_element = link.find_element(
                        By.XPATH,
                        "ancestor::*[.//p[contains(@class,'text-title3')]][1]//p[contains(@class,'text-title3')]"
                    )
                    price = price_element.text.strip()
                except Exception:
                    pass

                # Pokušaj da nađeš sliku u blizini linka
                img_url = None
                try:
                    img_element = link.find_element(By.XPATH, "ancestor::article[1]//img")
                    img_url = img_element.get_attribute("src")
                except Exception:
                    pass

                seen_ads.add(ad_id)

                if is_first_run:
                    continue

                send_telegram_notification(title, price, href, img_url)
                print(f"Poslat nov oglas: {title}")

            except Exception as e:
                continue

    except Exception as e:
        print(f"Greška pri otvaranju stranice: {e}")

def run_bot():
    try:
        print("Pokrećem prvu proveru...")
        driver = setup_driver()
        check_kleinanzeigen(driver, is_first_run=True)
        driver.quit()
        print(f"Učitano {len(seen_ads)} postojećih oglasa.")

        while True:
            time.sleep(CHECK_INTERVAL)
            driver = setup_driver()
            check_kleinanzeigen(driver, is_first_run=False)
            driver.quit()
    except Exception as e:
        import traceback
        print(f"KRITIČNA GREŠKA u run_bot: {e}")
        traceback.print_exc()

# Pokrećemo bota u zasebnoj niti (thread)
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
