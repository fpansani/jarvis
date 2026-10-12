"""Instagram do colégio: abre o perfil no Edge e fecha o aviso de login.

"jarvis, abra o instagram/insta/a rede social do colégio."

Testar sozinho (da pasta do projeto):  python -m automacao.instagram abra o instagram do colégio
"""
import time

import pyautogui

from .comum import Plano, abrir_site, log, rodar_isolado

URL = "instagram.com/colegio_clovis"
TITULO_ESPERADO = "colegio_clovis"  # trecho do título da aba quando o site carrega

RESPOSTA = "Certo, irei abrir o instagram do Colégio Clóvis no seu navegador."


def _cancelar_aviso_de_login():
    time.sleep(1.5)
    log("Fechando o aviso de login do Instagram (ESC).")
    pyautogui.press("esc")


def abrir_instagram():
    return abrir_site(URL, TITULO_ESPERADO, pos_abertura=_cancelar_aviso_de_login)


def planejar(frase=""):
    return Plano(RESPOSTA, abrir_instagram)


if __name__ == "__main__":
    rodar_isolado(planejar)
