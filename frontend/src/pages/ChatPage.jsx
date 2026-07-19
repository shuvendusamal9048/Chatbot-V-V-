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
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("connecting");

  const ws = useRef(null);
  const expectBinaryAudio = useRef(false);
  const reconnectTimer = useRef(null);
  const shouldReconnect = useRef(true);
  const pendingSends = useRef([]);

  const sendPayload = (payload) => {
    const socket = ws.current;
    const readyState = socket?.readyState;

    if (readyState === WebSocket.OPEN) {
      try {
        socket.send(payload);
        return true;
      } catch (err) {
        console.warn("[ChatPage] send failed, queueing payload", err);
        if (shouldReconnect.current) {
          pendingSends.current.push(payload);
          return true;
        }
        return false;
      }
    }

    if (shouldReconnect.current) {
      console.warn("[ChatPage] queueing payload until WS open", payload, "readyState=", readyState);
      pendingSends.current.push(payload);
      return true;
    }

    console.error("[ChatPage] cannot send payload, websocket not open", readyState);
    return false;
  };

  const blobToBase64 = (blob) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result?.toString().split(",")[1];
        if (base64) resolve(base64);
        else reject(new Error("Failed to convert blob to base64"));
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

  // ── Web Audio API Gapless Playback ─────────────────────
  const audioContextRef = useRef(null);
  const nextStartTimeRef = useRef(0);
  const activeSourcesRef = useRef([]);

  const getAudioContext = () => {
    if (!audioContextRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioContextClass();
    }
    if (audioContextRef.current.state === "suspended") {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  };

  const playBufferGapless = async (arrayBuffer) => {
    try {
      const ctx = getAudioContext();

      // Decode audio data asynchronously
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      // Create buffer source node
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      // Calculate continuous playback startTime
      const now = ctx.currentTime;
      let startTime = nextStartTimeRef.current;
      if (startTime < now) {
        startTime = now;
      }

      console.log("[TTS] Scheduling buffer playback. Duration:", audioBuffer.duration, "at:", startTime, "current:", now);
      source.start(startTime);

      activeSourcesRef.current.push(source);
      source.onended = () => {
        activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
      };

      // Update next startTime
      nextStartTimeRef.current = startTime + audioBuffer.duration;

    } catch (err) {
      console.error("[TTS] Failed to decode or play audio buffer:", err);
    }
  };

  /** Stop all playing audio buffers and reset scheduled times. */
  const stopAllAudio = () => {
    activeSourcesRef.current.forEach(source => {
      try {
        source.stop();
      } catch (e) { }
    });
    activeSourcesRef.current = [];
    nextStartTimeRef.current = 0;
    console.log("[TTS] All active audio sources stopped.");
  };

  // ── WebSocket ─────────────────────────────────────────
  useEffect(() => {
    const connect = () => {
      console.log("Creating websocket...");

      const socket = new WebSocket(`${WS_BASE_URL}/chat`);
      socket.binaryType = "arraybuffer";
      ws.current = socket;
      setConnectionStatus("connecting");

      socket.onopen = () => {
        console.log("WS Connected");
        setConnectionStatus("open");
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
        if (pendingSends.current.length > 0) {
          console.log("Flushing pending sends", pendingSends.current.length);
          pendingSends.current.forEach(payload => socket.send(payload));
          pendingSends.current = [];
        }
      };

      socket.onmessage = async (event) => {
        if (event.data instanceof ArrayBuffer) {
          console.log("[WS binary] Received audio chunk, length:", event.data.byteLength);
          playBufferGapless(event.data);
          return;
        }

        if (typeof event.data !== "string") {
          console.warn("[WS] Unsupported message type", typeof event.data);
          return;
        }

        let data;
        try {
          data = JSON.parse(event.data);
        } catch (error) {
          console.warn("[WS] Failed to parse message", error, event.data);
          return;
        }

        console.log("[WS msg]", data.type, data);

        if (data.type === "user_query") {
          const text = data.text;
          setMessages(prev => [
            ...prev,
            { role: "user", text: text },
            { role: "assistant", text: "", sources: [] }
          ]);
          setChatHistory(prev => [text, ...prev]);
          setIsStreaming(true);
          return;
        }

        if (data.type === "transcript_partial") {
          window.dispatchEvent(new CustomEvent("stt-partial", { detail: data.transcript }));
          return;
        }

        if (data.type === "audio-binary") {
          expectBinaryAudio.current = true;
          return;
        }

        if (data.type === "debug") {
          console.log("[WS debug]", data.message);
          return;
        }

        if (data.type === "start") {
          setIsStreaming(true);

        } else if (data.type === "chunk") {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;

            if (lastIndex >= 0 && next[lastIndex]?.role === "assistant") {
              const currentText = next[lastIndex].text || "";
              next[lastIndex] = {
                ...next[lastIndex],
                text: currentText + data.content
              };
              return next;
            }

            return [...next, { role: "assistant", text: data.content, sources: [] }];
          });

        } else if (data.type === "audio") {
          console.log("[TTS] Received audio chunk, enqueueing...");
          enqueueAudio(data.audio);

        } else if (data.type === "sources") {
          setMessages(prev => {
            const next = [...prev];
            const lastIndex = next.length - 1;

            if (lastIndex >= 0) {
              next[lastIndex] = {
                ...next[lastIndex],
                sources: data.sources
              };
            }

            return next;
          });

        } else if (data.type === "end") {
          setIsStreaming(false);
        }
      };

      socket.onerror = (e) => {
        console.error("WS ERROR", e);
        setConnectionStatus("error");
      };

      socket.onclose = (event) => {
        console.log("WS CLOSED", event.code, event.reason, event.wasClean);
        ws.current = null;
        setConnectionStatus("closed");
        if (shouldReconnect.current) {
          reconnectTimer.current = setTimeout(() => {
            console.log("Reconnecting websocket...");
            connect();
          }, 1500);
        }
      };
    };

    connect();

    return () => {
      shouldReconnect.current = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      ws.current?.close();
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
          isStreaming={isStreaming}
        />

        <ChatInput
          wsRef={ws}
          sendPayload={sendPayload}
          setMessages={setMessages}
          setChatHistory={setChatHistory}
          stopAllAudio={stopAllAudio}
          setIsStreaming={setIsStreaming}
          connectionStatus={connectionStatus}
        />

      </div>

    </div>

  );
}

export default ChatPage;