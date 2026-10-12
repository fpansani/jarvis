from .comum import Plano, abrir_site, mencionou, rodar_isolado

URL = "youtube.com"
TITULO_ESPERADO = "YouTube"  # trecho do título da aba quando o site carrega

# "jarvis, abra o youtube."          -> resposta curta
# "jarvis, eu queria ver vídeos."    -> resposta longa
RESPOSTA_ABRIR = "Certo, irei abrir o YouTube no navegador."
RESPOSTA_VER_VIDEOS = "Certo, irei abrir o YouTube no navegador para você poder assistir vídeos."


def abrir_youtube():
    return abrir_site(URL, TITULO_ESPERADO)


def planejar(frase=""):
    resposta = RESPOSTA_ABRIR if mencionou(frase, "youtube", "yt") else RESPOSTA_VER_VIDEOS
    return Plano(resposta, abrir_youtube)


if __name__ == "__main__":
    # python youtube.py abra o youtube
    rodar_isolado(planejar)
