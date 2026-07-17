import { Send } from "lucide-react";
import { BsFillMicFill } from "react-icons/bs";
import { useState } from "react";

function ChatInput({
  ws,
  setMessages,
  setChatHistory
}){
  const [question, setQuestion] =
    useState("");

  const [isRecording, setIsRecording] =
    useState(false);

  const send = () => {
    if (!question.trim()) return;

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        text: question
      },
      {
        role: "assistant",
        text: ""
      }
    ]);

    setChatHistory(
  prev => [
    question,
    ...prev
  ]
);

console.log(
  "State:",
  ws.current?.readyState
);

    ws.current.send(question);

    setQuestion("");
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
          transition-all
          hover:shadow-2xl
          "
        >
          <input
            value={question}
            onChange={(e) =>
              setQuestion(
                e.target.value
              )
            }
            onKeyDown={(e) => {
              if (
                e.key === "Enter"
              ) {
                send();
              }
            }}
            placeholder="
Ask anything about your documents...
"
            className="
            flex-1
            bg-transparent
            outline-none
            text-lg
            px-3
            py-2
            "
          />

          {/* Voice Button */}

          <button
            onClick={() =>
              setIsRecording(
                !isRecording
              )
            }
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

            ${
              isRecording
                ? `
                  bg-red-500
                  text-white
                  animate-pulse
                  scale-110
                `
                : `
                  bg-slate-100
                  text-slate-600
                  hover:bg-blue-100
                  hover:text-blue-600
                `
            }
          `}
          >
            <BsFillMicFill
              size={20}
            />
          </button>

          {/* Send Button */}

          <button
            onClick={send}
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
            🎤 Listening...
          </div>
        )}
      </div>
    </div>
  );
}



export default ChatInput;