import requests

# Podaci za slanje
BOT_TOKEN = "8688931289:AAEYAdmtq-AK7DkJJ2CKLc-mcOm2l-2ukMY"
CHAT_ID = "8846679847"

def test_poruka():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "🚀 <b>Test poruka iz VS Code-a!</b>\nAko vidis ovo, tvoj Telegram bot radi savrseno!",
        "parse_mode": "HTML"
    }

    print("Saljem test poruku na Telegram...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()

        if res_data.get("ok"):
            print("✅ USPESNO! Poruka je poslata. Proveri Telegram na telefonu.")
        else:
            print(f"❌ GRESKA od Telegrama: {res_data.get('description')}")

    except Exception as e:
        print(f"❌ GRESKA pri spajanju: {e}")

if __name__ == "__main__":
    test_poruka()