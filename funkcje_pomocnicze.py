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




"""
-----------------------------------------------------------------------------------
"""

from datetime import datetime
import time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")

def sleep_until(target: datetime):
    seconds = (target - datetime.now(TZ)).total_seconds()
    if seconds > 0:
        time.sleep(seconds)





"""
-----------------------------------------------------------------------------------
"""
from datetime import timedelta

def sleep_until_full_minute():
    now = datetime.now(TZ)
    target = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    sleep_until(target)


"""
-----------------------------------------------------------------------------------
"""
def sleep_until_full_hour():
    now = datetime.now(TZ)
    target = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    sleep_until(target)

"""
-----------------------------------------------------------------------------------
"""

import json

def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

"""
-----------------------------------------------------------------------------------
"""

"""
⚠️ Zakłada istnienie:

API_KEY, LOCATION, URL

data_lock

weather_data

funkcji save_json
"""

import requests
import os
from datetime import datetime

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

    minutely = timelines.get("minutely", [])
    hourly = timelines.get("hourly", [])
    daily = timelines.get("daily", [])

    os.makedirs("dane", exist_ok=True)

    save_json("dane/minutely.json", minutely)
    save_json("dane/hourly.json", hourly)
    save_json("dane/daily.json", daily)

    with data_lock:
        weather_data["minutely"] = minutely
        weather_data["hourly"] = hourly
        weather_data["daily"] = daily

    print(f"💾 Dane zapisane [{datetime.now(TZ).strftime('%H:%M:%S')}]")



"""
-----------------------------------------------------------------------------------
"""



from datetime import datetime

def find_closest_minute(data, now):
    closest = None
    min_diff = None

    for entry in data:
        entry_time = datetime.fromisoformat(
            entry["time"].replace("Z", "+00:00")
        ).astimezone(TZ)

        diff = abs((entry_time - now).total_seconds())

        if min_diff is None or diff < min_diff:
            min_diff = diff
            closest = entry

    return closest


"""
-----------------------------------------------------------------------------------
"""

import json

def minute_display_from_file():
    while True:
        sleep_until_full_minute()
        now = datetime.now(TZ)

        try:
            with open("dane/minutely.json", encoding="utf-8") as f:
                minutely = json.load(f)
        except FileNotFoundError:
            print("⚠️ Brak pliku dane/minutely.json")
            continue

        if not minutely:
            print("⚠️ Brak danych minutowych")
            continue

        entry = find_closest_minute(minutely, now)
        values = entry["values"]

        entry_time = datetime.fromisoformat(
            entry["time"].replace("Z", "+00:00")
        ).astimezone(TZ)

        print(
            f"[MIN {now.strftime('%H:%M')}] "
            f"(dane z {entry_time.strftime('%H:%M')}) | "
            f"🌡️ {values.get('temperature')}°C | "
            f"🌧️ {values.get('precipitationIntensity')} mm/h | "
            f"💨 {values.get('windSpeed')} m/s"
        )



"""
-----------------------------------------------------------------------------------
"""
def minutely_refresh():
    while True:
        sleep_until_full_hour()
        fetch_all()
"""
-----------------------------------------------------------------------------------
"""
def hourly_display():
    while True:
        sleep_until_full_hour()

        now = datetime.now(TZ)
        if now.hour % 6 != 0:
            continue

        with data_lock:
            hourly = weather_data.get("hourly", [])

        if not hourly:
            print("⚠️ Brak danych godzinowych")
            continue

        print("\n📊 PROGNOZA GODZINOWA (24h)")
        for h in hourly[:24]:
            t = h["time"][11:16]
            v = h["values"]
            print(
                f"{t} → 🌡️ {v.get('temperature')}°C | "
                f"☔ {v.get('precipitationProbability')}%"
            )



"""
-----------------------------------------------------------------------------------
"""
def daily_display():
    while True:
        sleep_until_full_hour()

        now = datetime.now(TZ)
        if now.hour % 12 != 0:
            continue

        with data_lock:
            daily = weather_data.get("daily", [])

        if not daily:
            print("⚠️ Brak danych dziennych")
            continue

        print("\n📅 PROGNOZA DZIENNA (7 dni)")
        for d in daily[:7]:
            date = d["time"][:10]
            v = d["values"]
            print(
                f"{date} → "
                f"🌡️ {v.get('temperatureAvg')}°C | "
                f"☀️ {v.get('weatherCode')}"
            )
"""
-----------------------------------------------------------------------------------
"""