import json
import os
from datetime import datetime, timedelta, time
from pathlib import Path
import argparse
from typing import List, Dict, Tuple, Optional
import sys

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
parametry
Opcja	Opis	Domyślnie
--plik	Ścieżka do pliku JSON	dane/weather_data.json
--temp	Minimalna temperatura	15.0°C
--godziny	Minimalna liczba godzin	4
--start	Godzina początkowa	16
--koniec	Godzina końcowa	24
--dni	Liczba dni do analizy	5
--ciagle	Wymagaj ciągłości godzin	False
--pokaz-wszystkie	Pokaż wszystkie dni	False
--verbose, -v	Szczegółowe informacje	False
"""
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

# Kody uznawane za "słoneczne" lub z lekkim zachmurzeniem
SUNNY_CODES = [1000, 1100, 1101]  # Bezchmurnie, przeważnie bezchmurnie, częściowe zachmurzenie

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
                        help='Szczegółowe informacje o każdej godzinie')
    
    return parser


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


def is_sunny(weather_code: Optional[int], cloudy_codes: List[int] = None) -> bool:
    """Sprawdź, czy kod pogodowy oznacza słoneczną pogodę"""
    if weather_code is None:
        return False
    if cloudy_codes is not None:
        return weather_code in cloudy_codes
    return weather_code in SUNNY_CODES


def format_hour(dt: datetime) -> str:
    """Formatuj godzinę do wyświetlenia"""
    return dt.strftime("%d.%m %H:%M")


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
            sunny_ok = is_sunny(weather_code)
            
            hours_in_range.append({
                'time': local_time,
                'temp': temp,
                'weather_code': weather_code,
                'weather_desc': get_weather_description(weather_code),
                'temp_ok': temp_ok,
                'sunny_ok': sunny_ok,
                'suitable': temp_ok and sunny_ok
            })
        
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


def display_results(results: List[Dict], args):
    """Wyświetl wyniki w czytelnej formie"""
    
    if not results:
        print("❌ Brak danych do wyświetlenia")
        return
    
    print("\n" + "="*70)
    print("📋 WYNIKI ANALIZY".center(70))
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
            
            # Pokaż szczegóły godzin
            if args.verbose and day['suitable_hours']:
                print("     • Godziny:")
                for h in day['suitable_hours']:
                    time_str = h['time'].strftime("%H:%M")
                    print(f"        - {time_str}: {h['temp']:.1f}°C, {h['weather_desc']}")
            
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
                    for h in day['all_hours']:
                        marker = "✅" if h['suitable'] else "❌"
                        time_str = h['time'].strftime("%H:%M")
                        temp_str = f"{h['temp']:.1f}°C" if h['temp'] is not None else "brak"
                        print(f"        {marker} {time_str}: {temp_str}, {h['weather_desc']}")
                        
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
    
    # Wyświetl powitanie
    print("\n" + "🔥"*35)
    print("         ANALIZATOR OKIEN POGODOWYCH NA OGNISKO")
    print("🔥"*35 + "\n")
    
    # Wczytaj dane
    data = load_json_data(args.plik)
    if not data:
        return 1
    
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
    
    return 0


if __name__ == "__main__":
    sys.exit(main())