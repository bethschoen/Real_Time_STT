const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");

let transcripts = [];  // Store all transcripts this session
let transcriptMode = "";
let uploadFilename = "";
let editedTranscript = "";
let generatedSummary = "";

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

function resetSummary() {
    const summaryElem = document.getElementById("summary-result");
    if (summaryElem) {
        summaryElem.innerHTML = "";
        summaryElem.style.display = "none";
        generatedSummary = "";
    }
    document.getElementById("summary-description-title").style.display = "block";
    document.getElementById("summary-description").style.display = "block";    
    document.getElementById("summary-description").textContent = "Transcribe an audio file to summarise.";
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
        // reset summary for new audio
        resetSummary()
        // hide scooter
        document.getElementById("scooter").style.display = "none";
        // start spinner 
        document.getElementById("loading-spinner").style.display = "block";
        uploadFilename = "";
        const blob = new Blob(audioChunks, { type: "audio/webm" }); // original format from MediaRecorder
        const formData = new FormData();
        formData.append("audio", blob, "recording.webm"); // use webm extension
        // add language
        languageString = getLanguageSetting();
        formData.append("language_setting", languageString);
        // add diarization option
        diarizedSelected = getDiarizationSetting();
        formData.append("diarization", diarizedSelected); 
        // add mode
        transcriptMode = "Recording"
        formData.append("mode", transcriptMode); 

        fetch("/transcribe", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            // stop spinner
            document.getElementById("loading-spinner").style.display = "none";             
            // show transcript and summarise elements
            document.getElementById("transcript-ready").style.display = "block";
            document.getElementById("previous-transcripts").style.display = "block";
            document.getElementById("summary-description").textContent = "Press the 'Summarise' button below.";
            
            const transcript = data.transcript || "Transcription failed: " + data.error;
            document.querySelector("textarea[name='edited_transcript']").value = transcript;
            
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
    // reset summary for new audio
    resetSummary()
    // hide scooter
    document.getElementById("scooter").style.display = "none";
    // start spinner
    document.getElementById("loading-spinner").style.display = "block";
    // e.target is the thing that triggered the event (e.g. the button) or anything inside the butotn (e.g. an icon)
    const formData = new FormData(e.target);
    uploadFilename = formData.get("audio").name;

    // Check contents uploaded
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
    // add mode
    transcriptMode = "Upload";
    formData.append("mode", transcriptMode); 

    const response = await fetch("/transcribe", {
        method: "POST",
        body: formData
    });

    const data = await response.json();
    // now that we have a response, stop spinner
    document.getElementById("loading-spinner").style.display = "none";
    // show transcript and summarise elements
    document.getElementById("transcript-ready").style.display = "block";
    document.getElementById("previous-transcripts").style.display = "block";
    document.getElementById("summary-description").textContent = "Press the 'Summarise' button below.";
    const transcript = data.transcript || "Transcription failed: " + data.error;

    // ✅ Set value inside the textarea
    document.querySelector("textarea[name='edited_transcript']").value = transcript;

    addTranscriptToHistory(transcript, transcriptMode);
});

let clickedButton = null;
document.querySelectorAll("#transcript-edit button").forEach((btn) => {
    btn.addEventListener("click", function (e) {
        clickedButton = e.target;
    });
});

// listen for email address submission
document.getElementById("email-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const emailFormData = new FormData(e.target);
    emailFormData.append("transcript", editedTranscript);
    emailFormData.append("mode", transcriptMode);
    emailFormData.append("filename", uploadFilename);
    languageString = getLanguageSetting();
    emailFormData.append("language", languageString);
    diarizedSelected = getDiarizationSetting();
    emailFormData.append("diarization", diarizedSelected);
    emailFormData.append("summary", generatedSummary);

    // Check contents being emailed
    for (let [key, value] of emailFormData.entries()) {
        console.log(`${key}: ${value}`);
    }

    const response = await fetch("/send-email", {
    method: "POST",
    body: emailFormData
    });

    const data = await response.json();
    const emailResult = data.success || data.error;
    const resultStatus = document.getElementById("email-sent-msg");
    resultStatus.textContent = emailResult
    resultStatus.style.display = "block";

    let fadeOutTime = 0;
    if (response.ok) {
        // fade it out after 2 seconds
        fadeOutTime = 2000;
    } else {
        // longer time to fade out
        fadeOutTime = 10000;
    }
    setTimeout(() => {
        resultStatus.style.display = "none";
        document.getElementById("email-popup").style.display = "none";
        document.getElementById("main-content").style["backdrop-filter"] = "none";
    }, fadeOutTime);
})

// Handle transcription actions
document.getElementById("transcript-edit").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    editedTranscript = formData.get("edited_transcript");
    const action = clickedButton?.value;

    if (action === "save") {
        formData.append("mode", transcriptMode);
        formData.append("language", getLanguageSetting());
        formData.append("diarization", getDiarizationSetting());

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
        generatedSummary = data.summary
        const htmlSummary = data.html_summary || "Summarisation failed: " + data.error;
        // Set value inside the paragraph
        document.getElementById("summary-result").style.display = "block";
        document.getElementById("summary-result").innerHTML = htmlSummary;

    } else if (action === "email") {
        // change display of pop up to block
        document.getElementById("email-popup").style.display = "block";
        // blur main content TODO: this doesn't work
        //document.getElementById("main-content").style["backdrop-filter"] = "blur(5px)";
        // listener is defined above
    }
});

// Handle reset button
document.getElementById("reset-page").addEventListener("click", () => {
    // Clear the textarea
    const textarea = document.querySelector("textarea[name='edited_transcript']");
    if (textarea) {
        textarea.value = "";
    }

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
    resetSummary()

    // Hide save/success messages
    document.getElementById("save-status").style.display = "none";
    document.getElementById("save-error").style.display = "none";

    // Reset language dropdown if needed
    const languageSelect = document.getElementById("language-setting");
    if (languageSelect) languageSelect.selectedIndex = 0;

    // Reset diarization toggle if needed
    const diarizationToggle = document.getElementById("diarization");
    if (diarizationToggle) diarizationToggle.checked = false;

    // hide transcript results elements    
    document.getElementById("transcript-ready").style.display = "none";
    document.getElementById("previous-transcripts").style.display = "none";

    // bring scooter back
    document.getElementById("scooter").style.display = "block";

    // Reset any custom state variables
    transcriptMode = "";    
    uploadFilename = "";   
    editedTranscript = ""; 
    generatedSummary = "";
});