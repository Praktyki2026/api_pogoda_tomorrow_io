
import os
from pathlib import Path
import requests
import json
from datetime import datetime, timedelta, timezone
import time

import konfiguracja



API_KEY = konfiguracja.get_api_key()
LOCATION = konfiguracja.get_location()
DATA_FOLDER = "dane"
DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")

weather_data_for_flask = {
    'minute': None,      # aktualne dane minutowe
    'hour': None,        # lista 24 godzin
    'day': None,         # lista dni
    'last_update': None, # timestamp
    'location': LOCATION
}

# ============================================
# SŁOWNIK KODÓW POGODOWYCH
# ============================================

WEATHER_CODES = {
    # Sunny / Clear conditions
    1000: "☀️ Słonecznie",
    1100: "🌤️ Głównie słonecznie",
    1101: "⛅ Częściowo słonecznie",
    
    # Cloudy conditions
    1102: "☁️ Częściowo pochmurnie",
    1001: "☁️ Pochmurnie",
    
    # Fog
    2000: "🌫️ Mgła",
    2100: "🌫️ Lekka mgła",
    
    # Rain
    4000: "🌧️ Lekki deszcz",
    4001: "🌧️ Deszcz",
    4200: "🌧️ Lekkie opady",
    4201: "🌧️ Ulewne opady",
    
    # Snow
    5000: "❄️ Lekki śnieg",
    5001: "❄️ Śnieg",
    5100: "❄️ Lekkie opady śniegu",
    5101: "❄️ Ulewne opady śniegu",
    
    # Mixed rain/snow
    6000: "🌨️ Lekki deszcz ze śniegiem",
    6001: "🌨️ Deszcz ze śniegiem",
    6200: "🌨️ Lekki deszcz ze śniegiem",
    6201: "🌨️ Ulewny deszcz ze śniegiem",
    
    # Hail / Ice
    7000: "🧊 Grad",
    7101: "🧊 Lekki lód",
    7102: "🧊 Gęsty lód",
    
    # Storm
    8000: "⛈️ Burza"
}


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
    
    return najblizszy_wpis, najblizszy_czas


def opis_pogody(weather_code):
    """
    Zwraca opis pogody dla podanego kodu.
    Jeśli kod nie istnieje, zwraca komunikat "Nieznany kod".
    """
    return WEATHER_CODES.get(weather_code, f"❓ Nieznany kod ({weather_code})")

def pokaz_pogode_teraz(dane):
    """
    Wyświetla podstawowe dane pogodowe dla aktualnego czasu
    Funkcja wyświetla temperaturę, wilgotność, wiatr, ciśnienie, prawdopodobieństwo opadów, zachmurzenie.
    """
    print("\n" + "="*50)
    print("POGODA TERAZ")
    print("="*50)
    
    # Znajdź wpis dla aktualnego czasu
    wartosci, czas = znajdz_najblizszy_wpis(dane)
    
    if not wartosci:
        print("Nie znaleziono danych dla aktualnego czasu")
        return
    
    # Wyświetl czas pomiaru
    if czas:
        czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
        czas_lokalny = czas_obj.astimezone()
        print(f"🕐 Czas pomiaru: {czas_lokalny.strftime('%H:%M:%S')}")
    
    # Wyświetl podstawowe dane
    if wartosci.get('weatherCode') is not None:
        kod = wartosci['weatherCode']
        opis = opis_pogody(kod)
        print(f"🌡️  Warunki: {opis}")
    
    if wartosci.get('temperature') is not None:
        print(f"🌡️  Temperatura: {wartosci['temperature']:.1f}°C")
    
    if wartosci.get('humidity') is not None:
        print(f"💧 Wilgotność: {wartosci['humidity']:.0f}%")
    
    if wartosci.get('windSpeed') is not None:
        # Przelicz m/s na km/h
        wiatr_kmh = wartosci['windSpeed'] * 3.6
        print(f"💨 Wiatr: {wiatr_kmh:.1f} km/h")
    
    if wartosci.get('pressureSeaLevel') is not None:
        print(f"📈 Ciśnienie: {wartosci['pressureSeaLevel']:.0f} hPa")
    
    if wartosci.get('precipitationProbability') is not None:
        print(f"☔  Prawd. opadów: {wartosci['precipitationProbability']:.0f}%")
    
    if wartosci.get('cloudCover') is not None:
        print(f"☁️  Zachmurzenie: {wartosci['cloudCover']:.0f}%")
    
    print("="*50)

