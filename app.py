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
from openai import AzureOpenAI
import smtplib
import ssl

import variables as vr
FFMPEG_PATH = r"ffmpeg.exe"

app = Flask(__name__)

# informal logger
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

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=vr.service_region)
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

    
def speech_transcription_continuous(filename: str, language:str="en-GB"):
    """
    performs continuous speech recognition with input from an audio file
    TODO: error handling
    """
    speech_config = speechsdk.SpeechConfig(subscription=os.getenv("SPEECH_KEY"), endpoint=vr.endpoint)
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

def speech_transcription_with_diarization(filename: str, language: str="en-GB"):
    speech_config = speechsdk.SpeechConfig(subscription=os.getenv('SPEECH_KEY'), endpoint=vr.endpoint)
    speech_config.speech_recognition_language=language
    speech_config.set_property(property_id=speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, value='true')

    audio_config = speechsdk.audio.AudioConfig(filename=filename)
    conversation_transcriber = speechsdk.transcription.ConversationTranscriber(speech_config=speech_config, audio_config=audio_config)

    transcribing_stop = False

    def conversation_transcriber_session_started_cb(evt: speechsdk.SessionEventArgs):
        logger.info('SessionStarted event')

    def conversation_transcriber_session_stopped_cb(evt: speechsdk.SessionEventArgs):
        logger.info('SessionStopped event')
        
    def conversation_transcriber_recognition_canceled_cb(evt: speechsdk.SessionEventArgs):
        logger.info('Canceled event')

    final_transcription = []

    def conversation_transcriber_transcribed_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            final_transcription.append(f"{evt.result.speaker_id.replace("Guest", "Speaker")}: {evt.result.text}")
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            logger.info('\tNOMATCH: Speech could not be TRANSCRIBED: {}'.format(evt.result.no_match_details))

    def stop_cb(evt: speechsdk.SessionEventArgs):
        #"""callback that signals to stop continuous recognition upon receiving an event `evt`"""
        logger.info('CLOSING on {}'.format(evt))
        nonlocal transcribing_stop
        transcribing_stop = True

    # Connect callbacks to the events fired by the conversation transcriber
    conversation_transcriber.transcribed.connect(conversation_transcriber_transcribed_cb)
    conversation_transcriber.session_started.connect(conversation_transcriber_session_started_cb)
    conversation_transcriber.session_stopped.connect(conversation_transcriber_session_stopped_cb)
    conversation_transcriber.canceled.connect(conversation_transcriber_recognition_canceled_cb)
    # stop transcribing on either session stopped or canceled events
    conversation_transcriber.session_stopped.connect(stop_cb)
    conversation_transcriber.canceled.connect(stop_cb)

    conversation_transcriber.start_transcribing_async()

    # Waits for completion.
    while not transcribing_stop:
        time.sleep(.5)

    conversation_transcriber.stop_transcribing_async()

    return "\n".join(final_transcription)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    logger.info("Start transcribe route...")
    # access uploaded audio and save locally
    file = request.files["audio"]
    
    file.save(vr.input_path)
    logger.info("Audio stored locally")  

    # Check if conversion is needed
    original_filename = file.filename.lower()      
    needs_conversion = not original_filename.endswith(".wav")
    if needs_conversion:
        
        convert_audio_to_wav(vr.input_path, vr.converted_path)
        audio_path = vr.converted_path
    else:
        logger.info("Uploaded file is already a WAV file. No conversion needed.")
        audio_path = vr.input_path

    # Transcribe with Azure
    language = request.form.get("language_setting")
    diarization = request.form.get("diarization") == 'true'
    logger.info(f"Diarization: {diarization}")
    # recognized_speech = single_shot_transcription(audio_path, language)
    if diarization:
        before = time.time()
        recognized_speech = speech_transcription_with_diarization(audio_path, language)
        after = time.time()
    else:
        before = time.time()
        recognized_speech = speech_transcription_continuous(audio_path, language)
        after = time.time()
    logger.info(f"Audio transcribed, Time elapsed: {after-before}s")
    
    # Remove audio locally
    os.remove(vr.input_path)
    if needs_conversion:
        os.remove(audio_path)
    logger.info("Audio removed locally")

    if len(recognized_speech) < 5:
        return jsonify({"error": "No information returned from Azure Speech Services. Something went wrong..."}), 400

    return jsonify({"transcript": recognized_speech}), 200

