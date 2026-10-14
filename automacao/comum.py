"""Funções compartilhadas pelas automações (PyAutoGUI) e pelo resto do Jarvis.

Cada automação (calc.py, word.py, youtube.py...) expõe `planejar(frase)`, que devolve um
`Plano`: a resposta do Jarvis + a ação (função sem argumentos) a executar. `executar_plano`
mostra a resposta, espera ATRASO_APOS_RESPOSTA segundos e só então roda a ação.

Toda ação passa pelo decorador `seguro`: nenhum erro do PyAutoGUI derruba o Jarvis. A ação
devolve True (deu certo) ou False (algo falhou; o motivo já foi mostrado).

Aqui também ficam as mensagens de depuração (DEBUG / SALVAR_LOG), usadas por todos os módulos.
"""
import functools
import os
import re
import socket
import sys
import time
import traceback
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pyautogui

pyautogui.PAUSE = 0.4      # pausa automática depois de cada comando do PyAutoGUI
pyautogui.FAILSAFE = True  # levar o mouse a um canto da tela interrompe a automação

PASTA_PROJETO = Path(__file__).resolve().parent.parent
PASTA_IMGS = Path(__file__).resolve().parent / "imgs"

ATRASO_APOS_RESPOSTA = 2       # segundos entre a resposta do Jarvis e a execução da ação
ESPERA_MENU_INICIAR = 1        # segundos para o menu Iniciar abrir antes de digitar
ESPERA_RESULTADO_BUSCA = 0.5   # segundos para a busca do menu Iniciar achar o programa antes do Enter
ALERTAS = False                # True ao testar uma automação sozinha (python -m automacao.calc ...)

# Barra de endereço do Edge, nos temas escuro e claro (o PyAutoGUI só acha a imagem do tema que
# está na tela). imagens_do_tema() põe primeiro as do tema atual do Windows.
IMAGENS_BARRA_ESCURO = ["edge-searchbar.png", "edge-searchbar-blink.png"]
IMAGENS_BARRA_CLARO = ["edge-searchbar-claro.png", "edge-searchbar-blink-claro.png"]

_SEM_OPENCV = False


# ---------------------------------------------------------------- depuração

# DEBUG: mostra no console as mensagens de depuração ([debug] + horário): tentativas, títulos de
# janela, tempos, comando detectado, erros inesperados com o traceback...
# False: o console mostra só as respostas do Jarvis e os erros.
DEBUG = False

# SALVAR_LOG: grava as mesmas mensagens (e os erros) no arquivo jarvis.log, na pasta do projeto,
# mesmo com DEBUG = False. Útil em apresentações: a tela fica limpa e, se algo falhar, o motivo
# fica registrado no arquivo.
SALVAR_LOG = False
ARQUIVO_LOG = PASTA_PROJETO / "jarvis.log"

# Também dá para ligar sem mexer no código, antes de rodar o Jarvis:
#   CMD:        set JARVIS_DEBUG=1        set JARVIS_LOG=1        set JARVIS_FORCAR_IMAGEM=1
#   PowerShell: $env:JARVIS_DEBUG = "1"   $env:JARVIS_LOG = "1"   $env:JARVIS_FORCAR_IMAGEM = "1"


def _ligado_no_ambiente(variavel):
    return os.environ.get(variavel, "").strip() not in ("", "0")


# FORCAR_IMAGEM_EDGE (só para teste): ao abrir sites, pula o CTRL+L e vai direto ao
# reconhecimento da imagem da barra de endereço. Assim dá para testar as imagens de imgs/.
# Deixe False no uso normal: o CTRL+L é mais rápido e não depende do tema nem da escala da tela.
FORCAR_IMAGEM_EDGE = False

if _ligado_no_ambiente("JARVIS_DEBUG"):
    DEBUG = True
if _ligado_no_ambiente("JARVIS_LOG"):
    SALVAR_LOG = True
if _ligado_no_ambiente("JARVIS_FORCAR_IMAGEM"):
    FORCAR_IMAGEM_EDGE = True


def _agora():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def texto_debug(texto):
    """Formata uma mensagem de depuração para o console: "[debug 14:03:22.123] texto"."""
    return f"[debug {_agora()}] {texto}"