def pobierz_nastepne_24h(dane):
    """
    Pobiera prognozę godzinową z danych.
    Domyślnie zwraca 24 godziny (można zmienić)
    """
    if not dane or "timelines" not in dane or "hourly" not in dane["timelines"]:
        print("Brak danych godzinowych")
        return []
    
    wszystkie_godziny = dane["timelines"]["hourly"]
    
    # Ogranicz do żądanej liczby godzin
    return wszystkie_godziny[:24]


def pokaz_prognoze_doba(dane):
    """
    Wyświetla prognozę pogody na najbliższe 24 godziny w formie tabeli
    """
    print("\n" + "="*70)
    print("PROGNOZA GODZINOWA (NASTĘPNE 24H)")
    print("="*70)
    
    prognoza = pobierz_nastepne_24h(dane)
    
    if not prognoza:
        print("Brak danych do wyświetlenia")
        return
    
    # Nagłówek tabeli
    print(f"{'Godzina':<10} {'Temp':<8} {'Opady':<8} {'Wiatr':<8} {'Zachm.'}")  # Zamień "na" na normalny tekst
    print("-" * 70)
    
    for wpis in prognoza:
        czas = wpis["time"]
        wartosci = wpis["values"]
        
        # Konwersja czasu UTC na lokalny
        czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
        czas_lokalny = czas_obj.astimezone()
        
        # Formatowanie godziny (np. "14:00")
        godzina = czas_lokalny.strftime("%H:%M")
        
        # Pobieranie danych
        temp = wartosci.get('temperature')
        opady = wartosci.get('precipitationProbability')
        wiatr = wartosci.get('windSpeed')
        zachmurzenie = wartosci.get('cloudCover')
        
        # Przygotowanie stringów do wyświetlenia
        temp_str = f"{temp:.1f}°C" if temp is not None else "---"
        opady_str = f"{opady:.0f}%" if opady is not None else "---"
        wiatr_str = f"{(wiatr * 3.6):.1f}" if wiatr is not None else "---"  # m/s na km/h
        zachm_str = f"{zachmurzenie:.0f}%" if zachmurzenie is not None else "---"
        
        # Wyświetlenie wiersza
        print(f"{godzina:<10} {temp_str:<8} {opady_str:<8} {wiatr_str:<8} {zachm_str}")
    
    print("="*70)

def pokaz_prognoze_doba_szczegolowa(dane):
    """
    Wyświetla bardziej szczegółową prognozę godzinową
    """
    print("\n" + "="*80)
    print("SZCZEGÓŁOWA PROGNOZA GODZINOWA")
    print("="*80)
    
    prognoza = pobierz_nastepne_24h(dane)  # Pokazujemy 12 godzin dla czytelności
    
    if not prognoza:
        print("Brak danych do wyświetlenia")
        return
    
    for wpis in prognoza:
        czas = wpis["time"]
        wartosci = wpis["values"]
        
        # Konwersja czasu
        czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
        czas_lokalny = czas_obj.astimezone()
        
        print(f"\n📅 {czas_lokalny.strftime('%H:%M - %d.%m.%Y')}")
        print("-" * 40)
        
        # Warunki pogodowe
        if wartosci.get('weatherCode') is not None:
            kod = wartosci['weatherCode']
            opis = opis_pogody(kod)
            print(f"  🌡️  Warunki: {opis}")
        
        # Temperatura
        if wartosci.get('temperature') is not None:
            print(f"  🌡️  Temperatura: {wartosci['temperature']:.1f}°C")
        
        # Odczuwalna
        if wartosci.get('temperatureApparent') is not None:
            print(f"  🤔 Odczuwalna: {wartosci['temperatureApparent']:.1f}°C")
        
        # Wilgotność
        if wartosci.get('humidity') is not None:
            print(f"  💧 Wilgotność: {wartosci['humidity']:.0f}%")
        
        # Wiatr
        if wartosci.get('windSpeed') is not None:
            wiatr_kmh = wartosci['windSpeed'] * 3.6
            print(f"  💨 Wiatr: {wiatr_kmh:.1f} km/h")
        
        # Opady
        if wartosci.get('precipitationProbability') is not None:
            print(f"  ☔  Prawd. opadów: {wartosci['precipitationProbability']:.0f}%")
        
        # Zachmurzenie
        if wartosci.get('cloudCover') is not None:
            print(f"  ☁️  Zachmurzenie: {wartosci['cloudCover']:.0f}%")
        
        # Ciśnienie
        if wartosci.get('pressureSeaLevel') is not None:
            print(f"  📈 Ciśnienie: {wartosci['pressureSeaLevel']:.0f} hPa")


