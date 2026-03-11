import requests
import time
from datetime import datetime

API_KEY = "pebLkhwqbzwZaKjOPI87kgnoL6cA2bHx"
LOCATION = "52.23,21.01"  # Warszawa

URL = "https://api.tomorrow.io/v4/weather/forecast"


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
    print("\n📡 Pobieram prognozę minutową na następną godzinę...")
    forecast_60min = fetch_next_hour_forecast()

    for i, minute in enumerate(forecast_60min):
        values = minute["values"]
        timestamp = minute["time"]

        temperature = values.get("temperature")
        wind = values.get("windSpeed")


        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"⏱ minuta {i+1}/60 | "
            f"🌡️ {temperature}°C | "
            f"💨 {wind} m/s | "
        )

        time.sleep(10)  # czekamy minutę

    print("🔁 Godzina minęła — pobieram nowe dane...\n")