import requests
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

API_KEY = "pebLkhwqbzwZaKjOPI87kgnoL6cA2bHx"
LOCATION = "52.23,21.01"
URL = "https://api.tomorrow.io/v4/weather/forecast"
TZ = ZoneInfo("Europe/Warsaw")


def sleep_until_next_full_minute():
    now = datetime.now(TZ)
    next_minute = (now + timedelta(minutes=1)).replace(
        second=0, microsecond=0
    )
    time.sleep((next_minute - now).total_seconds())


def fetch_next_hour_forecast():
    params = {
        "location": LOCATION,
        "timesteps": "1m",
        "apikey": API_KEY
    }
    r = requests.get(URL, params=params)
    r.raise_for_status()
    return r.json()["timelines"]["minutely"]


# ▶️ START PROGRAMU – OD RAZU POBIERAMY
print("📡 Start programu – pobieram dane...")
forecast = fetch_next_hour_forecast()

# 🔒 dane ważne do następnej pełnej godziny
now = datetime.now(TZ)
valid_until = (now + timedelta(hours=1)).replace(
    minute=0, second=0, microsecond=0
)

print(f"🕒 Dane ważne do: {valid_until.strftime('%H:%M:%S')}\n")

while True:
    sleep_until_next_full_minute()
    now = datetime.now(TZ)

    # ⏱️ pełna godzina → nowe dane
    if now >= valid_until:
        print("\n📡 Pełna godzina – pobieram nowe dane...")
        forecast = fetch_next_hour_forecast()
        valid_until = (now + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
        print(f"🕒 Nowe dane ważne do: {valid_until.strftime('%H:%M:%S')}")
        continue

    # ❌ pomijamy minutę 59
    if now.minute == 59:
        print("⏭️ Pomijam minutę 59")
        continue

    minute_index = now.minute
    values = forecast[minute_index]["values"]

    print(
        f"[{now.strftime('%H:%M:%S')}] "
        f"🌡️ {values.get('temperature')}°C | "
        f"💨 {values.get('windSpeed')} m/s | "
    )