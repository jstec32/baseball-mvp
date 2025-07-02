import React from "react";

function ResultsTable({ columns, rows }) {
  if (!rows.length) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-[#d4dbe2] bg-white mt-4">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50">
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 text-left text-[#101418] text-sm font-medium">{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-t-[#d4dbe2]">
              {columns.map((col) => (
                <td key={col} className="h-[72px] px-4 py-2 text-[#5c738a] text-sm">
                  {row[col]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ResultsTable;