"""Ativação do Jarvis pelo teclado.

Atalhos globais (funcionam com qualquer janela em foco, inclusive Word ou Edge abertos pelo
Jarvis), usando o pacote pynput:

- CTRL+ALT+J: o Jarvis começa a ouvir. Apertado de novo enquanto ele ouve, cancela a escuta.
- CTRL+ALT+NUM 0-9 (teclado numérico): o Jarvis age como se você tivesse falado a frase
  pré-programada daquele número (veja atalhos.py).

As teclas do teclado numérico são bloqueadas: não chegam à janela da frente (senão um Word
aberto receberia o número, ou um caractere como "²"). As teclas que o próprio Jarvis aperta
pelo PyAutoGUI nunca disparam os atalhos: o pynput ignora teclas simuladas por programas.

Para testar os atalhos sem executar nada:  python ativacao.py
"""
import queue
import threading
import time

from automacao.comum import log

ATALHO = "<ctrl>+<alt>+j"   # formato do pynput: "<ctrl>+<shift>+k", "<f9>", "<pause>"...

TEMPO_PARA_INICIAR = 3      # segundos esperando o gancho do teclado ficar pronto

# Eventos devolvidos por AtalhoGlobal.esperar()
OUVIR = "ouvir"             # (OUVIR, None)
FRASE = "frase"             # (FRASE, número do teclado numérico)

# ---------------------------------------------------------------- teclado numérico (Windows)
_VK_SHIFT, _VK_CONTROL, _VK_MENU = 0x10, 0x11, 0x12
_VK_DOS_MODIFICADORES = {"<shift>": _VK_SHIFT, "<ctrl>": _VK_CONTROL, "<alt>": _VK_MENU}
_VK_NUMPAD = {0x60 + n: n for n in range(10)}            # NumLock ligado: VK_NUMPAD0..9
# NumLock desligado: o teclado numérico manda as teclas de navegação, mas sem a marca
# "estendida" (as setas/Home/End separadas do teclado têm essa marca).
_VK_NUMPAD_SEM_NUMLOCK = {
    0x2D: 0, 0x23: 1, 0x28: 2, 0x22: 3, 0x25: 4,          # Insert, End, ↓, Page Down, ←
    0x0C: 5, 0x27: 6, 0x24: 7, 0x26: 8, 0x21: 9,          # Clear, →, Home, ↑, Page Up
}
_LLKHF_EXTENDED = 0x01
_LLKHF_INJETADA = 0x10 | 0x02                             # LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED
_WM_TECLA_DESCE = (0x0100, 0x0104)                        # WM_KEYDOWN, WM_SYSKEYDOWN
_WM_TECLA_SOBE = (0x0101, 0x0105)                         # WM_KEYUP, WM_SYSKEYUP
# Tecla sem função (a mesma que o AutoHotkey usa): apertada junto com um atalho bloqueado,
# evita que soltar o Alt ative o menu da janela da frente.
_VK_MASCARA = 0xE8


def nome_do_atalho(atalho):
    """Como o atalho aparece na tela: "<ctrl>+<alt>+j" -> "CTRL+ALT+J"."""
    return "+".join(parte.strip("<>").upper() for parte in atalho.split("+"))


NOME_ATALHO = nome_do_atalho(ATALHO)


def nome_atalho_numerico(numero):
    return f"CTRL+ALT+NUM {numero}"


def digito_do_teclado_numerico(vk, flags):
    """Número (0-9) se a tecla for do teclado numérico, com NumLock ligado ou desligado; senão None."""
    if vk in _VK_NUMPAD:
        return _VK_NUMPAD[vk]
    if vk in _VK_NUMPAD_SEM_NUMLOCK and not flags & _LLKHF_EXTENDED:
        return _VK_NUMPAD_SEM_NUMLOCK[vk]
    return None


def _teclas_apertadas(*vks):
    """Todas essas teclas estão apertadas agora, segundo o Windows? (fora do Windows: True)"""
    try:
        import ctypes
        estado = ctypes.windll.user32.GetAsyncKeyState
    except (ImportError, AttributeError):
        return True
    return all(estado(vk) & 0x8000 for vk in vks)


def _ctrl_e_alt_apertados():
    return _teclas_apertadas(_VK_CONTROL, _VK_MENU)


def _apertar_mascara():
    try:
        import ctypes
        teclado = ctypes.windll.user32.keybd_event
        teclado(_VK_MASCARA, 0, 0, 0)
        teclado(_VK_MASCARA, 0, 0x0002, 0)                 # KEYEVENTF_KEYUP
    except Exception:
        pass


class ErroAtalho(Exception):
    """O atalho de teclado não pôde ser ativado ou parou de funcionar."""


