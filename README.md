# (Almost) Real-Time Speech-to-Text Transcription
This app is for transcribing audio via Azure Speech Services. The app allows you to either upload audio files or record audio using your device's microphone. 

![diagram plot](images/Screenshot%202025-06-16.png)

## Requirements
 - An Azure Subscription with a deployed Azure Speech Services resource.
 - A .env file in the project directory with a key to the Azure resource.
 - The project is running **locally**. Currently, when running in the cloud, the project may struggle to connect to your machine's microphone. And Zscalar may also block the upload. 

 ## Usage

 With the repo cloned, you can also run this app **locally**:

 1. Create a new environment: `conda create --name stt_venv`
 2. Activate your new environment: `conda activate stt_venv`
 3. Install pip: `conda install pip`
 4. In your python terminal (I'm using VS Code), navigate to your project directory
 5. Install the necessary packages: `pip install -r requirements.txt`
 6. Run the app: `python app.py`
 7. Navigate to your localhost to view the app

