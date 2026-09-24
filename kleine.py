import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- PODEŠAVANJA ---
SEARCH_URL = "https://www.kleinanzeigen.de/s-fahrraeder/herren/93326/preis:200:650/fully/k0c217l6231r100+fahrraeder.art_s:herren"
TELEGRAM_BOT_TOKEN = "8688931289:AAEY4gIT7rO-CY85WLM_t8EQPnI5KZ7gK2U"
TELEGRAM_CHAT_ID = "8846679847"

# Provera na svakih 10 minuta (600 sekundi)
CHECK_INTERVAL = 600

seen_ads = set()

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")  # Pokreće se u pozadini
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Greška pri slanju na Telegram: {e}")

def check_kleinanzeigen(driver, is_first_run=False):
    print("Proveravam nove oglase na Kleinanzeigen...")
    driver.get(SEARCH_URL)
    time.sleep(3)  # Čekamo 3 sekunde da se stranica učita

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

                # Zapamti oglas
                seen_ads.add(ad_id)

                # Ako JE prvo pokretanje, samo ga dodajemo u skup bez slanja poruke
                if is_first_run:
                    continue

                # Ako NIJE prvo pokretanje, šaljemo notifikaciju na Telegram
                message = f"<b>Novi oglas na Kleinanzeigen!</b>\n\n" \
                          f"<b>Naslov:</b> {title}\n" \
                          f"<b>Cena:</b> {price}\n" \
                          f"<b>Link:</b> {link}"
                
                send_telegram_message(message)
                print(f"Poslat nov oglas: {title}")

        except Exception as e:
            continue

if __name__ == "__main__":
    driver = setup_driver()
    print("Bot je pokrenut...")

    try:
        # Prvo učitavanje — is_first_run=True sprečava da ti stigne 25 starih oglasa
        check_kleinanzeigen(driver, is_first_run=True)
        print(f"Učitano {len(seen_ads)} postojećih oglasa. Od sada stižu samo NOVI oglasi!")

        # Glavna petlja
        while True:
            time.sleep(CHECK_INTERVAL)def run_bot():
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
            check_kleinanzeigen(driver, is_first_run=False)

    except KeyboardInterrupt:
        print("Zaustavljanje bota...")
    finally:
        driver.quit()
