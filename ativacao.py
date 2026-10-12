"""Ativação do Jarvis pelo teclado.

Um atalho global (funciona com qualquer janela em foco, inclusive Word ou Edge abertos pelo
Jarvis) avisa o programa principal de que é hora de ouvir. Usa o pacote pynput.

As teclas que o próprio Jarvis aperta pelo PyAutoGUI não disparam o atalho: o pynput ignora
teclas simuladas por programas.
"""
import queue
import threading
import time

from automacao.comum import log

ATALHO = "<ctrl>+<alt>+j"   # formato do pynput: "<ctrl>+<shift>+k", "<f9>", "<pause>"...
NOME_ATALHO = "CTRL+ALT+J"  # como o atalho aparece na tela

TEMPO_PARA_INICIAR = 3      # segundos esperando o gancho do teclado ficar pronto


class ErroAtalho(Exception):
    """O atalho de teclado não pôde ser ativado ou parou de funcionar."""


class AtalhoGlobal:
    def __init__(self, atalho=ATALHO):
        self.atalho = atalho
        self._fila = queue.Queue()
        self._ouvinte = None

    def iniciar(self):
        """Começa a observar o teclado. Levanta ErroAtalho se não for possível."""
        try:
            from pynput import keyboard
        except ImportError as e:
            raise ErroAtalho("O pacote 'pynput' não está instalado (pip install -r requirements.txt).") from e

        try:
            self._ouvinte = keyboard.GlobalHotKeys({self.atalho: self._apertou})
        except ValueError as e:
            raise ErroAtalho(f"Atalho inválido: {self.atalho!r}.") from e
        self._ouvinte.start()

        # O wait() do pynput não tem prazo: se o gancho falhar ao iniciar, ele esperaria para sempre.
        pronto = threading.Thread(target=self._ouvinte.wait, daemon=True)
        pronto.start()
        pronto.join(TEMPO_PARA_INICIAR)
        if pronto.is_alive() or not self._ouvinte.is_alive():
            self.parar()
            raise ErroAtalho("Não consegui ativar o atalho de teclado.")
        log(f"Atalho {self.atalho} ativo.")

    def _apertou(self):
        # Roda na thread do teclado: só registra e volta rápido (o Windows desliga ganchos lentos).
        self._fila.put(time.monotonic())

    def descartar_pendentes(self):
        """Joga fora acionamentos feitos enquanto o Jarvis estava ocupado. Retorna quantos eram."""
        descartados = 0
        while True:
            try:
                self._fila.get_nowait()
            except queue.Empty:
                return descartados
            descartados += 1

    def esperar(self, intervalo=0.2):
        """Bloqueia até o atalho ser apertado.

        Espera em pedaços curtos para o CTRL+C continuar encerrando o Jarvis no Windows.
        """
        while True:
            try:
                return self._fila.get(timeout=intervalo)
            except queue.Empty:
                if self._ouvinte is None or not self._ouvinte.is_alive():
                    raise ErroAtalho("O atalho de teclado parou de funcionar.") from None

    def parar(self):
        if self._ouvinte is not None:
            try:
                self._ouvinte.stop()
            except Exception:
                pass
