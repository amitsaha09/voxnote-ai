/* Shared helpers: escaping, job polling, source-tab toggle. */
function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function nl2br(s) { return esc(s).replace(/\n/g, "<br>"); }

function show(id) { document.getElementById(id).style.display = ""; }
function hide(id) { document.getElementById(id).style.display = "none"; }
function setStage(t) { document.getElementById("stage").textContent = t; }

async function startJob(endpoint, formData) {
  const res = await fetch(endpoint, { method: "POST", body: formData });
  const data = await res.json();
  if (data.error) throw new Error(data.error);
  return data.job_id;
}

async function pollJob(jobId, onStage) {
  while (true) {
    const res = await fetch(`/api/status/${jobId}`);
    const data = await res.json();
    if (data.status === "error") throw new Error(data.error || "Job failed.");
    if (onStage) onStage(data.stage || "Working…");
    if (data.status === "complete") return data.result;
    await new Promise(r => setTimeout(r, 2000));
  }
}

/* URL / file tab toggle. Returns a function reporting the active source. */
function setupSourceToggle() {
  const urlBtn = document.getElementById("tab-url");
  const fileBtn = document.getElementById("tab-file");
  const urlWrap = document.getElementById("url-wrap");
  const fileWrap = document.getElementById("file-wrap");
  const fileInput = document.getElementById("source-file");
  const fileLabel = document.getElementById("file-label");

  function select(which) {
    const isUrl = which === "url";
    urlBtn.classList.toggle("active", isUrl);
    fileBtn.classList.toggle("active", !isUrl);
    urlWrap.style.display = isUrl ? "" : "none";
    fileWrap.style.display = isUrl ? "none" : "";
  }
  urlBtn.addEventListener("click", () => select("url"));
  fileBtn.addEventListener("click", () => select("file"));
  fileInput.addEventListener("change", () => {
    fileLabel.textContent = fileInput.files[0] ? fileInput.files[0].name : "Choose an audio or video file…";
  });
  select("url");
  return () => (urlBtn.classList.contains("active") ? "url" : "file");
}

/* Build FormData from the shared input form. Throws with a friendly message. */
function buildSourceForm() {
  const mode = window.__sourceMode();
  const fd = new FormData();
  fd.append("language", document.getElementById("language").value);
  if (mode === "url") {
    const url = document.getElementById("source-url").value.trim();
    if (!url) throw new Error("Paste a YouTube URL first.");
    fd.append("source_url", url);
  } else {
    const f = document.getElementById("source-file").files[0];
    if (!f) throw new Error("Choose a file first.");
    fd.append("file", f);
  }
  return fd;
}

function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
