import requests

API_KEY = "pebLkhwqbzwZaKjOPI87kgnoL6cA2bHx"

url = "https://api.tomorrow.io/v4/weather/forecast"
params = {
    "location": "52.23,21.01",
    "timesteps": "1d",
    "apikey": API_KEY
}

response = requests.get(url, params=params)
data = response.json()

daily = data["timelines"]["daily"]

print("Prognoza na 7 dni:\n")

for day in daily[:7]:
    date = day["time"][:10]
    values = day["values"]

    temp_max = values.get("temperatureMax")
    temp_min = values.get("temperatureMin")
    wind = values.get("windSpeedAvg")
    rain = values.get("precipitationProbabilityAvg")

    print(f"{date}")
    print(f"  🌡️ {temp_min}°C – {temp_max}°C")
    print(f"  💨 Wiatr: {wind} m/s")
    print(f"  🌧️ Szansa opadów: {rain}%\n")
