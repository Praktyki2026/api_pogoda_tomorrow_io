import requests
import time
import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from datetime import timezone
import sys

import konfiguracja

# Konfiguracja

API_KEY = konfiguracja.get_api_key()
LOCATION = konfiguracja.get_location()

DATA_FOLDER = "dane"
DATA_FILE = os.path.join(DATA_FOLDER, "minute_data.json")
LOG_FILE = os.path.join(DATA_FOLDER, "weather_app.log")

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def setup_folders():
    Path(DATA_FOLDER).mkdir(parents=True, exist_ok=True)

def fetch_minute_data():
    url = "https://api.tomorrow.io/v4/weather/forecast"
    params = {
        "location": LOCATION,
        "timesteps": "1m",
        "apikey": API_KEY,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Błąd pobierania: {e}")
        return None

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_data():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_closest_minute_entry(data, target_time):
    try:
        if not data or 'timelines' not in data or 'minutely' not in data['timelines']:
            return None, None
        
        minute_entries = data['timelines']['minutely']
        target_utc = target_time.astimezone(timezone.utc)
        
        closest_entry = None
        closest_diff = float('inf')
        
        for entry in minute_entries:
            entry_time = datetime.fromisoformat(entry['time'].replace('Z', '+00:00'))
            time_diff = abs((entry_time - target_utc).total_seconds())
            
            if time_diff < closest_diff:
                closest_diff = time_diff
                closest_entry = entry
        
        if closest_entry:
            return closest_entry.get('values', {}), closest_entry.get('time')
        return None, None
    except Exception as e:
        logging.error(f"Błąd wyszukiwania: {e}")
        return None, None

def display_weather(minute_data, time_data, current_time):
    """Wyświetla dane pogodowe - pojedynczy zestaw"""
    try:
        if time_data:
            api_time = datetime.fromisoformat(time_data.replace('Z', '+00:00'))
            local_api_time = api_time.astimezone()
            time_diff = (current_time.astimezone(timezone.utc) - api_time).total_seconds() / 60
            
            if time_diff > 2:
                age_info = f" (sprzed {time_diff:.0f} min)"
            else:
                age_info = ""
        
        # Czyszczenie konsoli (opcjonalnie)
        # os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "="*55)
        print(f"📊 DANE POGODOWE - {current_time.strftime('%H:%M:%S')}{age_info}")
        if time_data:
            print(f"🕐 Czas pomiaru: {local_api_time.strftime('%H:%M:%S')}")
        print("="*55)
        
        if not minute_data:
            print("❌ Brak danych")
            print("="*55)
            return
        
        # Wyświetl wszystko w jednym bloku
        if minute_data.get('temperature') is not None:
            print(f"🌡️  Temperatura: {minute_data['temperature']:.1f}°C")
        if minute_data.get('temperatureApparent') is not None:
            print(f"🤔 Odczuwalna: {minute_data['temperatureApparent']:.1f}°C")
        if minute_data.get('humidity') is not None:
            print(f"💧 Wilgotność: {minute_data['humidity']:.0f}%")
        if minute_data.get('windSpeed') is not None:
            wiatr_kmh = minute_data['windSpeed'] * 3.6
            print(f"💨 Wiatr: {wiatr_kmh:.1f} km/h")
        if minute_data.get('pressureSeaLevel') is not None:
            print(f"📈 Ciśnienie: {minute_data['pressureSeaLevel']:.0f} hPa")
        if minute_data.get('precipitationProbability') is not None:
            print(f"☔  Prawd. opadów: {minute_data['precipitationProbability']:.0f}%")
        if minute_data.get('cloudCover') is not None:
            print(f"☁️  Zachmurzenie: {minute_data['cloudCover']:.0f}%")
        if minute_data.get('visibility') is not None:
            print(f"👁️  Widoczność: {minute_data['visibility']:.1f} km")
        if minute_data.get('uvIndex') is not None:
            print(f"☀️  Indeks UV: {minute_data['uvIndex']:.0f}")
        if minute_data.get('dewPoint') is not None:
            print(f"💧 Punkt rosy: {minute_data['dewPoint']:.1f}°C")
        
        print("="*55)
        
    except Exception as e:
        logging.error(f"Błąd wyświetlania: {e}")

def wait_for_next_minute():
    """Precyzyjne czekanie do następnej pełnej minuty"""
    now = datetime.now()
    # Oblicz czas do następnej pełnej minuty
    seconds_to_next = 60 - now.second
    microseconds_to_next = 1000000 - now.microsecond if seconds_to_next == 60 else 0
    
    if seconds_to_next == 60:
        seconds_to_next = 0
    
    total_seconds = seconds_to_next + (microseconds_to_next / 1000000)
    
    if total_seconds > 0:
        # Logowanie tylko jeśli to konieczne (wyłączam debug)
        # logging.debug(f"Czekam {total_seconds:.2f}s do następnej minuty")
        time.sleep(total_seconds)
    
    return datetime.now()

def main():
    print("\n" + "🌟"*30)
    print("         PROGRAM POGODOWY - TOMORROW.IO")
    print("         (Dane minutowe)")
    print(f"         Lokalizacja: {LOCATION}")
    print("🌟"*30 + "\n")
    
    setup_folders()
    
    # Pierwsze pobranie danych
    print("📡 Pobieranie pierwszych danych...")
    weather_data = fetch_minute_data()
    
    if not weather_data:
        print("❌ Nie udało się pobrać danych")
        return
    
    save_data(weather_data)
    print("✅ Pierwsze dane pobrane")
    
    # Synchronizacja z pierwszą pełną minutą
    now = datetime.now()
    if now.second != 0:
        wait_seconds = 60 - now.second
        print(f"⏳ Synchronizacja... Start za {wait_seconds} sekund")
        time.sleep(wait_seconds)
    
    # Główna pętla
    next_hour_update = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    last_display_time = None
    
    try:
        while True:
            current_time = datetime.now()
            
            # Wyświetlaj tylko jeśli to nowa minuta
            if last_display_time is None or current_time.minute != last_display_time.minute:
                
                # Sprawdź aktualizację danych (pełna godzina)
                if current_time >= next_hour_update:
                    print("\n⏰ Aktualizacja danych...")
                    new_data = fetch_minute_data()
                    if new_data:
                        weather_data = new_data
                        save_data(weather_data)
                        print("✅ Dane zaktualizowane")
                    else:
                        print("⚠️ Używam starych danych")
                    
                    next_hour_update = current_time.replace(second=0, microsecond=0) + timedelta(hours=1)
                
                # Pokaż dane
                minute_data, time_data = find_closest_minute_entry(weather_data, current_time)
                display_weather(minute_data, time_data, current_time)
                
                last_display_time = current_time
            
            # Czekaj do następnej minuty
            wait_for_next_minute()
            
    except KeyboardInterrupt:
        print("\n\n👋 Program zatrzymany")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")

if __name__ == "__main__":
    main()