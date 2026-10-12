"""Excel: abre o programa e, se pedido, cria uma planilha em branco.

"jarvis, abra o excel."                                              -> abrir
"jarvis, crie uma nova planilha no excel." / "faça uma planilha no excel" -> novo

Testar sozinho (da pasta do projeto):  python -m automacao.excel crie uma nova planilha no excel
"""
import time

import pyautogui

from .comum import (Plano, aguardar_titulo, erro, iniciar_programa, log, mencionou,
                    rodar_isolado, seguro, simplificar, titulo_janela)

RESPOSTAS = {
    "abrir": "Certo, irei abrir o Excel.",
    "novo": "Certo, irei abrir e criar uma nova planilha no Excel.",
}

# Palavras que pedem uma planilha nova (sem elas, o Jarvis só abre o Excel)
PALAVRAS_CRIAR = ("novo", "nova", "crie", "criar", "cria", "faça", "faz", "fazer", "documento")


def _eh_excel(titulo):
    """Tela inicial ('Excel') ou planilha aberta ('Pasta1 - Excel')."""
    return titulo == "excel" or titulo.endswith(" - excel")


def _eh_planilha(titulo):
    return titulo.endswith(" - excel")


def detectar_modo(frase):
    if mencionou(frase, *PALAVRAS_CRIAR):
        return "novo"
    return "abrir"


@seguro("abrir o Excel")
def abrir_excel():
    return iniciar_programa("excel", _eh_excel, "Excel", timeout=30)


@seguro("criar uma nova planilha no Excel")
def nova_planilha():
    # Uma planilha que já estava na frente não pode ser confundida com a nova (o Enter iria nela).
    antes = simplificar(titulo_janela())
    evitar = antes if _eh_planilha(antes) else None
    eh_a_nova = lambda titulo: _eh_planilha(titulo) and titulo != evitar  # noqa: E731

    if not iniciar_programa("excel", _eh_excel, "Excel", timeout=30, evitar=evitar):
        return False

    # Cria uma nova planilha: espera a tela inicial carregar e aperta Enter
    time.sleep(2)
    pyautogui.press("enter")
    if not aguardar_titulo(eh_a_nova, timeout=15):
        erro("Não consegui confirmar a criação da nova planilha no Excel.")
        return False
    log("Nova planilha criada.")
    return True


# ---------------------------------------------------------------- plano

def planejar(frase=""):
    modo = detectar_modo(frase)
    return Plano(RESPOSTAS[modo], abrir_excel if modo == "abrir" else nova_planilha)


if __name__ == "__main__":
    rodar_isolado(planejar)
