let audioContext = null;
let scriptProcessor = null;
let mediaStreamSource = null;
let micStream = null;

/**
 * Start streaming PCM audio from the microphone.
 * Sends raw 16kHz 16-bit signed PCM binary chunks over the socket.
 * Monitors volume (RMS) to perform client-side Voice Activity Detection (VAD).
 */
export async function startSpeech(socket, onTranscript, onSpeechEnd) {
  try {
    stopSpeech(); // Clean up any active streams first

    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Create AudioContext forced at 16000Hz (downsampled natively by the browser)
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioContextClass({ sampleRate: 16000 });

    mediaStreamSource = audioContext.createMediaStreamSource(micStream);

    // Use ScriptProcessorNode to capture chunks of 4096 samples
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

    // VAD State variables
    const SILENCE_THRESHOLD = 0.012; // Volume threshold for silence
    const SILENCE_DURATION_MS = 1500; // Silence duration to trigger end-of-speech
    let silenceStart = null;
    let speechDetected = false;

    scriptProcessor.onaudioprocess = (event) => {
      const samples = event.inputBuffer.getChannelData(0);

      // Calculate RMS (Volume)
      let sum = 0;
      for (let i = 0; i < samples.length; i++) {
        sum += samples[i] * samples[i];
      }
      const rms = Math.sqrt(sum / samples.length);

      // Check Voice Activity Detection (VAD)
      const now = Date.now();
      if (rms > SILENCE_THRESHOLD) {
        speechDetected = true;
        silenceStart = null; // reset silence timer
      } else {
        if (speechDetected) {
          if (silenceStart === null) {
            silenceStart = now;
          } else if (now - silenceStart > SILENCE_DURATION_MS) {
            console.log("[STT] Silence detected (VAD). Stopping speech...");
            stopSpeech();
            if (onSpeechEnd) onSpeechEnd();
            return;
          }
        }
      }

      // Convert float32 samples to 16-bit signed PCM (Little Endian)
      const buffer = new ArrayBuffer(samples.length * 2);
      const view = new DataView(buffer);
      let offset = 0;
      for (let i = 0; i < samples.length; i++, offset += 2) {
        let s = Math.max(-1, Math.min(1, samples[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      }

      // Send binary PCM frame over WebSocket to backend
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(buffer);
      }
    };

    mediaStreamSource.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);
    console.log("[STT] Mic PCM streaming started at 16kHz.");

  } catch (err) {
    console.error("[STT] Failed to start microphone streaming:", err);
    alert("Microphone access denied or unavailable.");
  }
}

/** Stop streaming mic input and close AudioContext. */
export function stopSpeech() {
  if (scriptProcessor) {
    scriptProcessor.onaudioprocess = null;
    try {
      scriptProcessor.disconnect();
    } catch (e) { }
    scriptProcessor = null;
  }

  if (mediaStreamSource) {
    try {
      mediaStreamSource.disconnect();
    } catch (e) { }
    mediaStreamSource = null;
  }

  if (audioContext) {
    try {
      audioContext.close();
    } catch (e) { }
    audioContext = null;
  }

  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop());
    micStream = null;
  }
  console.log("[STT] Mic PCM streaming stopped.");
}