import subprocess
import sys
import time
from pathlib import Path

# Configurações
PASTA_JARVIS = Path(__file__).resolve().parent
ARQUIVO_MAIN = PASTA_JARVIS / "main.py"

CODIGO_AUTORIZADO = "3371173888"

# Evita abrir várias instâncias do Jarvis
jarvis_aberto = False

print("================================")
print("       JARVIS - NFC")
print("================================")
print("Aguardando leitura do cartão...")
print("Aproxime seu cartão NFC.")
print("Pressione Ctrl+C para encerrar.\n")

while True:
    try:
        codigo = input("Aguardando cartão: ").strip()

        if codigo == CODIGO_AUTORIZADO:
            if jarvis_aberto:
                print("O Jarvis já está em execução.")
                continue

            if not ARQUIVO_MAIN.exists():
                print("Erro: main.py não encontrado!")
                continue

            print("Cartão autorizado!")
            print("Iniciando o Jarvis...\n")

            processo = subprocess.Popen(
                [sys.executable, str(ARQUIVO_MAIN)],
                cwd=str(PASTA_JARVIS)
            )

            jarvis_aberto = True

            print("Jarvis iniciado!")

        else:
            print("Cartão não autorizado.\n")

    except KeyboardInterrupt:
        print("\nEncerrando o leitor NFC...")
        break