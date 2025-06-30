from flask import Flask, url_for, render_template, request, jsonify, session
import random
import os
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
import pandas as pd
from time import gmtime, strftime
import time
import smtplib
import ssl
import uuid

import variables as vr
from app import logger
import utils as ut

def handle_error(msg: str, e: Exception=None):
    if e:
        error = msg + ": " + str(e)
    else:
        error = msg
    logger.error(error)
    return jsonify({"error": error}), 400

app = Flask(__name__)
app.secret_key = "BAD_SECRET_KEY"

def select_scooter_pic():
    selected_pic = random.choice(vr.scooter_pics)
    pic_path = f"{vr.scooter_pics_dir}/{selected_pic}"

    return pic_path

@app.route("/")
def index():
    # store user id if it hasn't already been created
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    logger.info("Main page loaded")
    scooter_pic = select_scooter_pic()
    image_url = url_for('static', filename=scooter_pic)
    return render_template("index.html", cat_image=image_url)

@app.route("/transcribe", methods=["POST"])
def transcribe():
    logger.info("Starting transcription.")
    # access uploaded audio and save locally
    file = request.files["audio"]
    mode = request.form.get("mode")

    if mode == "Recording":
        # save in recording directory
        n_existing_files = len(os.listdir(vr.recorded_audio_dir))
        filename = vr.incoming_recording_filename
        base_path = vr.recorded_audio_dir
        converted_filename = vr.recording_file_name.format(n_existing_files + 1)
    elif mode == "Upload":
        # save in temp directory  
        filename = vr.temp_filename
        base_path = vr.temp_upload_dir
        converted_filename = vr.converted_filename
    else:
        return jsonify({"error":f"mode '{mode}' not recognised."}), 400    
    
    # save locally
    input_path = os.path.join(base_path, filename)
    file.save(input_path)
    logger.info("Audio stored locally")  

    # Check if conversion is needed
    original_filename = file.filename.lower()      
    needs_conversion = not original_filename.endswith(".wav")
    if needs_conversion: 
        logger.info(f"Uploaded file ({input_path}) is not WAV. Converting...")       
        conversion_path = os.path.join(base_path, converted_filename)
        msg, e = ut.convert_audio_to_wav(input_path, conversion_path)
        if e:
            return handle_error(msg, e)
        logger.info("Audio successfully converted to wav.")
        audio_path = conversion_path
        logger.info(audio_path)
    else:
        audio_path = input_path
        logger.info("Uploaded file is already a WAV file. No conversion needed.")

    # Transcribe with Azure
    language = request.form.get("language_setting")
    diarization = request.form.get("diarization") == 'true'
    logger.info(f"Diarization mode: {diarization}")
    # recognized_speech = single_shot_transcription(audio_path, language)
    if diarization:
        before = time.time()
        recognized_speech = ut.speech_transcription_with_diarization(audio_path, language)
        after = time.time()
    else:
        before = time.time()
        recognized_speech = ut.speech_transcription_continuous(audio_path, language)
        after = time.time()
    logger.info(f"Audio transcribed, Time elapsed: {after-before}s")
    
    # If upload, remove audio locally
    if mode == "Upload":
        os.remove(audio_path)
    # If a file was converted, remove the original
    if needs_conversion:
        os.remove(input_path)
        logger.info("Audio removed locally")

    if len(recognized_speech) < 5:
        logger.warning(f"Transcribed text is too small.")
        return jsonify({"error": "No information returned from Azure Speech Services. Something went wrong..."}), 400

    return jsonify({"transcript": recognized_speech}), 200

@app.route("/summarise", methods=["POST"])
def summarise():

    transcript = request.form.get("edited_transcript")
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
    summary, e = ut.generate_text(vr.model, messages)
    if e:
        return handle_error(summary, e)
    
    processed_summary = ut.process_summary(summary)
    return jsonify({"html_summary": processed_summary, "summary": summary}), 200

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

        logger.info("Transcription saved to CSV")
        return jsonify({"msg": "Successful!"}), 200
    
    except Exception as e:
        return handle_error("Something went wrong when saving transcription", e)

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
        return handle_error("Something wrong with the provided email information", e)
      
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
        return handle_error("Couldn't send email", e)
    
@app.route("/list-audio")
def list_audio():
    # add id to know which row to delete
    # recordings = {i:recording for i, recording in enumerate(os.listdir(vr.recorded_audio_dir))}
    recordings = os.listdir(vr.recorded_audio_dir)
    n_recordings = len(recordings)
    if n_recordings == 0:
        logger.info("No recordings saved locally to display.")
        n_recordings = -1
    return render_template("audio_page.html", recordings=recordings, n_recordings=n_recordings)

@app.route("/delete-recording", methods=["POST"])
def delete_recording():
    filename = request.form.get("filename")

    try:
        file_path = os.path.join(vr.recorded_audio_dir, filename)
        os.remove(file_path)
        logger.info(f"File '{filename}' deleted successfully!")
        return jsonify({"success": "Success!"}), 200
    except Exception as e:
        return handle_error("Couldn't delete file", e)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)