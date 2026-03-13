
"""
Program do analizy danych pogodowych z Tomorrow.io
Wyszukuje optymalne okno czasowe na ognisko wg kryteriów:
- temperatura powyżej zadanej wartości
- słoneczna pogoda lub lekkie zachmurzenie (na podstawie weatherCode)
- w zadanym przedziale godzinowym
- przez zadaną minimalną liczbę godzin
"""
#python analizator_ogniska.py --temp 18 --godziny 3 --start 18 --koniec 22
# domyślne ustawienia Szukaj 4 godzin z temperaturą 15°C między 16:00 a 24:00 (domyślne):

# python analizator_ogniska.py --temp 18 --godziny 3 --start 18 --koniec 22

# python analizator_ogniska.py --pokaz-wszystkie

"""
Lista wszystkich argumentów:
Argument	Typ	Domyślnie	Opis
--plik	string	dane/weather_data.json	Ścieżka do pliku JSON
--min-temp	float	10.0	Minimalna temperatura (°C)
--max-temp	float	None	Maksymalna temperatura (°C)
--akceptowane-kody	string	"all"	Lista kodów pogodowych lub "all"
--min-ciag-godzin	int	0	Minimalna liczba ciągłych godzin
--poczatek	int	0	Godzina początkowa przedziału
--koniec	int	24	Godzina końcowa przedziału
--dni-poczatek	int	0	Początek zakresu dni (0 = dziś)
--dni-koniec	int	6	Koniec zakresu dni
--ciaglosc	flaga	True	Wymagaj ciągłości godzin  (False)
--pokaz-wszystkie	flaga	False	Pokaż wszystkie dni
--verbose, -v	flaga	False	Szczegółowe informacje
--info	flaga	False	Pokaż kody pogodowe
--help, -h	flaga	False	Pokaż pomoc


python analizator_ogniska.py --min-temp 15 --max-temp 25 --poczatek 16 --koniec 22 --min-ciag-godzin 4


python analizator_ogniska.py --min-temp 15 --poczatek 16 --koniec 22 --min-ciag-godzin 4 --akceptowane-kody "1000"

python analizator_ogniska.py --min-temp 15 --poczatek 16 --koniec 22 --min-ciag-godzin 4 --akceptowane-kody "1000,1100,1101"

python analizator_ogniska.py --min-temp 5 --akceptowane-kody "1000" --poczatek 12 --koniec 17 --min-ciag-godzin 5 --wyswietlanie-bloku "zakres"

"""


import json
import os
from datetime import datetime, timedelta, time
from pathlib import Path
import argparse
from typing import List, Dict, Tuple, Optional, Any
import sys

# =============================================================================
# KONFIGURACJA
# =============================================================================

# Domyślne ścieżki
DATA_FOLDER = "dane"
DEFAULT_DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")

# Mapowanie kodów pogodowych Tomorrow.io na opisy
WEATHER_CODES = {
    0: "Nieznane",
    1000: "Bezchmurnie / Słonecznie",
    1100: "Przeważnie bezchmurnie",
    1101: "Częściowe zachmurzenie",
    1102: "Przeważnie pochmurnie",
    1001: "Pochmurnie",
    2000: "Mgła",
    2100: "Lekka mgła",
    4000: "Mżawka",
    4001: "Deszcz",
    4200: "Lekki deszcz",
    4201: "Ulewny deszcz",
    5000: "Śnieg",
    5001: "Opady śniegu",
    5100: "Lekki śnieg",
    5101: "Ulewny śnieg",
    6000: "Deszcz ze śniegiem",
    6001: "Lekki deszcz ze śniegiem",
    6200: "Ulewny deszcz ze śniegiem",
    7000: "Grad",
    7101: "Lekki grad",
    7102: "Ulewny grad",
    8000: "Burza"
}

# =============================================================================
# FUNKCJE POMOCNICZE
# =============================================================================

