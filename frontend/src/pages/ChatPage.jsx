import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";

import {
  useEffect,
  useRef,
  useState
} from "react";

import { WS_BASE_URL } from "../config";

function ChatPage() {

  const [messages, setMessages] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);

  const ws = useRef(null);

  // ── Audio playback queue ──────────────────────────────
  const audioQueue     = useRef([]);
  const isPlaying      = useRef(false);
  const currentAudio   = useRef(null);

  /** Play next item in queue; auto-chains until empty. */
  const playNext = () => {
    if (audioQueue.current.length === 0) {
      isPlaying.current = false;
      return;
    }

    isPlaying.current = true;
    const b64 = audioQueue.current.shift();

    const audio = new Audio("data:audio/wav;base64," + b64);
    currentAudio.current = audio;

    audio.onended = playNext;
    audio.onerror = (e) => {
      console.error("[TTS] Audio error:", e);
      playNext();
    };

    audio.play().catch((err) => {
      console.error("[TTS] play() failed:", err);
      playNext();
    });
  };

  /** Enqueue a base64 audio chunk and start playing if idle. */
  const enqueueAudio = (b64) => {
    if (!b64) return;
    audioQueue.current.push(b64);
    if (!isPlaying.current) {
      playNext();
    }
  };

  /** Stop all audio immediately and clear the queue. */
  const stopAllAudio = () => {
    audioQueue.current = [];
    isPlaying.current  = false;
    if (currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current.src = "";
      currentAudio.current = null;
    }
  };

  // ── WebSocket ─────────────────────────────────────────
  useEffect(() => {

    console.log("Creating websocket...");

    const socket = new WebSocket(`${WS_BASE_URL}/chat`);
    ws.current = socket;

    socket.onopen = () => {
      console.log("WS Connected");
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("[WS msg]", data.type, data);

      if (data.type === "chunk") {

        setMessages(prev => {
          const arr = [...prev];
          if (arr.length === 0) return prev;
          arr[arr.length - 1].text += data.content;
          return [...arr];
        });

      } else if (data.type === "audio") {

        // ← This is where we play the Sarvam TTS audio
        console.log("[TTS] Received audio chunk, enqueueing...");
        enqueueAudio(data.audio);

      } else if (data.type === "sources") {

        setMessages(prev => {
          const arr = [...prev];
          arr[arr.length - 1].sources = data.sources;
          return [...arr];
        });

      } else if (data.type === "end") {
        // response complete
      }
    };

    socket.onerror = (e) => {
      console.error("WS ERROR", e);
    };

    socket.onclose = () => {
      console.log("WS CLOSED");
    };

    return () => {
      socket.close();
      stopAllAudio();
    };

  }, []);

  return (

    <div
      className="
      h-screen
      flex
      overflow-hidden
      bg-slate-100
      "
    >

      <Sidebar
        chatHistory={chatHistory}
      />

      <div
        className="
        flex-1
        flex
        flex-col
        "
      >

        <Header />

        <ChatWindow
          messages={messages}
        />

        <ChatInput
          ws={ws}
          setMessages={setMessages}
          setChatHistory={setChatHistory}
          stopAllAudio={stopAllAudio}
        />

      </div>

    </div>

  );
}

export default ChatPage;