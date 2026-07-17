import {
  Upload,
  FileText
} from "lucide-react";

function Sidebar({
  chatHistory =[]
}) {

  return (

    <div
      className="
      w-80
      bg-[#081028]
      text-white
      p-6
      border-r
      border-slate-800
      "
    >

      <h1 className="text-4xl font-bold">
        Bihar AI
      </h1>

      <button
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
        "
      >
        <Upload />

        Upload File
      </button>

      <div className="mt-12">

        <p className="mb-4">
          Documents
        </p>

        <div
          className="
          bg-slate-800
          rounded-2xl
          p-4
          flex
          gap-3
          "
        >
          <FileText />

          Resume.pdf
        </div>

      </div>

      <div className="mt-12">

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
          "
        >

          {
chatHistory?.map(
(chat,i)=>(

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

))
}

        </div>

      </div>

    </div>

  );
}

export default Sidebar;