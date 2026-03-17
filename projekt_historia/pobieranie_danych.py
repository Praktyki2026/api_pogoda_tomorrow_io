
import os
from pathlib import Path
import requests
import json
from datetime import datetime, timedelta, timezone

import konfiguracja

API_KEY = konfiguracja.get_api_key()
LOCATION = konfiguracja.get_location()
DATA_FOLDER = "dane"
DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")


"""podstawowe funkcje"""

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

def load_data(filename):
    """Wczytuje dane z pliku JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None



def display_basic_info(data):
    """Wyświetlanie podstawowych informacji o pobranych danych"""

    print("\n" + "="*50)
    print("PODSTAWOWE INFORMACJE O DANYCH")
    print("="*50)
    
    if "timelines" in data:
        timelines = data["timelines"]
        for interval in ["minutely", "hourly", "daily"]:
            if interval in timelines:
                count = len(timelines[interval])
                print(f"📊 {interval}: {count} wpisów")
    
    print("="*50)



def znajdz_najblizszy_wpis(data):
    """
    Znajduje wpis minutowy najbliższy aktualnemu czasowi systemowemu
    """
    if not data or "timelines" not in data or "minutely" not in data["timelines"]:
        print("Brak danych minutowych")
        return None, None
    
    # Pobierz wszystkie wpisy minutowe
    wpisy_minutowe = data["timelines"]["minutely"]
    
    # Aktualny czas systemowy - konwertujemy do UTC dla porównania
    czas_systemowy = datetime.now()  # to jest czas lokalny "naiwny"
    
    # Tworzymy czas "świadomy" z lokalną strefą, potem konwertujemy do UTC
    # Dzięki temu target_utc będzie zawierać poprawny czas UTC dla Twojej lokalizacji
    target_utc = czas_systemowy.astimezone(timezone.utc)
    
    print(f"Twój czas systemowy: {czas_systemowy.strftime('%H:%M:%S')}")
    print(f"Ten sam czas w UTC: {target_utc.strftime('%H:%M:%S')}")
    
    najblizszy_wpis = None
    najblizszy_czas = None
    najmniejsza_roznica = float('inf')
    
    for wpis in wpisy_minutowe:
        # Czas z API (format: "2024-01-15T12:34:00Z")
        czas_api = wpis["time"]
        
        # Konwersja na obiekt datetime (świadomy UTC)
        czas_wpisu = datetime.fromisoformat(czas_api.replace('Z', '+00:00'))
        
        # Oblicz różnicę w sekundach - oba czasy są świadome UTC
        roznica = abs((czas_wpisu - target_utc).total_seconds())
        
        if roznica < najmniejsza_roznica:
            najmniejsza_roznica = roznica
            najblizszy_wpis = wpis["values"]
            najblizszy_czas = czas_api
    
    print(f"Znaleziono wpis z {najmniejsza_roznica:.1f}s różnicy")
    return najblizszy_wpis, najblizszy_czas







"""
wykonywanie programu 
"""
# print("Pobieranie danych")
# data = fetch_weather_data()


# print("zapisywanie danych do pliku json")
# setup_folders()
# save_data(data, DATA_FILE)



dane_pogodowe = load_data(DATA_FILE)

display_basic_info(dane_pogodowe)
wpis, czas = znajdz_najblizszy_wpis(dane_pogodowe)

print("wyświetlanie danych")
print (czas)
print (wpis)



















