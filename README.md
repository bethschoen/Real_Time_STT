# (Almost) Real-Time Speech-to-Text Transcription
This app is for transcribing audio via Azure Speech Services. The app allows you to either upload audio files or record audio using your device's microphone. 

![diagram plot](images/Screenshot%202025-06-16.png)

##  Limitations
This demo lets users record or upload audio and see a transcript almost immediately. When a user records audio, JavaScript is used to access the microphone and create a recording, this is saved in memory to be sent as an uploaded file to Azure. Therefore, **transcriptions aren't live but are almost real-time**. 

The reason the live transcription via `speech_recognizer.recognize_once()` doesn't work in an app is because the user's browser has access to their mic, not the server. So when the user records audio, the program gets a recorded file, not a live stream. The server can only process uploaded data, not directly tap into the user's hardware.

To go beyond that into true live streaming — like transcribing continuously as someone speaks — would require a real-time setup using WebSockets or a frontend-to-Azure streaming pipeline, which is more of a full-stack or backend engineering task! 

In addition to this, **this program doesn't work on machines with Zscalar**. This is because Zscalar may be configured by an organisation to block media uploads, which are needed to access audio and transcribe them. 

## Requirements
 - An Azure Subscription with a deployed Azure Speech Services resource.
 - A .env file in the project directory with a key to the Azure resource.
 - FFMPEG executable saved locally for conversion of audio to .wav
 - A device with a microphone (although, I'd be surprised if you found one without)
 - The project is running on a machine without **Zscalar**. 

 ## Usage

 With the repo cloned, you can also run this app (not on a machine with Zscalar):

 1. Create a new environment: `conda create --name stt_venv`
 2. Activate your new environment: `conda activate stt_venv`
 3. Install pip: `conda install pip`
 4. In your python terminal (I'm using VS Code), navigate to your project directory
 5. Install the necessary packages: `pip install -r requirements.txt`
 6. Run the app: `python app.py`
 7. Navigate to your localhost to view the app

