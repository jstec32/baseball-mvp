import React from "react";

function ChatHistory({ history, onSelect }) {
  return (
    <div className="w-[240px] flex flex-col border-r border-[#eaedf1] pr-4">
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-sm font-bold text-[#101418]">Past Chats</h4>
      </div>
      <ul className="space-y-2 overflow-y-auto flex-1 text-sm text-[#5c738a]">
        {history.map((entry, idx) => (
          <li
            key={idx}
            className="cursor-pointer hover:text-[#101418]"
            onClick={() => onSelect(entry)}
          >
            Q{idx + 1}: {entry.question}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default ChatHistory;