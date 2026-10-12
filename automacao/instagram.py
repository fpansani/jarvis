import time

import pyautogui

from .comum import Plano, abrir_site, rodar_isolado

URL = "instagram.com/colegio_clovis"
TITULO_ESPERADO = "colegio_clovis"  # trecho do título da aba quando o site carrega

# "jarvis, abra o instagram/insta/a rede social do colégio."
RESPOSTA = "Certo, irei abrir o instagram do Colégio Clóvis no seu navegador."


def _cancelar_aviso_de_login():
    time.sleep(1.5)
    pyautogui.press("esc")


def abrir_instagram():
    return abrir_site(URL, TITULO_ESPERADO, pos_abertura=_cancelar_aviso_de_login)


def planejar(frase=""):
    return Plano(RESPOSTA, abrir_instagram)


if __name__ == "__main__":
    rodar_isolado(planejar)