"""
na kiedyś do zrobienia
dodać jeszcze funkcję która będzie wyświetlała szczegółowe informacje godzinowe na wybrany dzień 
"""

def pobierz_prognoze_dzienna(dane):
    """
    Pobiera prognozę dzienną z danych
    """
    if not dane or "timelines" not in dane or "daily" not in dane["timelines"]:
        print("Brak danych dziennych")
        return []
    
    return dane["timelines"]["daily"]


def pokaz_prognoze_dzienna(dane):
    """
    Wyświetla prognozę na najbliższe dni w formie rozszerzonej
    """
    print("\n" + "="*90)
    print("PROGNOZA DZIENNA (NAJBLIŻSZE DNI)")
    print("="*90)
    
    prognoza = pobierz_prognoze_dzienna(dane)
    
    if not prognoza:
        print("Brak danych do wyświetlenia")
        return
    
    # Nagłówek tabeli
    print(f"{'Data':<12} {'Dzień tyg':<10} {'Temp max':<10} {'Temp min':<10} {'Opady max':<10} {'Opady min':<10} {'Wschód':<8} {'Zachód':<8}")
    print("-" * 90)
    
    for wpis in prognoza:
        czas = wpis["time"]
        wartosci = wpis["values"]
        
        # Konwersja daty
        czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
        data_lokalna = czas_obj.astimezone()
        
        # Formatowanie daty (np. "15.01.2024")
        data = data_lokalna.strftime("%d.%m.%Y")
        
        # Dzień tygodnia po polsku
        dni_tygodnia = {
            "Monday": "Poniedziałek",
            "Tuesday": "Wtorek", 
            "Wednesday": "Środa",
            "Thursday": "Czwartek",
            "Friday": "Piątek",
            "Saturday": "Sobota",
            "Sunday": "Niedziela"
        }
        dzien_tyg_ang = data_lokalna.strftime("%A")
        dzien_tyg = dni_tygodnia.get(dzien_tyg_ang, dzien_tyg_ang)
        
        # Temperatury
        temp_max = wartosci.get('temperatureMax')
        temp_min = wartosci.get('temperatureMin')
        
        # Opady
        opady_max = wartosci.get('precipitationProbabilityMax')
        opady_min = wartosci.get('precipitationProbabilityMin')
        
        # Wschód/zachód słońca
        wschod = wartosci.get('sunriseTime')
        zachod = wartosci.get('sunsetTime')
        
        if wschod:
            wschod_obj = datetime.fromisoformat(wschod.replace('Z', '+00:00'))
            wschod = wschod_obj.astimezone().strftime("%H:%M")
        else:
            wschod = "--:--"
        
        if zachod:
            zachod_obj = datetime.fromisoformat(zachod.replace('Z', '+00:00'))
            zachod = zachod_obj.astimezone().strftime("%H:%M")
        else:
            zachod = "--:--"
        
        # Przygotowanie stringów z obsługą braku danych
        temp_max_str = f"{temp_max:.0f}°C" if temp_max is not None else "---"
        temp_min_str = f"{temp_min:.0f}°C" if temp_min is not None else "---"
        opady_max_str = f"{opady_max:.0f}%" if opady_max is not None else "---"
        opady_min_str = f"{opady_min:.0f}%" if opady_min is not None else "---"
        
        print(f"{data:<12} {dzien_tyg:<10} {temp_max_str:<10} {temp_min_str:<10} {opady_max_str:<10} {opady_min_str:<10} {wschod:<8} {zachod:<8}")
    
    print("="*90)

