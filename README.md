# Jarvis

A Python project that listens to your voice commands and performs actions on your computer using PyAutoGUI. Speak a natural command, and the program transcribes it, interprets what you want, and automates the mouse and keyboard to carry it out.


## Features

- Real-time voice recognition
- Natural language command parsing
- Desktop automation (mouse movements, clicks, and keyboard input)
- Easily extensible: add new commands and workflows with a few lines of code

## Tech Stack

- **Python 3.x**
- **SpeechRecognition**: converts voice to text
- **PyAudio**: microphone access
- **PyAutoGUI**: controls the mouse and keyboard

## Installation

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Wait for the program to start listening, then speak your command.

## Notes

- A working microphone and an internet connection (for speech recognition) are required.
- PyAutoGUI takes control of your mouse and keyboard while running. Move the mouse to a screen corner to trigger the built-in fail-safe and stop it.

## Future Improvements

- Support for more commands and applications
- Wake word activation (e.g., "Hey Assistant")
- Offline speech recognition
- Multi-language support