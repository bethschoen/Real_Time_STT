from flask import Flask, render_template, request, jsonify
import azure.cognitiveservices.speech as speechsdk
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import subprocess
import pandas as pd
from time import gmtime, strftime
import time

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
        e = "No speech could be recognized: {}.".format(speech_recognition_result.no_match_details)
        logger.info(e)
        return jsonify({"error": e}), 400
   
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        e = "Speech Recognition canceled: {}.".format(cancellation_details.reason)
        logger.info(e)

        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            extra_details = f" Error details: {cancellation_details.error_details}. Did you set the speech resource key and endpoint values?"
            logger.info(extra_details)
        else:
            extra_details = ""

        return jsonify({"error": e + extra_details}), 400
    
def single_shot_transcription(audio_path: str, language:str="en-GB"):
    """
    Transcription of audio less than 15 seconds
    """
    speech_key = os.getenv("SPEECH_KEY")
    service_region = "uksouth"

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)  
    
    speech_config.speech_recognition_language=language
    logger.info(f"Connection to Azure Speech Services setup using language {language}")

    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    logger.info("Transcription request made")

    # delete resources so that we can delete audio files later
    del speech_recognizer
    audio_config = None

    return check_result_from_azure(speech_recognition_result)

    
def speech_recognize_continuous_from_file(filename: str, language:str="en-GB"):
    """
    performs continuous speech recognition with input from an audio file
    TODO: error handling
    """
    speech_config = speechsdk.SpeechConfig(subscription=os.getenv("SPEECH_KEY"), endpoint="https://uksouth.api.cognitive.microsoft.com")
    speech_config.speech_recognition_language=language 
    audio_config = speechsdk.audio.AudioConfig(filename=filename)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    done = False

    def stop_cb(evt: speechsdk.SessionEventArgs):
        """callback that signals to stop continuous recognition upon receiving an event `evt`"""
        logger.info("CLOSING on {}".format(evt))
        nonlocal done
        done = True

    final_transcription = []

    def text_recognized(evt):
        final_transcription.append(evt.result.text)

    # collect recognized text
    speech_recognizer.recognized.connect(text_recognized)

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.session_started.connect(lambda evt: logger.info("SESSION STARTED: {}".format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: logger.info("SESSION STOPPED {}".format(evt)))
    speech_recognizer.canceled.connect(lambda evt: logger.info("CANCELED {}".format(evt)))
    # Stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(0.5)

    speech_recognizer.stop_continuous_recognition()    

    return " ".join(final_transcription)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    logger.info("Start transcribe route...")
    # access uploaded audio and save locally
    file = request.files["audio"]
    input_path = "audio/input.wav"
    file.save(input_path)
    logger.info("Audio stored locally")  

    # Check if conversion is needed
    original_filename = file.filename.lower()      
    needs_conversion = not original_filename.endswith(".wav")
    if needs_conversion:
        converted_path = "audio/converted.wav"
        convert_audio_to_wav(input_path, converted_path)
        audio_path = converted_path
    else:
        logger.info("Uploaded file is already a WAV file. No conversion needed.")
        audio_path = input_path

    # Transcribe with Azure
    language = request.form.get("language_setting")
    # recognized_speech = single_shot_transcription(audio_path, language)
    before = time.time()
    recognized_speech = speech_recognize_continuous_from_file(audio_path, language)
    after = time.time()
    logger.info(f"Audio transcribed, Time elapsed: {after-before}s")
    
    # Remove audio locally
    os.remove(input_path)
    if needs_conversion:
        os.remove(audio_path)
    logger.info("Audio removed locally")

    if len(recognized_speech) < 5:
        return jsonify({"error": "No information returned from Azure Speech Services. Something went wrong..."}), 400

    return jsonify({"transcript": recognized_speech}), 200

@app.route("/save-transcript", methods=["POST"])
def save_transcript():
    edited_text = request.form.get("edited_transcript")
    if len(edited_text) == 0:
        return jsonify({"error": f"No text provided when trying to save."}), 400

    mode = request.form.get("mode")
    language = request.form.get("language")

    try:
        df = pd.read_csv("transcriptions.csv")
        id = 1 if len(df) == 0 else df["id"].max() + 1        
        timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        df.loc[len(df)] = [id, timestamp, mode, language, edited_text]
        df.to_csv("transcriptions.csv", index=False)

        return jsonify({"msg": "Successful!"}), 200
    
    except Exception as e:
        return jsonify({"error": f"Something went wrong when saving transcription: {e}"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)






