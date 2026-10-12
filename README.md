# Jarvis

A Python project that listens to your voice commands and performs actions on your computer using PyAutoGUI. Speak a natural command, and the program transcribes it, interprets what you want, and automates the mouse and keyboard to carry it out.


## Features

- Real-time voice recognition
- Natural language command parsing
- Desktop automation (mouse movements, clicks, and keyboard input)
- Easily extensible: add new commands and workflows with a few lines of code

## Tech Stack

- **Python 3.13.0**
- **SpeechRecognition**: converts voice to text
- **PyAudio**: microphone access
- **PyAutoGUI**: controls the mouse and keyboard
- **Requests**: weather lookup (Open-Meteo API)

## Requirements

- **Windows** (this project is intended to run on Windows machines only)
- **Python 3.13.0** (see the note below about other versions)
- A working microphone and an internet connection (for speech recognition and weather)

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

## Usage

With the virtual environment active:

```powershell
python main.py
```

Wait for the program to start listening, then speak your command.

## Commands

Speak naturally; Jarvis matches keywords from `words.py` (accents and capitalization are ignored). After answering, it waits 2 seconds and then runs the automation.

| Command | Example | What it does |
|---|---|---|
| `time` | "Que horas são?" | Says the current time |
| `degree` | "Qual a temperatura?" | Says the current temperature |
| `calc` | "Abra a calculadora" / "Calcule 5 vezes 2" | Opens the Calculator, or computes and types the operation |
| `word` | "Crie um novo documento no Word e escreva uma saudação" | Opens Word, creates a document, optionally writes a greeting |
| `excel` | "Crie uma nova planilha no Excel" | Opens Excel, optionally creates a new workbook |
| `paint` | "Abra o Paint" | Opens Paint |
| `yt` | "Abra o YouTube" | Opens YouTube in Edge |
| `news` | "Me mostre as notícias do dia" | Opens CNN Brasil in Edge |
| `site` | "Abra o site do colégio" | Opens the school website in Edge |
| `insta` | "Abra o Instagram do colégio" | Opens the school Instagram in Edge |

The PyAutoGUI automations live in the `automacao/` package. Each one can also be tested alone, from the project root with the `.venv` active, using the spoken sentence as arguments:

```powershell
python -m automacao.calc calcule 5 vezes 2
python -m automacao.word crie um novo documento no word e escreva uma saudação
python -m automacao.youtube abra o youtube
```

## Notes

- A working microphone and an internet connection (for speech recognition) are required. Make sure Windows allows desktop apps to use the microphone (Settings > Privacy & security > Microphone).
- PyAutoGUI takes control of your mouse and keyboard while running. Move the mouse to a screen corner to trigger the built-in fail-safe and stop it.
- The `.venv` folder is local to your machine and should not be committed to Git.
- Image recognition (`automacao/imgs/`) needs `Pillow` and `opencv-python`, which are already in `requirements.txt`. Screen scaling other than 100% may stop the images from being found.
- If an automation fails (window did not open, image not found, no internet), Jarvis prints the reason and keeps running.

## Future Improvements

- Support for more commands and applications
- Wake word activation (e.g., "Hey Assistant")
- Offline speech recognition
- Multi-language support
