"""Funções compartilhadas pelos scripts PyAutoGUI do Jarvis.

Cada script (calc.py, word.py, youtube.py, ...) expõe uma função `planejar(frase)`
que devolve um `Plano`: a resposta do Jarvis + a ação (função sem argumentos) a
executar. `executar_plano` imprime a resposta, espera ATRASO_APOS_RESPOSTA segundos
e só então roda a ação.

Toda ação passa pelo decorator `seguro`: nenhum erro do PyAutoGUI derruba o Jarvis.
A ação devolve True (deu certo) ou False (algo falhou; a mensagem já foi mostrada).
"""
import functools
import os
import re
import socket
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pyautogui

pyautogui.PAUSE = 0.4
pyautogui.FAILSAFE = True  # levar o mouse a um canto da tela interrompe a automação

PASTA_IMGS = Path(__file__).resolve().parent / "imgs"

ATRASO_APOS_RESPOSTA = 2   # segundos entre a resposta do Jarvis e a execução
ESPERA_MENU_INICIAR = 1    # segundos para o menu Iniciar abrir antes de digitar
ALERTAS = False            # True nos testes isolados (python calc.py): mostra caixas de diálogo

IMAGENS_BARRA = ["edge-searchbar.png", "edge-searchbar-blink.png"]

_SEM_OPENCV = False


# ---------------------------------------------------------------- mensagens

# Mensagens de depuração (tentativas, títulos de janela, tempos, comando detectado...).
# False: só aparecem as respostas do Jarvis e os erros. Mude para True para reativá-las.
# Também dá para ligar sem mexer no código, antes de rodar o Jarvis:
#   CMD:        set JARVIS_DEBUG=1
#   PowerShell: $env:JARVIS_DEBUG = "1"
DEBUG = False

if os.environ.get("JARVIS_DEBUG", "").strip() not in ("", "0"):
    DEBUG = True


def log(texto):
    """Mensagem de depuração: só aparece com DEBUG = True."""
    if DEBUG:
        print(f"[debug] {texto}")


def erro(texto, titulo="Erro"):
    """Mostra um erro; nos testes isolados também abre a caixa de diálogo."""
    print(texto)
    if ALERTAS:
        try:
            pyautogui.alert(text=texto, title=titulo, button="OK") # type: ignore
        except Exception:
            pass


def fim_da_execucao():
    if ALERTAS:
        try:
            pyautogui.alert(text="Fim da execucao", title="", button="OK") # type: ignore
        except Exception:
            pass


# ---------------------------------------------------------------- plano (resposta + ação)

@dataclass
class Plano:
    resposta: str
    acao: Optional[Callable[[], bool]] = None


def _nome_acao(acao):
    nome = getattr(acao, "__name__", "")
    return "ação" if not nome or nome == "<lambda>" else nome


def executar_plano(plano):
    """Imprime a resposta, espera ATRASO_APOS_RESPOSTA s e executa a ação."""
    print(plano.resposta)
    if plano.acao is None:
        return False
    time.sleep(ATRASO_APOS_RESPOSTA)

    nome = _nome_acao(plano.acao)
    log(f"Executando {nome}...")
    inicio = time.time()
    sucesso = bool(plano.acao())
    log(f"{nome} terminou em {time.time() - inicio:.1f} s ({'sucesso' if sucesso else 'falhou'}).")
    return sucesso


def rodar_isolado(planejar):
    """Para `python calc.py calcule 5 vezes 2`: usa os argumentos como a frase falada."""
    global ALERTAS
    ALERTAS = True
    frase = " ".join(sys.argv[1:])
    if executar_plano(planejar(frase)):
        fim_da_execucao()


# ---------------------------------------------------------------- erros

def liberar_teclas():
    """Solta modificadores que podem ter ficado presos após uma falha no meio de um atalho."""
    failsafe = pyautogui.FAILSAFE
    pyautogui.FAILSAFE = False  # senão o próprio keyUp poderia levantar FailSafeException de novo
    try:
        for tecla in ("ctrl", "alt", "shift", "win"):
            try:
                pyautogui.keyUp(tecla)
            except Exception:
                pass
    finally:
        pyautogui.FAILSAFE = failsafe


