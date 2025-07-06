import React from "react";
import Layout from "../components/Layout";
import LiveScoreTicker from "../components/LiveScoreTicker";
import StandingsSection from "../components/StandingsSection";

function HomePage() {
  return (
    <Layout>
      <div className="p-10">
        <h1 className="text-3xl font-bold mb-4">Welcome to Baseball Analytics</h1>
        <LiveScoreTicker />

        <div className="mt-10 grid grid-cols-3 gap-8">
          {/* STANDINGS SECTION (2/3 width) */}
          <div className="col-span-2">
            <StandingsSection />
          </div>

          {/* NEWS SECTION (1/3 width) */}
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