def setup_argparse():
    """Konfiguracja argumentów linii poleceń"""
    parser = argparse.ArgumentParser(
        description='Analiza danych pogodowych w poszukiwaniu okna na ognisko',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  %(prog)s --min-temp 15 --min-ciag-godzin 4 --poczatek 16 --koniec 24
  %(prog)s --min-temp 18 --min-ciag-godzin 3 --poczatek 18 --koniec 22 --dni-koniec 3
  %(prog)s --min-temp 5 --akceptowane-kody "1000,1100,1101" --pokaz-wszystkie
  %(prog)s --min-temp 10 --max-temp 25 --dni-poczatek 1 --dni-koniec 7 --verbose
  %(prog)s --min-temp 5 --akceptowane-kody "1000" --wyswietlanie-bloku "zakres"
  %(prog)s --min-temp 5 --akceptowane-kody "1000" --wyswietlanie-bloku "szczegoly"
        """
    )
    
    # Podstawowe argumenty
    parser.add_argument('--plik', type=str, default=DEFAULT_DATA_FILE,
                        help=f'Ścieżka do pliku JSON (domyślnie: {DEFAULT_DATA_FILE})')
    
    # Temperatura
    parser.add_argument('--min-temp', type=float, default=10.0,
                        help='Minimalna temperatura w °C (domyślnie: 10)')
    
    parser.add_argument('--max-temp', type=float, default=None,
                        help='Maksymalna temperatura w °C (domyślnie: brak ograniczenia)')
    
    # Kody pogodowe
    parser.add_argument('--akceptowane-kody', '--akceptowalne-kody', type=str, default="all",
                        help='Lista kodów pogodowych do akceptacji (oddzielone przecinkami) lub "all" dla wszystkich (domyślnie: all)')
    
    # Godziny
    parser.add_argument('--min-ciag-godzin', type=int, default=0,
                        help='Minimalna liczba ciągłych godzin spełniających kryteria (domyślnie: 0)')
    
    parser.add_argument('--poczatek', type=int, default=0,
                        help='Godzina początkowa przedziału (0-23, domyślnie: 0)')
    
    parser.add_argument('--koniec', type=int, default=24,
                        help='Godzina końcowa przedziału (0-24, domyślnie: 24)')
    
    # Zakres dni
    parser.add_argument('--dni-poczatek', type=int, default=0,
                        help='Liczba dni od dziś do rozpoczęcia analizy (0 = dziś, domyślnie: 0)')
    
    parser.add_argument('--dni-koniec', type=int, default=6,
                        help='Liczba dni od dziś do zakończenia analizy (domyślnie: 6)')
    
    # Flagi

    parser.add_argument('--ciaglosc', type=lambda x: x.lower() == 'true', default=True,
                    help='Wymagaj ciągłości godzin (True/False, domyślnie: True)')
    
    # NOWY ARGUMENT: sposób wyświetlania ciągłego bloku
    parser.add_argument('--wyswietlanie-bloku', type=str, default="szczegoly",
                        choices=['zakres', 'szczegoly', 'oba'],
                        help='Sposób wyświetlania ciągłego bloku: "zakres" (tylko przedział), "szczegoly" (wszystkie godziny), "oba" (obie formy) (domyślnie: szczegoly)')
    
    parser.add_argument('--pokaz-wszystkie', action='store_true', default=False,
                        help='Pokaż wszystkie dni, nawet nie spełniające kryteriów (domyślnie: False)')
    
    parser.add_argument('--verbose', '-v', action='store_true', default=False,
                        help='Bardzo szczegółowe informacje - pokaż wszystkie godziny w przedziale (domyślnie: False)')
    
    # Informacje
    parser.add_argument('--info', action='store_true',
                        help='Pokaż dostępne kody pogodowe i ich opisy')
    
    return parser


def show_weather_codes():
    """Wyświetl wszystkie dostępne kody pogodowe"""
    print("\n📋 DOSTĘPNE KODY POGODOWE:")
    print("-" * 60)
    
    # Grupuj kody według typów dla lepszej czytelności
    sunny = [1000, 1100, 1101]
    cloudy = [1102, 1001]
    fog = [2000, 2100]
    rain = [4000, 4001, 4200, 4201]
    snow = [5000, 5001, 5100, 5101]
    mixed = [6000, 6001, 6200, 6201]
    hail = [7000, 7101, 7102]
    storm = [8000]
    
    print("\n☀️ SŁONECZNIE:")
    for code in sunny:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n☁️ POCHMURNIE:")
    for code in cloudy:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n🌫️ MGŁA:")
    for code in fog:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n🌧️ DESZCZ:")
    for code in rain:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n❄️ ŚNIEG:")
    for code in snow:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n🌨️ DESZCZ ZE ŚNIEGIEM:")
    for code in mixed:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n🧊 GRAD:")
    for code in hail:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("\n⛈️ BURZA:")
    for code in storm:
        print(f"  {code:4d}: {WEATHER_CODES[code]}")
    
    print("-" * 60)
    print("\nUżyj --akceptowane-kody z listą kodów oddzielonych przecinkami")
    print("np. --akceptowane-kody \"1000,1100,1101,1102\"")
    print("lub --akceptowane-kody \"all\" aby akceptować wszystkie kody\n")


def load_json_data(file_path: str) -> Optional[Dict]:
    """Wczytaj dane z pliku JSON"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ Plik nie istnieje: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Wczytano dane z pliku: {file_path}")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Błąd parsowania JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Błąd odczytu pliku: {e}")
        return None