def seguro(descricao):
    """Captura os erros possíveis da automação, mostra uma mensagem clara e devolve False.

    A ordem dos except importa: FailSafeException e ImageNotFoundException são
    subclasses de PyAutoGUIException. KeyboardInterrupt (Ctrl+C) não é capturado.
    """
    def decorador(funcao):
        @functools.wraps(funcao)
        def wrapper(*args, **kwargs):
            try:
                return funcao(*args, **kwargs)
            except pyautogui.FailSafeException:
                liberar_teclas()
                erro("Execução interrompida: o mouse foi levado a um canto da tela (fail-safe do PyAutoGUI).")
            except pyautogui.ImageNotFoundException:
                liberar_teclas()
                erro(f"Não encontrei na tela a imagem necessária para {descricao}.")
            except pyautogui.PyAutoGUIException as e:
                liberar_teclas()
                erro(f"O PyAutoGUI não conseguiu {descricao}: {e}\n"
                     "(Se a mensagem fala de PyScreeze/Pillow, rode: pip install -r requirements.txt)")
            except OSError as e:
                liberar_teclas()
                erro(f"Erro de arquivo ou sistema ao {descricao}: {e}")
            except Exception as e:
                liberar_teclas()
                erro(f"Erro inesperado ao {descricao}: {type(e).__name__}: {e}")
            return False
        return wrapper
    return decorador


# ---------------------------------------------------------------- texto e janelas

def simplificar(texto):
    """Minúsculas, sem acentos, sem caracteres invisíveis e com espaços normalizados.

    O Edge, por exemplo, coloca um espaço de largura zero em "Microsoft Edge" no título.
    """
    texto = unicodedata.normalize("NFKC", texto or "")
    texto = "".join(c for c in texto if c not in "​‌‍⁠﻿")
    texto = re.sub(r"[‐-―−]", "-", texto)
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def mencionou(frase, *palavras):
    """True se alguma das palavras aparece inteira na frase (sem acento/maiúscula)."""
    f = simplificar(frase)
    return any(re.search(rf"\b{re.escape(simplificar(p))}\b", f) for p in palavras)


def titulo_janela():
    """Título da janela ativa (vazio se não for possível obter)."""
    try:
        return pyautogui.getActiveWindowTitle() or "" # type: ignore
    except Exception:
        return ""


def _criar_teste(condicao):
    """condicao: texto, lista de textos (contém) ou função que recebe o título simplificado."""
    if callable(condicao):
        return lambda titulo: bool(condicao(simplificar(titulo)))
    trechos = [condicao] if isinstance(condicao, str) else list(condicao)
    trechos = [simplificar(t) for t in trechos]
    return lambda titulo: any(t in simplificar(titulo) for t in trechos)


def janela_ativa_eh(condicao):
    return _criar_teste(condicao)(titulo_janela())


def aguardar_titulo(condicao, timeout=10, intervalo=0.5):
    """Espera até a janela ativa satisfazer 'condicao'. False se estourar o timeout."""
    teste = _criar_teste(condicao)
    inicio = time.time()
    fim = inicio + timeout
    ultimo = None
    while time.time() < fim:
        titulo = titulo_janela()
        if titulo != ultimo:              # registra só quando o título muda
            log(f'Janela ativa: "{titulo}"')
            ultimo = titulo
        if teste(titulo):
            log(f"Janela esperada encontrada em {time.time() - inicio:.1f} s.")
            return True
        time.sleep(intervalo)
    log(f'Tempo esgotado ({timeout} s) esperando a janela. Último título: "{ultimo}"')
    return False


def tem_internet(timeout=3):
    try:
        socket.create_connection(("www.google.com", 443), timeout=timeout).close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- abrir programas

def iniciar_programa(busca, condicao_janela, nome, timeout=20):
    """Abre um programa pelo menu Iniciar e espera a janela dele ficar ativa."""
    log(f'Abrindo "{nome}" pelo menu Iniciar (busca: "{busca}").')
    pyautogui.press("win")
    time.sleep(ESPERA_MENU_INICIAR)  # sem isso as primeiras letras se perdem
    pyautogui.write(busca, interval=0.2)
    pyautogui.press("enter")

    if aguardar_titulo(condicao_janela, timeout):
        return True
    erro(f"Não consegui confirmar que o {nome} abriu (esperei {timeout} s).")
    return False


