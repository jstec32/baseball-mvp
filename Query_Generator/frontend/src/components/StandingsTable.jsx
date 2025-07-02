import React, { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function StandingsTable() {
  const [standings, setStandings] = useState([]);

  useEffect(() => {
    const fetchStandings = async () => {
      try {
        const res = await fetch(`${API_URL}/standings`);
        const data = await res.json();
        if (data.success && data.standings) {
          setStandings(data.standings);
        } else {
          console.error("Failed to fetch standings:", data.error || "No data");
        }
      } catch (err) {
        console.error("Error fetching standings:", err);
      }
    };

    fetchStandings();
  }, []);

  return (
    <div className="space-y-6">
      {standings.map((division, i) => (
        <div key={i}>
          <h3 className="text-lg font-bold text-[#101418] mb-2">{division.division}</h3>
          <table className="w-full border border-[#d4dbe2] text-sm bg-white rounded-lg">
            <thead className="bg-[#f9fafb]">
              <tr>
                <th className="p-2 text-left">Team</th>
                <th className="p-2 text-right">W</th>
                <th className="p-2 text-right">L</th>
                <th className="p-2 text-right">PCT</th>
                <th className="p-2 text-right">GB</th>
              </tr>
            </thead>
            <tbody>
              {division.teams.map((team, j) => (
                <tr key={j} className="border-t border-[#eaedf1]">
                  <td className="p-2">{team.team}</td>
                  <td className="p-2 text-right">{team.wins}</td>
                  <td className="p-2 text-right">{team.losses}</td>
                  <td className="p-2 text-right">{team.pct}</td>
                  <td className="p-2 text-right">{team.gb}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

export default StandingsTable;
