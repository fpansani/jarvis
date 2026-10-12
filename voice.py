import json
import os
import time
from pathlib import Path

import speech_recognition as sr

from automacao import comum
from automacao.comum import log

# Reconhecimento offline (Vosk): o modelo fica na pasta models/, ao lado deste arquivo.
PASTA_MODELOS = Path(__file__).resolve().parent / "models"
VARIAVEL_MODELO = "JARVIS_MODELO_VOSK"   # opcional: escolhe o modelo quando houver mais de um
TAXA_VOSK = 16000                        # taxa de amostragem (Hz) usada pelos modelos do Vosk

TEMPO_LIMITE_GOOGLE = 5                  # segundos esperando o Google antes de desistir
SEGUNDOS_OFFLINE = 30                    # depois de uma falha, usa o Vosk por este tempo antes de tentar o Google

MENSAGEM_SEM_MODELO = """Nenhum modelo do Vosk encontrado na pasta models/.
  1. Baixe um modelo em português em https://alphacephei.com/vosk/models
  2. Descompacte dentro da pasta models/ (ao lado do main.py), ficando por exemplo:
     models/vosk-model-pt-fb-v0.1.1-pruned/
  3. Rode o Jarvis de novo."""

_usar_google_a_partir_de = 0.0   # enquanto o relógio estiver abaixo disso, usa só o Vosk
_avisou_offline = False          # evita repetir o aviso "usando o reconhecimento offline"


class ErroModelo(Exception):
    """O modelo do Vosk não existe, não abriu ou o pacote 'vosk' não está instalado."""


def find_microphone():
    """Retorna o nome do microfone padrão, ou None se não houver nenhum."""
    import pyaudio

    audio = pyaudio.PyAudio()
    try:
        return audio.get_default_input_device_info()["name"]
    except OSError:
        return None
    finally:
        audio.terminate()


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
            self.erro = "O pacote 'vosk' não está instalado. Rode: pip install vosk"
            raise ErroModelo(self.erro) from e

        SetLogLevel(-1)  # silencia o log interno do Vosk (erros graves ainda aparecem)
        try:
            self._modelo = Model(str(self.pasta))
        except Exception as e:  # o Vosk só levanta Exception("Failed to create a model")
            self.erro = (f"Não consegui carregar o modelo '{self.nome}'. Os arquivos podem estar "
                         "incompletos (baixe e descompacte de novo) ou faltar memória no computador.")
            raise ErroModelo(self.erro) from e

    def transcrever(self, audio):
        """Texto falado em 'audio' (um AudioData do SpeechRecognition), ou None se não entendeu."""
        self.carregar()
        from vosk import KaldiRecognizer

        reconhecedor = KaldiRecognizer(self._modelo, TAXA_VOSK)
        # o SpeechRecognition converte o áudio do microfone para 16 kHz, 16 bits
        reconhecedor.AcceptWaveform(audio.get_raw_data(convert_rate=TAXA_VOSK, convert_width=2))
        texto = json.loads(reconhecedor.FinalResult()).get("text", "").strip()
        return texto or None


def preferir_offline(segundos=SEGUNDOS_OFFLINE):
    """Usa o Vosk por 'segundos' antes de voltar a tentar o Google (chamado quando já se sabe que está sem internet)."""
    global _usar_google_a_partir_de, _avisou_offline
    _usar_google_a_partir_de = time.monotonic() + segundos
    _avisou_offline = True


# ---------------------------------------------------------------- reconhecimento

def _aviso_padrao(mensagem):
    print(f"\r{mensagem}")


def _debug(avisar, mensagem):
    """Debug durante a escuta: passa pelo 'avisar' para não bagunçar o prompt "> "."""
    if comum.DEBUG:
        avisar(f"[debug] {mensagem}")


def _transcrever_offline(offline, audio, avisar):
    try:
        if not offline.carregado:
            avisar(f"Carregando o modelo offline '{offline.nome}'...")
            inicio = time.monotonic()
            offline.carregar()
            _debug(avisar, f"Modelo carregado em {time.monotonic() - inicio:.1f} s.")
        inicio = time.monotonic()
        texto = offline.transcrever(audio)
    except ErroModelo as e:
        raise sr.RequestError(str(e)) from e

    duracao = time.monotonic() - inicio
    if texto:
        _debug(avisar, f"Vosk reconheceu em {duracao:.2f} s.")
    else:
        _debug(avisar, f"Vosk não entendeu a fala ({duracao:.2f} s).")
    return texto


def SpeechRecognition(offline=None, avisar=_aviso_padrao):
    """Escuta uma vez e retorna o texto falado.

    Usa o Google quando há internet. Se o Google falhar (sem conexão, tempo esgotado) e houver um
    ReconhecedorOffline disponível, a mesma fala é reconhecida pelo Vosk, e o Vosk continua sendo
    usado por SEGUNDOS_OFFLINE segundos antes de o Google ser tentado de novo.

    Retorna None se nenhuma fala foi detectada ou se a fala não foi entendida.
    Erros do serviço de reconhecimento (sr.RequestError) e do microfone (OSError)
    são propagados para quem chamou.
    """
    global _usar_google_a_partir_de, _avisou_offline

    recognition = sr.Recognizer()
    recognition.operation_timeout = TEMPO_LIMITE_GOOGLE

    with sr.Microphone() as microfone:
        recognition.adjust_for_ambient_noise(microfone, duration=1)

        try:
            audio = recognition.listen(
                microfone,
                timeout=10,
                phrase_time_limit=15
            )
        except sr.WaitTimeoutError:
            return None

    _debug(avisar, f"Áudio capturado: {len(audio.frame_data) / (audio.sample_rate * audio.sample_width):.1f} s.")
    tem_offline = offline is not None and offline.disponivel

    agora = time.monotonic()
    if tem_offline and agora < _usar_google_a_partir_de:
        _debug(avisar, f"Usando o Vosk direto (o Google volta a ser tentado em {_usar_google_a_partir_de - agora:.0f} s).")
        return _transcrever_offline(offline, audio, avisar)

    inicio = time.monotonic()
    try:
        texto = recognition.recognize_google(
            audio,
            language='pt-BR'
        )
        _debug(avisar, f"Google reconheceu em {time.monotonic() - inicio:.2f} s.")
        _avisou_offline = False
        return texto
    except sr.UnknownValueError:
        _debug(avisar, f"Google não entendeu a fala ({time.monotonic() - inicio:.2f} s).")
        _avisou_offline = False
        return None
    except (sr.RequestError, OSError) as erro:
        _debug(avisar, f"Google falhou após {time.monotonic() - inicio:.1f} s: {type(erro).__name__}: {erro}")
        if not tem_offline:
            if isinstance(erro, sr.RequestError):
                raise
            raise sr.RequestError(f"recognition connection failed: {erro}") from erro

        _usar_google_a_partir_de = time.monotonic() + SEGUNDOS_OFFLINE
        if not _avisou_offline:
            avisar("Sem acesso ao serviço de voz do Google: usando o reconhecimento offline.")
            _avisou_offline = True
        return _transcrever_offline(offline, audio, avisar)
