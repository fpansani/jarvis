import time

import pyautogui

from .comum import (Plano, aguardar_titulo, erro, iniciar_programa, mencionou,
                   rodar_isolado, seguro)

# "jarvis, abra o excel."                    -> abrir
# "jarvis, crie uma nova planilha no excel." -> novo
RESPOSTAS = {
    "abrir": "Certo, irei abrir o Excel.",
    "novo": "Certo, irei abrir e criar uma nova planilha no Excel.",
}


def _eh_excel(titulo):
    """Tela inicial ('Excel') ou planilha aberta ('Pasta1 - Excel')."""
    return titulo == "excel" or titulo.endswith(" - excel")


def _eh_planilha(titulo):
    return titulo.endswith(" - excel")


def detectar_modo(frase):
    if mencionou(frase, "novo", "nova", "crie", "criar", "cria", "documento"):
        return "novo"
    return "abrir"


@seguro("abrir o Excel")
def abrir_excel():
    return iniciar_programa("excel", _eh_excel, "Excel", timeout=30)


@seguro("criar uma nova planilha no Excel")
def nova_planilha():
    if not iniciar_programa("excel", _eh_excel, "Excel", timeout=30):
        return False

    # Cria uma nova planilha: espera a tela inicial carregar e aperta Enter
    time.sleep(2)
    pyautogui.press("enter")
    if not aguardar_titulo(_eh_planilha, timeout=15):
        erro("Não consegui confirmar a criação da nova planilha no Excel.")
        return False
    return True


# ---------------------------------------------------------------- plano

def planejar(frase=""):
    modo = detectar_modo(frase)
    return Plano(RESPOSTAS[modo], abrir_excel if modo == "abrir" else nova_planilha)


if __name__ == "__main__":
    # python excel.py abra o excel
    # python excel.py crie uma nova planilha no excel
    rodar_isolado(planejar)
