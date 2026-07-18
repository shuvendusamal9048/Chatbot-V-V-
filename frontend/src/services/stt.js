import axios from "axios";

import { API_BASE_URL } from "../config";

let mediaRecorder = null;
let audioChunks = [];
let onTextCallback = null;
let mediaStream = null;

/**
 * Start recording from the microphone.
 * When stopSpeech() is called, the audio is sent to the
 * backend /stt endpoint which uses Sarvam AI to transcribe it.
 * The resulting transcript is passed to onText().
 */
export async function startSpeech(onText) {
  try {
    onTextCallback = onText;
    audioChunks = [];

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const options = MediaRecorder.isTypeSupported("audio/webm")
      ? { mimeType: "audio/webm" }
      : {};

    mediaRecorder = new MediaRecorder(mediaStream, options);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const mimeType = mediaRecorder.mimeType || "audio/webm";
      const audioBlob = new Blob(audioChunks, { type: mimeType });

      console.log(
        "[STT] Sending audio blob:",
        audioBlob.size,
        "bytes,",
        mimeType
      );

      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");

      try {
        const res = await axios.post(
          `${API_BASE_URL}/stt`,
          formData,
          {
            headers: { "Content-Type": "multipart/form-data" },
          }
        );

        const transcript = res.data.transcript || "";
        console.log("[STT] Transcript:", transcript);

        if (onTextCallback && transcript) {
          onTextCallback(transcript);
        } else if (!transcript) {
          console.warn("[STT] Empty transcript received");
        }
      } catch (err) {
        console.error("[STT] Request failed:", err);
        alert("Voice transcription failed. Please try again.");
      } finally {
        if (mediaStream) {
          mediaStream.getTracks().forEach((track) => track.stop());
          mediaStream = null;
        }
      }
    };

    mediaRecorder.start();
    console.log("[STT] MediaRecorder started");
  } catch (err) {
    console.error("[STT] Failed to start recording:", err);
    alert("Microphone access denied or unavailable.");
  }
}

/**
 * Stop the recording — this triggers the onstop handler
 * which sends the audio to the backend and calls onText().
 */
export function stopSpeech() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
    console.log("[STT] MediaRecorder stopped");
  }
}