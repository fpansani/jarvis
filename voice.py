"""Reconhecimento de voz do Jarvis.

- Online: Google (SpeechRecognition), em português.
- Offline: Vosk, com um modelo na pasta models/. Usado quando não há internet ao abrir o Jarvis
  ou quando o Google falha no meio do uso.
- A escuta pode ser cancelada no meio (CTRL+ALT+J de novo; veja ativacao.py).
"""
import contextlib
import http.client
import json
import os
import time
from pathlib import Path

import speech_recognition as sr

from automacao.comum import log, log_excecao

# Reconhecimento offline (Vosk): o modelo fica na pasta models/, ao lado deste arquivo.
PASTA_MODELOS = Path(__file__).resolve().parent / "models"
VARIAVEL_MODELO = "JARVIS_MODELO_VOSK"   # opcional: escolhe o modelo quando houver mais de um
TAXA_VOSK = 16000                        # taxa de amostragem (Hz) usada pelos modelos do Vosk

ESPERA_PELA_FALA = 10                    # segundos esperando você começar a falar
DURACAO_MAXIMA_FALA = 15                 # segundos no máximo de uma frase
TEMPO_LIMITE_GOOGLE = 5                  # segundos esperando o Google antes de desistir
SEGUNDOS_OFFLINE = 30                    # depois de uma falha, usa o Vosk por este tempo antes de tentar o Google

# Erros que significam "o Google não respondeu direito": sem conexão, tempo esgotado, ou uma
# resposta que não é do Google (por exemplo, a página de login do Wi-Fi da escola, em HTML).
ERROS_DO_GOOGLE = (sr.RequestError, OSError, ValueError, KeyError, http.client.HTTPException)

MENSAGEM_SEM_MODELO = """Nenhum modelo do Vosk encontrado na pasta models/.
  1. Baixe um modelo em português em https://alphacephei.com/vosk/models
  2. Descompacte dentro da pasta models/ (ao lado do main.py), ficando por exemplo:
     models/vosk-model-pt-fb-v0.1.1-pruned/
  3. Rode o Jarvis de novo."""

MENSAGEM_MICROFONE_BLOQUEADO = (
    "não consegui abrir o microfone. Ele pode estar em uso por outro programa ou bloqueado em "
    "Configurações > Privacidade > Microfone (permita o acesso de aplicativos da área de trabalho).")

_usar_google_a_partir_de = 0.0   # enquanto o relógio estiver abaixo disso, usa só o Vosk
_avisou_offline = False          # evita repetir o aviso "usando o reconhecimento offline"
_limiar_energia = None           # volume que separa fala de ruído (medido em calibrar_microfone)


class ErroModelo(Exception):
    """O modelo do Vosk não existe, não abriu ou o pacote 'vosk' não está instalado."""


class EscutaCancelada(Exception):
    """A escuta foi cancelada (por exemplo, CTRL+ALT+J apertado de novo)."""


# ---------------------------------------------------------------- microfone

class _MicrofoneCancelavel:
    """Envolve o stream do microfone: a cada pedaço lido (uns 20 a 60 ms), confere se a escuta
    foi cancelada. O listen() do SpeechRecognition lê o microfone só por aqui, tanto esperando
    a fala começar quanto gravando, então o cancelamento é quase imediato."""

    def __init__(self, stream, cancelar):
        self._stream = stream
        self._cancelar = cancelar

    def read(self, size):
        if self._cancelar.is_set():
            raise EscutaCancelada()
        return self._stream.read(size)

    def close(self):
        self._stream.close()


@contextlib.contextmanager
def _abrir_microfone(cancelar=None):
    """Abre o microfone padrão. Levanta OSError com uma mensagem clara se não conseguir.

    O SpeechRecognition engole o erro quando o PyAudio não consegue abrir o microfone (em uso
    por outro programa, bloqueado na privacidade do Windows) e deixa o stream vazio, o que
    depois virava um erro confuso. Aqui isso vira um OSError com a explicação.
    """
    try:
        microfone = sr.Microphone()
    except AttributeError as e:          # o SpeechRecognition faz isso quando falta o PyAudio
        raise OSError("o PyAudio não está instalado (pip install -r requirements.txt)") from e
    microfone.__enter__()
    if microfone.stream is None:
        raise OSError(MENSAGEM_MICROFONE_BLOQUEADO)
    try:
        if cancelar is not None:
            microfone.stream = _MicrofoneCancelavel(microfone.stream, cancelar)
        yield microfone
    finally:
        microfone.__exit__(None, None, None)


