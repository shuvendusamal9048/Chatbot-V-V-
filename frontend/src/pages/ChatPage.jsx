import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import ChatWindow from "../components/ChatWindow";
import ChatInput from "../components/ChatInput";
import {
  useEffect,
  useRef,
  useState
} from "react";

function ChatPage() {

  const [
    messages,
    setMessages
  ] = useState([]);

  const [
    chatHistory,
    setChatHistory
  ] = useState([]);

  const ws = useRef(null);

  useEffect(() => {

  console.log("Creating websocket...");

  const socket =
    new WebSocket(
      "ws://localhost:8000/chat"
    );

  ws.current = socket;

  socket.onopen = () => {
    console.log(
      "✅ WS Connected"
    );
  };

  socket.onmessage =
    (event) => {

      console.log(
        "Received:",
        event.data
      );

      if (
        event.data === "[END]"
      )
        return;

      setMessages(
        (prev) => {

          const arr =
            [...prev];

          if (
            arr.length === 0
          )
            return prev;

          arr[
            arr.length - 1
          ].text +=
            event.data;

          return [...arr];
        }
      );
    };

  socket.onerror =
    (e) => {
      console.log(
        "❌ WS Error",
        e
      );
    };

  socket.onclose =
    (e) => {
      console.log(
        "⚠️ WS Closed",
        e
      );
    };

  return () => {
    socket.close();
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
        chatHistory={
          chatHistory
        }
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
          messages={
            messages
          }
        />

        <ChatInput
          ws={ws}
          setMessages={
            setMessages
          }
          setChatHistory={
            setChatHistory
          }
        />

      </div>

    </div>

  );
}

export default ChatPage;