import React, { useState } from "react";
import Layout from "../components/Layout";
import { format } from "date-fns";

const API_URL = import.meta.env.VITE_API_URL;

function Players() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [gameDate, setGameDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [reportUrl, setReportUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchSuggestions = async (q) => {
    setQuery(q);
    if (q.length < 2) {
      setSuggestions([]);
      return;
    }
    try {
      const res = await fetch(`${API_URL}/players/suggest?query=${encodeURIComponent(q)}`);
      const data = await res.json();
      setSuggestions(data.players || []);
    } catch (err) {
      console.error("Suggestion fetch failed", err);
      setSuggestions([]);
    }
  };

  const handleSelect = (player) => {
    setSelectedPlayer(player);
    setQuery(player.player_name);
    setSuggestions([]);
  };

  const generateReport = async () => {
    if (!selectedPlayer || !gameDate) {
      alert("Select a player and date");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/generate_hitter_report?player_id=${selectedPlayer.key_mlbam}&game_date=${gameDate}`);
      const data = await res.json();

      if (data.success && data.report_url) {
        setReportUrl(data.report_url);
      } else {
        alert("Failed to generate report.");
      }
    } catch (err) {
      console.error("Report generation error", err);
      alert("Error generating report.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="flex gap-8 p-6">
        {/* LEFT PANEL */}
        <div className="w-[360px] space-y-6">
          <div>
            <label className="block text-sm font-medium text-[#101418] mb-1">Search Player</label>
            <input
              type="text"
              className="w-full border border-[#d4dbe2] rounded-lg px-3 py-2 text-sm"
              value={query}
              onChange={(e) => fetchSuggestions(e.target.value)}
              placeholder="Start typing a player name..."
            />
            {suggestions.length > 0 && (
              <ul className="border border-[#d4dbe2] mt-1 rounded-md bg-white max-h-40 overflow-y-auto">
                {suggestions.map((p) => (
                  <li
                    key={p.key_mlbam}
                    className="p-2 text-sm text-[#101418] hover:bg-[#f0f4f8] cursor-pointer"
                    onClick={() => handleSelect(p)}
                  >
                    {p.player_name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-[#101418] mb-1">Select Date</label>
            <input
              type="date"
              className="w-full border border-[#d4dbe2] rounded-lg px-3 py-2 text-sm"
              value={gameDate}
              onChange={(e) => setGameDate(e.target.value)}
            />
          </div>

          <button
            onClick={generateReport}
            disabled={loading}
            className="rounded-full bg-[#699bcd] text-white text-sm font-bold px-4 py-2 disabled:opacity-60"
          >
            {loading ? "Generating..." : "Generate Report"}
          </button>
        </div>

        {/* RIGHT PANEL */}
        <div className="flex-1">
          <h2 className="text-xl font-bold mb-4">Preview</h2>
          {reportUrl ? (
            <iframe
              src={reportUrl}
              title="Report Preview"
              className="w-full h-[800px] border rounded-xl"
            />
          ) : (
            <p className="text-sm text-gray-600">No report generated yet.</p>
          )}
        </div>
      </div>
    </Layout>
  );
}

export default Players;
