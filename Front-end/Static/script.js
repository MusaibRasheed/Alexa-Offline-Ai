const orb = document.getElementById('orb');
const responseDisplay = document.querySelector('#response-display p');
const textInput = document.getElementById('text-input');
const micBtn = document.getElementById('mic-btn');

let isListening = false;
let recognition;

// Initialize Speech Recognition
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isListening = true;
        orb.classList.add('listening');
        micBtn.classList.add('active');
        responseDisplay.textContent = "Listening...";
        responseDisplay.classList.remove('placeholder-text');
    };

    recognition.onend = () => {
        isListening = false;
        orb.classList.remove('listening');
        micBtn.classList.remove('active');
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        textInput.value = transcript;
        sendCommand(transcript);
    };
} else {
    micBtn.style.display = 'none';
    console.log("Speech recognition not supported");
}

micBtn.addEventListener('click', () => {
    if (!recognition) return;
    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
});

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendCommand(textInput.value);
    }
});

async function sendCommand(command) {
    if (!command.trim()) return;

    responseDisplay.textContent = "Processing...";
    orb.classList.remove('listening');

    try {
        const res = await fetch('/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command })
        });

        const data = await res.json();
        const reply = data.response;

        // Update UI
        responseDisplay.textContent = reply;
        textInput.value = '';

        // Speak response
        speak(reply);

    } catch (error) {
        responseDisplay.textContent = "Error connecting to server.";
        console.error(error);
    }
}

function speak(text) {
    if (!text) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // Try to set a nice voice
    const voices = window.speechSynthesis.getVoices();
    // Prefer Google US English or Microsoft Zira (common female voices)
    const preferredVoice = voices.find(v => v.name.includes('Google US English') || v.name.includes('Zira'));
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => orb.classList.add('speaking');
    utterance.onend = () => orb.classList.remove('speaking');

    window.speechSynthesis.speak(utterance);
}

// Preload voices to ensure they are available
window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
};