def get_weather_description(code: Optional[int]) -> str:
    """Zwróć opis kodu pogodowego"""
    if code is None:
        return "Brak danych"
    return WEATHER_CODES.get(code, f"Nieznany kod ({code})")


def get_weather_emoji(code: Optional[int]) -> str:
    """Zwróć emoji dla kodu pogodowego"""
    if code is None:
        return "❓"
    if code in [1000, 1100]:
        return "☀️"
    if code == 1101:
        return "⛅"
    if code == 1102:
        return "⛅☁️"
    if code == 1001:
        return "☁️"
    if code in [2000, 2100]:
        return "🌫️"
    if code in [4000, 4001, 4200, 4201]:
        return "🌧️"
    if code in [5000, 5001, 5100, 5101]:
        return "❄️"
    if code in [6000, 6001, 6200, 6201]:
        return "🌨️"
    if code in [7000, 7101, 7102]:
        return "🧊"
    if code == 8000:
        return "⛈️"
    return "☁️"


def is_weather_accepted(weather_code: Optional[int], accepted_codes: Any) -> bool:
    """
    Sprawdź, czy kod pogodowy jest akceptowany
    accepted_codes może być listą int lub string "all"
    """
    if weather_code is None:
        return False
    
    if accepted_codes == "all":
        return True
    
    if isinstance(accepted_codes, list):
        return weather_code in accepted_codes
    
    return False


def show_available_date_range(data: Dict):
    """Pokaż jaki zakres dat jest dostępny w pliku"""
    if 'timelines' not in data or 'hourly' not in data['timelines']:
        return
    
    hourly = data['timelines']['hourly']
    if not hourly:
        return
    
    # Znajdź pierwszą i ostatnią datę
    first_time = datetime.fromisoformat(hourly[0]['time'].replace('Z', '+00:00')).astimezone()
    last_time = datetime.fromisoformat(hourly[-1]['time'].replace('Z', '+00:00')).astimezone()
    
    print(f"\n📅 Dostępny zakres danych:")
    print(f"   Od: {first_time.strftime('%A, %d %B %Y %H:%M')}")
    print(f"   Do: {last_time.strftime('%A, %d %B %Y %H:%M')}")
    
    # Policz ile pełnych dni
    dates = set()
    for entry in hourly:
        dt = datetime.fromisoformat(entry['time'].replace('Z', '+00:00')).astimezone()
        dates.add(dt.date())
    
    print(f"   Liczba dni: {len(dates)}")
    print(f"   Dni: {', '.join([d.strftime('%A %d.%m') for d in sorted(dates)])}")
    print()


