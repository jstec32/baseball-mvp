import React, { useState } from "react";
import Layout from "./components/Layout";
import QueryInput from "./components/QueryInput";
import ResultsTable from "./components/ResultsTable";
import ChatHistory from "./components/ChatHistory";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [columns, setColumns] = useState([]);
  const [rows, setRows] = useState([]);
  const [chatHistory, setChatHistory] = useState(() => {
    const saved = localStorage.getItem("chatHistoryLog");
    return saved ? JSON.parse(saved) : [];
  });

  const runQuery = async (question) => {
    const entry = {
      question,
      columns: [],
      rows: [],
      success: null,
      error: null,
    };

    const tempHistory = [...chatHistory, entry];
    setChatHistory(tempHistory);
    localStorage.setItem("chatHistoryLog", JSON.stringify(tempHistory));

    try {
      const res = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, output_format: "web" }),
      });

      const data = await res.json();
      entry.columns = data.columns || [];
      entry.rows = data.rows || [];
      entry.success = data.success;
      entry.error = data.error || null;

      const updatedHistory = [...tempHistory.slice(0, -1), entry];
      setChatHistory(updatedHistory);
      localStorage.setItem("chatHistoryLog", JSON.stringify(updatedHistory));

      if (data.success) {
        setColumns(entry.columns);
        setRows(entry.rows);
      } else {
        alert(`Error: ${entry.error}`);
      }
    } catch (err) {
      entry.success = false;
      entry.error = err.message;

      const erroredHistory = [...tempHistory.slice(0, -1), entry];
      setChatHistory(erroredHistory);
      localStorage.setItem("chatHistoryLog", JSON.stringify(erroredHistory));
      alert(`Network error: ${err.message}`);
    }
  };

  const loadChat = (entry) => {
    setColumns(entry.columns);
    setRows(entry.rows);
  };

  return (
    <Layout>
      <div className="flex p-6 gap-6">
        {/* LEFT: Past Chat Panel */}
        <div className="w-[240px] flex flex-col border-r border-[#eaedf1] pr-4">
          <div className="flex justify-between items-center mb-2">
            <h4 className="text-sm font-bold text-[#101418]">Past Chats</h4>
            <button
              onClick={() => {
                setColumns([]);
                setRows([]);
                setChatHistory([]);
                localStorage.removeItem("chatHistoryLog");
              }}
              className="text-xs text-[#699bcd] font-bold hover:underline"
            >
              New Chat
            </button>
          </div>
          <ul className="space-y-2 overflow-y-auto flex-1 text-sm text-[#5c738a]">
            {chatHistory.map((entry, idx) => (
              <li
                key={idx}
                className="cursor-pointer hover:text-[#101418]"
                onClick={() => loadChat(entry)}
              >
                Q{idx + 1}: {entry.question}
              </li>
            ))}
          </ul>
        </div>

        {/* CENTER: Query Results */}
        <div className="flex-1 max-w-[920px]">
          <div className="flex justify-between items-center pb-3">
            <h2 className="text-[28px] font-bold">Current Query Results</h2>
            {rows.length > 0 && (
              <button
                onClick={async () => {
                  const res = await fetch(`${API_URL}/query`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      question: chatHistory.at(-1)?.question,
                      output_format: "csv",
                    }),
                  });
                  const data = await res.json();
                  if (data.csv_download_buffer) {
                    const blob = new Blob([data.csv_download_buffer], {
                      type: "text/csv",
                    });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "query_results.csv";
                    a.click();
                    window.URL.revokeObjectURL(url);
                  } else {
                    alert("No CSV returned.");
                  }
                }}
                className="rounded-full bg-[#699bcd] text-white text-sm font-bold px-4 py-2"
              >
                Download CSV
              </button>
            )}
          </div>

          <div className="overflow-hidden rounded-xl border border-[#d4dbe2] bg-white">
            <ResultsTable columns={columns} rows={rows} />
          </div>
        </div>

        {/* RIGHT: Chat Input */}
        <div className="w-[360px] flex flex-col">
          <h3 className="text-2xl font-bold pb-2">Chat History</h3>
          <div className="space-y-2 flex-1 overflow-y-auto border rounded-lg p-2 bg-white">
            {chatHistory.map((entry, i) => (
              <div key={i} className="space-y-2">
                <p className="p-3 bg-[#eaedf1] text-sm rounded-xl text-[#101418]">
                  {entry.question}
                </p>
                <p
                  className={`p-3 text-sm rounded-xl ${
                    entry.success === null
                      ? "bg-yellow-100 text-yellow-800"
                      : entry.success
                      ? "bg-[#699bcd] text-white"
                      : "bg-red-200 text-red-900"
                  }`}
                >
                  {entry.success === null
                    ? "Processing..."
                    : entry.success
                    ? `Query succeeded. ${entry.rows.length} rows returned.`
                    : `Query failed: ${entry.error}`}
                </p>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4">
            <QueryInput onSubmit={runQuery} />
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default App;
