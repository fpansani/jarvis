"""Calculadora: responde contas faladas e, se pedido, digita a conta na Calculadora do Windows.

"jarvis, abra a calculadora"                  -> só abre a calculadora
"jarvis, calcule 5 vezes 2" / "faça 2 x 2" / "faz 2 x 2 pra mim" -> só responde o resultado
"jarvis, calcule 5 vezes 2 na calculadora"    -> responde, abre a calculadora e digita a conta

Testar sozinho (da pasta do projeto):  python -m automacao.calc calcule 5 vezes 2 na calculadora
"""
import re
import time
from decimal import Decimal
from typing import NamedTuple

import pyautogui

from .comum import (Plano, erro, iniciar_programa, janela_ativa_eh, log, mencionou,
                    rodar_isolado, seguro, simplificar)

RESPOSTA_ABRIR = "Certo, irei abrir a calculadora."
RESPOSTA_SEM_CONTA = "Qual conta você quer que eu faça? Diga, por exemplo: calcule 5 vezes 2."
RESPOSTA_SEM_COMANDO = "Desculpe, não entendi o comando."

# Verbos que pedem uma conta ("calcule 5 vezes 2", "faça 2 x 2", "faz 2 x 2"), já sem acento.
# "faça" e "faz" também aparecem em frases que não são contas ("faça uma saudação", "faz frio"):
# para eles, uma frase sem número E operação não é tratada como conta.
VERBOS_CONTA = r"\b(?:calcul(?:ar|e|a)|faca|faz)\b"
VERBOS_GENERICOS = ("faca", "faz")

UNIDADES = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
    "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
    "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
}
DEZENAS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
}
CENTENAS = {
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900,
}

OPERADORES = {"mais": "+", "menos": "-", "vezes": "*", "x": "*"}
PALAVRA_OPERADOR = {"+": "mais", "-": "menos", "*": "vezes", "/": "dividido por"}
# Teclas do teclado numérico: funcionam em qualquer layout (no ABNT2 a "/" não sai direto)
TECLAS = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", ".": "decimal"}

MAX_DIGITOS = 15
MAX_NUMEROS = 20


class ContaInvalida(Exception):
    """A frase não virou uma conta que a calculadora consiga fazer."""


class Conta(NamedTuple):
    exibicao: str                 # "5 vezes 2"  (usada na resposta do Jarvis)
    resultado: str                # "10" ou "2,5"
    tokens: list                  # ["5", "*", "2"]  (usados para digitar)
    precisa_precedencia: bool     # mistura (+ -) com (* /)


# ---------------------------------------------------------------- interpretar a conta

def _ler_numero(tokens, i):
    """Lê um número por extenso de 0 a 999 a partir de tokens[i]. Retorna (valor, qtd_tokens)."""
    n = len(tokens)
    tok = lambda k: tokens[k] if k < n else None  # noqa: E731
    j, total, consumiu = i, 0, False

    if tok(j) in CENTENAS:
        total += CENTENAS[tok(j)]
        j += 1
        consumiu = True
        if tokens[j - 1] == "cem":
            return total, j - i
        proximo = j + 1 if tok(j) == "e" else j      # "cento e vinte"
        if tok(proximo) in DEZENAS or tok(proximo) in UNIDADES:
            j = proximo
        else:
            return total, j - i

    if tok(j) in DEZENAS:
        total += DEZENAS[tok(j)]
        j += 1
        if tok(j) == "e" and tok(j + 1) in UNIDADES and 1 <= UNIDADES[tok(j + 1)] <= 9:
            total += UNIDADES[tok(j + 1)]
            j += 2
        return total, j - i

    if tok(j) in UNIDADES:
        total += UNIDADES[tok(j)]
        j += 1
        consumiu = True

    return (total, j - i) if consumiu else (0, 0)


def _ler_numero_com_mil(tokens, i):
    """Como _ler_numero, mas aceita milhares: "mil", "dois mil", "mil e duzentos", "três mil cento e dez"."""
    valor, usados = _ler_numero(tokens, i)
    j = i + usados
    if j >= len(tokens) or tokens[j] != "mil":
        return valor, usados

    milhares = valor if usados else 1                   # "mil" sozinho = 1000
    j += 1
    inicio_resto = j + 1 if j < len(tokens) and tokens[j] == "e" else j
    resto, usados_resto = _ler_numero(tokens, inicio_resto)
    if usados_resto:
        j = inicio_resto + usados_resto
    return milhares * 1000 + resto, j - i


