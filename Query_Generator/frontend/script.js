const input            = document.getElementById("user-input");
const sendButton       = document.getElementById("send-btn");
const resultsContainer = document.querySelector("tbody");
const columnHeaders    = document.querySelector("thead tr");
const chatHistory      = document.getElementById("chat-history");
const downloadBtn      = document.getElementById("download-csv-btn");
const chatHistoryPanel = document.getElementById("chat-history-panel");
const newChatButton    = document.getElementById("new-chat-btn");
const adminTab         = document.getElementById("admin-tab");
const adminLogsPanel   = document.getElementById("admin-logs-panel");
const logsOutput       = document.getElementById("logs-output");
const downloadLogsBtn  = document.getElementById("download-logs-btn");
const mainResultsBox = document.getElementById("main-results");

let lastSuccessfulQuery = "";
let chatHistoryLog = [];

const savedHistory = localStorage.getItem("chatHistoryLog");
if (savedHistory) {
  chatHistoryLog = JSON.parse(savedHistory);
  updateChatHistoryPanel();
}

/* ========= Chat Panel Renderer ========= */
function updateChatHistoryPanel() {
  chatHistoryPanel.innerHTML = "";

  chatHistoryLog.forEach((entry, idx) => {
    const li = document.createElement("li");
    li.className = "cursor-pointer hover:text-[#101418]";
    li.textContent = `Q${idx + 1}: ${entry.question}`;
    li.dataset.index = idx;

    li.addEventListener("click", () => {
      loadChatFromHistory(entry);
    });

    chatHistoryPanel.appendChild(li);
  });
}

/* ========= Restore Previous Chat View ========= */
function loadChatFromHistory(entry) {
  chatHistory.innerHTML = "";

  const userMsg = document.createElement("p");
  userMsg.className = "p-3 bg-[#eaedf1] text-sm rounded-xl text-[#101418]";
  userMsg.textContent = entry.question;
  chatHistory.appendChild(userMsg);

  const sysMsg = document.createElement("p");
  sysMsg.className = "p-3 bg-[#699bcd] text-sm rounded-xl text-white";
  sysMsg.textContent = `Query succeeded. ${entry.rows.length} rows returned.`;
  chatHistory.appendChild(sysMsg);

  columnHeaders.innerHTML = "";
  resultsContainer.innerHTML = "";

  entry.columns.forEach(col => {
    const th = document.createElement("th");
    th.className = "px-4 py-3 text-left text-[#101418] text-sm font-medium";
    th.textContent = col;
    columnHeaders.appendChild(th);
  });

  entry.rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.className = "border-t border-t-[#d4dbe2]";
    entry.columns.forEach(col => {
      const td = document.createElement("td");
      td.className = "h-[72px] px-4 py-2 text-[#5c738a] text-sm";
      td.textContent = row[col];
      tr.appendChild(td);
    });
    resultsContainer.appendChild(tr);
  });

  downloadBtn.style.display = entry.rows.length > 0 ? "inline-block" : "none";
}

/* ========= MAIN QUERY HANDLER ========= */
sendButton?.addEventListener("click", async () => {
  const question = input.value.trim();
  localStorage.setItem("lastQuery", question);
  if (!question) return;

  const userMsg = document.createElement("p");
  userMsg.className = "p-3 bg-[#eaedf1] text-sm rounded-xl text-[#101418]";
  userMsg.textContent = question;
  chatHistory.appendChild(userMsg);

  const res = await fetch("http://localhost:8000/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, output_format: "web" })
  });
  const data = await res.json();

  const sysMsg = document.createElement("p");
  sysMsg.className = "p-3 bg-[#699bcd] text-sm rounded-xl text-white";
  chatHistory.appendChild(sysMsg);

  if (!data.success) {
    sysMsg.textContent = `Error: ${data.error}`;
    downloadBtn.style.display = "none";
    return;
  }

  sysMsg.textContent = `Query succeeded. ${data.rows.length} rows returned.`;

  columnHeaders.innerHTML = "";
  resultsContainer.innerHTML = "";

  data.columns.forEach(col => {
    const th = document.createElement("th");
    th.className = "px-4 py-3 text-left text-[#101418] text-sm font-medium";
    th.textContent = col;
    columnHeaders.appendChild(th);
  });

  data.rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.className = "border-t border-t-[#d4dbe2]";
    data.columns.forEach(col => {
      const td = document.createElement("td");
      td.className = "h-[72px] px-4 py-2 text-[#5c738a] text-sm";
      td.textContent = row[col];
      tr.appendChild(td);
    });
    resultsContainer.appendChild(tr);
  });

  lastSuccessfulQuery = question;
  downloadBtn.style.display = "inline-block";
  input.value = "";

  chatHistoryLog.push({
    question,
    response: data,
    columns: data.columns || [],
    rows: data.rows || []
  });
  localStorage.setItem("chatHistoryLog", JSON.stringify(chatHistoryLog));
  updateChatHistoryPanel();
});

/* ========= CSV DOWNLOAD ========= */
downloadBtn?.addEventListener("click", async () => {
  if (!lastSuccessfulQuery) return;

  const res = await fetch("http://localhost:8000/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: lastSuccessfulQuery, output_format: "csv" })
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

/* ========= ADMIN LOGS PANEL (optional) ========= */
if (adminTab && adminLogsPanel && logsOutput && downloadLogsBtn && mainResultsBox) {
  adminTab.addEventListener("click", async (e) => {
    e.preventDefault();

    const isHidden = adminLogsPanel.classList.contains("hidden");
    if (isHidden) {
      mainResultsBox.style.display = "none";
      adminLogsPanel.classList.remove("hidden");

      const res = await fetch("http://localhost:8000/admin/logs");
      const data = await res.json();
      logsOutput.textContent = data.logs || "No logs found.";
    } else {
      adminLogsPanel.classList.add("hidden");
      mainResultsBox.style.display = "";

      const last = localStorage.getItem("lastQuery");
      if (last) {
      input.value = last;
      }
    }
  });

  downloadLogsBtn.addEventListener("click", () => {
    window.open("http://localhost:8000/admin/logs/download", "_blank");
  });
}

const last = localStorage.getItem("lastQuery");
if (last) {
  input.value = last;
}
/* ========= NEW CHAT RESET ========= */
newChatButton?.addEventListener("click", () => {
  chatHistory.innerHTML = "";
  columnHeaders.innerHTML = "";
  resultsContainer.innerHTML = "";
  input.value = "";
  downloadBtn.style.display = "none";
});



