import speech_recognition as sr


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


def SpeechRecognition():
    """Escuta uma vez e retorna o texto falado.

    Retorna None se nenhuma fala foi detectada ou se a fala não foi entendida.
    Erros do serviço de reconhecimento (sr.RequestError) e do microfone
    (OSError) são propagados para quem chamou.
    """
    recognition = sr.Recognizer()

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

    try:
        return recognition.recognize_google(
            audio,
            language='pt-BR'
        )
    except sr.UnknownValueError:
        return None
