const input = document.getElementById("user-input");
const sendButton = document.getElementById("send-btn");
const resultsContainer = document.querySelector("tbody");
const columnHeaders = document.querySelector("thead tr");
const chatHistory = document.getElementById("chat-history");
const downloadBtn = document.getElementById("download-csv-btn");

let lastSuccessfulQuery = ""; // store last successful question

sendButton.addEventListener("click", async () => {
  const question = input.value.trim();
  if (!question) return;

  // Append to chat
  const userMsg = document.createElement("p");
  userMsg.className = "p-3 bg-[#eaedf1] text-sm rounded-xl text-[#101418]";
  userMsg.textContent = question;
  chatHistory.appendChild(userMsg);

  const res = await fetch("http://localhost:8000/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, output_format: "web" }),
  });

  const data = await res.json();

  const sysMsg = document.createElement("p");
  sysMsg.className = "p-3 bg-[#699bcd] text-sm rounded-xl text-white";

  if (!data.success) {
    sysMsg.textContent = `Error: ${data.error}`;
    chatHistory.appendChild(sysMsg);
    downloadBtn.style.display = "none"; // hide button on error
    return;
  }

  sysMsg.textContent = `Query succeeded. ${data.rows.length} rows returned.`;
  chatHistory.appendChild(sysMsg);

  // Update Table
  columnHeaders.innerHTML = "";
  resultsContainer.innerHTML = "";

  data.columns.forEach((col) => {
    const th = document.createElement("th");
    th.className =
      "px-4 py-3 text-left text-[#101418] text-sm font-medium leading-normal";
    th.textContent = col;
    columnHeaders.appendChild(th);
  });

  data.rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "border-t border-t-[#d4dbe2]";
    data.columns.forEach((col) => {
      const td = document.createElement("td");
      td.className =
        "h-[72px] px-4 py-2 text-[#5c738a] text-sm font-normal leading-normal";
      td.textContent = row[col];
      tr.appendChild(td);
    });
    resultsContainer.appendChild(tr);
  });

  input.value = "";
  // Save last query for CSV use
  lastSuccessfulQuery = question;
  downloadBtn.style.display = "inline-block";

  input.value = "";
});

downloadBtn.addEventListener("click", async () => {
  if (!lastSuccessfulQuery) return;

  const res = await fetch("http://localhost:8000/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: lastSuccessfulQuery, output_format: "csv" }),
  });

  const data = await res.json();

  if (data.csv_download_buffer) {
    const blob = new Blob([data.csv_download_buffer], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "query_results.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  } else {
    alert("No CSV returned.");
  }
});
