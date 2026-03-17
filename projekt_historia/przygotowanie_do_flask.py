import os
from pathlib import Path
import requests
import json
from datetime import datetime, timedelta, timezone
import time
import threading
import logging

import konfiguracja

API_KEY = konfiguracja.get_api_key()
LOCATION = konfiguracja.get_location()
DATA_FOLDER = "dane"
DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")

# Blokada dla bezpiecznego dostępu do współdzielonych danych
weather_lock = threading.Lock()

# Słownik z danymi - to zastępuje kolejki!
weather_data = {
    'minute': None,      # ostatnie dane minutowe
    'hour': None,        # ostatnie dane godzinowe
    'day': None,         # ostatnie dane dzienne
    'last_update': None, # timestamp ostatniej aktualizacji
    'location': LOCATION
}

# ============================================
# SŁOWNIK KODÓW POGODOWYCH
# ============================================

WEATHER_CODES = {
    1000: "☀️ Słonecznie",
    1100: "🌤️ Głównie słonecznie",
    1101: "⛅ Częściowo słonecznie",
    1102: "☁️ Częściowo pochmurnie",
    1001: "☁️ Pochmurnie",
    2000: "🌫️ Mgła",
    2100: "🌫️ Lekka mgła",
    4000: "🌧️ Lekki deszcz",
    4001: "🌧️ Deszcz",
    4200: "🌧️ Lekkie opady",
    4201: "🌧️ Ulewne opady",
    5000: "❄️ Lekki śnieg",
    5001: "❄️ Śnieg",
    5100: "❄️ Lekkie opady śniegu",
    5101: "❄️ Ulewne opady śniegu",
    6000: "🌨️ Lekki deszcz ze śniegiem",
    6001: "🌨️ Deszcz ze śniegiem",
    6200: "🌨️ Lekki deszcz ze śniegiem",
    6201: "🌨️ Ulewny deszcz ze śniegiem",
    7000: "🧊 Grad",
    7101: "🧊 Lekki lód",
    7102: "🧊 Gęsty lód",
    8000: "⛈️ Burza"
}


"""podstawowe funkcje"""

def setup_folders():
    """Tworzy folder na dane jeśli nie istnieje"""
    Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

def setup_logging():
    """Konfiguracja logowania"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(DATA_FOLDER, 'weather_service.log')),
            logging.StreamHandler()
        ]
    )

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
        logging.info("Dane pobrane z API")
        return data
    except Exception as e:
        logging.error(f"Błąd pobierania: {e}")
        return None

def save_data(data):
    """Funkcja do zapisywania danych do pliku json"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Dane zapisane do pliku")
    except Exception as e:
        logging.error(f"Błąd zapisu: {e}")