def pokaz_prognoze_dzienna_uproszczona(dane):
    """
    Uproszczona wersja - pokazuje tylko najważniejsze informacje
    """
    print("\n" + "="*70)
    print("PROGNOZA DZIENNA (Uproszczona)")
    print("="*70)
    
    prognoza = pobierz_prognoze_dzienna(dane)
    
    if not prognoza:
        print("Brak danych do wyświetlenia")
        return
    
    print(f"{'Data':<12} {'Dzień':<10} {'Temp':<12} {'Opady':<12}")
    print("-" * 70)
    
    for wpis in prognoza:
        czas = wpis["time"]
        wartosci = wpis["values"]
        
        czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
        data_lokalna = czas_obj.astimezone()
        
        data = data_lokalna.strftime("%d.%m.%Y")
        
        dni_tygodnia = {
            "Monday": "Pon",
            "Tuesday": "Wt",
            "Wednesday": "Śr",
            "Thursday": "Czw",
            "Friday": "Pt",
            "Saturday": "Sob",
            "Sunday": "Nd"
        }
        dzien_tyg_ang = data_lokalna.strftime("%A")
        dzien_tyg = dni_tygodnia.get(dzien_tyg_ang, dzien_tyg_ang)
        
        temp_max = wartosci.get('temperatureMax')
        temp_min = wartosci.get('temperatureMin')
        opady_max = wartosci.get('precipitationProbabilityMax')
        
        temp_str = f"{temp_min:.0f}-{temp_max:.0f}°C" if temp_min and temp_max else "---"
        opady_str = f"{opady_max:.0f}%" if opady_max is not None else "---"
        
        print(f"{data:<12} {dzien_tyg:<10} {temp_str:<12} {opady_str:<12}")
    
    print("="*70)




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


def przygotuj_dane_minutowe(wartosci, czas):
    """Przygotowuje dane minutowe do słownika"""
    if not wartosci:
        return None
    
    czas_obj = datetime.fromisoformat(czas.replace('Z', '+00:00'))
    
    return {
        'timestamp': czas,
        'time_local': czas_obj.astimezone().strftime('%H:%M:%S'),
        'weather_code': wartosci.get('weatherCode'),
        'weather_description': opis_pogody(wartosci.get('weatherCode')),
        'temperature': wartosci.get('temperature'),
        'temperature_apparent': wartosci.get('temperatureApparent'),
        'humidity': wartosci.get('humidity'),
        'wind_speed_kmh': wartosci.get('windSpeed') * 3.6 if wartosci.get('windSpeed') else None,
        'pressure': wartosci.get('pressureSeaLevel'),
        'precipitation_probability': wartosci.get('precipitationProbability'),
        'cloud_cover': wartosci.get('cloudCover')
    }

def przygotuj_dane_godzinowe(dane, liczba_godzin=24):
    """Przygotowuje dane godzinowe do słownika"""
    if not dane or "timelines" not in dane or "hourly" not in dane["timelines"]:
        return []
    
    wszystkie_godziny = dane["timelines"]["hourly"][:liczba_godzin]
    wynik = []
    
    for wpis in wszystkie_godziny:
        czas_obj = datetime.fromisoformat(wpis["time"].replace('Z', '+00:00'))
        wartosci = wpis["values"]
        
        wynik.append({
            'time_local': czas_obj.astimezone().strftime('%H:%M'),
            'temperature': wartosci.get('temperature'),
            'precipitation_probability': wartosci.get('precipitationProbability'),
            'wind_speed_kmh': wartosci.get('windSpeed') * 3.6 if wartosci.get('windSpeed') else None,
            'cloud_cover': wartosci.get('cloudCover'),
            'weather_description': opis_pogody(wartosci.get('weatherCode'))
        })
    
    return wynik

def przygotuj_dane_dzienne(dane):
    """Przygotowuje dane dzienne do słownika"""
    if not dane or "timelines" not in dane or "daily" not in dane["timelines"]:
        return []
    
    wszystkie_dni = dane["timelines"]["daily"]
    wynik = []
    
    dni_tygodnia = {
        "Monday": "Pon", "Tuesday": "Wt", "Wednesday": "Śr",
        "Thursday": "Czw", "Friday": "Pt", "Saturday": "Sob", "Sunday": "Nd"
    }
    
    for wpis in wszystkie_dni:
        czas_obj = datetime.fromisoformat(wpis["time"].replace('Z', '+00:00'))
        wartosci = wpis["values"]
        
        wynik.append({
            'date': czas_obj.astimezone().strftime('%d.%m'),
            'day': dni_tygodnia.get(czas_obj.strftime("%A"), ""),
            'temp_max': wartosci.get('temperatureMax'),
            'temp_min': wartosci.get('temperatureMin'),
            'precipitation_max': wartosci.get('precipitationProbabilityMax'),
            'weather_description': opis_pogody(wartosci.get('weatherCodeMax'))
        })
    
    return wynik


