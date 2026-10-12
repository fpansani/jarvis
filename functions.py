"""Comandos do Jarvis: detecta o comando na frase (words.py) e monta a resposta + ação.

- time e degree respondem direto (hora atual; temperatura pela Open-Meteo).
- Os outros comandos ficam no pacote automacao/ (uma automação PyAutoGUI por comando).
"""
import re
from datetime import datetime

import requests

from automacao import calc as calc_auto
from automacao import excel as excel_auto
from automacao import instagram as insta_auto
from automacao import noticias as news_auto
from automacao import paint as paint_auto
from automacao import site_clovis as site_auto
from automacao import word as word_auto
from automacao import youtube as yt_auto
from automacao.comum import Plano, log, simplificar, tem_internet
from words import app_names, commands

TEMPO_LIMITE_API = 5     # segundos esperando a Open-Meteo responder


def has_internet(timeout=3):
    """True se conseguir abrir conexão com o Google (usado para escolher o modo off-line)."""
    return tem_internet(timeout)


# ---------------------------------------------------------------- detectar o comando

_NOMES = {simplificar(n) for n in app_names}


def find_command(text):
    """(categoria, comando) da palavra-chave encontrada na frase, ou None.

    A comparação ignora acentos e maiúsculas. Se a frase tiver palavras-chave de comandos
    diferentes, os nomes de programas e sites (app_names em words.py) vencem as palavras
    genéricas e, entre palavras do mesmo tipo, vence a mais longa:
    "abra o site da CNN" -> news; "abra o site do Instagram" -> insta.
    """
    text = simplificar(text)
    encontrados = []    # (é nome?, tamanho, ordem, categoria, comando, palavra-chave)
    for category, group in commands.items():
        for name, keywords in group.items():
            for keyword in keywords:
                chave = simplificar(keyword)
                if re.search(rf"\b{re.escape(chave)}\b", text):
                    encontrados.append((chave in _NOMES, len(chave), -len(encontrados), category, name, keyword))

    if not encontrados:
        log(f'Nenhuma palavra-chave encontrada em "{text}"')
        return None

    *_, category, name, keyword = max(encontrados)
    if len({(c, n) for *_, c, n, _ in encontrados}) > 1:
        log("Palavras-chave de comandos diferentes: "
            + ", ".join(f'{n} ("{k}")' for *_, n, k in encontrados) + f" -> vence {name}")
    log(f'Comando detectado: {category}/{name} (palavra-chave "{keyword}")')
    return category, name


# ---------------------------------------------------------------- time

def time():
    """Hora atual por extenso: "São 15 horas e 5 minutos", "É 1 hora em ponto"."""
    agora = datetime.now()
    horas, minutos = agora.hour, agora.minute
    if horas == 0:
        texto = "É meia-noite"
    elif horas == 12:
        texto = "É meio-dia"
    elif horas == 1:
        texto = "É 1 hora"
    else:
        texto = f"São {horas} horas"
    if minutos == 0:
        return f"{texto} em ponto"
    return f"{texto} e {minutos} {'minuto' if minutos == 1 else 'minutos'}"


# ---------------------------------------------------------------- degree

CIDADE_PADRAO = "Santo André"
COORDENADAS_PADRAO = (-23.6639, -46.5383)

_PALAVRAS_CLIMA = {"temperatura", "tempo", "clima"}
_PREPOSICOES = {"em", "de", "do", "da", "dos", "das", "no", "na", "para"}
# palavras que encerram o nome da cidade: "em Santos agora", "em Curitiba hoje"
_FIM_DA_CIDADE = {"agora", "hoje", "amanha", "atualmente", "aqui", "daqui", "momento", "neste",
                  "nesse", "minha", "nossa", "por", "favor", "jarvis", "qual", "como", "esta"}
_PONTUACAO = ".,;:!?"


class CityNotFound(Exception):
    """A cidade pedida não foi encontrada pelo serviço de geocodificação."""


def _separar_palavras(frase):
    """[(palavra sem pontuação, simplificada, termina com pontuação?)]"""
    palavras = []
    for bruta in frase.split():
        palavra = bruta.strip(_PONTUACAO)
        if palavra:
            palavras.append((palavra, simplificar(palavra), bruta[-1] in _PONTUACAO))
    return palavras


def _cidade_depois_de_preposicao(palavras):
    """Primeiro nome de cidade depois de uma preposição ("em São Paulo"), ou None."""
    for i, (_, simples, _) in enumerate(palavras):
        if simples not in _PREPOSICOES:
            continue

        cidade = []
        for palavra, simples_, pontuada in palavras[i + 1:]:
            if simples_ in _FIM_DA_CIDADE or simples_ in _PALAVRAS_CLIMA:
                break
            cidade.append((palavra, simples_))
            if pontuada:                                    # "em São Paulo, capital": para na vírgula
                break

        if cidade and cidade[0][1] == "cidade":             # "na cidade de Santos"
            cidade.pop(0)
            if cidade and cidade[0][1] in _PREPOSICOES:
                cidade.pop(0)
        while cidade and cidade[-1][1] in _PREPOSICOES:     # "em Santos no momento"
            cidade.pop()

        if cidade:
            return " ".join(palavra for palavra, _ in cidade)
    return None


