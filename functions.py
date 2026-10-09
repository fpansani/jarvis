import re
from datetime import datetime
from words import commands
import requests


def find_command(text):
    text = text.lower()
    for category, group in commands.items():
        for name, keywords in group.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", text):
                    return category, name
    return None

def time():
    agora = datetime.now()
    return agora.strftime("São %H horas e %M minutos")

def degree():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": -23.55,       # São Paulo
        "longitude": -46.63,
        "current": "temperature_2m",
    }
    response = requests.get(url, params=params, timeout=5)
    data = response.json()
    temp = data["current"]["temperature_2m"]
    return f"Faz {temp:.0f} graus agora"