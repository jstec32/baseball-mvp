import React from "react";
import Layout from "../components/Layout";

function Teams() {
  return (
    <Layout>
      <main className="p-6 max-w-[920px] mx-auto">
        <h1 className="text-2xl font-bold mb-4">Team Stats & Trends</h1>
        <p className="text-sm text-gray-700">This page will show team-level scoring trends, win probabilities, and inning breakdowns.</p>
      </main>
    </Layout>
  );
}

export default Teams;