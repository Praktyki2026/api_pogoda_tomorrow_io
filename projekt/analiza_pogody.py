
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
Pełna lista argumentów programu analizatora pogody
Argument	Typ	Domyślnie	Opis
Podstawowe			
--plik	string	dane/weather_data.json	Ścieżka do pliku JSON z danymi pogodowymi
--temp	float	15.0	Minimalna temperatura w °C
--godziny	int	4	Minimalna liczba słonecznych godzin (w sumie lub ciągłych)
--start	int	16	Godzina początkowa przedziału (0-23)
--koniec	int	24	Godzina końcowa przedziału (0-24)
--dni	int	5	Liczba dni do przodu do analizy
| Filtrowanie pogody | | | |
| --tylko-temperatura | flaga | False | Ignoruj warunki pogodowe (weatherCode), sprawdzaj tylko temperaturę |
| --akceptowane-kody | string | None | Lista kodów pogodowych do akceptacji (oddzielone przecinkami), np. "1000,1100,1101,1102" |

| Wyszukiwanie | | | |
| --ciagle | flaga | False | Wymagaj ciągłości godzin (domyślnie: sumaryczna liczba) |

| Wyniki | | | |
| --pokaz-wszystkie | flaga | False | Pokaż wszystkie dni, nawet nie spełniające kryteriów |
| --pokaz-godziny | flaga | True | Pokaż konkretne godziny dla spełniających dni |
| --verbose, -v | flaga | False | Bardzo szczegółowe informacje (pokaż wszystkie godziny w przedziale) |

| Informacje | | | |
| --info | flaga | False | Pokaż dostępne kody pogodowe i ich opisy |
| --help, -h | flaga | False | Pokaż pomoc i zakończ |
"""


import json
import os
from datetime import datetime, timedelta, time
from pathlib import Path
import argparse
from typing import List, Dict, Tuple, Optional
import sys

# =============================================================================
# KONFIGURACJA
# =============================================================================

# Domyślne ścieżki
DATA_FOLDER = "dane"
DEFAULT_DATA_FILE = os.path.join(DATA_FOLDER, "weather_data.json")

# Mapowanie kodów pogodowych Tomorrow.io na opisy
# Źródło: https://docs.tomorrow.io/reference/data-layers-weather-codes
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

# Domyślne kody uznawane za "słoneczne" lub z lekkim zachmurzeniem
DEFAULT_SUNNY_CODES = [1000, 1100, 1101]  # Bezchmurnie, przeważnie bezchmurnie, częściowe zachmurzenie

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
  %(prog)s --temp 15 --godziny 4 --start 16 --koniec 24
  %(prog)s --temp 18 --godziny 3 --start 18 --koniec 22 --dni 3
  %(prog)s --plik moje_dane.json --temp 12 --pokaz-wszystkie
  %(prog)s --temp 5 --tylko-temperatura  # ignoruj warunki pogodowe
  %(prog)s --temp 5 --akceptowane-kody "1000,1100,1101,1102"  # własna lista kodów
        """
    )
    
    parser.add_argument('--plik', type=str, default=DEFAULT_DATA_FILE,
                        help=f'Ścieżka do pliku JSON (domyślnie: {DEFAULT_DATA_FILE})')
    
    parser.add_argument('--temp', type=float, default=15.0,
                        help='Minimalna temperatura w °C (domyślnie: 15)')
    
    parser.add_argument('--godziny', type=int, default=4,
                        help='Minimalna liczba słonecznych godzin (domyślnie: 4)')
    
    parser.add_argument('--start', type=int, default=16,
                        help='Godzina początkowa przedziału (0-23, domyślnie: 16)')
    
    parser.add_argument('--koniec', type=int, default=24,
                        help='Godzina końcowa przedziału (0-24, domyślnie: 24)')
    
    parser.add_argument('--dni', type=int, default=5,
                        help='Liczba dni do przodu do analizy (domyślnie: 5)')
    
    parser.add_argument('--pokaz-wszystkie', action='store_true',
                        help='Pokaż wszystkie dni, nawet nie spełniające kryteriów')
    
    parser.add_argument('--ciagle', action='store_true',
                        help='Wymagaj ciągłości godzin (domyślnie: sumaryczna liczba)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Bardzo szczegółowe informacje (pokaż wszystkie godziny w przedziale)')
    
    parser.add_argument('--pokaz-godziny', action='store_true', default=True,
                        help='Pokaż konkretne godziny dla spełniających dni (domyślnie: True)')
    
    # NOWE OPCJE
    parser.add_argument('--tylko-temperatura', action='store_true',
                        help='Ignoruj warunki pogodowe (weatherCode), sprawdzaj tylko temperaturę')
    
    parser.add_argument('--akceptowane-kody', type=str, default=None,
                        help='Lista kodów pogodowych do akceptacji (oddzielone przecinkami), np. "1000,1100,1101,1102"')
    
    parser.add_argument('--info', action='store_true',
                        help='Pokaż dostępne kody pogodowe i ich opisy')
    
    return parser


