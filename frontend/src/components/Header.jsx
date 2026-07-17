function Header() {
  return (
    <div
      className="
      h-20
      bg-white/70
      backdrop-blur-xl
      border-b
      px-10
      flex
      items-center
      justify-between
      "
    >

      <div>

        <h1 className="text-2xl font-bold">
          Bihar AI Assistant
        </h1>

        <p className="text-gray-500">
          Document Intelligence Platform
        </p>

      </div>

      <div
        className="
        text-green-600
        font-semibold
        "
      >
        ● Connected
      </div>

    </div>
  );
}

export default Header;