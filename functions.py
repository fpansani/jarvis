import re
from datetime import datetime
from words import commands
import requests

from automacao import calc as calc_auto
from automacao import excel as excel_auto
from automacao import instagram as insta_auto
from automacao import noticias as news_auto
from automacao import paint as paint_auto
from automacao import site_clovis as site_auto
from automacao import word as word_auto
from automacao import youtube as yt_auto
from automacao.comum import Plano, simplificar, tem_internet


def has_internet(timeout=3):
    """True se conseguir abrir conexão com o Google (usado no reconhecimento de voz)."""
    return tem_internet(timeout)


def find_command(text):
    # simplificar: minúsculas e sem acentos, então "videos" casa com "vídeo" e vice-versa
    text = simplificar(text)
    for category, group in commands.items():
        for name, keywords in group.items():
            for keyword in keywords:
                if re.search(rf"\b{re.escape(simplificar(keyword))}\b", text):
                    return category, name
    return None

def time():
    agora = datetime.now()
    return agora.strftime("São %H horas e %M minutos")

CIDADE_PADRAO = "Santo André"
COORDENADAS_PADRAO = (-23.6639, -46.5383)

_PALAVRAS_CLIMA = {"temperatura", "tempo", "clima"}
_PREPOSICOES = {"em", "de", "do", "da", "no", "na", "para"}
# palavras que encerram o nome da cidade: "em Santos agora", "em Curitiba hoje"
_FIM_DA_CIDADE = {"agora", "hoje", "amanha", "atualmente", "aqui", "daqui", "momento", "neste",
                  "nesse", "minha", "nossa", "por", "favor", "jarvis"}


class CityNotFound(Exception):
    """A cidade pedida não foi encontrada pelo serviço de geocodificação."""


def extract_city(frase):
    """Cidade pedida na frase ("qual a temperatura em São Paulo?" -> "São Paulo"), ou None."""
    palavras = [p.strip(".,;:!?") for p in frase.split()]
    palavras = [p for p in palavras if p]
    simples = [simplificar(p) for p in palavras]

    inicio = next((i for i, p in enumerate(simples) if p in _PALAVRAS_CLIMA), 0)
    for i in range(inicio + 1, len(palavras)):
        if simples[i] not in _PREPOSICOES:
            continue

        cidade = []
        for palavra, simples_ in zip(palavras[i + 1:], simples[i + 1:]):
            if simples_ in _FIM_DA_CIDADE:
                break
            cidade.append((palavra, simples_))

        if cidade and cidade[0][1] == "cidade":              # "na cidade de Santos"
            cidade.pop(0)
            if cidade and cidade[0][1] in _PREPOSICOES:
                cidade.pop(0)
        while cidade and cidade[-1][1] in _PREPOSICOES:      # "em Santos no momento"
            cidade.pop()

        if cidade:
            return " ".join(palavra for palavra, _ in cidade)
    return None


def find_city(nome):
    """(nome, latitude, longitude) da cidade, via Open-Meteo. Prefere cidades do Brasil."""
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": nome, "count": 10, "language": "pt", "format": "json"},
        timeout=5,
    )
    resultados = response.json().get("results") or []

    # a busca também devolve nomes parecidos ("Sao Paulo" traz "Frei Paulo"): exige o mesmo nome
    alvo = simplificar(nome)
    iguais = [r for r in resultados if simplificar(r.get("name", "")) == alvo]
    if not iguais:
        raise CityNotFound(nome)

    escolhida = next((r for r in iguais if r.get("country_code") == "BR"), iguais[0])
    return escolhida["name"], escolhida["latitude"], escolhida["longitude"]


def degree(frase=""):
    cidade = extract_city(frase)
    if cidade is None or simplificar(cidade) == simplificar(CIDADE_PADRAO):
        nome = CIDADE_PADRAO
        latitude, longitude = COORDENADAS_PADRAO
    else:
        nome, latitude, longitude = find_city(cidade)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m",
    }
    response = requests.get(url, params=params, timeout=5)
    data = response.json()
    temp = round(data["current"]["temperature_2m"])
    return f"A temperatura em {nome} é de {temp}ºC."


# Um comando por palavra de words.py. Cada um recebe a frase falada (é ela que decide,
# por exemplo, entre "só abrir" e "criar documento" no Word) e devolve um Plano:
# a resposta do Jarvis + a ação PyAutoGUI que roda 2 s depois da resposta.

def calc(frase):
    return calc_auto.planejar(frase)

def paint(frase):
    return paint_auto.planejar(frase)

def yt(frase):
    return yt_auto.planejar(frase)

def word(frase):
    return word_auto.planejar(frase)

def excel(frase):
    return excel_auto.planejar(frase)

def news(frase):
    return news_auto.planejar(frase)

def site(frase):
    return site_auto.planejar(frase)

def insta(frase):
    return insta_auto.planejar(frase)


COMANDOS = {
    "calc": calc,
    "paint": paint,
    "yt": yt,
    "word": word,
    "excel": excel,
    "news": news,
    "site": site,
    "insta": insta,
}


def respond(category, name, frase=""):
    """Plano (resposta + ação opcional) do Jarvis para o comando detectado."""
    if name == "time":
        return Plano(time())

    if name == "degree":
        try:
            return Plano(degree(frase))
        except CityNotFound as e:
            return Plano(f"Não encontrei a cidade {e}.")
        except (requests.RequestException, KeyError, ValueError):
            return Plano("Não consegui consultar a temperatura. Verifique sua conexão com a internet.")

    comando = COMANDOS.get(name)
    if comando:
        return comando(frase)

    return Plano(f"<RESPOSTA - detectado dicionário {category}>")