def show_weather_codes():
    """Wyświetl wszystkie dostępne kody pogodowe"""
    print("\n📋 DOSTĘPNE KODY POGODOWE:")
    print("-" * 50)
    for code, desc in sorted(WEATHER_CODES.items()):
        if code > 0:  # Pomijamy kod 0 (Nieznane)
            emoji = get_weather_emoji(code)
            default_marker = " ✓" if code in DEFAULT_SUNNY_CODES else ""
            print(f"  {emoji} {code}: {desc}{default_marker}")
    print("-" * 50)
    print("✓ - domyślnie uznawane za słoneczne")
    print("\nUżyj --akceptowane-kody z listą kodów oddzielonych przecinkami")
    print("lub --tylko-temperatura aby zignorować warunki pogodowe\n")


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
        return "☁️"
    if code == 1001:
        return "☁️☁️"
    if code in [2000, 2100]:
        return "🌫️"
    if code in [4000, 4001, 4200, 4201]:
        return "🌧️"
    if code in [5000, 5001, 5100, 5101]:
        return "❄️"
    if code in [6000, 6001, 6200, 6201]:
        return "🌨️"
    if code == 8000:
        return "⛈️"
    return "☁️"


def is_weather_accepted(weather_code: Optional[int], accepted_codes: List[int] = None) -> bool:
    """
    Sprawdź, czy kod pogodowy jest akceptowany
    Jeśli accepted_codes = None, używa domyślnych słonecznych kodów
    """
    if weather_code is None:
        return False
    
    if accepted_codes is not None:
        return weather_code in accepted_codes
    else:
        return weather_code in DEFAULT_SUNNY_CODES


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
    accepted_codes = None
    if args.akceptowane_kody:
        try:
            accepted_codes = [int(c.strip()) for c in args.akceptowane_kody.split(',')]
            print(f"🔧 Akceptowane kody pogodowe: {accepted_codes}")
        except ValueError:
            print(f"⚠️ Błąd parsowania kodów, używam domyślnych")
            accepted_codes = None
    
    if args.tylko_temperatura:
        print(f"🔧 Tryb: TYLKO TEMPERATURA (ignoruję warunki pogodowe)")
    
    # Konwersja godzin na obiekty time
    start_time = time(args.start, 0)
    
    # Obsługa przypadku, gdy koniec to 24 (północ następnego dnia)
    if args.koniec == 24:
        end_time = time(23, 59)  # Traktujemy jako koniec dnia
        crosses_midnight = False
    else:
        end_time = time(args.koniec, 0)
        crosses_midnight = args.koniec < args.start
    
    print(f"🔍 Szukam w przedziale: {args.start}:00 - {args.koniec}:00" + 
          (" (przez północ)" if crosses_midnight else ""))
    print(f"🌡️  Minimalna temperatura: {args.temp}°C")
    print(f"☀️  Minimalna liczba godzin: {args.godziny}" + 
          (" (ciągłych)" if args.ciagle else " (w sumie)"))
    print(f"📅 Analizuję {args.dni} dni do przodu\n")
    
    # Grupuj dane według daty
    days_data = {}
    current_date = None
    cutoff_date = datetime.now().date() + timedelta(days=args.dni)
    
    for entry in hourly_data:
        try:
            # Parsuj czas UTC
            time_str = entry['time']
            if time_str.endswith('Z'):
                time_str = time_str.replace('Z', '+00:00')
            utc_time = datetime.fromisoformat(time_str)
            
            # Konwertuj na lokalny (zakładamy strefę systemową)
            local_time = utc_time.astimezone()
            local_date = local_time.date()
            
            # Pomijaj dni poza zakresem
            if local_date > cutoff_date:
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
                # Przedział przez północ (np. 20:00 - 04:00)
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
            
            # Sprawdź kryteria
            temp_ok = temp is not None and temp >= args.temp
            
            if args.tylko_temperatura:
                # Tylko temperatura się liczy
                suitable = temp_ok
                sunny_ok = True  # Dla celów wyświetlania
            else:
                # Sprawdzaj też pogodę
                sunny_ok = is_weather_accepted(weather_code, accepted_codes)
                suitable = temp_ok and sunny_ok
            
            hours_in_range.append({
                'time': local_time,
                'temp': temp,
                'weather_code': weather_code,
                'weather_desc': get_weather_description(weather_code),
                'weather_emoji': get_weather_emoji(weather_code),
                'temp_ok': temp_ok,
                'sunny_ok': sunny_ok,
                'suitable': suitable
            })
        
        # Sortuj godziny
        hours_in_range.sort(key=lambda x: x['time'])
        
        # Analiza odpowiednich godzin
        suitable_hours = [h for h in hours_in_range if h['suitable']]
        
        if args.ciagle:
            # Szukaj najdłuższego ciągłego bloku
            max_block = find_longest_continuous_block(suitable_hours)
            if max_block:
                block_length = len(max_block)
                if block_length >= args.godziny:
                    results.append({
                        'date': date,
                        'total_suitable': len(suitable_hours),
                        'max_continuous': block_length,
                        'continuous_block': max_block,
                        'all_hours': hours_in_range,
                        'suitable_hours': suitable_hours
                    })
        else:
            # Wymagaj tylko sumarycznej liczby godzin
            if len(suitable_hours) >= args.godziny:
                results.append({
                    'date': date,
                    'total_suitable': len(suitable_hours),
                    'max_continuous': find_max_continuous_length(suitable_hours),
                    'all_hours': hours_in_range,
                    'suitable_hours': suitable_hours
                })
            elif args.pokaz_wszystkie:
                # Dodaj dzień nawet jeśli nie spełnia kryteriów
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
        # Sprawdź, czy godziny są kolejne (różnica 1 godziny)
        prev_time = sorted_hours[i-1]['time']
        curr_time = sorted_hours[i]['time']
        
        # Różnica w godzinach
        hour_diff = (curr_time - prev_time).total_seconds() / 3600
        
        if hour_diff <= 1.5:  # Dopuszczamy mały margines
            current_block.append(sorted_hours[i])
        else:
            if len(current_block) > len(longest_block):
                longest_block = current_block
            current_block = [sorted_hours[i]]
    
    # Sprawdź ostatni blok
    if len(current_block) > len(longest_block):
        longest_block = current_block
    
    return longest_block


