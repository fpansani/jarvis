from .comum import Plano, abrir_site, mencionou, rodar_isolado

URL = "cnnbrasil.com.br"
TITULO_ESPERADO = "CNN"  # trecho do título da aba quando o site carrega

# "jarvis, abra a CNN Brasil."                              -> resposta curta
# "jarvis, eu quero ver notícias." / "me mostre as notícias do dia."  -> resposta longa
RESPOSTA_ABRIR = "Certo, irei abrir o site da CNN Brasil no seu navegador."
RESPOSTA_NOTICIAS = ("Certo, irei abrir o site da CNN Brasil no seu navegador "
                     "para você ver as notícias atuais.")


def abrir_noticias():
    return abrir_site(URL, TITULO_ESPERADO)


def planejar(frase=""):
    resposta = RESPOSTA_ABRIR if mencionou(frase, "cnn") else RESPOSTA_NOTICIAS
    return Plano(resposta, abrir_noticias)


if __name__ == "__main__":
    # python noticias.py me mostre as notícias do dia
    rodar_isolado(planejar)