def uruchom_program():
    """
    Główna funkcja uruchamiająca program
    Wyświetla dane minutowe co minutę i aktualizuje dane co godzinę
    """
    print("\n" + "🌟"*30)
    print("         PROGRAM POGODOWY - TOMORROW.IO")
    print("         (Dane minutowe)")
    print(f"         Lokalizacja: {LOCATION}")
    print("🌟"*30 + "\n")
    
    # Inicjalizacja
    setup_folders()
    
    # Pobierz pierwsze dane
    print("📡 Pobieranie danych...")
    dane = fetch_weather_data()
    
    if not dane:
        print("❌ Nie udało się pobrać danych")
        return
    
    save_data(dane, DATA_FILE)
    print("✅ Dane pobrane")
    

    global weather_data_for_flask
    wartosci_min, czas_min = znajdz_najblizszy_wpis(dane)
    weather_data_for_flask['minute'] = przygotuj_dane_minutowe(wartosci_min, czas_min)
    weather_data_for_flask['hour'] = przygotuj_dane_godzinowe(dane)
    weather_data_for_flask['day'] = przygotuj_dane_dzienne(dane)
    weather_data_for_flask['last_update'] = datetime.now().isoformat()
    
    # WYŚWIETL PIERWSZE DANE OD RAZU
    print("\n📊 Wyświetlanie pierwszych danych...")
    pokaz_pogode_teraz(dane)
    
    # Główna pętla
    next_hour_update = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    last_display_time = datetime.now()
    
    try:
        while True:
            current_time = datetime.now()
            
            # Wyświetlaj tylko jeśli to nowa minuta
            if current_time.minute != last_display_time.minute:
                
                # Sprawdź aktualizację danych (pełna godzina)
                if current_time >= next_hour_update:
                    print("\n⏰ Aktualizacja danych...")
                    new_data = fetch_weather_data()
                    if new_data:
                        dane = new_data
                        save_data(dane, DATA_FILE)
                        

                        weather_data_for_flask['hour'] = przygotuj_dane_godzinowe(dane)
                        weather_data_for_flask['day'] = przygotuj_dane_dzienne(dane)
                        weather_data_for_flask['last_update'] = datetime.now().isoformat()
                        
                        print("✅ Dane zaktualizowane")
                    else:
                        print("⚠️ Używam starych danych")
                    
                    next_hour_update = current_time.replace(second=0, microsecond=0) + timedelta(hours=1)
                

                wartosci_min, czas_min = znajdz_najblizszy_wpis(dane)
                weather_data_for_flask['minute'] = przygotuj_dane_minutowe(wartosci_min, czas_min)
                
                # Pokaż dane
                pokaz_pogode_teraz(dane)
                
                last_display_time = current_time
            
            # Czekaj do następnej minuty
            wait_for_next_minute()
            
    except KeyboardInterrupt:
        print("\n\n👋 Program zatrzymany")
    except Exception as e:
        print(f"\n❌ Błąd: {e}")








"""
wykonywanie programu 
"""
# print("Pobieranie danych")
# data = fetch_weather_data()


# print("zapisywanie danych do pliku json")
# setup_folders()
# save_data(data, DATA_FILE)



# dane_pogodowe = load_data(DATA_FILE)

#display_basic_info(dane_pogodowe)

"""dane minutowe"""
#pokaz_pogode_teraz(dane_pogodowe)


"""dane godzinowe"""
# pokaz_prognoze_doba(dane_pogodowe)

# pokaz_prognoze_doba_szczegolowa(dane_pogodowe)



"""dane dzienne"""
# pokaz_prognoze_dzienna(dane_pogodowe)

# pokaz_prognoze_dzienna_uproszczona(dane_pogodowe)





# """główna część programu"""

# print("Pobieranie danych")
# data = fetch_weather_data()


# print("zapisywanie danych do pliku json")
# setup_folders()
# save_data(data, DATA_FILE)

# print("wczytywanie danych json")
# dane_pogodowe = load_data(DATA_FILE)


# ============================================
# URUCHOMIENIE PROGRAMU
# ============================================

# Po prostu wywołaj funkcję
uruchom_program()















# ============================================
# FUNKCJE DLA SERWERA FLASK
# ============================================

# def get_current_weather():
#     """Zwraca aktualne dane minutowe"""
#     return weather_data_for_flask.get('minute')

# def get_hourly_forecast():
#     """Zwraca prognozę godzinową"""
#     return weather_data_for_flask.get('hour', [])

# def get_daily_forecast():
#     """Zwraca prognozę dzienną"""
#     return weather_data_for_flask.get('day', [])

# def get_all_weather_data():
#     """Zwraca wszystkie dane"""
#     return weather_data_for_flask.copy()
