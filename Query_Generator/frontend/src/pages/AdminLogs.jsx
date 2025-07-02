import React, { useEffect, useState } from "react";
import Layout from "../components/Layout";

const API_URL = import.meta.env.VITE_API_URL;

function AdminLogs() {
  const [logs, setLogs] = useState("");
  const [successRate, setSuccessRate] = useState("Loading...");

  const fetchLogs = async () => {
    const res = await fetch(`${API_URL}/admin/logs`);
    const data = await res.json();

    const lines = data.logs
      .split("\n")
      .filter(line => line.trim())
      .map(line => {
        try {
          return JSON.parse(line);
        } catch {
          return null;
        }
      })
      .filter(Boolean);

    const total = lines.length;
    const successful = lines.filter(l => l.success === true).length;
    const rate = total === 0 ? 0 : ((successful / total) * 100).toFixed(1);

    setSuccessRate(`${rate}% success (${successful}/${total})`);
    setLogs(data.logs || "No logs available.");
  };

  const downloadLogs = () => {
    window.open(`${API_URL}/admin/logs/download`, "_blank");
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <Layout>
      <main className="p-6 flex flex-col gap-4 max-w-[920px] mx-auto">
        <div className="flex justify-between items-center">
          <h3 className="text-2xl font-bold">Query Error Logs</h3>
          <button
            onClick={downloadLogs}
            className="rounded-full bg-[#699bcd] text-white text-sm font-bold px-4 py-2"
          >
            Download JSONL
          </button>
        </div>

        <div className="p-4 rounded-xl bg-green-50 border border-green-200">
          <h4 className="text-md font-semibold text-green-800">Query Generator Success Rate</h4>
          <p className="text-xl font-mono text-green-900 mt-1">{successRate}</p>
        </div>

        <pre className="whitespace-pre-wrap bg-white border border-[#d4dbe2] rounded-xl p-4 h-[70vh] overflow-y-auto text-sm">
          {logs}
        </pre>
      </main>
    </Layout>
  );
}

export default AdminLogs;