def find_suitable_windows(data: Dict, args) -> List[Dict]:
    """
    Główna funkcja wyszukująca okna pogodowe
    
    Args:
        data: Słownik z danymi z Tomorrow.io
        args: Argumenty z parsera
    
    Returns:
        Lista słowników z informacjami o znalezionych oknach
    """
    
    # Sprawdź strukturę danych
    if 'timelines' not in data or 'hourly' not in data['timelines']:
        print("❌ Brak danych godzinowych w pliku")
        return []
    
    hourly_data = data['timelines']['hourly']
    print(f"📊 Znaleziono {len(hourly_data)} wpisów godzinowych")
    
    # Przygotuj listę akceptowanych kodów pogodowych
    accepted_codes = args.akceptowane_kody
    if accepted_codes != "all":
        try:
            accepted_codes = [int(c.strip()) for c in accepted_codes.split(',')]
            print(f"🔧 Akceptowane kody pogodowe: {accepted_codes}")
        except ValueError:
            print(f"⚠️ Błąd parsowania kodów, akceptuję wszystkie kody")
            accepted_codes = "all"
    else:
        print(f"🔧 Akceptowane kody pogodowe: WSZYSTKIE")
    
    # Konwersja godzin na obiekty time
    start_time = time(args.poczatek, 0)
    
    # Obsługa przypadku, gdy koniec to 24 (północ następnego dnia)
    if args.koniec == 24:
        end_time = time(23, 59)
        crosses_midnight = False
    else:
        end_time = time(args.koniec, 0)
        crosses_midnight = args.koniec < args.poczatek
    
    # Zakres dni
    start_date = datetime.now().date() + timedelta(days=args.dni_poczatek)
    end_date = datetime.now().date() + timedelta(days=args.dni_koniec)
    
    print(f"\n🔍 Parametry wyszukiwania:")
    print(f"   • Zakres dni: od {args.dni_poczatek} dni ({(start_date).strftime('%d.%m')}) do {args.dni_koniec} dni ({(end_date).strftime('%d.%m')})")
    print(f"   • Przedział godzin: {args.poczatek}:00 - {args.koniec}:00" + 
          (" (przez północ)" if crosses_midnight else ""))
    print(f"   • Temperatura: min {args.min_temp}°C" + 
          (f", max {args.max_temp}°C" if args.max_temp is not None else ""))
    print(f"   • Minimalna liczba ciągłych godzin: {args.min_ciag_godzin}")
    print(f"   • Wymagana ciągłość: {'TAK' if args.ciaglosc else 'NIE'}")
    print(f"   • Wyświetlanie bloku: {args.wyswietlanie_bloku}")
    print()
    
    # Grupuj dane według daty
    days_data = {}
    
    for entry in hourly_data:
        try:
            # Parsuj czas UTC
            time_str = entry['time']
            if time_str.endswith('Z'):
                time_str = time_str.replace('Z', '+00:00')
            utc_time = datetime.fromisoformat(time_str)
            
            # Konwertuj na lokalny
            local_time = utc_time.astimezone()
            local_date = local_time.date()
            
            # Filtruj według zakresu dni
            if local_date < start_date or local_date > end_date:
                continue
            
            # Grupuj według daty
            if local_date not in days_data:
                days_data[local_date] = []
            
            days_data[local_date].append((local_time, entry['values']))
            
        except (KeyError, ValueError) as e:
            if args.verbose:
                print(f"⚠️ Błąd parsowania wpisu: {e}")
            continue
    
    # Analiza każdego dnia
    results = []
    
    for date, entries in sorted(days_data.items()):
        # Filtruj godziny w zadanym przedziale
        hours_in_range = []
        
        for local_time, values in entries:
            current_hour = local_time.time()
            
            # Sprawdź, czy godzina należy do przedziału
            in_range = False
            
            if crosses_midnight:
                # Przedział przez północ
                if current_hour >= start_time or current_hour <= end_time:
                    in_range = True
            else:
                # Normalny przedział w ciągu dnia
                if start_time <= current_hour <= end_time:
                    in_range = True
            
            if not in_range:
                continue
            
            # Pobierz dane
            temp = values.get('temperature')
            weather_code = values.get('weatherCode')
            
            # Sprawdź kryteria temperatury
            temp_ok = True
            if temp is not None:
                if temp < args.min_temp:
                    temp_ok = False
                if args.max_temp is not None and temp > args.max_temp:
                    temp_ok = False
            else:
                temp_ok = False
            
            # Sprawdź kod pogodowy
            weather_ok = is_weather_accepted(weather_code, accepted_codes)
            
            # Czy godzina jest odpowiednia
            suitable = temp_ok and weather_ok
            
            hours_in_range.append({
                'time': local_time,
                'temp': temp,
                'weather_code': weather_code,
                'weather_desc': get_weather_description(weather_code),
                'weather_emoji': get_weather_emoji(weather_code),
                'temp_ok': temp_ok,
                'weather_ok': weather_ok,
                'suitable': suitable
            })
        
        # Sortuj godziny
        hours_in_range.sort(key=lambda x: x['time'])
        
        # Analiza odpowiednich godzin
        suitable_hours = [h for h in hours_in_range if h['suitable']]
        
        if args.ciaglosc:
            # Szukaj najdłuższego ciągłego bloku
            max_block = find_longest_continuous_block(suitable_hours)
            max_continuous = len(max_block)
            
            if max_continuous >= args.min_ciag_godzin:
                results.append({
                    'date': date,
                    'total_suitable': len(suitable_hours),
                    'max_continuous': max_continuous,
                    'continuous_block': max_block if max_continuous > 0 else [],
                    'all_hours': hours_in_range,
                    'suitable_hours': suitable_hours
                })
            elif args.pokaz_wszystkie:
                results.append({
                    'date': date,
                    'total_suitable': len(suitable_hours),
                    'max_continuous': max_continuous,
                    'all_hours': hours_in_range,
                    'suitable_hours': suitable_hours,
                    'insufficient': True
                })
        else:
            # Nie wymagamy ciągłości
            if len(suitable_hours) >= args.min_ciag_godzin:
                results.append({
                    'date': date,
                    'total_suitable': len(suitable_hours),
                    'max_continuous': find_max_continuous_length(suitable_hours),
                    'all_hours': hours_in_range,
                    'suitable_hours': suitable_hours
                })
            elif args.pokaz_wszystkie:
                results.append({
                    'date': date,
                    'total_suitable': len(suitable_hours),
                    'max_continuous': find_max_continuous_length(suitable_hours),
                    'all_hours': hours_in_range,
                    'suitable_hours': suitable_hours,
                    'insufficient': True
                })
    
    return results


