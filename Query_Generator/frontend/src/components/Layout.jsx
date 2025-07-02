import React from "react";
import { Link } from "react-router-dom";

function Layout({ children }) {
  return (
    <div className="bg-gray-50 min-h-screen">
      <header className="flex items-center justify-between border-b border-[#eaedf1] px-10 py-3">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-4 text-[#101418]">
            <svg className="size-4" viewBox="0 0 48 48" fill="none">
              <path d="M24 .76 47.24 24 24 47.24.76 24 24 .76Zm-3 35V12.24L9.24 24 21 35.76Z" fill="currentColor" />
            </svg>
            <h2 className="text-lg font-bold tracking-tight">Baseball Analytics</h2>
          </div>
          <nav className="flex items-center gap-9 text-sm font-medium text-[#101418]">
            <Link to="/home">Home</Link>
            <Link to="/stats">Stats</Link>
            <Link to="/players">Players</Link>
            <Link to="/teams">Teams</Link>
            <Link to="/games">Games</Link>
            <Link to="/admin" className="text-[#699bcd] font-bold">Admin Logs</Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

export default Layout;
