const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");

let transcripts = [];  // Store all transcripts this session
let transcriptMode = "";

function addTranscriptToHistory(text, inputType) {
  const transcriptHistory = document.getElementById("transcript-history");
  console.log("Adding to history:", { text, inputType });

  const timestamp = new Date();
  const transcriptObj = { text, inputType, timestamp };
  transcripts.unshift(transcriptObj);

  transcriptHistory.innerHTML = "";
  transcripts.forEach(({ text, inputType, timestamp }) => {
    const li = document.createElement("li");
    const formattedTime = timestamp.toLocaleString();
    li.textContent = `[${formattedTime}, ${inputType}]: ${text}`;
    transcriptHistory.appendChild(li);
  });
}

function getLanguageSetting() {
    const selectedLanguage = document.getElementById("language-setting");
    const languageString = selectedLanguage.value;

    return languageString
}

function getDiarizationSetting() {
    const diarization = document.getElementById("diarization");
    const diarizedSelected = diarization.checked;

    return diarizedSelected
}

let mediaRecorder;
let audioChunks = [];

recordBtn.addEventListener("click", async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = event => {
    audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
        // start spinner 
        document.getElementById("loading-spinner").style.display = "block";
        const blob = new Blob(audioChunks, { type: "audio/webm" }); // original format from MediaRecorder
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm"); // use webm extension
        // add language
        languageString = getLanguageSetting();
        formData.append("language_setting", languageString);
        // add diarization option
        diarizedSelected = getDiarizationSetting();
        formData.append("diarization", diarizedSelected);

        fetch("/transcribe", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            // stop spinner
            document.getElementById("loading-spinner").style.display = "none";            
            document.getElementById("summary-description").textContent = "Press the 'Summarise' button below.";
            const transcript = data.transcript || "Transcription failed: " + data.error;
            document.querySelector("textarea[name='edited_transcript']").value = transcript;
            transcriptMode = "Recording"
            //document.getElementById("transcript-mode").textContent = transcriptMode;
            addTranscriptToHistory(transcript, transcriptMode); 
        });

        recordBtn.classList.remove("recording");

    };

    mediaRecorder.start();
    recordBtn.disabled = true;
    stopBtn.disabled = false;
    recordBtn.classList.add("recording"); // ← Add recording state

});

stopBtn.addEventListener("click", () => {
    mediaRecorder.stop();
    recordBtn.disabled = false;
    stopBtn.disabled = true;
});

// Handle uploaded file form
document.getElementById("upload-form").addEventListener("submit", async (e) => {
    // stop the program from simply sending the request to the API, edit the request first
    e.preventDefault();
    // start spinner
    document.getElementById("loading-spinner").style.display = "block";
    const formData = new FormData(e.target);

    // Optional: log for debugging
    for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
            console.log(`${key}: ${value.name}, ${value.size} bytes, ${value.type}`);
        } else {
            console.log(`${key}: ${value}`);
        }
    }
    // add language
    languageString = getLanguageSetting();
    formData.append("language_setting", languageString);
    // add diarization option
    diarizedSelected = getDiarizationSetting();
    formData.append("diarization", diarizedSelected); 

    const response = await fetch("/transcribe", {
        method: "POST",
        body: formData
    });

    const data = await response.json();
    // now that we have a response, stop spinner
    document.getElementById("loading-spinner").style.display = "none";
    document.getElementById("summary-description").textContent = "Press the 'Summarise' button below.";
    const transcript = data.transcript || "Transcription failed: " + data.error;

    // ✅ Set value inside the textarea
    document.querySelector("textarea[name='edited_transcript']").value = transcript;

    // ✅ Display current mode and update history
    transcriptMode = "Upload";
    //document.getElementById("transcript-mode").textContent = transcriptMode;
    addTranscriptToHistory(transcript, transcriptMode);
});

let clickedButton = null;
document.querySelectorAll("#transcript-edit button").forEach((btn) => {
    btn.addEventListener("click", function (e) {
        clickedButton = e.target;
    });
});

// Handle form for editing transcription
document.getElementById("transcript-edit").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const action = clickedButton?.value;

    if (action === "save") {
        formData.append("mode", transcriptMode);
        formData.append("language", document.getElementById("language-setting").value);
        formData.append("diarization", document.getElementById("diarization").checked);

        const response = await fetch("/save-transcript", {
        method: "POST",
        body: formData
        });

        const data = await response.json();
        if (response.ok) {
            // make sure there's no error message
            document.getElementById("save-error").style.display = "none"
            // Show the "Saved!" message
            const saveStatus = document.getElementById("save-status");
            saveStatus.style.display = "block";

            // fade it out after 2 seconds
            setTimeout(() => {
                saveStatus.style.display = "none";
            }, 2000);

            // reset TODO: create a reset button
            //document.getElementById("transcript-edit").reset()
            //transcriptMode = ""
        } else {
            // Show the save error message
            document.getElementById("save-error").textContent = data.error || "Something went wrong."
            const saveStatus = document.getElementById("save-error");
            saveStatus.style.display = "block";
        }
    } else if (action === "summarise") {
        document.getElementById("summary-description-title").style.display = "none";
        document.getElementById("summary-description").style.display = "none";
        // start spinner
        document.getElementById("loading-spinner-summarise").style.display = "block";

        const response = await fetch("/summarise", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        // now that we have a response, stop spinner
        document.getElementById("loading-spinner-summarise").style.display = "none";
        const summary = data.summary || "Summarisation failed: " + data.error;
        // Set value inside the paragraph
        document.getElementById("summary-result").style.display = "block";
        document.getElementById("summary-result").innerHTML = summary;
    }
});

// Handle reset button
document.getElementById("reset-page").addEventListener("click", () => {
    // Clear the textarea
    const textarea = document.querySelector("textarea[name='edited_transcript']");
    if (textarea) textarea.value = "";

    // Clear transcript history
    transcripts = []; 
    const transcriptHistory = document.getElementById("transcript-history");
    if (transcriptHistory) transcriptHistory.innerHTML = "";

    // Clear uploaded file input (if you have one)
    const fileInput = document.querySelector("#upload-form input[type='file']");
    if (fileInput) {
        fileInput.value = "";
    }

    // Hide spinner
    document.getElementById("loading-spinner-summarise").style.display = "none";

    // Clear summary
    const summaryElem = document.getElementById("summary-result");
    if (summaryElem) {
        summaryElem.innerHTML = "";
        summaryElem.style.display = "none";
    }
    document.getElementById("summary-description-title").style.display = "block";
    document.getElementById("summary-description").style.display = "block";    
    document.getElementById("summary-description").textContent = "Transcribe an audio file to summarise.";
    

    // Hide save/success messages
    document.getElementById("save-status").style.display = "none";
    document.getElementById("save-error").style.display = "none";

    // Reset language dropdown if needed
    const languageSelect = document.getElementById("language-setting");
    if (languageSelect) languageSelect.selectedIndex = 0;

    // Reset diarization toggle if needed
    const diarizationToggle = document.getElementById("diarization");
    if (diarizationToggle) diarizationToggle.checked = false;

    // Reset any custom state variables
    transcriptMode = "";
});