def _gravar_log(nivel, texto):
    """Acrescenta uma linha ao jarvis.log (se SALVAR_LOG). Nunca derruba o Jarvis."""
    global SALVAR_LOG
    if not SALVAR_LOG:
        return
    try:
        data = datetime.now().strftime("%Y-%m-%d")
        with open(ARQUIVO_LOG, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"{data} {_agora()} [{nivel}] {texto}\n")
    except OSError as e:
        SALVAR_LOG = False
        print(f"Aviso: não consegui gravar o log em {ARQUIVO_LOG} ({e}). Log em arquivo desligado.")


def log(texto, mostrar=None):
    """Mensagem de depuração: aparece no console só com DEBUG = True (e vai para o arquivo
    com SALVAR_LOG = True). 'mostrar' troca o print, para não bagunçar o prompt "> "."""
    _gravar_log("debug", texto)
    if DEBUG:
        (mostrar or print)(texto_debug(texto))


def log_excecao(contexto):
    """Registra a exceção que está sendo tratada, com o traceback (no debug e no arquivo).

    Chame dentro de um `except`. Fora do debug, o usuário vê só a mensagem curta do erro.
    """
    detalhes = traceback.format_exc().rstrip()
    _gravar_log("erro", f"{contexto}\n{detalhes}")
    if DEBUG:
        print(texto_debug(f"{contexto}\n{detalhes}"))


def erro(texto, titulo="Erro"):
    """Mostra um erro (sempre visível); ao testar uma automação sozinha, abre também uma caixa de diálogo."""
    print(texto)
    _gravar_log("erro", texto)
    if ALERTAS:
        try:
            pyautogui.alert(text=texto, title=titulo, button="OK")  # type: ignore
        except Exception:
            pass


def fim_da_execucao():
    if ALERTAS:
        try:
            pyautogui.alert(text="Fim da execução", title="Jarvis", button="OK")  # type: ignore
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
    """Mostra a resposta, espera ATRASO_APOS_RESPOSTA s e executa a ação (se houver).

    Retorna True se a ação deu certo; False se falhou ou se não havia ação.
    """
    print(plano.resposta)
    _gravar_log("resposta", plano.resposta)
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
    """Para testar uma automação sozinha, a partir da pasta do projeto:
        python -m automacao.calc calcule 5 vezes 2
    Os argumentos viram a frase falada; erros também aparecem em caixas de diálogo.
    """
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

    A ordem dos except importa: FailSafeException e ImageNotFoundException são subclasses
    de PyAutoGUIException. KeyboardInterrupt (CTRL+C) não é capturado.
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
                log_excecao(f"Erro do PyAutoGUI ao {descricao}")
                erro(f"O PyAutoGUI não conseguiu {descricao}: {e}\n"
                     "(Se a mensagem fala de PyScreeze/Pillow, rode: pip install -r requirements.txt)")
            except OSError as e:
                liberar_teclas()
                log_excecao(f"Erro de sistema ao {descricao}")
                erro(f"Erro de arquivo ou sistema ao {descricao}: {e}")
            except Exception as e:
                liberar_teclas()
                log_excecao(f"Erro inesperado ao {descricao}")
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
    texto = re.sub(r"[‐-―−]", "-", texto)      # hífens e traços diversos -> "-"
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
        return pyautogui.getActiveWindowTitle() or ""  # type: ignore
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
    """True se conseguir abrir uma conexão com o Google."""
    try:
        socket.create_connection(("www.google.com", 443), timeout=timeout).close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- abrir programas

def iniciar_programa(busca, condicao_janela, nome, timeout=20, evitar=None):
    """Abre um programa pelo menu Iniciar e espera a janela dele ficar ativa.

    evitar: título (simplificado) de uma janela do mesmo programa que já estava na frente antes.
    Enquanto ela continuar na frente, não conta como "abriu" (senão o Jarvis digitaria num
    documento que já existia em vez de no novo).
    """
    log(f'Abrindo "{nome}" pelo menu Iniciar (busca: "{busca}").')
    pyautogui.press("win")
    time.sleep(ESPERA_MENU_INICIAR)  # sem isso as primeiras letras se perdem
    pyautogui.write(busca, interval=0.2)
    time.sleep(ESPERA_RESULTADO_BUSCA)
    pyautogui.press("enter")

    teste = _criar_teste(condicao_janela)
    if evitar:
        log(f'Ignorando a janela que já estava aberta: "{evitar}".')
        condicao = lambda titulo: teste(titulo) and titulo != evitar  # noqa: E731
    else:
        condicao = teste
    if aguardar_titulo(condicao, timeout):
        return True
    erro(f"Não consegui confirmar que o {nome} abriu (esperei {timeout} s).")
    return False