def find_longest_continuous_block(hours: List[Dict]) -> List[Dict]:
    """Znajdź najdłuższy ciągły blok godzin"""
    if not hours:
        return []
    
    # Sortuj według czasu
    sorted_hours = sorted(hours, key=lambda x: x['time'])
    
    longest_block = []
    current_block = [sorted_hours[0]]
    
    for i in range(1, len(sorted_hours)):
        prev_time = sorted_hours[i-1]['time']
        curr_time = sorted_hours[i]['time']
        
        hour_diff = (curr_time - prev_time).total_seconds() / 3600
        
        if hour_diff <= 1.5:
            current_block.append(sorted_hours[i])
        else:
            if len(current_block) > len(longest_block):
                longest_block = current_block
            current_block = [sorted_hours[i]]
    
    if len(current_block) > len(longest_block):
        longest_block = current_block
    
    return longest_block


def find_max_continuous_length(hours: List[Dict]) -> int:
    """Znajdź długość najdłuższego ciągłego bloku"""
    return len(find_longest_continuous_block(hours))


def display_results(results: List[Dict], args):
    """Wyświetl wyniki w czytelnej formie"""
    
    if not results:
        print("❌ Brak danych do wyświetlenia")
        return
    
    print("\n" + "="*80)
    print("                           📋 WYNIKI ANALIZY                            ")
    print("="*80)
    
    # Filtruj tylko dni spełniające kryteria
    suitable_days = [r for r in results if not r.get('insufficient', False)]
    
    if suitable_days:
        print(f"\n✅ ZNALEZIONO {len(suitable_days)} DNI SPEŁNIAJĄCYCH KRYTERIA:\n")
        
        for i, day in enumerate(suitable_days, 1):
            date_str = day['date'].strftime("%A, %d %B %Y")
            print(f"  {i}. 📅 {date_str}")
            print(f"     • Godzin spełniających kryteria: {day['total_suitable']}")
            print(f"     • Najdłuższy ciągły blok: {day['max_continuous']} godz.")
            
            # Wyświetlanie godzin w zależności od argumentu --wyswietlanie-bloku
            if day['suitable_hours']:
                if args.wyswietlanie_bloku == "szczegoly":
                    # Tylko szczegółowa lista
                    print("     • Godziny:")
                    for h in day['suitable_hours']:
                        time_str = h['time'].strftime("%H:%M")
                        temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "??°C"
                        print(f"        - {time_str}: {temp_str} {h['weather_emoji']} {h['weather_desc']}")
                
                elif args.wyswietlanie_bloku == "zakres":
                    # Tylko zakres (jeśli jest ciągły blok)
                    if day.get('continuous_block') and day['continuous_block']:
                        block = day['continuous_block']
                        start = block[0]['time'].strftime("%H:%M")
                        end = block[-1]['time'].strftime("%H:%M")
                        print(f"     • Ciągły blok: {start} - {end} ({len(block)} godz.)")
                    else:
                        # Jeśli nie ma ciągłego bloku, pokaż godziny
                        print("     • Godziny (brak ciągłości):")
                        hours_str = ", ".join([h['time'].strftime("%H:%M") for h in day['suitable_hours']])
                        print(f"        {hours_str}")
                
                elif args.wyswietlanie_bloku == "oba":
                    # Zarówno szczegóły jak i zakres
                    print("     • Godziny:")
                    for h in day['suitable_hours']:
                        time_str = h['time'].strftime("%H:%M")
                        temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "??°C"
                        print(f"        - {time_str}: {temp_str} {h['weather_emoji']} {h['weather_desc']}")
                    
                    if day.get('continuous_block') and day['continuous_block']:
                        block = day['continuous_block']
                        start = block[0]['time'].strftime("%H:%M")
                        end = block[-1]['time'].strftime("%H:%M")
                        print(f"     • Ciągły blok: {start} - {end} ({len(block)} godz.)")
            
            print()
    else:
        print("\n❌ BRAK DNI SPEŁNIAJĄCYCH KRYTERIA")
    
    # Pokaż wszystkie dni jeśli args.pokaz_wszystkie
    if args.pokaz_wszystkie and len(results) > len(suitable_days):
        print("\n" + "-"*80)
        print("📊 WSZYSTKIE DNI W ZAKRESIE:\n")
        
        for day in results:
            if day.get('insufficient', False):
                date_str = day['date'].strftime("%A, %d %B %Y")
                print(f"  📅 {date_str}")
                print(f"     • Godzin spełniających kryteria: {day['total_suitable']}/{args.min_ciag_godzin}")
                print(f"     • Najdłuższy ciągły blok: {day['max_continuous']} godz.")
                
                if args.verbose:
                    # Pokaż wszystkie godziny w przedziale
                    print("     • Wszystkie godziny w przedziale:")
                    for h in day['all_hours']:
                        marker = "✅" if h['suitable'] else "❌"
                        time_str = h['time'].strftime("%H:%M")
                        temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "brak"
                        print(f"        {marker} {time_str}: {temp_str} {h['weather_emoji']} {h['weather_desc']}")
                
                print()
    
    print("="*80)