def find_microphone():
    """Retorna o nome do microfone padrão, ou None se não houver nenhum."""
    try:
        import pyaudio
    except ImportError:
        log("PyAudio não instalado.")
        return None

    audio = pyaudio.PyAudio()
    try:
        info = audio.get_default_input_device_info()
        log(f"Microfone padrão: {info.get('name')} (índice {info.get('index')}, "
            f"{info.get('defaultSampleRate', 0):.0f} Hz, {audio.get_device_count()} dispositivo(s) de áudio)")
        return info["name"]
    except OSError:
        return None
    finally:
        audio.terminate()


def calibrar_microfone(segundos=1):
    """Mede o ruído do ambiente uma vez, para não gastar 1 s calibrando a cada frase.

    O limiar continua se ajustando sozinho durante o uso (dynamic_energy_threshold).
    Levanta OSError se o microfone não abrir.
    """
    global _limiar_energia
    recognition = sr.Recognizer()
    with _abrir_microfone() as microfone:
        recognition.adjust_for_ambient_noise(microfone, duration=segundos)
    _limiar_energia = recognition.energy_threshold
    log(f"Limiar de energia do microfone: {_limiar_energia:.0f} (quanto maior, mais barulhento o ambiente).")
    return _limiar_energia


# ---------------------------------------------------------------- modelo offline (Vosk)

def parece_modelo(pasta):
    """Um modelo do Vosk é uma pasta com os arquivos do modelo.

    Há dois formatos: o dos modelos pequenos (final.mdl, mfcc.conf e ivector/ soltos na pasta)
    e o dos modelos grandes (subpastas am/, conf/ e graph/).
    """
    if not pasta.is_dir():
        return False
    pequeno = (pasta / "final.mdl").is_file() or (pasta / "mfcc.conf").is_file()
    grande = (pasta / "am").is_dir() or (pasta / "conf").is_dir()
    return pequeno or grande


def achar_modelos(base):
    """Modelos dentro de 'base' (até 2 níveis: alguns descompactadores criam pasta dentro de pasta)."""
    if not base.is_dir():
        return []
    achados = []
    for filho in sorted(p for p in base.iterdir() if p.is_dir()):
        if parece_modelo(filho):
            achados.append(filho)
        else:
            achados += [neto for neto in sorted(p for p in filho.iterdir() if p.is_dir())
                        if parece_modelo(neto)]
    return achados


def escolher_modelo():
    """Pasta do modelo a usar, ou None se não houver nenhum.

    Se a variável JARVIS_MODELO_VOSK existir, ela manda (nome da pasta dentro de models/ ou
    caminho completo). Senão, usa o único modelo da pasta; havendo vários, prefere um que não
    seja o "small" (os modelos pequenos erram mais).
    """
    pedido = os.environ.get(VARIAVEL_MODELO, "").strip()
    if pedido:
        caminho = Path(pedido)
        if not caminho.is_absolute():
            caminho = PASTA_MODELOS / caminho
        candidatos = [caminho] if parece_modelo(caminho) else achar_modelos(caminho)
        if not candidatos:
            raise ErroModelo(f"{VARIAVEL_MODELO} aponta para '{pedido}', que não parece um modelo do Vosk.")
    else:
        candidatos = achar_modelos(PASTA_MODELOS)
        if not candidatos:
            log(f"Nenhum modelo do Vosk em {PASTA_MODELOS}.")
            return None

    grandes = [c for c in candidatos if "small" not in c.name.lower()]
    escolhido = (grandes or candidatos)[0]
    origem = f"{VARIAVEL_MODELO}={pedido}" if pedido else str(PASTA_MODELOS)
    log(f"Modelos do Vosk ({origem}): {[c.name for c in candidatos]} -> usando {escolhido}")
    return escolhido


