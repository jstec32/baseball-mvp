import React, { useState } from "react";

function QueryInput({ onSubmit }) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    if (input.trim()) {
      onSubmit(input.trim());
      setInput("");
    }
  };

  return (
    <div className="flex items-center gap-2 mt-4">
      <input
        className="flex-1 h-12 p-3 rounded-xl border border-[#d4dbe2]"
        placeholder="Type your message..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
      />
      <button
        onClick={handleSubmit}
        className="h-12 px-4 rounded-full bg-[#699bcd] text-white font-bold"
      >
        Send
      </button>
    </div>
  );
}

export default QueryInput;