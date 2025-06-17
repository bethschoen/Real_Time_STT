const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");
const transcriptDisplay = document.getElementById("transcript");
const transcriptHistory = document.getElementById("transcript-history");

const transcripts = [];  // Store all transcripts this session

function addTranscriptToHistory(text, inputType) {
  const timestamp = new Date();
  const transcriptObj = { text, inputType, timestamp };
  transcripts.unshift(transcriptObj); // add to start of array (newest first)

  // Clear and rebuild list
  transcriptHistory.innerHTML = ""; 
  transcripts.forEach(({ text, inputType, timestamp }) => {
    const li = document.createElement("li");
    const formattedTime = timestamp.toLocaleString(); // format for display
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
    const blob = new Blob(audioChunks, { type: "audio/webm" }); // original format from MediaRecorder
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm"); // use webm extension

    fetch("/transcribe", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        const transcript = data.transcript || "Transcription failed: " + data.error;
        transcriptDisplay.textContent = transcript;
        addTranscriptToHistory(transcript, "Recording"); // <-- Add this line
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
    e.preventDefault();
    const formData = new FormData(e.target);

    // Log the contents of the FormData object
    for (let [key, value] of formData.entries()) {
    if (value instanceof File) {
        console.log(`${key}: ${value.name}, ${value.size} bytes, ${value.type}`);
    } else {
        console.log(`${key}: ${value}`);
    }
    }

    const response = await fetch("/transcribe", {
    method: "POST",
    body: formData
    });

    const data = await response.json();
    const transcript = data.transcript || "Transcription failed: " + data.error;
    transcriptDisplay.textContent = transcript;
    addTranscriptToHistory(transcript, "Upload");
    });