class ReconhecedorOffline:
    """Reconhecimento de voz offline com o Vosk. O modelo só é carregado quando for preciso."""

    def __init__(self):
        self.pasta = None
        self.erro = None        # None enquanto estiver tudo certo; senão, o motivo (e o que fazer)
        self._modelo = None
        try:
            self.pasta = escolher_modelo()
        except ErroModelo as e:
            self.erro = str(e)
        if self.pasta is None and self.erro is None:
            self.erro = MENSAGEM_SEM_MODELO

    @property
    def disponivel(self):
        return self.erro is None

    @property
    def carregado(self):
        return self._modelo is not None

    @property
    def nome(self):
        return self.pasta.name if self.pasta else None

    def carregar(self):
        """Carrega o modelo (leva alguns segundos). Levanta ErroModelo se não conseguir."""
        if self._modelo is not None:
            return
        if not self.disponivel:
            raise ErroModelo(self.erro)

        try:
            from vosk import Model, SetLogLevel
        except ImportError as e:
            self.erro = "O pacote 'vosk' não está instalado. Rode: pip install -r requirements.txt"
            raise ErroModelo(self.erro) from e

        SetLogLevel(-1)  # silencia o log interno do Vosk (erros graves ainda aparecem)
        try:
            self._modelo = Model(str(self.pasta))
        except Exception as e:  # o Vosk só levanta Exception("Failed to create a model")
            log_excecao(f"Falha ao carregar o modelo do Vosk em {self.pasta}")
            if not str(self.pasta.resolve()).isascii():
                self.erro = (f"Não consegui carregar o modelo '{self.nome}'. O caminho tem acentos ou "
                             f"caracteres especiais ({self.pasta.resolve()}), que o Vosk pode não aceitar "
                             "no Windows: mova a pasta do Jarvis (ou só o modelo) para um caminho simples, "
                             f"como C:\\jarvis, ou indique o modelo com {VARIAVEL_MODELO}.")
            else:
                self.erro = (f"Não consegui carregar o modelo '{self.nome}'. Os arquivos podem estar "
                             "incompletos (baixe e descompacte de novo) ou faltar memória no computador.")
            raise ErroModelo(self.erro) from e

    def transcrever(self, audio):
        """Texto falado em 'audio' (um AudioData do SpeechRecognition), ou None se não entendeu."""
        self.carregar()
        from vosk import KaldiRecognizer

        try:
            reconhecedor = KaldiRecognizer(self._modelo, TAXA_VOSK)
            # o SpeechRecognition converte o áudio do microfone para 16 kHz, 16 bits
            reconhecedor.AcceptWaveform(audio.get_raw_data(convert_rate=TAXA_VOSK, convert_width=2))
            texto = json.loads(reconhecedor.FinalResult()).get("text", "").strip()
        except Exception as e:
            log_excecao("Falha do Vosk ao reconhecer a fala")
            raise ErroModelo(f"O reconhecimento offline falhou: {type(e).__name__}: {e}") from e
        return texto or None


def preferir_offline(segundos=SEGUNDOS_OFFLINE):
    """Usa o Vosk por 'segundos' antes de voltar a tentar o Google (chamado quando já se sabe que está sem internet)."""
    global _usar_google_a_partir_de, _avisou_offline
    _usar_google_a_partir_de = time.monotonic() + segundos
    _avisou_offline = True


# ---------------------------------------------------------------- reconhecimento

def _aviso_padrao(mensagem):
    print(f"\r{mensagem}")


def _transcrever_offline(offline, audio, avisar):
    try:
        if not offline.carregado:
            avisar(f"Carregando o modelo offline '{offline.nome}'...")
            inicio = time.monotonic()
            offline.carregar()
            log(f"Modelo carregado em {time.monotonic() - inicio:.1f} s.", avisar)
        inicio = time.monotonic()
        texto = offline.transcrever(audio)
    except ErroModelo as e:
        raise sr.RequestError(str(e)) from e

    duracao = time.monotonic() - inicio
    log(f"Vosk reconheceu em {duracao:.2f} s: {texto!r}" if texto
        else f"Vosk não entendeu a fala ({duracao:.2f} s).", avisar)
    return texto


