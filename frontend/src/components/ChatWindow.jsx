import MessageBubble from "./MessageBubble";
import {
  useEffect,
  useRef
} from "react";

function ChatWindow({
  messages
}) {

  const bottomRef =
    useRef(null);

  useEffect(() => {

    bottomRef.current?.
      scrollIntoView({
        behavior: "smooth"
      });

  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">

        <div className="text-center">

          <h1 className="text-6xl font-bold text-slate-800">
            Bihar AI
          </h1>

          <p className="mt-4 text-gray-500 text-lg">
            Upload documents and start chatting
          </p>

          <div className="grid grid-cols-2 gap-5 mt-10">

            <Card
              title="📄 Summarize"
              desc="Generate document summary"
            />

            <Card
              title="🔍 Search"
              desc="Find information quickly"
            />

            <Card
              title="👤 Candidate"
              desc="Extract candidate details"
            />

            <Card
              title="🎤 Voice"
              desc="Ask by speaking"
            />

          </div>

        </div>

      </div>
    );
  }

  return (
    <div
      className="
      flex-1
      overflow-y-auto
      px-10
      py-8
      "
    >

      <div
        className="
        max-w-5xl
        mx-auto
        "
      >
        {
          messages.map(
            (msg, i) => (

             <MessageBubble
              key={i}
              role={msg.role}
              text={msg.text}
              sources={msg.sources}
            />

            )
          )
        }

        <div ref={bottomRef} />

      </div>

    </div>
  );
}

function Card({
  title,
  desc
}) {
  return (
    <div
      className="
      bg-white
      rounded-3xl
      p-6
      shadow-sm
      hover:shadow-xl
      transition
      cursor-pointer
      w-72
      "
    >
      <h3 className="font-bold text-lg">
        {title}
      </h3>

      <p className="text-gray-500 mt-2">
        {desc}
      </p>
    </div>
  );
}

export default ChatWindow;