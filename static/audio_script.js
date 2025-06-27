// ChatGPT made me this badge when we figured out why audio wasn't playing 
// (it was because I was calling audio.textContent = ... which removed all other attributes)
/*
  /\_/\    💻
 ( o.o )   🎉  You squashed a sneaky DOM bug!
  > ^ <    🐾  Your code purrs beautifully now.
*/

// function for deleting one recording 
// 1. functions making flask calls must be async
async function deleteRecording(fileToDelete) {
    const formData = new FormData();
    formData.append("filename", fileToDelete);

    try {
        // 2. js won't wait for the flask call to finish. Instead, it returns a "promise"
        const response = await fetch("/delete-recording", {
            method: "POST",
            body: formData
        });

        // 3. therefore, we need to wait for the promise to "resolve" before checking the output
        // 4. if we didn't want to use async, we could use .then(do something)
        const data = await response.json();
        if (response.ok) {
            const result = data.success;
            console.log(result);
            return true;
        } else {
            const result = "Something went wrong: " + data.error;
            console.log(result);
            return false;
        }

    } catch (err) {
        console.error("Failed to delete:", err);
        return false;
    }
};

// this will run when the HTML has been parsed by the browser - now safe to edit the DOM
document.addEventListener("DOMContentLoaded", () => {

    const recordingTable = document.getElementById("recording-list");
    // check table and recordings exist
    if (!recordingTable || recordingsSaved === -1) {
        console.log(recordingsSaved);
        document.getElementById("empty-table").style.display = "block";
        recordingTable.style.display = "none";
    } else {
        // populate table
        //for (const [key, item] of Object.entries(recordingTable)) {
        recordingsList.forEach(item => {
            const tr = document.createElement("tr");
            // # file name # //
            const tdFile = document.createElement("td");
            tdFile.textContent = item;
            tr.appendChild(tdFile);
            const audioLocation = `/static/recorded_audio/${item}`;
            console.log(audioLocation)
            // # playback # //
            const tdAudio = document.createElement("td");
            const audio = document.createElement("audio");
            audio.preload = "metadata";
            audio.controls = true;
            const source = document.createElement("source");
            source.src = audioLocation;
            source.type = "audio/wav";
            audio.appendChild(source);
            tdAudio.appendChild(audio);
            tr.appendChild(tdAudio);
            // # download link # //
            const tdDownload = document.createElement("td");
            const link = document.createElement("a");
            // location of file locally
            link.href = audioLocation;
            link.download = item;
            // icon - uses Google available ones
            link.innerHTML = `<span class="material-icons">file_download</span>`;
            link.classList.add("download-link");
            // setAttribute syntax lets you set anything (don't have to remember JS specifics)
            link.setAttribute("aria-label", `Download ${item}`);
            tdDownload.appendChild(link);
            tr.appendChild(tdDownload);
            // # delete button # //
            const tdDelete = document.createElement("td");
            const button = document.createElement("button");
            // icon
            button.innerHTML = `<span class="material-icons">delete</span>`;
            // js will look out for all delete-buttons
            button.classList.add("delete-button");
            // custom attribute. In html: <button data-user-id=42</button> (hyphen-case)
            // Then to access in js: button.dataset.userID (camelCase)
            //button.dataset.id = key;
            button.dataset.filename = item;
            button.type = "button";
            button.setAttribute("aria-label", `Delete ${item}`);
            // need to add event listener here - if we try add outside, that would be too early (apparently)
            button.addEventListener("click", (e) => {
                // currentTarget lets us get the data associated with the button pressed
                const fileToDelete = e.currentTarget.dataset.filename;
                console.log("DELETE:", fileToDelete);
                // we need .then to wait for the response for the function rather than processing the promise
                // the alternative is that the event listener is async and we await the response from the function
                deleteRecording(fileToDelete).then(result => {
                    if (result) {
                        button.closest("tr").remove();
                    } else {
                        document.getElementById("delete-error").style.display = "block";
                    }
                });
            });
            tdDelete.appendChild(button);
            tr.appendChild(tdDelete);
            // # add all to table # //
            recordingTable.appendChild(tr);
        });
    }
});

// Handle deleting all files
document.getElementById("delete-recordings").addEventListener("click", async (e) => {
    e.preventDefault();
    let hasFailed = false
    recordingsList.forEach(item => {
        deleteRecording(item).then(result => {
            if (!result) {
                hasFailed = true;
                document.getElementById("delete-error").style.display = "block";
            }
        });
    });
    if (!hasFailed) {
        const recordingTable = document.getElementById("recording-list");
        recordingTable.remove()
        recordingTable.style.display = "none";
        document.getElementById("empty-table").style.display = "block";
    }
});
// event listener for reset button
// show pop up saying are you sure you want to delete all
// listen for "yes I'm sure"
// use delete function for all