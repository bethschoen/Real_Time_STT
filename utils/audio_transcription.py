import azure.cognitiveservices.speech as speechsdk
import os
import subprocess
import time
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import variables as vr
from log import logger

def convert_audio_to_wav(audio_path: str, save_path: str):

    try:
        subprocess.run([
            vr.FFMPEG_PATH, "-y", "-i", audio_path,
            "-ar", "16000", "-ac", "1", save_path
        ], check=True)
        return None, None
        
    except subprocess.CalledProcessError as e:
        return "Audio conversion failed", e
    
def check_result_from_azure(speech_recognition_result):
    """
    Having received a result from Azure, check whether it worked or not
    """
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        logger.info("Recognized: {}".format(speech_recognition_result.text))
        return speech_recognition_result.text, None
   
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        return "No speech could be recognised", speech_recognition_result.no_match_details
   
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            e = cancellation_details.error_details
        else:
            e = cancellation_details.reason
        return "Speech Recognition cancelled", e
    
def single_shot_transcription(audio_path: str, language:str="en-GB"):
    """
    Transcription of audio less than 15 seconds
    """
    speech_key = os.getenv("SPEECH_KEY")    

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region="uksouth")
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)  
    
    speech_config.speech_recognition_language=language
    logger.info(f"Connection to Azure Speech Services setup using language {language}")

    speech_recognition_result = speech_recognizer.recognize_once_async().get()
    logger.info("Transcription request made")

    # delete resources so that we can delete audio files later
    del speech_recognizer
    audio_config = None

    text, e = check_result_from_azure(speech_recognition_result)
    if not e:
        return text

    
def speech_transcription_continuous(filename: str, language:str="en-GB"):
    """
    performs continuous speech recognition with input from an audio file
    TODO: error handling
    """
    logger.info("Starting continuous transcription")
    logger.info(filename)
    speech_config = speechsdk.SpeechConfig(subscription=os.getenv("SPEECH_KEY"), endpoint=os.getenv("SPEECH_ENDPOINT"))
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
    speech_recognizer.canceled.connect(lambda evt: logger.info("CANCELLED {}".format(evt)))
    # Stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(0.5)

    speech_recognizer.stop_continuous_recognition()   
    result =  " ".join(final_transcription)
    logger.info("Transcription generated")

    return result

def speech_transcription_with_diarization(filename: str, language: str="en-GB"):

    speech_config = speechsdk.SpeechConfig(subscription=os.getenv('SPEECH_KEY'), endpoint=os.getenv("SPEECH_ENDPOINT"))
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
        logger.info('Cancelled event')

    final_transcription = []

    def conversation_transcriber_transcribed_cb(evt: speechsdk.SpeechRecognitionEventArgs):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            final_transcription.append(f"{evt.result.speaker_id.replace('Guest', 'Speaker')}: {evt.result.text}")
        elif evt.result.reason == speechsdk.ResultReason.NoMatch:
            logger.warning('\tNOMATCH: Speech could not be TRANSCRIBED: {}'.format(evt.result.no_match_details))
            return ""

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