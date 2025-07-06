import React, { useEffect, useState } from "react";
import StandingsTable from "./StandingsTable";

const API_URL = import.meta.env.VITE_API_URL;

function StandingsSection() {
  const [divisionStandings, setDivisionStandings] = useState([]);
  const [wildCardStandings, setWildCardStandings] = useState([]);
  const [activeTab, setActiveTab] = useState("division");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_URL}/standings`).then(res => res.json()),
      fetch(`${API_URL}/standings/wildcard`).then(res => res.json()),
    ])
      .then(([divData, wcData]) => {
        if (divData.success) {
          const normalized = Object.entries(divData.standings)
            .map(([division, teams]) => {
              if (!Array.isArray(teams)) return null;
              return { division, teams };
            })
            .filter(Boolean);
          setDivisionStandings(normalized);
        }

        if (wcData.success) {
          const normalized = Object.entries(wcData.standings)
            .map(([league, teams]) => {
              if (!Array.isArray(teams)) return null;
              return { division: league, teams };
            })
            .filter(Boolean);
          setWildCardStandings(normalized);
        }
      })
      .catch(err => {
        console.error("Failed to fetch standings:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const standingsToDisplay = activeTab === "division" ? divisionStandings : wildCardStandings;

  if (loading) {
    return <p className="text-gray-500 italic">Loading standings...</p>;
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        <button
          onClick={() => setActiveTab("division")}
          className={`px-4 py-2 rounded font-bold text-sm ${
            activeTab === "division" ? "bg-[#699bcd] text-white" : "bg-gray-100 text-[#101418]"
          }`}
        >
          Division Standings
        </button>
        <button
          onClick={() => setActiveTab("wildcard")}
          className={`px-4 py-2 rounded font-bold text-sm ${
            activeTab === "wildcard" ? "bg-[#699bcd] text-white" : "bg-gray-100 text-[#101418]"
          }`}
        >
          Wild Card Standings
        </button>
      </div>

      <h2 className="text-xl font-semibold mb-4">
        {activeTab === "division" ? "Division Standings" : "Wild Card Standings"}
      </h2>

      <StandingsTable standings={standingsToDisplay} />
    </div>
  );
}

export default StandingsSection;
