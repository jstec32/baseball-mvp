import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import StatsPage from "./App.jsx";
import AdminLogs from "./pages/AdminLogs.jsx";
import Teams from "./pages/Teams.jsx";
import Players from "./pages/Players.jsx";
import Games from "./pages/Games.jsx";
import HomePage from "./pages/HomePage.jsx";
import { Navigate } from "react-router-dom";
import "./index.css";

ReactDOM.createRoot(document.getElementById("react-root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/stats" element={<StatsPage />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="/admin" element={<AdminLogs />} />
        <Route path="/teams" element={<Teams />} />
        <Route path="/players" element={<Players />} />
        <Route path="/games" element={<Games />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);

