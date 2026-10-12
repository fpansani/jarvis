import os
import sys
import time

import pyautogui
import speech_recognition as sr

import functions as fn
import voice
from automacao import comum
from automacao.comum import executar_plano
from voice import ErroModelo, ReconhecedorOffline, SpeechRecognition, find_microphone

WIDTH = 47

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


def startup():
    """Verifica microfone, internet e reconhecimento offline. Retorna (online, offline)."""
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

    return online, offline


def show_header(online):
    print(BANNER)
    print("VER. 1.0 - PRESSIONE CTRL+C PARA SAIR".center(WIDTH).rstrip())
    if not online:
        print("Modo off-line".center(WIDTH).rstrip())
    if comum.DEBUG:
        print("** MODO DEBUG **".center(WIDTH).rstrip())
    print("-" * WIDTH)
    print("Olá, usuário. No que posso ajudar hoje?")


def show_notice(message):
    """Mostra um aviso no lugar do prompt "> " e volta a mostrar o prompt."""
    print(f"\r{message}")
    print("> ", end="", flush=True)


def listen_for_text(offline):
    """Mostra o prompt e fica ouvindo até entender uma frase."""
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


def main():
    try:
        online, offline = startup()
        time.sleep(3)
        clear_screen()
        show_header(online)

        while True:
            text = listen_for_text(offline)

            result = fn.find_command(text)
            if result:
                category, name = result
                plano = fn.respond(category, name, text)

                # imprime a resposta, espera 2 s e executa a ação (se houver)
                sucesso = executar_plano(plano)
                if plano.acao is not None:
                    if sucesso:
                        print("A tarefa foi executada com sucesso.")
                    else:
                        print("Não consegui concluir a tarefa.")
            else:
                print("Desculpe, não entendi o comando.")

            print("--")
    except KeyboardInterrupt:
        print()
        print("-" * 46)
        print("Jarvis está encerrando. Até breve!")


if __name__ == "__main__":
    main()