# ---------------------------------------------------------------- imagens

def tema_claro():
    """True se o Windows está no tema claro, False se no escuro, None se não der para saber.

    Lê a opção "modo padrão de aplicativo" (Configurações > Personalização > Cores).
    """
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as chave:
            valor, _ = winreg.QueryValueEx(chave, "AppsUseLightTheme")
        return bool(valor)
    except (ImportError, OSError):
        return None


def imagens_do_tema(escuras, claras):
    """Todas as imagens, com as do tema atual do Windows primeiro.

    As do outro tema continuam na lista: o Office e o Edge podem ter um tema próprio,
    diferente do Windows.
    """
    claro = tema_claro()
    log(f"Tema do Windows: {'claro' if claro else 'escuro' if claro is False else 'desconhecido'}.")
    return list(claras) + list(escuras) if claro else list(escuras) + list(claras)


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


def _teste_site_carregou(url, titulo_esperado):
    """O título da aba tem o trecho esperado E não é só o endereço digitado.

    Enquanto carrega, quando o endereço não existe ou quando vira uma busca no Bing, o Edge
    mostra o próprio endereço no título ("youtube.com", "cnnbrasil.com.br - Pesquisar"), que
    também contém o trecho esperado ("youtube", "cnn"). Esses títulos não contam.
    """
    dominio = simplificar(url.split("/")[0])
    tem_trecho = _criar_teste(titulo_esperado)
    return lambda titulo: tem_trecho(titulo) and dominio not in titulo


def _abrir_por_atalho(url, carregou):
    """Método principal: CTRL+L foca a barra de endereço do Edge."""
    pyautogui.hotkey("ctrl", "l")
    pyautogui.write(url, interval=0.1)
    pyautogui.press("enter")
    return aguardar_titulo(carregou)


def _abrir_por_imagem(url, carregou):
    """Alternativa: clica na barra de endereço reconhecendo a imagem dela."""
    if not encontrar_e_clicar(imagens_do_tema(IMAGENS_BARRA_ESCURO, IMAGENS_BARRA_CLARO)):
        return False
    pyautogui.write(url, interval=0.1)
    pyautogui.press("enter")
    return aguardar_titulo(carregou)


@seguro("abrir o site no Edge")
def abrir_site(url, titulo_esperado, pos_abertura=None):
    """Abre o Edge e carrega 'url'. 'titulo_esperado': trecho(s) do título da aba quando o site carrega."""
    if not tem_internet():
        erro("Sem conexão com a internet: não consigo abrir o site.")
        return False

    carregou = _teste_site_carregou(url, titulo_esperado)

    # --- Abrir o Edge ---
    log(f"Abrindo o Edge para carregar {url}.")
    pyautogui.press("win")
    time.sleep(ESPERA_MENU_INICIAR)
    pyautogui.write("edge", interval=0.2)
    time.sleep(ESPERA_RESULTADO_BUSCA)
    pyautogui.press("enter")

    # Espera a janela do Edge ficar ativa (até 10 s)
    if not aguardar_titulo(_eh_edge, timeout=10):
        log("Não confirmei que o Edge ficou ativo. Seguindo mesmo assim...")
    time.sleep(1)

    # --- Abrir o site ---
    if FORCAR_IMAGEM_EDGE:
        log("FORCAR_IMAGEM_EDGE ligado: pulando o CTRL+L e indo direto ao reconhecimento de imagem.")
    else:
        log("Tentando com CTRL+L...")
    if not FORCAR_IMAGEM_EDGE and _abrir_por_atalho(url, carregou):
        log("Site aberto com o atalho.")
    else:
        if not FORCAR_IMAGEM_EDGE:
            log("Atalho não funcionou. Tentando por reconhecimento de imagem...")
        if _abrir_por_imagem(url, carregou):
            log("Site aberto com a imagem.")
        else:
            erro("Não consegui abrir o site.")
            return False

    if pos_abertura is not None:
        pos_abertura()
    return True