def extract_city(frase):
    """Cidade pedida na frase ("qual a temperatura em São Paulo?" -> "São Paulo"), ou None.

    Procura depois da palavra de clima ("temperatura", "tempo", "clima") e, se não achar,
    antes dela ("Em Curitiba, qual a temperatura?").
    """
    palavras = _separar_palavras(frase)
    clima = next((i for i, (_, simples, _) in enumerate(palavras) if simples in _PALAVRAS_CLIMA), None)
    if clima is None:
        return _cidade_depois_de_preposicao(palavras)
    return (_cidade_depois_de_preposicao(palavras[clima + 1:])
            or _cidade_depois_de_preposicao(palavras[:clima]))


def _buscar_cidade(nome):
    response = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": nome, "count": 10, "language": "pt", "format": "json"},
        timeout=TEMPO_LIMITE_API,
    )
    response.raise_for_status()
    resultados = response.json().get("results") or []

    # a busca também devolve nomes parecidos ("Sao Paulo" traz "Frei Paulo"): exige o mesmo nome
    alvo = simplificar(nome)
    iguais = [r for r in resultados if simplificar(r.get("name", "")) == alvo]
    log(f'Geocodificação de "{nome}": {len(resultados)} resultado(s), {len(iguais)} com o mesmo nome.')
    if not iguais:
        return None

    escolhida = next((r for r in iguais if r.get("country_code") == "BR"), iguais[0])
    log(f"Cidade escolhida: {escolhida['name']} ({escolhida.get('admin1', '?')}, "
        f"{escolhida.get('country_code', '?')}) em {escolhida['latitude']}, {escolhida['longitude']}")
    return escolhida["name"], escolhida["latitude"], escolhida["longitude"]


def find_city(nome):
    """(nome, latitude, longitude) da cidade, via Open-Meteo. Prefere cidades do Brasil.

    Se não achar, tenta de novo sem a última palavra (o Vosk não põe vírgulas:
    "são paulo capital" -> "são paulo"). Levanta CityNotFound se nada der certo.
    """
    palavras = nome.split()
    for tamanho in range(len(palavras), max(len(palavras) - 3, 0), -1):
        tentativa = palavras[:tamanho]
        while len(tentativa) > 1 and simplificar(tentativa[-1]) in _PREPOSICOES:   # "Rio de"
            tentativa.pop()
        cidade = _buscar_cidade(" ".join(tentativa))
        if cidade:
            return cidade
    raise CityNotFound(nome)


def degree(frase=""):
    """Temperatura atual na cidade pedida na frase (ou em CIDADE_PADRAO)."""
    cidade = extract_city(frase)
    log(f"Cidade extraída da frase: {cidade!r}" + (f" (usando o padrão: {CIDADE_PADRAO})" if cidade is None else ""))
    if cidade is None or simplificar(cidade) == simplificar(CIDADE_PADRAO):
        nome = CIDADE_PADRAO
        latitude, longitude = COORDENADAS_PADRAO
    else:
        nome, latitude, longitude = find_city(cidade)

    inicio = datetime.now()
    response = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": latitude, "longitude": longitude, "current": "temperature_2m"},
        timeout=TEMPO_LIMITE_API,
    )
    response.raise_for_status()
    data = response.json()
    log(f"Open-Meteo respondeu em {(datetime.now() - inicio).total_seconds():.1f} s: "
        f"{data.get('current', {}).get('temperature_2m')} ºC")
    temp = round(data["current"]["temperature_2m"])
    return f"A temperatura em {nome} é de {temp}ºC."


# ---------------------------------------------------------------- comandos com automação
# Cada um recebe a frase falada (é ela que decide, por exemplo, entre "só abrir" e "criar
# documento" no Word) e devolve um Plano: a resposta do Jarvis + a ação PyAutoGUI, que roda
# 2 s depois da resposta.

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
        except (requests.RequestException, KeyError, TypeError, ValueError) as e:
            log(f"Falha ao consultar a temperatura: {type(e).__name__}: {e}")
            return Plano("Não consegui consultar a temperatura. Verifique sua conexão com a internet.")

    comando = COMANDOS.get(name)
    if comando:
        return comando(frase)

    # palavra-chave nova em words.py sem função correspondente aqui
    log(f'O comando "{name}" ({category}) existe em words.py, mas não tem função em functions.py.')
    return Plano(f"Ainda não sei executar o comando {name}.")
