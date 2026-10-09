from speech import SpeechRecognition
from datetime import datetime
import pyautogui
from speech_recognition import SpeechRecognition
from words import commands
import functions as fn
import re
import requests

text = SpeechRecognition()

result = fn.find_command(text)

if result:
    category, name = result
    func = getattr(fn, name, None)
    if func:
        func()