# (Almost) Real-Time Speech-to-Text Transcription
This app is for transcribing audio via Azure Speech Services. The app allows you to either upload audio files or record audio using the device's microphone. 

<img src="images/250627%20App%20Demo.gif" alt="drawing" width="1000"/>

1. Language and diarization options can be set in the left-hand sidebar.

2. The user can choose to upload an audio file or record a new file. Once an audio file has been provided (via either method), the app presents a spinner to show the file is bring processed.

3. The completed transcript appears in a text area allowing users to edit the text in case the model has made any mistakes.

4. Users can ask the app to summarise the contents of the audio. The result will appear to the right of the transcript.

5. The transcription can be saved. Currently, the program has been setup to save this to a CSV in the project directory. Ideally, this would be a some type of tabular storage for further use.

6. The session can be emailed to the user. Clicking the email button, a pop-up will appear requesting a email address. The user will then receive the transcription, summary, and settings: 

<img src="images/Screenshot%202025-06-27%20Email.png" alt="drawing" width="1000"/>

7. If the user has made any recordings, they are listed at `/list-audio`. The user can choose to download or delete files. Currently, the files are saved in the project directory. Ideally, this would be listing cloud storage and more meta-data would be provided e.g. date and time of recording. 

<img src="images/Screenshot%202025-06-27%20Listed%20recordings.png" alt="drawing" width="1000"/>

Some error handling has been considered during development: the API handles errors received from Azure Speech Services; nothing will be saved if the text area is empty; if anything goes wrong while saving a transcription, the error message appears at the bottom.

<img src="images/Screenshot%202025-06-18%20error%20handling.png" alt="drawing" width="1000"/>

## Project Files

To achieve this, we have the following file structure:

```
real-time-stt
|
├── logs
|   └── logger_config.py
|
├── templates
|   ├── index.html
|   └── audio_page.html
|
├── static
|   ├── recorded_audio
|   |   └── (recorded audio as wav files)
|   |
|   ├── style.css
|   ├── script.js
|   └── audio_script.js
|
├── utils
|   ├── audio_transcription.py
|   └── summary_generation.py
|
├── app.py
└── variables.py
```

Each file serves a different purpose:

- **app.py**: Flask API connecting app to Azure Speech Services (backend)
- **variables.py**: Important variables used by several files/functions stored here for easier editing
- **utils**: Python functions used by the Flask routes
- **script.js**: functionality of frontend (main page), connecting actions to the backend
- **index.html**: layout of frontend (main page)
- **style.css**: design of frontend
- **audio_script.js** and **audio_page.html**: layout and functionality of the second page
- **logger_config.py**: project logger used by backend nodes

##  Limitations
This demo lets users record or upload audio and see a transcript almost immediately. When a user records audio, JavaScript is used to access the microphone and create a recording, this is saved in memory to be sent as an uploaded file to Azure. Therefore, **transcriptions aren't live but are almost real-time**.

The reason the live transcription via `speech_recognizer.recognize_once()` doesn't work in an app is because the user's browser has access to their mic, not the server. So when the user records audio, the program gets a recorded file, not a live stream. The server can only process uploaded data, not directly tap into the user's hardware.

To go beyond that into true live streaming — like transcribing continuously as someone speaks — would require a real-time setup using WebSockets or a frontend-to-Azure streaming pipeline, which is more of a full-stack or backend engineering task!

In addition to this, **this program doesn't work reliably on machines with Zscalar**. This is because Zscalar may be configured by an organisation to block media uploads, which are needed to access audio and transcribe them. We've found this code has worked locally (when running `python app.py`) but not necessarily when deployed.

## Requirements
 - An Azure Subscription
 - A deployed Azure Speech Services resource.
 - A deployed Azure OpenAI resource.
 - A .env file in the project directory with a key to the Azure resources.
 - FFMPEG executable saved locally for conversion of audio to .wav
 - A device with a microphone (although, I'd be surprised if you found one without)
 - (Ideally) The project is running on a machine without **Zscalar**.

 ## Usage (Locally)

 With the repo cloned, you can also run this app:

 1. Create a new environment: `conda create --name stt_venv`
 2. Activate your new environment: `conda activate stt_venv`
 3. Install pip: `conda install pip`
 4. Check the `load_dotenv` is being called in `app.py`
 5. In your python terminal (I'm using VS Code), navigate to your project directory
 6. Install the necessary packages: `pip install -r requirements.txt`
 7. Run the app: `python app.py`
 8. Navigate to your localhost to view the app

 ## Deployment

The app has been containerised and deployed in Azure. 

Here are the steps taken to containerise and deploy the app:

 1. Check if there are problematic python packages in `requirements.txt` (numpy and pywin - you'll see them commented out in my requirements file)
 2. Check load_dotenv is **not** being called in `app.py` - this isn't needed when deployed
 3. Check you are calling the correct type of FFMPEG in variables.py (this should be something compatiable with your type of container - Windows, Linux, etc.)
 4. Create an image: `docker build --tag rts-app .`
 5. Run the container: `docker run -d -p 5000:5000 rts-app`
 6. List all containers and copy the ID of your new, running container: `docker ps -a`
 7. Get the logs for the container to start the app: `docker logs <container_id>`
 8. Navigate to localhost and check the app is running as expected
 9. Stop the container: `docker kill <container_id>`
 10. Remove your container : `docker rm <container_id>`
 11. Deploy the image to Azure Container Apps: `az containerapp up --resource-group <resource_group> --name rts-app --location uksouth --ingress external --target-port 5000 --source .`
 12. With the app started and running, you can view the logs by running `az containerapp logs show --name rts-app --resource-group <resource_group>`