def process_summary(summary: str) -> str:

    # check the LLM formatted the output as bullet points
    if "•" not in summary:
        return summary
    
    # get each bullet point
    points = [i.strip() for i in summary.split("•") if len(i) > 2]#
    # start html bullet points
    combined_str = "<ul style='padding-left: 20px;'>"
    # iterate through each point, creating bullet point in html
    for item in points:
        combined_str += f"<li style='margin-bottom:5px;'>{item}</li>"
    # end html
    combined_str += "</ul>"

    return combined_str

@app.route("/summarise", methods=["POST"])
def summarise():

    transcript = request.form.get("edited_transcript")
    
    try:
        client_4o = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY_4O"),
            api_version="2025-01-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_4O")
        )
        logger.info("Connected to 4o-mini model")
    except Exception as e:
        error = "Unable to connect to client: " + str(e)
        return jsonify({"error": error}), 400

    try:
        response = client_4o.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role":"system",
                    "content":vr.summarise_prompt
                },
                {
                    "role":"user",
                    "content":"TRANSCRIPT: "+transcript
                }
            ]
        )
        summary = response.choices[0].message.content
        logger.info(f"Summary generated")
        processed_summary = process_summary(summary)

        return jsonify({"html_summary": processed_summary, "summary": summary}), 200
    
    except Exception as e:
        error = "Unable to generate summary: " + str(e)
        return jsonify({"error": error}), 400

@app.route("/save-transcript", methods=["POST"])
def save_transcript():
    edited_text = request.form.get("edited_transcript")
    if len(edited_text) == 0:
        return jsonify({"error": f"No text provided when trying to save."}), 400

    mode = request.form.get("mode")
    language = request.form.get("language")
    diarization = request.form.get("diarization")

    try:
        df = pd.read_csv(vr.transcriptions_data_path)
        id = 1 if len(df) == 0 else df["id"].max() + 1        
        timestamp = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        df.loc[len(df)] = [id, timestamp, mode, language, diarization, edited_text]
        df.to_csv(vr.transcriptions_data_path, index=False)

        return jsonify({"msg": "Successful!"}), 200
    
    except Exception as e:
        return jsonify({"error": f"Something went wrong when saving transcription: {e}"}), 400


def populate_email_template(email_info: dict) -> str:    

    def construct_email_part(template, info):

        if info == "":
            return ''
        else:
            return "\n" + template + info
    
    email_time = datetime.today().strftime('%Y-%m-%d %H:%M')
    email_subject = vr.email_subject + email_time
    email_datetime = vr.email_datetime + email_time
    email_filename = construct_email_part(vr.email_filename, email_info["filename"])
    email_mode = construct_email_part(vr.email_mode, email_info["mode"])
    email_language = construct_email_part(vr.email_language, email_info["language"])
    email_diarization = construct_email_part(vr.email_diarization, email_info["diarization"])
    email_transcript = construct_email_part(vr.email_transcript, email_info["transcript"])
    email_summary = construct_email_part(vr.email_summary, email_info["summary"])

    email_body = email_subject + vr.email_header + email_datetime + email_filename + email_mode + email_language + email_diarization + email_transcript + email_summary + vr.email_close

    return email_body
    
@app.route("/send-email", methods=["POST"])
def send_email():

    # get info
    try:
        needed_info = ["filename", "mode", "language", "diarization", "transcript", "summary", "user_email"]
        email_info = {i:request.form.get(i) for i in needed_info}
        email_message = populate_email_template(email_info)
        receiver_email = email_info["user_email"].lower()
        logger.info("Email generated")
        logger.info(email_message)

    except Exception as e:
        error = "Something wrong with the provided information: " + str(e)
        logger.info(error)
        return jsonify({"error": error}), 400
      
    # send email  
    try:
        sender_email = os.getenv("GMAIL_ADDRESS")
        port = 465  # For SSL
        password = os.getenv("GMAIL_PASSWORD")

        # Create a secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, email_message.encode('utf-8'))
        logger.info("Email sent!")
        return jsonify({"success": "Success!"}), 200

    except Exception as e:
        error = "Couldn't send email: " + str(e)
        logger.info(error)
        return jsonify({"error": error}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)






