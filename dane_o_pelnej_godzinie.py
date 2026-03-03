import requests
import time
from datetime import datetime, timedelta

API_KEY = "pebLkhwqbzwZaKjOPI87kgnoL6cA2bHx"
LOCATION = "52.23,21.01"  # Warszawa
URL = "https://api.tomorrow.io/v4/weather/forecast"


def sleep_until_full_hour():
    """funkcja czeka na kolejną pełną godzinę"""
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(
        minute=0, second=0, microsecond=0
    )
    seconds = (next_hour - now).total_seconds()

    print(f"⏳ Czekam do pełnej godziny ({next_hour.strftime('%H:%M:%S')})")
    time.sleep(seconds)

def sleep_until_next_full_minute():
    """czekanie do pełnej minuty"""
    now = datetime.now().astimezone()
    next_minute = (now + timedelta(minutes=1)).replace(
        second=0,
        microsecond=0
    )
    time.sleep((next_minute - now).total_seconds())

def sleep_until_next_10_minutes():
    """czeka na kolejne pełną 10 minut (jak jest 8:15 to czeka do 8:20)"""
    now = datetime.now()

    # ile minut brakuje do kolejnej "dziesiątki"
    minutes_to_add = 10 - (now.minute % 10)

    next_run = (now + timedelta(minutes=minutes_to_add)).replace(
        second=0,
        microsecond=0
    )

    seconds = (next_run - now).total_seconds()
    print(f"⏳ Test: czekam do {next_run.strftime('%H:%M:%S')}")
    time.sleep(seconds)




def fetch_next_hour_forecast():
    params = {
        "location": LOCATION,
        "timesteps": "1m",
        "apikey": API_KEY
    }

    response = requests.get(URL, params=params)
    response.raise_for_status()
    data = response.json()

    return data["timelines"]["minutely"][:60]

while True:
    # 1️⃣ czekamy do pełnej godziny
    #sleep_until_full_hour()
    sleep_until_next_10_minutes()

    print("📡 Pobieram prognozę minutową na następną godzinę...")
    forecast = fetch_next_hour_forecast()

    # 2️⃣ wyświetlanie minut (bez ostatniej)
    for minute_data in forecast:
        sleep_until_next_full_minute()

        now = datetime.now().astimezone()

        # ❌ pomijamy ostatnią minutę godziny
        if now.minute == 59:
            print("⏭️ Pomijam minutę 59 – przygotowanie do nowej godziny")
            break

        values = minute_data["values"]

        print(
            f"[{now.strftime('%H:%M:%S')}] "
            f"🌡️ {values.get('temperature')}°C | "
            f"💨 {values.get('windSpeed')} m/s | "
            f"🌧️ {values.get('precipitationIntensity')} mm/h"
        )

    print("🔁 Koniec godziny – czekam na kolejne pobranie\n")