def _palavras_para_numeros(tokens):
    """["dois", "mil", "mais", "tres"] -> ["2000", "mais", "3"]."""
    saida, i = [], 0
    while i < len(tokens):
        valor, usados = _ler_numero_com_mil(tokens, i)
        if usados:
            saida.append(str(valor))
            i += usados
        else:
            saida.append(tokens[i])
            i += 1
    return saida


def _juntar_virgula(tokens):
    """["2", "virgula", "5"] -> ["2.5"] (o Vosk escreve "dois vírgula cinco")."""
    saida = []
    for tok in tokens:
        if (len(saida) >= 2 and saida[-1] == "virgula" and saida[-2].isdigit() and tok.isdigit()):
            saida[-2:] = [f"{saida[-2]}.{tok}"]
        else:
            saida.append(tok)
    return saida


def extrair_conta(frase):
    """Tira da frase o trecho da conta: 'eu queria calcular 5 vezes 2' -> '5 vezes 2'."""
    f = simplificar(frase)
    m = re.search(VERBOS_CONTA + r"\s*(.*)$", f)
    conta = m.group(1) if m else f
    # "... e abra a calculadora", "... na calculadora", "... usando a calculadora"
    conta = re.sub(r"\b(?:e\s+)?(?:abra|abre|abrir|mostre|mostra)\s+(?:a|na)\s+calculadora\b", " ", conta)
    conta = re.sub(r"\b(?:na|pela|usando a|com a)\s+calculadora\b", " ", conta)
    # "faça a conta de 2 x 2", "calcule o resultado de...", "quanto é..."
    conta = re.sub(r"^\s*(?:(?:pra|para) mim|por favor)\s+", "", conta)                 # "faz pra mim 2 x 2"
    conta = re.sub(r"^\s*(?:a conta|o resultado|o calculo|a operacao|quanto e)(?:\s+de)?\s+", "", conta)
    conta = re.sub(r"(?:\s*(?:por favor|(?:pra|para) mim))+$", "", conta)               # "... pra mim"
    return conta.strip(" ?!.,")


def _formatar(valor):
    if valor == valor.to_integral_value():
        return str(int(valor))
    texto = format(valor.quantize(Decimal("0.000001")), "f").rstrip("0").rstrip(".")
    if texto in ("", "-0"):
        texto = "0"
    return texto.replace(".", ",")


def avaliar_conta(texto):
    """Converte a conta falada em Conta. Levanta ContaInvalida se não der."""
    t = simplificar(texto)
    t = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", t)        # 1.000 -> 1000
    t = re.sub(r"(?<=\d),(?=\d)", ".", t)                 # 2,5   -> 2.5
    t = t.replace("multiplicado por", " * ").replace("dividido por", " / ")
    t = t.replace("×", " * ").replace("÷", " / ")
    t = re.sub(r"(?<=\d)x(?=\d)", " * ", t)               # 5x2
    t = re.sub(r"([+\-*/])", r" \1 ", t)

    tokens = _juntar_virgula(_palavras_para_numeros(t.split()))
    tokens = [OPERADORES.get(tok, tok) for tok in tokens]

    padrao = r"\d+(?:\.\d+)?"
    if not re.fullmatch(rf"{padrao}(?: [+\-*/] {padrao})*", " ".join(tokens)):
        raise ContaInvalida(
            "Não consegui entender a conta. Eu sei somar, subtrair, multiplicar e dividir.")
    if len(tokens) > 2 * MAX_NUMEROS - 1:
        raise ContaInvalida("Essa conta é longa demais para eu digitar.")
    if any(len(n.split(".")[0]) > MAX_DIGITOS for n in tokens[0::2]):
        raise ContaInvalida("Esse número é grande demais para a calculadora.")

    numeros = [Decimal(n) for n in tokens[0::2]]
    operadores = tokens[1::2]

    termos, somas = [numeros[0]], []                      # * e / primeiro, depois + e -
    for op, n in zip(operadores, numeros[1:]):
        if op == "*":
            termos[-1] *= n
        elif op == "/":
            if n == 0:
                raise ContaInvalida("Não é possível dividir por zero.")
            termos[-1] /= n
        else:
            somas.append(op)
            termos.append(n)
    resultado = termos[0]
    for op, n in zip(somas, termos[1:]):
        resultado = resultado + n if op == "+" else resultado - n

    if abs(resultado) >= Decimal(10) ** MAX_DIGITOS:
        raise ContaInvalida("O resultado é grande demais para a calculadora.")

    exibicao = " ".join(PALAVRA_OPERADOR.get(tok, tok.replace(".", ",")) for tok in tokens)
    mistura = ({"*", "/"} & set(operadores)) and ({"+", "-"} & set(operadores))
    return Conta(exibicao, _formatar(resultado), tokens, bool(mistura))


