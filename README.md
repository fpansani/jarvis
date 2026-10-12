# Jarvis

A Python project that listens to your voice commands and performs actions on your computer using PyAutoGUI. Speak a natural command, and the program transcribes it, interprets what you want, and automates the mouse and keyboard to carry it out.

## Features

- Real-time voice recognition
- Natural language command parsing
- Desktop automation (mouse movements, clicks, and keyboard input)
- Easily extensible: add new commands and workflows with a few lines of code

## Tech Stack

- **Python 3.13.0**
- **SpeechRecognition**: converts voice to text (Google online)
- **Vosk**: offline voice recognition, used when there is no internet
- **pynput**: global keyboard shortcut (CTRL+ALT+J) that tells Jarvis to listen
- **PyAudio**: microphone access
- **PyAutoGUI**: controls the mouse and keyboard
- **Requests**: weather lookup (Open-Meteo API)

## Requirements

- **Windows** (this project is intended to run on Windows machines only)
- **Python 3.13.0** (see the note below about other versions)
- A working microphone
- An internet connection for the best speech recognition and for the weather (without it, Jarvis falls back to offline recognition; see [Offline mode](#offline-mode))

> **Note:** Python 3.14 is not supported. Use 3.13.0 to make sure every package installs correctly, especially PyAudio, which needs a pre-built Windows package for your Python version.
>
> If you have several Python versions installed, run `py -0` to list them and use `py -3.13` to pick the right one.

## Installation

### 1. Get the project

```bash
git clone https://github.com/marcospmtech/jarvis
cd jarvis
```

### 2. Create the virtual environment (`.venv`) with Python 3.13

```powershell
py -3.13 -m venv .venv
```

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt (CMD):

```bat
.venv\Scripts\activate.bat
```

When it is active, the prompt starts with `(.venv)`. Check the version:

```powershell
python --version
```

It should print `Python 3.13.0`.

### 4. Install the dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Offline mode

With internet, Jarvis recognizes your voice with Google. Without it (or if Google stops answering), it switches to **Vosk**, which runs on your computer. This needs a Portuguese Vosk model in the `models/` folder (it is not part of the repository because of its size):

1. Download a Portuguese model from <https://alphacephei.com/vosk/models>. The small `vosk-model-small-pt-0.3` (31 MB) loads fast but recognizes poorly; the [`vosk-model-pt-fb-v0.1.1-pruned`](https://github.com/alphacep/vosk-api/issues/991#issuecomment-1197512394) model worked well in tests.
2. Unzip it inside `models/`, so you get e.g. `models/vosk-model-pt-fb-v0.1.1-pruned/` (with the model files directly inside).
3. Run `python main.py` as usual.

How it behaves:

- **No internet at startup:** the model is loaded right away (a few seconds) and Jarvis starts in offline mode.
- **Internet drops while running:** the sentence being recognized is reprocessed by Vosk, and Jarvis keeps using Vosk for 30 seconds before trying Google again. It goes back to Google by itself when the connection returns.
- **With internet:** Vosk stays unloaded (no extra memory) until it is needed.
- **Several models in `models/`:** Jarvis prefers one that is not the "small" model. To choose, set the `JARVIS_MODELO_VOSK` environment variable to the folder name (PowerShell: `$env:JARVIS_MODELO_VOSK = "vosk-model-pt-fb-v0.1.1-pruned"`).
- Offline mode only recognizes speech. Commands that need the internet (such as `degree`, or opening websites) still need it.
- Vosk writes everything in lowercase and may misspell foreign words (Excel, YouTube, Instagram). If a command is not detected offline, check how Jarvis printed what you said and add that spelling to `words.py`.

## Usage

With the virtual environment active:

```powershell
python main.py
```

When the screen shows `Pressione CTRL+ALT+J para falar.`, press **CTRL+ALT+J** (it works with any window in front, even Word or Edge opened by Jarvis), wait for the short beep and speak your command. Jarvis listens to one sentence, answers and goes back to waiting for the shortcut.

### Keyboard activation

- Jarvis only listens after **CTRL+ALT+J**. If you say nothing for 10 seconds, it shows `(não entendi)` and waits for the shortcut again.
- **Cancel:** press **CTRL+ALT+J again while Jarvis is listening**. It stops right away, plays a lower beep, shows `(cancelado)` and waits for the shortcut again. If you press it while your sentence is already being recognized, the result is discarded and nothing is executed.
- Presses made while Jarvis is busy (listening or running a task) are ignored, so a double press does not start a second command.
- The keys Jarvis itself types through PyAutoGUI never trigger the shortcut.
- The shortcut still reaches the window in front. CTRL+ALT+J does nothing in the apps Jarvis uses, but keep that in mind if you change it.
- **Change the shortcut:** edit `ATALHO` and `NOME_ATALHO` in `ativacao.py` (pynput format, e.g. `"<ctrl>+<shift>+k"` or `"<f9>"`).
- **Always listening, as before:** set `ATIVACAO_POR_TECLA = False` in `main.py`. Jarvis also falls back to this mode by itself (and says so in the header) if the shortcut cannot be enabled.
- **No beep:** set `BIPE_AO_OUVIR = False` in `main.py`.
- The microphone is calibrated once at startup (stay quiet for that second), so Jarvis starts listening right after the shortcut.

### Pre-programmed phrases (CTRL+ALT+NUM 0-9)

For presentations, **CTRL+ALT + a number on the numeric keypad** makes Jarvis act as if you had said a fixed phrase: after a short pause the phrase appears after `> `, exactly like recognized speech, and goes through the same commands. The microphone is not used.

| Shortcut | Phrase | Needs internet |
|---|---|---|
| CTRL+ALT+NUM 1 | "Jarvis, que horas são?" | No |
| CTRL+ALT+NUM 2 | "Jarvis, qual a temperatura em Santo André?" | Yes |
| CTRL+ALT+NUM 3 | "Jarvis, calcule 5 vezes 2." (only says the result; does not open the Calculator) | No |
| CTRL+ALT+NUM 4 | "Jarvis, crie um novo documento no Word e escreva uma saudação." | No |
| CTRL+ALT+NUM 5 | "Jarvis, crie uma nova planilha no Excel." | No |
| CTRL+ALT+NUM 6 | "Jarvis, abra o Paint." | No |
| CTRL+ALT+NUM 7 | "Jarvis, abra o YouTube." | Yes |
| CTRL+ALT+NUM 8 | "Jarvis, me mostre as notícias do dia." | Yes |
| CTRL+ALT+NUM 9 | "Jarvis, abra o site do colégio." | Yes |
| CTRL+ALT+NUM 0 | "Jarvis, abra o Instagram do colégio." | Yes |

- Only the **numeric keypad** keys work (with NumLock on or off), not the numbers above the letters.
- These keys are blocked for the window in front, so Word or Notepad never receive the number while you use a shortcut. Numeric keypad keys without CTRL+ALT keep working normally.
- **Change a phrase:** edit `FRASES` in `atalhos.py` (write it the way you would say it). Delete a line to free that key.
- **Pause before the phrase appears:** `PAUSA_ANTES_DA_FRASE` in `atalhos.py` (use `0` to show it immediately).
- **Test the shortcuts without running anything:** `python ativacao.py` prints which shortcut was detected and its phrase. Keep Notepad in front while testing: no numbers should appear in it.

## Debug messages

By default Jarvis only shows what you said, its answers and, when something fails, the reason. To see the step-by-step messages (automation attempts, window titles, recognition and response times, which keyword matched each command, how the city was found, which Vosk model was chosen), turn on debug mode in either of these ways:

- **In the code:** in `automacao/comum.py`, change `DEBUG = False` to `DEBUG = True`.
- **Only for one run, without editing the code:** set the `JARVIS_DEBUG` environment variable before starting Jarvis:

  ```powershell
  $env:JARVIS_DEBUG = "1"    # PowerShell
  python main.py
  ```

  ```bat
  set JARVIS_DEBUG=1
  python main.py
  ```

  It stays on for that terminal window; close it (or set `JARVIS_DEBUG` to `0`) to turn it off.

Debug lines start with `[debug]`, and the header shows `** MODO DEBUG **` while it is on. The same setting applies to the automations tested alone (`python -m automacao.calc ...`).

## Commands

Speak naturally; Jarvis matches keywords from `words.py` (accents and capitalization are ignored). After answering, it waits 2 seconds and then runs the automation.

| Command  | Example                                                 | What it does                                                                                                                                       |
| -------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `time`   | "Que horas são?"                                        | Says the current time                                                                                                                              |
| `degree` | "Qual a temperatura em Curitiba?"                       | Says the current temperature in the city you name (default: Santo André)                                                                           |
| `calc`   | "Abra a calculadora" / "Calcule 5 vezes 2"              | Opens the Calculator, or just says the result of the operation. Say "...na calculadora" ("Calcule 5 vezes 2 na calculadora") to also type it there |
| `word`   | "Crie um novo documento no Word e escreva uma saudação" | Opens Word, creates a document, optionally writes a greeting                                                                                       |
| `excel`  | "Crie uma nova planilha no Excel"                       | Opens Excel, optionally creates a new workbook                                                                                                     |
| `paint`  | "Abra o Paint"                                          | Opens Paint                                                                                                                                        |
| `yt`     | "Abra o YouTube"                                        | Opens YouTube in Edge                                                                                                                              |
| `news`   | "Me mostre as notícias do dia"                          | Opens CNN Brasil in Edge                                                                                                                           |
| `site`   | "Abra o site do colégio"                                | Opens the school website in Edge                                                                                                                   |
| `insta`  | "Abra o Instagram do colégio"                           | Opens the school Instagram in Edge                                                                                                                 |

The PyAutoGUI automations live in the `automacao/` package. Each one can also be tested alone, from the project root with the `.venv` active, using the spoken sentence as arguments:

```powershell
python -m automacao.calc calcule 5 vezes 2
python -m automacao.word crie um novo documento no word e escreva uma saudação
python -m automacao.youtube abra o youtube
```

## Notes

- A working microphone is required (and an internet connection, unless you set up [offline mode](#offline-mode)). Make sure Windows allows desktop apps to use the microphone (Settings > Privacy & security > Microphone).
- PyAutoGUI takes control of your mouse and keyboard while running. Move the mouse to a screen corner to trigger the built-in fail-safe and stop it.
- The `.venv` folder is local to your machine and should not be committed to Git.
- Image recognition (`automacao/imgs/`) needs `Pillow` and `opencv-python`, which are already in `requirements.txt`. Screen scaling other than 100% may stop the images from being found.
- If an automation fails (window did not open, image not found, no internet), Jarvis prints the reason and keeps running.

## Future Improvements

- Support for more commands and applications
- Wake word activation (e.g., "Hey Jarvis")
- Multi-language support
