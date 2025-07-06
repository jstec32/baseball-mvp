import React from "react";

function StandingsTable({ standings }) {
  if (!Array.isArray(standings) || standings.length === 0) {
    return <p className="text-gray-500 italic">No standings available.</p>;
  }

  return (
    <div className="space-y-6">
      {standings.map((group, i) => {
        const { division, teams } = group;

        if (!Array.isArray(teams)) {
          console.warn(`Invalid or missing 'teams' array in entry:`, group);
          return null;
        }

        return (
          <div key={i}>
            <h3 className="text-lg font-bold text-[#101418] mb-2">{division}</h3>
            <table className="w-full border border-[#d4dbe2] text-sm bg-white rounded-lg">
              <thead className="bg-[#f9fafb]">
                <tr>
                  <th className="p-2 text-left">Team</th>
                  <th className="p-2 text-right">W</th>
                  <th className="p-2 text-right">L</th>
                  <th className="p-2 text-right">PCT</th>
                  <th className="p-2 text-right">GB</th>
                  <th className="p-2 text-right">Streak</th>
                </tr>
              </thead>
              <tbody>
                {teams.map((team, j) => (
                  <tr key={j} className="border-t border-[#eaedf1]">
                    <td className="p-2">{team.team}</td>
                    <td className="p-2 text-right">{team.wins}</td>
                    <td className="p-2 text-right">{team.losses}</td>
                    <td className="p-2 text-right">{team.pct}</td>
                    <td className="p-2 text-right">{team.gb}</td>
                    <td className="p-2 text-right">{team.streak}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

export default StandingsTable;