def find_max_continuous_length(hours: List[Dict]) -> int:
    """Znajdź długość najdłuższego ciągłego bloku"""
    return len(find_longest_continuous_block(hours))


def format_hours_list(hours: List[Dict], show_details: bool = False) -> str:
    """Formatuj listę godzin do wyświetlenia"""
    if not hours:
        return "brak"
    
    if show_details:
        # Szczegółowa lista z temperaturą i pogodą
        lines = []
        for h in hours:
            time_str = h['time'].strftime("%H:%M")
            temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "??°C"
            lines.append(f"        • {time_str}: {temp_str} {h['weather_emoji']} {h['weather_desc']}")
        return "\n" + "\n".join(lines)
    else:
        # Zwarta lista samych godzin
        return ", ".join([h['time'].strftime("%H:%M") for h in hours])


def display_results(results: List[Dict], args):
    """Wyświetl wyniki w czytelnej formie"""
    
    if not results:
        print("❌ Brak danych do wyświetlenia")
        return
    
    print("\n" + "="*70)
    print("                           📋 WYNIKI ANALIZY                            ")
    print("="*70)
    
    # Filtruj tylko dni spełniające kryteria
    suitable_days = [r for r in results if not r.get('insufficient', False)]
    
    if suitable_days:
        print(f"\n✅ ZNALEZIONO {len(suitable_days)} DNI SPEŁNIAJĄCYCH KRYTERIA:\n")
        
        for i, day in enumerate(suitable_days, 1):
            date_str = day['date'].strftime("%A, %d %B %Y")
            print(f"  {i}. 📅 {date_str}")
            print(f"     • Godzin spełniających kryteria: {day['total_suitable']}")
            print(f"     • Najdłuższy ciągły blok: {day['max_continuous']} godz.")
            
            # ZAWSZE pokazuj godziny (chyba że explicitly wyłączone)
            if args.pokaz_godziny and day['suitable_hours']:
                print("     • Godziny:")
                for h in day['suitable_hours']:
                    time_str = h['time'].strftime("%H:%M")
                    temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "??°C"
                    
                    # Wyświetl tylko emoji i opis, bez dopisku (ignorowany)
                    weather_info = f"{h['weather_emoji']} {h['weather_desc']}"
                    
                    # W trybie tylko-temperatura nie dodajemy dopisku
                    print(f"        - {time_str}: {temp_str} {weather_info}")
            
            # Jeśli znaleziono ciągły blok i args.ciagle
            if args.ciagle and 'continuous_block' in day:
                block = day['continuous_block']
                if block:
                    start = block[0]['time'].strftime("%H:%M")
                    end = block[-1]['time'].strftime("%H:%M")
                    print(f"     • Ciągły blok: {start} - {end} ({len(block)} godz.)")
            
            print()
    else:
        print("\n❌ BRAK DNI SPEŁNIAJĄCYCH KRYTERIA")
    
    # Pokaż wszystkie dni jeśli args.pokaz_wszystkie
    if args.pokaz_wszystkie and len(results) > len(suitable_days):
        print("\n" + "-"*70)
        print("📊 WSZYSTKIE DNI W ZAKRESIE:\n")
        
        for day in results:
            if day.get('insufficient', False):
                date_str = day['date'].strftime("%A, %d %B %Y")
                print(f"  📅 {date_str}")
                print(f"     • Godzin spełniających kryteria: {day['total_suitable']}/{args.godziny}")
                print(f"     • Najdłuższy ciągły blok: {day['max_continuous']} godz.")
                
                if args.verbose:
                    # Pokaż wszystkie godziny w przedziale
                    suitable_count = 0
                    print("     • Wszystkie godziny w przedziale:")
                    for h in day['all_hours']:
                        marker = "✅" if h['suitable'] else "❌"
                        time_str = h['time'].strftime("%H:%M")
                        temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "brak"
                        print(f"        {marker} {time_str}: {temp_str} {h['weather_emoji']} {h['weather_desc']}")
                        
                        if h['suitable']:
                            suitable_count += 1
                    
                    if suitable_count > 0:
                        print(f"        Razem: {suitable_count} godzin")
                
                print()
    
    print("="*70)

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
    print("\n" + "🔥"*35)
    print("         ANALIZATOR OKIEN POGODOWYCH NA OGNISKO")
    print("🔥"*35 + "\n")
    
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
            best_day = suitable_days[0]  # Pierwszy dzień (najwcześniejszy)
            print(f"\n🎯 NAJLEPSZY DZIEŃ: {best_day['date'].strftime('%d.%m.%Y')}")
            print(f"   z {best_day['total_suitable']} godzinami dobrej pogody")
            
            # Pokaż godziny dla najlepszego dnia
            if best_day['suitable_hours']:
                hours_str = ", ".join([h['time'].strftime("%H:%M") for h in best_day['suitable_hours']])
                print(f"   Godziny: {hours_str}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())