def load_data():
    """Wczytuje dane z pliku JSON"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.error(f"Błąd odczytu: {e}")
        return None

def znajdz_najblizszy_wpis(data, czas_docelowy=None):
    """
    Znajduje wpis minutowy najbliższy podanemu czasowi
    """
    if not data or "timelines" not in data or "minutely" not in data["timelines"]:
        return None, None
    
    if czas_docelowy is None:
        czas_docelowy = datetime.now()
    
    wpisy_minutowe = data["timelines"]["minutely"]
    target_utc = czas_docelowy.astimezone(timezone.utc)
    
    najblizszy_wpis = None
    najblizszy_czas = None
    najmniejsza_roznica = float('inf')
    
    for wpis in wpisy_minutowe:
        czas_wpisu = datetime.fromisoformat(wpis["time"].replace('Z', '+00:00'))
        roznica = abs((czas_wpisu - target_utc).total_seconds())
        
        if roznica < najmniejsza_roznica:
            najmniejsza_roznica = roznica
            najblizszy_wpis = wpis["values"]
            najblizszy_czas = wpis["time"]
    
    return najblizszy_wpis, najblizszy_czas

def opis_pogody(weather_code):
    """Zwraca opis pogody dla podanego kodu"""
    return WEATHER_CODES.get(weather_code, f"Nieznany kod ({weather_code})")

def przygotuj_dane_minutowe(wartosci, czas):
    """Przygotowuje dane minutowe do wysłania do Flaska"""
    if not wartosci:
        return None
    
    czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
    
    dane = {
        'timestamp': czas,
        'time_local': czas_obj.astimezone().strftime('%H:%M:%S'),
        'time_utc': czas_obj.strftime('%H:%M:%S'),
        'weather_code': wartosci.get('weatherCode'),
        'weather_description': opis_pogody(wartosci.get('weatherCode')),
        'temperature': wartosci.get('temperature'),
        'temperature_apparent': wartosci.get('temperatureApparent'),
        'humidity': wartosci.get('humidity'),
        'wind_speed_ms': wartosci.get('windSpeed'),
        'wind_speed_kmh': wartosci.get('windSpeed') * 3.6 if wartosci.get('windSpeed') else None,
        'pressure': wartosci.get('pressureSeaLevel'),
        'precipitation_probability': wartosci.get('precipitationProbability'),
        'cloud_cover': wartosci.get('cloudCover'),
        'visibility': wartosci.get('visibility'),
        'uv_index': wartosci.get('uvIndex'),
        'dew_point': wartosci.get('dewPoint')
    }
    return dane

def przygotuj_dane_godzinowe(dane, liczba_godzin=24):
    """Przygotowuje dane godzinowe do wysłania do Flaska"""
    if not dane or "timelines" not in dane or "hourly" not in dane["timelines"]:
        return []
    
    wszystkie_godziny = dane["timelines"]["hourly"][:liczba_godzin]
    dane_godzinowe = []
    
    for wpis in wszystkie_godziny:
        czas_obj = datetime.fromisoformat(wpis["time"].replace('Z', '+00:00'))
        wartosci = wpis["values"]
        
        dane_godzinowe.append({
            'timestamp': wpis["time"],
            'time_local': czas_obj.astimezone().strftime('%H:%M'),
            'time_utc': czas_obj.strftime('%H:%M'),
            'temperature': wartosci.get('temperature'),
            'precipitation_probability': wartosci.get('precipitationProbability'),
            'wind_speed_kmh': wartosci.get('windSpeed') * 3.6 if wartosci.get('windSpeed') else None,
            'cloud_cover': wartosci.get('cloudCover'),
            'weather_code': wartosci.get('weatherCode'),
            'weather_description': opis_pogody(wartosci.get('weatherCode'))
        })
    
    return dane_godzinowe

def przygotuj_dane_dzienne(dane):
    """Przygotowuje dane dzienne do wysłania do Flaska"""
    if not dane or "timelines" not in dane or "daily" not in dane["timelines"]:
        return []
    
    wszystkie_dni = dane["timelines"]["daily"]
    dane_dzienne = []
    
    dni_tygodnia = {
        "Monday": "Poniedziałek", "Tuesday": "Wtorek", "Wednesday": "Środa",
        "Thursday": "Czwartek", "Friday": "Piątek", "Saturday": "Sobota", "Sunday": "Niedziela"
    }
    
    for wpis in wszystkie_dni:
        czas_obj = datetime.fromisoformat(wpis["time"].replace('Z', '+00:00'))
        wartosci = wpis["values"]
        
        dane_dzienne.append({
            'timestamp': wpis["time"],
            'date': czas_obj.astimezone().strftime('%d.%m.%Y'),
            'day_of_week': dni_tygodnia.get(czas_obj.strftime("%A"), czas_obj.strftime("%A")),
            'temperature_max': wartosci.get('temperatureMax'),
            'temperature_min': wartosci.get('temperatureMin'),
            'precipitation_probability_max': wartosci.get('precipitationProbabilityMax'),
            'precipitation_probability_min': wartosci.get('precipitationProbabilityMin'),
            'sunrise': wartosci.get('sunriseTime'),
            'sunset': wartosci.get('sunsetTime'),
            'weather_code': wartosci.get('weatherCodeMax'),
            'weather_description': opis_pogody(wartosci.get('weatherCodeMax'))
        })
    
    return dane_dzienne

def wait_for_next_minute():
    """Precyzyjne czekanie do następnej pełnej minuty"""
    now = datetime.now()
    seconds_to_next = 60 - now.second
    microseconds_to_next = 1000000 - now.microsecond if seconds_to_next == 60 else 0
    
    if seconds_to_next == 60:
        seconds_to_next = 0
    
    total_seconds = seconds_to_next + (microseconds_to_next / 1000000)
    
    if total_seconds > 0:
        time.sleep(total_seconds)
    
    return datetime.now()

# ============================================
# FUNKCJE DLA SERWERA FLASK - TERAZ PROSTE!
# ============================================

def get_current_weather():
    """Zwraca aktualne dane pogodowe (dla endpointu /api/weather/now)"""
    with weather_lock:
        return weather_data.get('minute')

def get_hourly_forecast(hours=24):
    """Zwraca prognozę godzinową (dla endpointu /api/weather/hourly)"""
    with weather_lock:
        dane = weather_data.get('hour', [])
        return dane[:hours]

def get_daily_forecast():
    """Zwraca prognozę dzienną (dla endpointu /api/weather/daily)"""
    with weather_lock:
        return weather_data.get('day', [])

def get_all_weather_data():
    """Zwraca wszystkie dane (dla dashboardu)"""
    with weather_lock:
        # Zwracamy kopię żeby nie modyfikować oryginału
        return weather_data.copy()

# ============================================
# GŁÓWNY PROCES AKTUALIZACJI DANYCH
# ============================================

def aktualizuj_dane():
    """Pobiera nowe dane i aktualizuje słownik weather_data"""
    global weather_data
    
    logging.info("Rozpoczęcie aktualizacji danych")
    dane = fetch_weather_data()
    
    if not dane:
        logging.error("Nie udało się pobrać danych")
        return False
    
    # Zapisz do pliku (opcjonalnie)
    save_data(dane)
    
    # Przygotuj wszystkie dane
    wartosci_min, czas_min = znajdz_najblizszy_wpis(dane)
    dane_minutowe = przygotuj_dane_minutowe(wartosci_min, czas_min)
    dane_godzinowe = przygotuj_dane_godzinowe(dane)
    dane_dzienne = przygotuj_dane_dzienne(dane)
    
    # ZABLOKUJ - aktualizuj - ODBlOKUJ
    with weather_lock:
        weather_data.update({
            'minute': dane_minutowe,
            'hour': dane_godzinowe,
            'day': dane_dzienne,
            'last_update': datetime.now().isoformat(),
            'location': LOCATION
        })
    
    logging.info("Dane zaktualizowane pomyślnie")
    return True

def uruchom_usluge_pogodowa():
    """
    Główna usługa działająca w tle
    Aktualizuje dane co godzinę
    """
    setup_folders()
    setup_logging()
    
    logging.info("🚀 Uruchomienie usługi pogodowej")
    logging.info(f"Lokalizacja: {LOCATION}")
    
    # Pierwsza aktualizacja
    if not aktualizuj_dane():
        logging.error("Nie udało się pobrać początkowych danych")
        return
    
    # Wyświetl pierwsze dane (opcjonalnie)
    print("\n" + "🌟"*30)
    print("         USŁUGA POGODOWA")
    print(f"         Lokalizacja: {LOCATION}")
    print("🌟"*30 + "\n")
    
    # Główna pętla aktualizacji
    next_hour_update = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    
    try:
        while True:
            current_time = datetime.now()
            
            # Aktualizacja danych co godzinę
            if current_time >= next_hour_update:
                aktualizuj_dane()
                next_hour_update = current_time.replace(second=0, microsecond=0) + timedelta(hours=1)
                logging.info(f"Następna aktualizacja o {next_hour_update.strftime('%H:%M')}")
            
            # Czekaj do następnej minuty (oszczędzamy CPU)
            wait_for_next_minute()
            
    except KeyboardInterrupt:
        logging.info("👋 Usługa pogodowa zatrzymana")
    except Exception as e:
        logging.error(f"❌ Błąd w usłudze: {e}")

# ============================================
# URUCHOMIENIE
# ============================================

if __name__ == "__main__":
    # Uruchom usługę w głównym wątku
    uruchom_usluge_pogodowa()
else:
    # Jeśli importowany do Flaska - tylko konfiguracja i załadowanie ostatnich danych
    setup_folders()
    
    # Załaduj ostatnie dane z pliku (żeby Flask miał coś od razu)
    dane_z_pliku = load_data()
    if dane_z_pliku:
        wartosci_min, czas_min = znajdz_najblizszy_wpis(dane_z_pliku)
        weather_data['minute'] = przygotuj_dane_minutowe(wartosci_min, czas_min)
        weather_data['hour'] = przygotuj_dane_godzinowe(dane_z_pliku)
        weather_data['day'] = przygotuj_dane_dzienne(dane_z_pliku)
        weather_data['last_update'] = datetime.now().isoformat()
        logging.info("Wczytano ostatnie dane z pliku")