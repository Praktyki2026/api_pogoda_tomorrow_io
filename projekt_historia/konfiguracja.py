import os

folder = os.path.dirname(os.path.abspath(__file__))

sciezka_do_pliku = os.path.join(folder, "klucz.txt")

def get_config_value(key):
    """funkcja ta pobiera wartości z pliku config.txt"""

    with open(sciezka_do_pliku, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                k,v =line.split("=",1)
                if k==key:
                    return v.strip()

def get_api_key():
    """ta funkcja zwraca IP z pliku config lub gdy go nie ma albo jest problem zwraca 127.0.0.1"""
    return get_config_value("KLUCZ")

def get_location():
    """funkcja do zwracania portu na którym jest serwer http"""
    return get_config_value("LOKALIZACJA")