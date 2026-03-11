import requests
import time
from threading import Thread, Lock
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =======================
# KONFIGURACJA
# =======================
API_KEY = "pebLkhwqbzwZaKjOPI87kgnoL6cA2bHx"
LOCATION = "52.23,21.01"  # Warszawa
URL = "https://api.tomorrow.io/v4/weather/forecast"
TZ = ZoneInfo("Europe/Warsaw")

# =======================
# WSPÓLNE DANE + LOCK
# =======================
data_lock = Lock()

weather_data = {
    "minutely": [],
    "hourly": [],
    "daily": []
}

# =======================
# POMOCNICZE SLEEPY (bez driftu)
# =======================
def sleep_until(target: datetime):
    seconds = (target - datetime.now(TZ)).total_seconds()
    if seconds > 0:
        time.sleep(seconds)

def sleep_until_full_minute():
    now = datetime.now(TZ)
    target = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    sleep_until(target)

def sleep_until_full_hour():
    now = datetime.now(TZ)
    target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    sleep_until(target)

# =======================
# POBIERANIE DANYCH
# =======================
def fetch_all():
    params = {
        "location": LOCATION,
        "timesteps": "1m,1h,1d",
        "units": "metric",
        "apikey": API_KEY
    }

    r = requests.get(URL, params=params, timeout=20)
    r.raise_for_status()

    timelines = r.json()["timelines"]

    with data_lock:
        weather_data["minutely"] = timelines.get("minutely", [])
        weather_data["hourly"] = timelines.get("hourly", [])
        weather_data["daily"] = timelines.get("daily", [])

    print(f"📡 Dane zaktualizowane [{datetime.now(TZ).strftime('%H:%M:%S')}]")

# =======================
# WĄTEK 1 – WYŚWIETLANIE MINUTOWE
# =======================
def minute_display():
    while True:
        sleep_until_full_minute()
        now = datetime.now(TZ)

        # nie wyświetlamy ostatniej minuty godziny
        if now.minute == 59:
            continue

        with data_lock:
            if not weather_data["minutely"]:
                continue
            entry = weather_data["minutely"][now.minute]["values"]

        print(
            f"[MIN {now.strftime('%H:%M')}] "
            f"🌡️ {entry.get('temperature')}°C | "
            f"🌧️ {entry.get('precipitationIntensity')} mm/h | "
            f"💨 {entry.get('windSpeed')} m/s"
        )

# =======================
# WĄTEK 2 – ODŚWIEŻANIE MINUTOWE (co godzinę)
# =======================
def minutely_refresh():
    while True:
        sleep_until_full_hour()
        fetch_all()

# =======================
# WĄTEK 3 – GODZINOWE (co 6h)
# =======================
def hourly_display():
    while True:
        sleep_until_full_hour()
        if datetime.now(TZ).hour % 6 != 0:
            continue

        with data_lock:
            print("\n📊 PROGNOZA GODZINOWA (24h)")
            for h in weather_data["hourly"][:24]:
                t = h["time"][11:16]
                temp = h["values"]["temperature"]
                rain = h["values"]["precipitationProbability"]
                print(f"{t} → {temp}°C | ☔ {rain}%")

# =======================
# WĄTEK 4 – DZIENNE (co 12h)
# =======================
def daily_display():
    while True:
        sleep_until_full_hour()
        if datetime.now(TZ).hour % 12 != 0:
            continue

        with data_lock:
            print("\n📅 PROGNOZA DZIENNA (7 dni)")
            for d in weather_data["daily"][:7]:
                date = d["time"][:10]
                temp = d["values"]["temperatureAvg"]
                print(f"{date} → {temp}°C")

# =======================
# START PROGRAMU
# =======================
if __name__ == "__main__":
    print("🚀 Start programu – pierwsze pobranie danych")
    fetch_all()

    Thread(target=minute_display, daemon=True).start()
    Thread(target=minutely_refresh, daemon=True).start()
    Thread(target=hourly_display, daemon=True).start()
    Thread(target=daily_display, daemon=True).start()

    while True:
        time.sleep(1)