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

## Notes

- A working microphone and an internet connection (for speech recognition) are required. Make sure Windows allows desktop apps to use the microphone (Settings > Privacy & security > Microphone).
- PyAutoGUI takes control of your mouse and keyboard while running. Move the mouse to a screen corner to trigger the built-in fail-safe and stop it.
- The `.venv` folder is local to your machine and should not be committed to Git.

## Future Improvements

- Support for more commands and applications
- Wake word activation (e.g., "Hey Assistant")
- Offline speech recognition
- Multi-language support
