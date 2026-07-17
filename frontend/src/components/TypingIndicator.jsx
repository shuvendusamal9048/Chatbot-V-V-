function TypingIndicator() {
  return (
    <div className="flex mb-6">

      <div
        className="
        bg-white
        rounded-3xl
        px-6
        py-4
        shadow-md
        "
      >
        <div className="flex gap-2">

          <div
            className="
            w-3
            h-3
            rounded-full
            bg-gray-400
            animate-bounce
            "
          />

          <div
            className="
            w-3
            h-3
            rounded-full
            bg-gray-400
            animate-bounce
            [animation-delay:200ms]
            "
          />

          <div
            className="
            w-3
            h-3
            rounded-full
            bg-gray-400
            animate-bounce
            [animation-delay:400ms]
            "
          />

        </div>
      </div>

    </div>
  );
}

export default TypingIndicator;