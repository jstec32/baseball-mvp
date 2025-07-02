import React, { useEffect, useState } from "react";
import Layout from "../components/Layout";
import LiveScoreTicker from "../components/LiveScoreTicker";

const API_URL = import.meta.env.VITE_API_URL;

function HomePage() {
  const [standings, setStandings] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/standings`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setStandings(data.standings);
        } else {
          throw new Error(data.error || "Failed to fetch standings.");
        }
      })
      .catch(err => {
        console.error(err);
        setError("Failed to load standings.");
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <div className="p-10">
        <h1 className="text-3xl font-bold mb-4">Welcome to Baseball Analytics</h1>
        <LiveScoreTicker />

        <div className="mt-10 grid grid-cols-3 gap-8">
          {/* STANDINGS - Two-thirds width */}
          <div className="col-span-2">
            <h2 className="text-xl font-bold mb-2">Division Standings</h2>

            {loading && <p className="text-gray-500">Loading standings...</p>}
            {error && <p className="text-red-500">{error}</p>}

            {!loading && !error && Object.entries(standings).map(([division, teams]) => (
              <div key={division} className="mb-6">
                <h3 className="text-md font-semibold mb-1">{division}</h3>
                <table className="w-full text-sm border border-[#d4dbe2] bg-white rounded overflow-hidden">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-3 py-2 text-left">Team</th>
                      <th className="px-3 py-2 text-right">W</th>
                      <th className="px-3 py-2 text-right">L</th>
                      <th className="px-3 py-2 text-right">Pct</th>
                      <th className="px-3 py-2 text-right">GB</th>
                      <th className="px-3 py-2 text-right">Streak</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teams.map((team, i) => (
                      <tr key={i} className="border-t border-[#eaedf1]">
                        <td className="px-3 py-2">{team.team}</td>
                        <td className="px-3 py-2 text-right">{team.wins}</td>
                        <td className="px-3 py-2 text-right">{team.losses}</td>
                        <td className="px-3 py-2 text-right">{team.pct}</td>
                        <td className="px-3 py-2 text-right">{team.gb}</td>
                        <td className="px-3 py-2 text-right">{team.streak}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>

          {/* NEWS - Placeholder */}
          <div className="col-span-1">
            <h2 className="text-xl font-bold mb-2">News</h2>
            <div className="p-4 bg-white border border-[#d4dbe2] rounded text-sm text-gray-500">
              Coming soon...
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default HomePage;
