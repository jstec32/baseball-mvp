import React from "react";
import Layout from "../components/Layout";

function Games() {
  return (
    <Layout>
      <main className="p-6 max-w-[920px] mx-auto">
        <h1 className="text-2xl font-bold mb-4">Game-Level Analysis</h1>
        <p className="text-sm text-gray-700">This page will show inning-by-inning run breakdowns and match-level summaries.</p>
      </main>
    </Layout>
  );
}

export default Games;