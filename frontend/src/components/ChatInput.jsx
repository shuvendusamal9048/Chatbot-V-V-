import { Send } from "lucide-react";
import { BsFillMicFill } from "react-icons/bs";
import { useState, useEffect } from "react";

import {
  startSpeech,
  stopSpeech
} from "../services/stt";

function ChatInput({
  wsRef,
  sendPayload,
  setMessages,
  setChatHistory,
  stopAllAudio,
  setIsStreaming,
  connectionStatus
}) {

  const [question, setQuestion] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  useEffect(() => {
    const handlePartial = (e) => {
      setQuestion(e.detail);
    };
    window.addEventListener("stt-partial", handlePartial);
    return () => window.removeEventListener("stt-partial", handlePartial);
  }, []);


  /////////////////////////////////////////////////////
  // Normal Send
  /////////////////////////////////////////////////////
  const send = () => {

    if (!question.trim()) return;

    console.log("[ChatInput] send() connectionStatus=", connectionStatus, "text=", question);

    // Stop any playing TTS before sending new message
    stopAllAudio?.();
    setIsStreaming?.(true);

    setMessages(prev => [
      ...prev,
      { role: "user", text: question },
      { role: "assistant", text: "", sources: [] }
    ]);

    setChatHistory(prev => [question, ...prev]);

    const payload = JSON.stringify({ type: "text", text: question });
    const sent = sendPayload(payload);
    if (!sent) {
      console.error("[ChatInput] Failed to send question payload");
    }

    setQuestion("");
  };


  /////////////////////////////////////////////////////
  // Voice Send (called after STT returns transcript)
  /////////////////////////////////////////////////////
  const sendVoice = (text) => {

    if (!text || !text.trim()) return;

    console.log("[ChatInput] sendVoice() connectionStatus=", connectionStatus, "text=", text);

    // Stop any playing TTS before sending new message
    stopAllAudio?.();
    setIsStreaming?.(true);

    setMessages(prev => [
      ...prev,
      { role: "user", text: text },
      { role: "assistant", text: "", sources: [] }
    ]);

    setChatHistory(prev => [text, ...prev]);

    const payload = JSON.stringify({ type: "text", text });
    const sent = sendPayload(payload);
    if (!sent) {
      console.error("[ChatInput] Failed to send voice payload");
    }

    setQuestion("");
  };


  /////////////////////////////////////////////////////
  // Mic Toggle
  /////////////////////////////////////////////////////
  const handleMic = () => {
    if (isRecording) {
      stopSpeech();
      setIsRecording(false);
      wsRef.current?.send(JSON.stringify({ type: "speech_end" }));
      return;
    }

    stopAllAudio?.();
    setIsRecording(true);

    startSpeech(
      wsRef.current,
      null,
      () => {
        console.log("[ChatInput] VAD silence detected, ending speech...");
        setIsRecording(false);
        wsRef.current?.send(JSON.stringify({ type: "speech_end" }));
      }
    );
  };


  return (

    <div
      className="
      p-6
      bg-white/70
      backdrop-blur-xl
      border-t
      "
    >

      <div
        className="
        max-w-5xl
        mx-auto
        "
      >

        <div
          className="
          bg-white/90
          backdrop-blur-xl
          rounded-[35px]
          border
          shadow-xl
          px-5
          py-3
          flex
          items-center
          gap-3
          "
        >

          <input
            value={question}
            onChange={(e) =>
              setQuestion(e.target.value)
            }
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                send();
              }
            }}
            placeholder="Ask anything about your documents..."
            className="
            flex-1
            bg-transparent
            outline-none
            text-lg
            px-3
            py-2
            "
          />

          {/* MIC BUTTON */}

          <button
            onClick={handleMic}
            title={isRecording ? "Stop recording" : "Start voice input"}
            className={`
            w-12
            h-12
            rounded-full
            flex
            items-center
            justify-center
            transition-all
            duration-300
            shadow-md
            ${isRecording
                ? "bg-red-500 text-white animate-pulse scale-110"
                : "bg-slate-100 text-slate-600 hover:bg-blue-100 hover:text-blue-600"
              }
            `}
          >
            <BsFillMicFill size={20} />
          </button>


          {/* SEND BUTTON */}

          <button
            onClick={send}
            title="Send message"
            className="
            w-12
            h-12
            rounded-full
            flex
            items-center
            justify-center
            bg-gradient-to-r
            from-blue-600
            to-indigo-600
            text-white
            shadow-md
            hover:scale-110
            transition-all
            duration-300
            "
          >
            <Send size={20} />
          </button>

        </div>

        {isRecording && (
          <div
            className="
            text-center
            mt-3
            text-red-500
            animate-pulse
            font-medium
            "
          >
            Listening via Sarvam AI...
          </div>
        )}

      </div>

    </div>

  );
}

export default ChatInput;