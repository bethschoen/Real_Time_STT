import os

# directories
# Get absolute path to the project root (variables living in project root)
proj_dir = os.path.dirname(os.path.abspath(__file__))
# Define reusable absolute paths
audio_dir = os.path.join(proj_dir, "audio")
static_dir = os.path.join(proj_dir, "static")
scooter_pics_dir = os.path.join(static_dir, "cat_pics")
# for linux, use "ffmpeg", for windows, using "ffmpeg.exe"
ffmpeg = "ffmpeg.exe"
FFMPEG_PATH = os.path.join(proj_dir, ffmpeg)

# scooter pictures
scooter_pics = ["meow meow.png", "meow mew mew meow.png", "purr purr.png"]
# path relative to static folder. Make sure to use "/"
scooter_pics_dir = "cat_pics"

# azure speech service info
service_region = "uksouth"
endpoint = "https://uksouth.api.cognitive.microsoft.com"

# transcribe route
temp_upload_dir = os.path.join(audio_dir, "temp_upload")
temp_filename = "input.wav"
recorded_audio_dir = os.path.join(static_dir, "recorded_audio")
incoming_recording_filename = "incoming_recording.wav"
recording_file_name = "recording_{}.wav"
converted_filename = "converted.wav"

# save transcript route
transcriptions_data_path = "transcriptions.csv"

# summarise route
summarise_prompt = """
You are an assistant that specialises in summarising spoken conversations. A transcript of a conversation is provided below. Summarise what happened in a concise and informative paragraph or bullet points. Focus on the key topics discussed, any decisions made, and important context. Be objective, avoid filler, and don't include speaker names unless essential.
"""
model="o4-mini"

# email route
email_example = """\
Subject: Transcription dd/mm/yy hh:mm

Hi there, 

Thank you for using our Speech-to-Text services! See below your transcription:

Date and Time:
Filename:
Mode:
Language: 
Diarization: 
Transcript:
Summary:

Made with 💖 by Beth"""

email_subject = """\
Subject: Transcription """

email_header = """

Hi there, 

Thank you for using our Speech-to-Text services! See below your transcription:

"""

email_datetime = "Date and Time: "
email_filename = "Filename: "
email_mode = "Mode: "
email_language = "Language: "
email_diarization = "Diarization: "
email_transcript = "Transcript:\n"
email_summary = "\nSummary:\n"

email_close = """

Made with <3 by Beth"""