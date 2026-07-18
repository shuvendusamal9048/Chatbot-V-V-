import { motion } from "framer-motion";
import { BsRobot } from "react-icons/bs";
import { FaUserCircle } from "react-icons/fa";

function MessageBubble({
  role,
  text,
  sources = []
}) {

  return (

    <motion.div
      initial={{
        opacity: 0,
        y: 20
      }}
      animate={{
        opacity: 1,
        y: 0
      }}
      className={`
      flex
      gap-4
      mb-8
      ${
        role === "user"
          ? "justify-end"
          : ""
      }
      `}
    >

      {
        role === "assistant" && (

          <div
            className="
            w-10
            h-10
            rounded-full
            bg-blue-600
            text-white
            flex
            items-center
            justify-center
            "
          >
            <BsRobot />
          </div>

        )
      }

      <div
        className={`
        max-w-4xl
        rounded-3xl
        px-6
        py-5
        shadow-md
        whitespace-pre-wrap
        ${
          role === "user"
            ? `
            bg-gradient-to-r
            from-blue-600
            to-indigo-600
            text-white
            `
            : `
            bg-white
            `
        }
        `}
      >

        {text}

        {
          role === "assistant" &&
          sources?.length > 0 && (

            <div
              className="
              mt-5
              pt-4
              border-t
              "
            >

              <p
                className="
                text-xs
                text-gray-400
                mb-3
                "
              >
                Sources
              </p>

              {
                sources.map(
                  (src, i) => (

                    <div
                      key={i}
                      className="
                      bg-slate-100
                      rounded-xl
                      px-3
                      py-2
                      mb-2
                      text-sm
                      "
                    >
                      📄 {src}
                    </div>

                  )
                )
              }

            </div>

          )
        }

      </div>

      {
        role === "user" && (

          <FaUserCircle
            size={40}
            className="
            text-gray-500
            "
          />

        )
      }

    </motion.div>

  );
}

export default MessageBubble;