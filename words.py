# Palavras-chave de cada comando. A frase falada é comparada sem acentos e sem maiúsculas, e
# cada palavra-chave precisa aparecer inteira ("plan" não casa com "planeta").
commands = {
    "asks": {
        "time": ["horas", "horário", "hora"],
        "degree": ["temperatura", "tempo", "clima"],
    },
    "apps": {
        "calc": ["calculadora", "calc", "calcular", "calcule", "calcula", "faça", "faz"],
        "paint": ["paint", "desenho", "desenhar"],
        "yt": ["youtube", "yt", "vídeo", "vídeos"],
        "word": ["word", "editor de texto", "editor", "texto", "wor", "world"],
        "excel": ["excel", "planilha", "planilhas", "plan"],
        "news": ["notícias", "cnn", "cnn brasil", "notícia"],
    },
    "social": {
        "site": ["site", "portal"],
        "insta": ["instagram", "insta", "rede social"],
    },
}

# Se a frase tiver palavras-chave de comandos diferentes, os nomes de programas e sites abaixo
# vencem as palavras genéricas ("site", "horas", "texto"...): "abra o site da CNN" -> news e
# "crie uma planilha de horas no Excel" -> excel. Entre palavras do mesmo tipo, vence a mais longa.
app_names = ["calculadora", "calc", "paint", "youtube", "yt", "word", "wor", "world", "excel",
             "cnn", "cnn brasil", "instagram", "insta"]
