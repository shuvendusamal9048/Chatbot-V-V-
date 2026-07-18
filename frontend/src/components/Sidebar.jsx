import {
  Upload,
  FileText
} from "lucide-react";

import axios from "axios";
import {
  useEffect,
  useRef,
  useState
} from "react";

import { API_BASE_URL } from "../config";

function Sidebar({
  chatHistory = []
}) {

  const fileRef =
    useRef(null);

  const [
    documents,
    setDocuments
  ] = useState([]);

  // ===========================
  // Load Existing Documents
  // ===========================

  const loadDocuments =
    async () => {

      try {

        const res =
          await axios.get(
            `${API_BASE_URL}/documents`
          );

        console.log(
          "Documents:",
          res.data
        );

        setDocuments(
          res.data
        );

      }

      catch (err) {

        console.log(err);

      }

    };

  useEffect(() => {

    loadDocuments();

  }, []);

  // ===========================
  // Upload File
  // ===========================

  const uploadFile =
    async (e) => {

      const file =
        e.target.files[0];

      if (!file)
        return;

      try {

        const form =
          new FormData();

        form.append(
          "file",
          file
        );

        console.log(
          "Uploading:",
          file.name
        );

        const res =
          await axios.post(
            `${API_BASE_URL}/upload`,
            form,
            {
              headers: {
                "Content-Type":
                  "multipart/form-data"
              }
            }
          );

        console.log(
          res.data
        );

        alert(
          "Uploaded Successfully"
        );

        // reload sidebar docs
        loadDocuments();

      }

      catch (err) {

        console.log(err);

        alert(
          "Upload Failed"
        );

      }

    };

  return (

    <div
      className="
      w-80
      bg-[#081028]
      text-white
      p-6
      border-r
      border-slate-800
      flex
      flex-col
      "
    >

      {/* Logo */}

      <h1
        className="
        text-4xl
        font-bold
        "
      >
        Bihar AI
      </h1>

      <p
        className="
        text-gray-400
        mt-2
        "
      >
        Document Intelligence
      </p>

      {/* Hidden File Input */}

      <input
        type="file"
        hidden
        ref={fileRef}
        accept="
          .pdf,
          .txt,
          .docx
        "
        onChange={uploadFile}
      />

      {/* Upload Button */}

      <button
        onClick={() =>
          fileRef.current.click()
        }
        className="
        mt-8
        w-full
        bg-gradient-to-r
        from-blue-600
        to-indigo-600
        rounded-2xl
        p-4
        flex
        gap-3
        items-center
        justify-center
        hover:scale-[1.02]
        transition
        shadow-lg
        "
      >
        <Upload />

        Upload File
      </button>

      {/* Documents */}

      <div className="mt-10">

        <p
          className="
          text-gray-400
          mb-4
          "
        >
          Documents
        </p>

        <div
          className="
          flex
          flex-col
          gap-3
          "
        >

          {
            documents.length === 0
            && (

              <div
                className="
                text-gray-500
                text-sm
                "
              >
                No documents uploaded
              </div>

            )
          }

          {
            documents.map(
              (
                doc,
                i
              ) => (

                <div
                  key={i}
                  className="
                  bg-slate-800
                  rounded-2xl
                  p-4
                  flex
                  gap-3
                  hover:bg-slate-700
                  transition
                  cursor-pointer
                  "
                >

                  <FileText
                    size={20}
                  />

                  <span
                    className="
                    truncate
                    text-sm
                    "
                  >
                    {doc}
                  </span>

                </div>

              )
            )
          }

        </div>

      </div>

      {/* Recent Chats */}

      <div className="mt-10 flex-1">

        <p
          className="
          text-gray-400
          mb-4
          "
        >
          Recent Chats
        </p>

        <div
          className="
          flex
          flex-col
          gap-2
          max-h-[300px]
          overflow-y-auto
          "
        >

          {
            chatHistory.map(
              (
                chat,
                i
              ) => (

                <div
                  key={i}
                  className="
                  p-3
                  rounded-xl
                  hover:bg-slate-800
                  transition
                  cursor-pointer
                  text-sm
                  truncate
                  "
                >
                  {chat}
                </div>

              )
            )
          }

        </div>

      </div>

    </div>

  );
}

export default Sidebar;