# ---------------------------------------------------------------- imagens

def _caminho_imagem(imagem):
    caminho = Path(imagem)
    return caminho if caminho.is_absolute() else PASTA_IMGS / caminho.name


def _localizar(imagem, confianca):
    """Centro da imagem na tela, ou None. Sem OpenCV, busca sem margem de tolerância."""
    global _SEM_OPENCV
    try:
        if _SEM_OPENCV:
            return pyautogui.locateCenterOnScreen(str(imagem))
        return pyautogui.locateCenterOnScreen(str(imagem), confidence=confianca)
    except pyautogui.ImageNotFoundException:
        return None
    except NotImplementedError:
        _SEM_OPENCV = True
        log("OpenCV não instalado: procurando a imagem sem tolerância (pip install opencv-python).")
        return _localizar(imagem, confianca)


def encontrar_e_clicar(imagens, tentativas=5, espera=1, confianca=0.8, duplo=False):
    """Tenta cada imagem, em ordem, por várias rodadas. True se achou e clicou."""
    caminhos = [_caminho_imagem(i) for i in imagens]
    existentes = [c for c in caminhos if c.exists()]
    for c in caminhos:
        if c not in existentes:
            log(f'Imagem "{c.name}" não existe em {c.parent}.')
    if not existentes:
        return False

    for tentativa in range(1, tentativas + 1):
        for caminho in existentes:
            pos = _localizar(caminho, confianca)
            if pos is not None:
                (pyautogui.doubleClick if duplo else pyautogui.click)(pos)
                log(f'Encontrou "{caminho.name}" na tentativa {tentativa}.')
                return True

        log(f"Tentativa {tentativa}/{tentativas} falhou. Aguardando...")
        time.sleep(espera)

    return False


# ---------------------------------------------------------------- navegador (Edge)

def _eh_edge(titulo):
    return titulo.endswith("microsoft edge")


def _abrir_por_atalho(url, titulo_esperado):
    """Método principal: Ctrl+L foca a barra de endereço do Edge."""
    pyautogui.hotkey("ctrl", "l")
    pyautogui.write(url, interval=0.1)
    pyautogui.press("enter")
    return aguardar_titulo(titulo_esperado)


def _abrir_por_imagem(url, titulo_esperado):
    """Fallback: clica na barra de endereço reconhecendo a imagem dela."""
    if not encontrar_e_clicar(IMAGENS_BARRA):
        return False
    pyautogui.write(url, interval=0.1)
    pyautogui.press("enter")
    return aguardar_titulo(titulo_esperado)


@seguro("abrir o site no Edge")
def abrir_site(url, titulo_esperado, pos_abertura=None):
    """Abre o Edge e carrega 'url'. 'titulo_esperado': trecho(s) do título da aba quando o site carrega."""
    if not tem_internet():
        erro("Sem conexão com a internet: não consigo abrir o site.")
        return False

    # --- Abrir o Edge ---
    log(f"Abrindo o Edge para carregar {url}.")
    pyautogui.press("win")
    time.sleep(ESPERA_MENU_INICIAR)
    pyautogui.write("edge", interval=0.2)
    pyautogui.press("enter")

    # Espera a janela do Edge ficar ativa (até 10 s)
    if not aguardar_titulo(_eh_edge, timeout=10):
        log("Não confirmei que o Edge ficou ativo. Seguindo mesmo assim...")
    time.sleep(1)

    # --- Abrir o site ---
    log("Tentando com Ctrl+L...")
    if _abrir_por_atalho(url, titulo_esperado):
        log("Site aberto com o atalho.")
    else:
        log("Atalho não funcionou. Tentando por reconhecimento de imagem...")
        if _abrir_por_imagem(url, titulo_esperado):
            log("Site aberto com a imagem.")
        else:
            erro("Não consegui abrir o site.")
            return False

    if pos_abertura is not None:
        pos_abertura()
    return True
