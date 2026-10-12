# Frases pré-programadas: CTRL+ALT+número do TECLADO NUMÉRICO faz o Jarvis agir como se você
# tivesse falado a frase (útil em apresentações, quando o microfone ou o ambiente atrapalham).
#
# - Para trocar uma frase, edite o texto. Ela passa pelas mesmas palavras-chave de words.py,
#   então escreva como você falaria.
# - Para desativar um atalho, apague a linha: a tecla volta a funcionar normalmente.
# - Para testar os atalhos sem executar nada:  python ativacao.py
FRASES = {
    1: "Jarvis, que horas são?",
    2: "Jarvis, qual a temperatura em Santo André?",
    3: "Jarvis, calcule 5 vezes 2.",                  # só responde (não abre a calculadora)
    4: "Jarvis, crie um novo documento no Word e escreva uma saudação.",
    5: "Jarvis, crie uma nova planilha no Excel.",
    6: "Jarvis, abra o Paint.",
    7: "Jarvis, abra o YouTube.",
    8: "Jarvis, me mostre as notícias do dia.",
    9: "Jarvis, abra o site do colégio.",
    0: "Jarvis, abra o Instagram do colégio.",
}

# Segundos com o prompt "> " vazio antes de a frase aparecer, imitando o tempo de ouvir e
# reconhecer a fala. Use 0 para mostrar a frase na hora.
PAUSA_ANTES_DA_FRASE = 1.0