def SpeechRecognition(offline=None, avisar=_aviso_padrao, cancelar=None, ao_abrir=None):
    """Escuta uma vez e retorna o texto falado.

    Usa o Google quando há internet. Se o Google falhar (sem conexão, tempo esgotado, resposta
    inválida) e houver um ReconhecedorOffline disponível, a mesma fala é reconhecida pelo Vosk,
    e o Vosk continua sendo usado por SEGUNDOS_OFFLINE segundos antes de o Google ser tentado de novo.

    avisar:   função que mostra avisos e mensagens de debug sem bagunçar o prompt "> ".
    cancelar: threading.Event opcional. Se for ativado durante a escuta, ela para na hora; se for
              ativado durante o reconhecimento, o resultado é descartado. Nos dois casos: EscutaCancelada.
    ao_abrir: função chamada assim que o microfone estiver aberto, logo antes de ouvir (o bipe e o
              prompt "> "): assim nada do que você fala depois do bipe se perde.

    Retorna None se nenhuma fala foi detectada ou se a fala não foi entendida.
    Levanta sr.RequestError (serviço de reconhecimento) e OSError (microfone).
    """
    texto = _ouvir_e_reconhecer(offline, avisar, cancelar, ao_abrir)
    if cancelar is not None and cancelar.is_set():
        raise EscutaCancelada()
    return texto


def _ouvir_e_reconhecer(offline, avisar, cancelar, ao_abrir):
    global _usar_google_a_partir_de, _avisou_offline, _limiar_energia

    recognition = sr.Recognizer()
    recognition.operation_timeout = TEMPO_LIMITE_GOOGLE

    with _abrir_microfone(cancelar) as microfone:
        if _limiar_energia is None:
            recognition.adjust_for_ambient_noise(microfone, duration=1)
        else:
            recognition.energy_threshold = _limiar_energia
        if ao_abrir is not None:
            ao_abrir()

        try:
            audio = recognition.listen(
                microfone,
                timeout=ESPERA_PELA_FALA,
                phrase_time_limit=DURACAO_MAXIMA_FALA,
            )
        except sr.WaitTimeoutError:
            log(f"Nenhuma fala em {ESPERA_PELA_FALA} s.", avisar)
            return None
        finally:
            if _limiar_energia is not None:
                _limiar_energia = recognition.energy_threshold   # guarda o ajuste feito durante a escuta

    duracao = len(audio.frame_data) / (audio.sample_rate * audio.sample_width)
    log(f"Áudio capturado: {duracao:.1f} s (limiar de energia {recognition.energy_threshold:.0f}).", avisar)
    tem_offline = offline is not None and offline.disponivel

    agora = time.monotonic()
    if tem_offline and agora < _usar_google_a_partir_de:
        log(f"Usando o Vosk direto (o Google volta a ser tentado em {_usar_google_a_partir_de - agora:.0f} s).", avisar)
        return _transcrever_offline(offline, audio, avisar)

    inicio = time.monotonic()
    try:
        texto = recognition.recognize_google(audio, language="pt-BR")
        log(f"Google reconheceu em {time.monotonic() - inicio:.2f} s.", avisar)
        _avisou_offline = False
        return texto
    except sr.UnknownValueError:
        log(f"Google não entendeu a fala ({time.monotonic() - inicio:.2f} s).", avisar)
        _avisou_offline = False
        return None
    except ERROS_DO_GOOGLE as erro:
        log(f"Google falhou após {time.monotonic() - inicio:.1f} s: {type(erro).__name__}: {erro}", avisar)
        if cancelar is not None and cancelar.is_set():
            raise EscutaCancelada() from erro                 # cancelado: nem tenta o Vosk
        if not tem_offline:
            if isinstance(erro, sr.RequestError):
                raise
            raise sr.RequestError(f"recognition connection failed: {erro}") from erro

        _usar_google_a_partir_de = time.monotonic() + SEGUNDOS_OFFLINE
        if not _avisou_offline:
            avisar("Sem acesso ao serviço de voz do Google: usando o reconhecimento offline.")
            _avisou_offline = True
        return _transcrever_offline(offline, audio, avisar)
