import os
import sys
import time

import pyautogui
import speech_recognition as sr

import functions as fn
import voice
from atalhos import FRASES, PAUSA_ANTES_DA_FRASE
from ativacao import FRASE, NOME_ATALHO, AtalhoGlobal, ErroAtalho, nome_atalho_numerico
from automacao import comum
from automacao.comum import executar_plano, log
from voice import (ErroModelo, EscutaCancelada, ReconhecedorOffline, SpeechRecognition,
                   calibrar_microfone, find_microphone)

WIDTH = 47

# Ativação por teclado: True = o Jarvis só ouve depois do atalho (CTRL+ALT+J; para trocar a
# tecla, veja ATALHO em ativacao.py) e aceita as frases prontas de CTRL+ALT+NUM 0-9 (atalhos.py).
# False = ouve o tempo todo, como antes, sem atalhos.
ATIVACAO_POR_TECLA = True
BIPE_AO_OUVIR = True  # bipe agudo ao começar a ouvir e grave ao cancelar (ajuda com o console escondido)

AGUARDANDO = f"Pressione {NOME_ATALHO} para falar."

BANNER = r"""===============================================
|    ___   ___   ______  _   _ _____  _____   |
|   |_  | / _ \  | ___ \| | | |_   _|/  ___|  |
|     | |/ /_\ \ | |_/ /| | | | | |  \ `--.   |
|     | ||  _  | |    / | | | | | |   `--. \  |
| /\__/ /| | | |_| |\ \ \ \_/ /_| |__/\__/ /  |
| \____(_)_| |_(_)_| \_(_)___(_)___(_)____(_) |
|                                             |
==============================================="""


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def load_offline(offline):
    """Carrega o modelo do Vosk agora (leva alguns segundos). Encerra se não for possível."""
    if not offline.disponivel:
        print(f"ERRO: {offline.erro}")
        sys.exit(1)

    print(f"Carregando o modelo offline '{offline.nome}'...", end=" ", flush=True)
    inicio = time.time()
    try:
        offline.carregar()
    except ErroModelo as erro:
        print()
        print(f"ERRO: {erro}")
        sys.exit(1)
    print(f"OK ({time.time() - inicio:.1f} s)")


def start_hotkey():
    """Liga o atalho de teclado. Retorna o AtalhoGlobal, ou None para ouvir o tempo todo."""
    if not ATIVACAO_POR_TECLA:
        return None

    atalho = AtalhoGlobal(numeros=FRASES)
    try:
        atalho.iniciar()
    except ErroAtalho as erro:
        print(f"Aviso: {erro} O Jarvis vai ouvir o tempo todo.")
        return None
    print(f"Atalho {NOME_ATALHO} ativado.")
    return atalho


def startup():
    """Verifica microfone, internet, reconhecimento offline e atalho. Retorna (online, offline, atalho)."""
    print("Iniciando Jarvis...")

    microfone = find_microphone()
    if microfone is None:
        print("ERRO: Microfone não encontrado! Conecte-o e tente novamente.")
        sys.exit(1)
    print(f"Microfone encontrado! Dispositivo: {microfone}")

    print("Verificando conexão com a internet....", end=" ", flush=True)
    online = fn.has_internet()
    offline = ReconhecedorOffline()

    if online:
        print("OK")
        # com internet o modelo só é carregado se o Google falhar no meio do uso
        if offline.disponivel:
            print(f"Reconhecimento offline disponível: {offline.nome}")
        else:
            print(f"Aviso: reconhecimento offline indisponível. {offline.erro.splitlines()[0]}")
    else:
        print("Não há conexão com a Internet! Entrando em modo off-line...")
        load_offline(offline)
        voice.preferir_offline()

    print("Calibrando o microfone (fique em silêncio)...", end=" ", flush=True)
    try:
        calibrar_microfone()
    except OSError as erro:
        print()
        print(f"ERRO ao acessar o microfone: {erro}")
        sys.exit(1)
    print("OK")

    return online, offline, start_hotkey()


def show_header(online, escuta_continua=False):
    print(BANNER)
    print("VER. 1.0 - PRESSIONE CTRL+C PARA SAIR".center(WIDTH).rstrip())
    if not online:
        print("Modo off-line".center(WIDTH).rstrip())
    if escuta_continua:
        print("Atalho indisponível: ouvindo o tempo todo".center(WIDTH).rstrip())
    if comum.DEBUG:
        print("** MODO DEBUG **".center(WIDTH).rstrip())
    print("-" * WIDTH)
    print("Olá, usuário. No que posso ajudar hoje?")


