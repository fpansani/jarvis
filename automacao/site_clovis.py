from .comum import Plano, abrir_site, rodar_isolado

URL = "portalclovis.com.br"
TITULO_ESPERADO = "Portal Clóvis"  # trecho do título da aba quando o site carrega

# "jarvis, abra o site/portal do colégio."
RESPOSTA = "Certo, irei abrir o site do Colégio Clóvis no seu navegador."


def abrir_site_clovis():
    return abrir_site(URL, TITULO_ESPERADO)


def planejar(frase=""):
    return Plano(RESPOSTA, abrir_site_clovis)


if __name__ == "__main__":
    rodar_isolado(planejar)