# ---------------------------------------------------------------- automação

def _eh_calculadora(titulo):
    return titulo.startswith(("calculadora", "calculator"))


@seguro("abrir a calculadora")
def abrir_calculadora():
    return iniciar_programa("calc", _eh_calculadora, "Calculadora", timeout=15)


@seguro("digitar a conta na calculadora")
def digitar_conta(conta):
    if not iniciar_programa("calc", _eh_calculadora, "Calculadora", timeout=15):
        return False
    time.sleep(0.5)

    if conta.precisa_precedencia:
        # O modo Padrão calcula na ordem digitada (2+3*4 = 20); o Científico respeita
        # a precedência (= 14), igual ao resultado que o Jarvis anuncia.
        log("Conta mistura + - com * /: mudando a calculadora para o modo Científico (ALT+2).")
        pyautogui.hotkey("alt", "2")
        time.sleep(0.5)

    if not janela_ativa_eh(_eh_calculadora):
        erro("A calculadora não está na frente; cancelei para não digitar em outra janela.")
        return False

    pyautogui.press("esc")  # limpa o que já estava no visor
    for token in conta.tokens:
        for caractere in token:
            pyautogui.press(TECLAS.get(caractere, caractere))
    pyautogui.press("enter")
    return True


# ---------------------------------------------------------------- plano

def _parece_conta(trecho):
    """True se o trecho tem um número E uma operação ("2 x 2", "dois mais três").

    Só número não basta: "uma saudação" tem "uma" (= 1), mas não é conta.
    """
    t = simplificar(trecho)
    tokens = _palavras_para_numeros(t.split())
    tem_numero = any(re.search(r"\d", tok) for tok in tokens)
    tem_operacao = (any(tok in OPERADORES for tok in tokens)
                    or re.search(r"[+\-*/×÷]|\d\s*x\s*\d|dividido por|multiplicado por", t) is not None)
    return tem_numero and tem_operacao


def planejar(frase=""):
    pediu_calculadora = mencionou(frase, "calculadora")
    verbo = re.search(VERBOS_CONTA, simplificar(frase))
    if not verbo:
        return Plano(RESPOSTA_ABRIR, abrir_calculadora)

    trecho = extrair_conta(frase)
    if not trecho:
        # "abra a calculadora para eu calcular": sem conta na frase
        log("Pediu para calcular, mas a frase não tem conta.")
        if pediu_calculadora:
            return Plano(RESPOSTA_ABRIR, abrir_calculadora)
        return Plano(RESPOSTA_SEM_CONTA)

    try:
        conta = avaliar_conta(trecho)
    except ContaInvalida as e:
        log(f'Conta não entendida em "{trecho}": {e}')
        if verbo.group(0) in VERBOS_GENERICOS and not pediu_calculadora and not _parece_conta(trecho):
            # "faça uma saudação", "faz frio": não era uma conta, então a resposta não fala de contas
            log(f'"{verbo.group(0)}" sem número e operação: não parece uma conta.')
            return Plano(RESPOSTA_SEM_COMANDO)
        return Plano(str(e))
    log(f'Conta: "{trecho}" -> {" ".join(conta.tokens)} = {conta.resultado}'
        + (" (precisa de precedência: modo Científico)" if conta.precisa_precedencia else ""))

    resposta = f"O resultado de {conta.exibicao} é {conta.resultado}."
    if pediu_calculadora:
        return Plano(resposta, lambda: digitar_conta(conta))   # pediu a calculadora: digita lá
    return Plano(resposta)                                      # só responde, sem abrir nada


if __name__ == "__main__":
    rodar_isolado(planejar)
