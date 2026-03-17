
import os
from pathlib import Path
import requests
import json

import konfiguracja

API_KEY = konfiguracja.get_api_key()
LOCATION = konfiguracja.get_location()
DATA_FOLDER = "dane"
DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")


def setup_folders():
    """Tworzy folder na dane jeśli nie istnieje"""
    Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)



def fetch_weather_data():
    """funkcja służy do pobierania danych z tomorrow.io o wybranych parametrach"""
    url = "https://api.tomorrow.io/v4/weather/forecast"
    params = {
        "location": LOCATION,
        "timesteps": ["1m", "1h", "1d"],
        "apikey": API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        return None
    except Exception as e:
        return None


def save_data(data, filename):
    """Funkcja do zapisywania danych do pliku json"""
    filename = DATA_FILE
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"błąd: {e}")




print("Pobieranie danych")
data = fetch_weather_data()


print("zapisywanie danych do pliku json")
setup_folders()
save_data(data, DATA_FILE)





















