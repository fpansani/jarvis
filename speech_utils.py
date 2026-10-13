import speech_recognition as sr

def SpeechRecognition():
    recognition = sr.Recognizer()

    try:
        with sr.Microphone() as microfone:
            print("Ligando o microfone...")
            recognition.adjust_for_ambient_noise(
                microfone, duration = 1
            )

            print("Fale agora...")
            audio = recognition.listen(
                microfone,
                timeout=10,
                phrase_time_limit=15
            )

        print("Convertendo voz em texto...")

        text = recognition.recognize_google(
            audio,
            language='pt-BR'
        )

        print(f"Você disse: {text}")

        return text
    
    except sr.WaitTimeoutError:
        print("Nenhuma fala detectada.")
    except sr.UnknownValueError:
        print("Não consegui entender o que foi dito.")
    except sr.RequestError as erro:
        print(f"Erro no serviço de reconhecimento: {erro}")
    except OSError as erro:
        print(f"Erro ao aacessar o microfone: {erro}")

    return None