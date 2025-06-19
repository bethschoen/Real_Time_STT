const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");

const transcripts = [];  // Store all transcripts this session
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
        const selectedLanguage = document.getElementById("language-setting");
        const languageString = selectedLanguage.value;
        formData.append("language_setting", languageString);

        fetch("/transcribe", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            // stop spinner
            document.getElementById("loading-spinner").style.display = "none";
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
    const selectedLanguage = document.getElementById("language-setting");
    const languageString = selectedLanguage.value;
    formData.append("language_setting", languageString);

    const response = await fetch("/transcribe", {
        method: "POST",
        body: formData
    });

    const data = await response.json();
    // now that we have a response, stop spinner
    document.getElementById("loading-spinner").style.display = "none";
    const transcript = data.transcript || "Transcription failed: " + data.error;

    // ✅ Set value inside the textarea
    document.querySelector("textarea[name='edited_transcript']").value = transcript;

    // ✅ Display current mode and update history
    transcriptMode = "Upload";
    //document.getElementById("transcript-mode").textContent = transcriptMode;
    addTranscriptToHistory(transcript, transcriptMode);
});

// Handle form for editing transcription
document.getElementById("transcript-edit").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    formData.append("mode", transcriptMode);
    formData.append("language", document.getElementById("language-setting").value);

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

        // reset
        document.getElementById("transcript-edit").reset()
        transcriptMode = ""
    } else {
        // Show the save error message
        document.getElementById("save-error").textContent = data.error || "Something went wrong."
        const saveStatus = document.getElementById("save-error");
        saveStatus.style.display = "block";
    }
});