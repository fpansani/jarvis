"""Word: abre o programa, cria um documento e, se pedido, escreve uma saudação.

"jarvis, abra o editor de texto/word."                                  -> abrir
"jarvis, crie um novo documento no editor de texto/word." / "faça um texto no word" -> novo
"jarvis, crie um novo documento no word e escreva uma saudação."        -> saudacao

Testar sozinho (da pasta do projeto):  python -m automacao.word crie um novo documento no word
"""
import time

import pyautogui

from .comum import (Plano, aguardar_titulo, encontrar_e_clicar, erro, iniciar_programa,
                    janela_ativa_eh, log, mencionou, rodar_isolado, seguro, simplificar,
                    titulo_janela)

RESPOSTAS = {
    "abrir": "Certo, irei abrir o Word.",
    "novo": "Certo, irei criar um novo documento no Word.",
    "saudacao": "Certo, irei criar um novo documento e escrever uma saudação no Word.",
}

# Palavras que pedem um documento novo (sem elas, o Jarvis só abre o Word)
PALAVRAS_CRIAR = ("novo", "nova", "crie", "criar", "cria", "faça", "faz", "fazer", "documento")

SAUDACAO = "Oi, seja bem-vindo a nossa Feira Cultural!"
IMAGEM_AUMENTAR_FONTE = "word-aumentartamanhofonte.png"


def _eh_word(titulo):
    """Tela inicial ('Word') ou documento aberto ('Documento1 - Word')."""
    return titulo == "word" or titulo.endswith(" - word")


def _eh_documento(titulo):
    return titulo.endswith(" - word")


def detectar_modo(frase):
    if mencionou(frase, "saudação", "saudações", "cumprimento"):
        return "saudacao"
    if mencionou(frase, *PALAVRAS_CRIAR):
        return "novo"
    return "abrir"


@seguro("abrir o Word")
def abrir_word():
    return iniciar_programa("word", _eh_word, "Word", timeout=30)


@seguro("criar um novo documento no Word")
def novo_documento(saudacao=False):
    # Se um documento do Word já estava na frente, ele não pode ser confundido com o novo:
    # senão o Enter e a saudação iriam parar nele.
    antes = simplificar(titulo_janela())
    evitar = antes if _eh_documento(antes) else None
    eh_o_novo = lambda titulo: _eh_documento(titulo) and titulo != evitar  # noqa: E731

    if not iniciar_programa("word", _eh_word, "Word", timeout=30, evitar=evitar):
        return False

    # Cria um novo documento: espera a tela inicial carregar e aperta Enter
    time.sleep(2)
    pyautogui.press("enter")
    if not aguardar_titulo(eh_o_novo, timeout=15):
        erro("Não consegui confirmar a criação do novo documento no Word.")
        return False

    if saudacao:
        return _escrever_saudacao(eh_o_novo)
    return True


def _escrever_saudacao(eh_o_novo):
    time.sleep(1)

    # Aumenta o tamanho da fonte (clica 2x no botão "A^"). Se não achar, segue com o padrão.
    if not encontrar_e_clicar([IMAGEM_AUMENTAR_FONTE], tentativas=3, duplo=True):
        log("Botão de aumentar a fonte não encontrado. Seguindo com o tamanho padrão...")

    if not janela_ativa_eh(eh_o_novo):
        erro("O Word não está na frente; cancelei para não escrever em outra janela.")
        return False

    pyautogui.hotkey("ctrl", "n")  # negrito (no Word em português; em inglês seria CTRL+B)
    pyautogui.write(SAUDACAO, interval=0.1)
    return True


# ---------------------------------------------------------------- plano

def planejar(frase=""):
    modo = detectar_modo(frase)
    if modo == "abrir":
        return Plano(RESPOSTAS[modo], abrir_word)
    return Plano(RESPOSTAS[modo], lambda: novo_documento(saudacao=(modo == "saudacao")))


if __name__ == "__main__":
    rodar_isolado(planejar)