def main():
    """Główna funkcja programu"""
    
    # Parsuj argumenty
    parser = setup_argparse()
    args = parser.parse_args()
    
    # Jeśli --info, pokaż kody i zakończ
    if args.info:
        show_weather_codes()
        return 0
    
    # Wyświetl powitanie
    print("\n" + "🔥"*40)
    print("         ANALIZATOR OKIEN POGODOWYCH NA OGNISKO")
    print("🔥"*40 + "\n")
    
    # Walidacja argumentów
    if args.poczatek < 0 or args.poczatek > 23:
        print("❌ Błąd: --poczatek musi być w zakresie 0-23")
        return 1
    
    if args.koniec < 0 or args.koniec > 24:
        print("❌ Błąd: --koniec musi być w zakresie 0-24")
        return 1
    
    if args.dni_poczatek > args.dni_koniec:
        print("❌ Błąd: --dni-poczatek nie może być większy niż --dni-koniec")
        return 1
    
    # Wczytaj dane
    data = load_json_data(args.plik)
    if not data:
        return 1
    
    # Pokaż dostępny zakres dat
    show_available_date_range(data)
    
    # Znajdź okna
    results = find_suitable_windows(data, args)
    
    # Wyświetl wyniki
    display_results(results, args)
    
    # Podsumowanie
    if results:
        suitable_days = [r for r in results if not r.get('insufficient', False)]
        if suitable_days:
            best_day = suitable_days[0]
            print(f"\n🎯 NAJLEPSZY DZIEŃ: {best_day['date'].strftime('%d.%m.%Y')}")
            print(f"   z {best_day['total_suitable']} godzinami dobrej pogody")
            
            if best_day['suitable_hours']:
                hours_str = ", ".join([h['time'].strftime("%H:%M") for h in best_day['suitable_hours']])
                print(f"   Godziny: {hours_str}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())