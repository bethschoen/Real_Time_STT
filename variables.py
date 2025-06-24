# azure speech service info
service_region = "uksouth"
endpoint = "https://uksouth.api.cognitive.microsoft.com"

# transcribe route
input_path = "audio/input.wav"
converted_path = "audio/converted.wav"

# save transcript route
transcriptions_data_path = "transcriptions.csv"

# summarise route
summarise_prompt = """
You are an assistant that specialises in summarising spoken conversations. A transcript of a conversation is provided below. Summarise what happened in a concise and informative paragraph or bullet points. Focus on the key topics discussed, any decisions made, and important context. Be objective, avoid filler, and don't include speaker names unless essential.
"""

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

Made with 💖 by Beth"""