def show_notice(message):
    """Mostra um aviso no lugar do prompt "> " e volta a mostrar o prompt."""
    print(f"\r{message}")
    print("> ", end="", flush=True)


def beep(frequencia=880):
    if not BIPE_AO_OUVIR:
        return
    try:
        import winsound
        winsound.Beep(frequencia, 120)
    except (ImportError, RuntimeError):  # fora do Windows, ou sem como tocar o bipe
        pass


def listen_for_text(offline):
    """Escuta contínua: mostra o prompt e fica ouvindo até entender uma frase."""
    print("> ", end="", flush=True)

    while True:
        try:
            text = SpeechRecognition(offline, show_notice)
        except sr.RequestError as erro:
            print(f"\nErro no serviço de reconhecimento: {erro}")
            print("> ", end="", flush=True)
            continue
        except OSError as erro:
            print(f"\nErro ao acessar o microfone: {erro}")
            sys.exit(1)

        if text:
            print(text)
            return text


def listen_with_hotkey(atalho, offline):
    """Espera um atalho. CTRL+ALT+J: ouve uma frase. CTRL+ALT+NUM n: usa a frase pronta n.

    Retorna o texto, ou None se não entendeu.
    """
    ignorados = atalho.descartar_pendentes()
    if ignorados:
        log(f"{ignorados} acionamento(s) de atalho ignorado(s): o Jarvis estava ocupado.")

    print(AGUARDANDO, end="", flush=True)
    tipo, numero = atalho.esperar()
    print("\r" + " " * len(AGUARDANDO) + "\r", end="")   # apaga o "Pressione..."

    if tipo == FRASE:
        # aparece como se tivesse sido falada; o resto do caminho é o mesmo da voz
        log(f"{nome_atalho_numerico(numero)}: frase pré-programada.")
        print("> ", end="", flush=True)
        time.sleep(PAUSA_ANTES_DA_FRASE)
        text = FRASES[numero]
        print(text)
        return text

    log(f"{NOME_ATALHO} pressionado: ouvindo ({NOME_ATALHO} de novo cancela).")

    atalho.comecar_escuta()             # daqui em diante, CTRL+ALT+J cancela a escuta
    try:
        beep()
        print("> ", end="", flush=True)
        try:
            text = SpeechRecognition(offline, show_notice, atalho.cancelar)
        except EscutaCancelada:
            log("Escuta cancelada.")
            beep(440)
            print("(cancelado)")
            return None
        except sr.RequestError as erro:
            print(f"\nErro no serviço de reconhecimento: {erro}")
            return None
        except OSError as erro:
            print(f"\nErro ao acessar o microfone: {erro}")
            sys.exit(1)
    finally:
        atalho.terminar_escuta()

    if text:
        print(text)
        return text
    print("(não entendi)")
    return None


def process(text):
    """Detecta o comando na frase, responde e executa a ação (se houver)."""
    result = fn.find_command(text)
    if not result:
        print("Desculpe, não entendi o comando.")
        return

    category, name = result
    plano = fn.respond(category, name, text)

    # imprime a resposta, espera 2 s e executa a ação (se houver)
    sucesso = executar_plano(plano)
    if plano.acao is not None:
        if sucesso:
            print("A tarefa foi executada com sucesso.")
        else:
            print("Não consegui concluir a tarefa.")


def main():
    atalho = None
    try:
        online, offline, atalho = startup()
        time.sleep(3)
        clear_screen()
        show_header(online, escuta_continua=ATIVACAO_POR_TECLA and atalho is None)

        while True:
            if atalho is not None:
                try:
                    text = listen_with_hotkey(atalho, offline)
                except ErroAtalho as erro:
                    print(f"\r{erro} O Jarvis vai ouvir o tempo todo.".ljust(len(AGUARDANDO) + 1))
                    atalho.parar()
                    atalho = None
                    continue
            else:
                text = listen_for_text(offline)

            if text:
                process(text)
            print("--")
    except KeyboardInterrupt:
        print()
        print("-" * 46)
        print("Jarvis está encerrando. Até breve!")
    finally:
        if atalho is not None:
            atalho.parar()


if __name__ == "__main__":
    main()
