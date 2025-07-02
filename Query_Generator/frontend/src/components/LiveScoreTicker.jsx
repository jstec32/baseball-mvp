import React, { useState, useEffect } from "react";
import { format, subDays, addDays } from "date-fns";

const API_URL = import.meta.env.VITE_API_URL;

function LiveScoreTicker() {
  const [scores, setScores] = useState([]);
  const [date, setDate] = useState(new Date());

  const fetchScores = async (targetDate) => {
    const dateStr = format(targetDate, "yyyy-MM-dd");
    try {
      const res = await fetch(`${API_URL}/live_scores?date=${dateStr}`);
      const data = await res.json();
        if (data.success) {
        setScores(data.games || []);
        } else {
        console.error("API error:", data.error);
        setScores([]);
        }
    } catch (err) {
      console.error("Error fetching scores:", err);
      setScores([]);
    }
  };

  useEffect(() => {
    fetchScores(date);
  }, [date]);

  const goPrevDay = () => setDate(subDays(date, 1));
  const goNextDay = () => setDate(addDays(date, 1));

  return (
    <div className="w-full bg-white border-y border-[#d4dbe2] py-3 px-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-bold text-[#101418]">Live Scores</h3>
        <div className="flex items-center gap-2 text-sm">
          <button onClick={goPrevDay} className="px-3 py-1 rounded bg-[#699bcd] text-white font-bold">
            ◀
          </button>
          <span className="text-[#101418]">{format(date, "MMMM d, yyyy")}</span>
          <button onClick={goNextDay} className="px-3 py-1 rounded bg-[#699bcd] text-white font-bold">
            ▶
          </button>
        </div>
      </div>

      <div className="overflow-x-auto whitespace-nowrap">
        <div className="flex gap-3">
          {scores.map((game, i) => (
            <div
              key={i}
              className="min-w-[160px] border border-[#d4dbe2] bg-[#f9fafb] rounded-lg px-3 py-2 text-sm text-[#101418] flex flex-col items-center"
            >
              <div className="flex justify-between w-full">
                <span>{game.away_abbr}</span>
                <span>{game.away_score}</span>
              </div>
              <div className="flex justify-between w-full">
                <span>{game.home_abbr}</span>
                <span>{game.home_score}</span>
              </div>
              <div className="mt-1 text-xs text-gray-500">{game.inning}</div>
              {/* Placeholder for future logo */}
              {/* <img src={`/logos/${game.home_abbr}.svg`} alt="logo" className="mt-1 h-4" /> */}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default LiveScoreTicker;
