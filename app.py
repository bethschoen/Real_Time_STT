from flask import Flask, render_template, request, jsonify
import azure.cognitiveservices.speech as speechsdk
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import subprocess

FFMPEG_PATH = r"ffmpeg.exe"

app = Flask(__name__)

class Logger:

    def __init__(self, print:bool=True):
        self.print = print

    def info(self, msg):
        if self.print:
            print(f'{datetime.now()} - INFO - {msg}', flush=True)

logger = Logger()

@app.route("/")
def index():
    logger.info("Page loaded")
    return render_template("index.html")
    #return "Hello from flask"

def convert_audio_to_wav(audio_path: str, save_path: str):

    logger.info(f"Uploaded file ({audio_path}) is not WAV. Converting...")
    try:
        subprocess.run([
            FFMPEG_PATH, "-y", "-i", audio_path,
            "-ar", "16000", "-ac", "1", save_path
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        logger.info(f"FFmpeg conversion failed: {e}")
        return jsonify({"error": "Audio conversion failed"}), 400
    
def check_result_from_azure(speech_recognition_result):
    """
    Having received a result from Azure, check whether it worked or not
    """
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        logger.info("Recognized: {}".format(speech_recognition_result.text))
        return jsonify({"transcript": speech_recognition_result.text}), 200
   
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        logger.info("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
        return jsonify({"error": "Could not recognize speech"}), 400
   
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        logger.info("Speech Recognition canceled: {}".format(cancellation_details.reason))

        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            logger.info("Error details: {}".format(cancellation_details.error_details))
            logger.info("Did you set the speech resource key and endpoint values?")

        return jsonify({"error": "Could not recognize speech"}), 400


@app.route("/transcribe", methods=["POST"])
def transcribe():
    logger.info("Start transcribe route...")
    file = request.files["audio"]
    input_path = "input.wav"
    file.save(input_path)
    logger.info("Audio stored locally")  

    # Check if conversion is needed
    original_filename = file.filename.lower()      
    needs_conversion = not original_filename.endswith(".wav")
    if needs_conversion:
        converted_path = "converted.wav"
        convert_audio_to_wav(input_path, converted_path)
        audio_path = converted_path
    else:
        logger.info("Uploaded file is already a WAV file. No conversion needed.")
        audio_path = input_path

    # Transcribe with Azure
    speech_key = os.getenv("SPEECH_KEY")
    service_region = "uksouth"

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)  
    logger.info("Connection to Azure Speech Services setup")

    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    logger.info("Transcription request made")

    # delete local audio files
    del speech_recognizer
    audio_config = None
    os.remove(input_path)
    if needs_conversion:
        os.remove(audio_path)
    logger.info("Audio removed locally")

    return check_result_from_azure(speech_recognition_result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)