class AtalhoGlobal:
    def __init__(self, atalho=ATALHO, numeros=()):
        """numeros: dígitos do teclado numérico com frase pré-programada (os outros não são tocados)."""
        self.atalho = atalho
        self.numeros = frozenset(numeros)
        self._fila = queue.Queue()
        self._ouvinte = None
        self._seguradas = set()      # teclas numéricas bloqueadas que ainda não foram soltas
        self._ouvindo = False
        self.cancelar = threading.Event()   # ativado por CTRL+ALT+J durante a escuta

        # modificadores do atalho de ouvir ("<ctrl>+<alt>+j" -> CTRL e ALT), conferidos a cada uso
        self._vks_do_atalho = [_VK_DOS_MODIFICADORES[p] for p in atalho.lower().split("+")
                               if p in _VK_DOS_MODIFICADORES]

        # dá para trocar nos testes (fora do Windows)
        self._ctrl_e_alt = _ctrl_e_alt_apertados
        self._modificadores_apertados = lambda: _teclas_apertadas(*self._vks_do_atalho)
        self._mascara = _apertar_mascara

    def iniciar(self):
        """Começa a observar o teclado. Levanta ErroAtalho se não for possível."""
        try:
            from pynput import keyboard
        except ImportError as e:
            log(f"Falha ao importar o pynput: {e}")
            raise ErroAtalho("Não consegui carregar o pacote 'pynput' (pip install -r requirements.txt).") from e

        try:
            self._ouvinte = keyboard.GlobalHotKeys(
                {self.atalho: self._apertou_ouvir},
                win32_event_filter=self._filtrar,
            )
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
        log(f"Atalho {self.atalho} ativo. Frases no teclado numérico: {sorted(self.numeros)}")

    # -------------------------------------------- roda na thread do teclado: precisa ser rápido
    # (o Windows desliga ganchos lentos), então só registra o evento e volta.

    def _apertou_ouvir(self):
        # O pynput guarda sozinho quais teclas estão apertadas. Se ele perder o "soltar" do CTRL
        # ou do ALT (CTRL+ALT+DEL, janela de administrador...), um J sozinho dispararia o atalho;
        # por isso confere no Windows se os modificadores estão mesmo apertados.
        if not self._modificadores_apertados():
            log(f"{nome_do_atalho(self.atalho)} ignorado: os modificadores não estão apertados "
                "(estado preso no pynput).")
            return
        if self._ouvindo:
            self.cancelar.set()             # já está ouvindo: o mesmo atalho cancela
        else:
            self._fila.put((OUVIR, None))

    def _filtrar(self, msg, data):
        """Filtro do pynput, chamado para cada tecla antes de chegar aos programas.

        Retorna True para a tecla seguir normalmente; chama suppress_event() para bloqueá-la.
        """
        if data.flags & _LLKHF_INJETADA:                  # tecla simulada (PyAutoGUI, a máscara...)
            return True
        numero = digito_do_teclado_numerico(data.vkCode, data.flags)
        if numero is None or numero not in self.numeros:
            return True

        if msg in _WM_TECLA_DESCE:
            if data.vkCode in self._seguradas:            # repetição automática da tecla segurada
                self._ouvinte.suppress_event()            # (bloqueia e sai: levanta uma exceção)
            if not self._ctrl_e_alt():
                return True                               # número sem CTRL+ALT: segue normal
            self._seguradas.add(data.vkCode)
            self._fila.put((FRASE, numero))
            self._mascara()
            self._ouvinte.suppress_event()
        elif msg in _WM_TECLA_SOBE and data.vkCode in self._seguradas:
            self._seguradas.discard(data.vkCode)
            self._ouvinte.suppress_event()
        return True

    # -------------------------------------------- usado pelo programa principal

    def comecar_escuta(self):
        """A partir daqui, CTRL+ALT+J cancela a escuta (ativa self.cancelar)."""
        self.cancelar.clear()
        self._ouvindo = True

    def terminar_escuta(self):
        """CTRL+ALT+J volta a significar "comece a ouvir"."""
        self._ouvindo = False

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
        """Bloqueia até um atalho ser apertado. Retorna (OUVIR, None) ou (FRASE, número).

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


if __name__ == "__main__":
    # Teste dos atalhos: mostra o que cada um faria, sem ouvir nem executar nada.
    from atalhos import FRASES

    atalho = AtalhoGlobal(numeros=FRASES)
    try:
        atalho.iniciar()
    except ErroAtalho as erro:
        raise SystemExit(f"ERRO: {erro}")

    print(f"Teste dos atalhos. Aperte {NOME_ATALHO} ou CTRL+ALT+NUM 0-9 (CTRL+C para sair).")
    print(f"(Aqui o {NOME_ATALHO} não abre a escuta, então também não mostra o cancelamento.)")
    print("Dica: abra o Bloco de Notas na frente; os números NÃO devem aparecer nele.")
    try:
        while True:
            tipo, numero = atalho.esperar()
            hora = time.strftime("%H:%M:%S")
            if tipo == OUVIR:
                print(f"[{hora}] {NOME_ATALHO}: o Jarvis começaria a ouvir.")
            else:
                print(f'[{hora}] {nome_atalho_numerico(numero)}: "{FRASES[numero]}"')
    except KeyboardInterrupt:
        print("\nTeste encerrado.")
    finally:
        atalho.parar()
