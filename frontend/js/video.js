/* Video intelligence page: submit job, poll, render report + chat. */
document.addEventListener("DOMContentLoaded", () => {
  window.__sourceMode = setupSourceToggle();
  let currentJobId = null;

  document.getElementById("analyze-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    hide("results"); hide("error-panel"); show("progress"); setStage("Starting…");
    try {
      const jobId = await startJob("/api/analyze", buildSourceForm());
      currentJobId = jobId;
      const result = await pollJob(jobId, setStage);
      renderResults(result);
      hide("progress"); show("results");
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      hide("progress"); show("error-panel");
      document.getElementById("error-msg").textContent = err.message;
    }
  });

  function renderResults(r) {
    document.getElementById("r-title").textContent = r.title || "Video analysis";
    document.getElementById("m-words").textContent = (r.transcript || "").split(/\s+/).filter(Boolean).length.toLocaleString();
    document.getElementById("r-summary").innerHTML = nl2br(r.summary || "No summary returned.");
    document.getElementById("r-actions").innerHTML = nl2br(r.action_items || "No action items returned.");
    document.getElementById("r-decisions").innerHTML = nl2br(r.key_decisions || "No key decisions returned.");
    document.getElementById("r-questions").innerHTML = nl2br(r.open_questions || "No open questions returned.");
    document.getElementById("r-transcript").textContent = r.transcript || "";
    document.getElementById("chat-log").innerHTML = "";
    document.getElementById("dl-transcript").onclick = () =>
      downloadText("video_transcript.txt", r.transcript || "");
  }

  /* RAG chat */
  document.getElementById("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const q = input.value.trim();
    if (!q || !currentJobId) return;
    input.value = "";
    const log = document.getElementById("chat-log");
    log.insertAdjacentHTML("beforeend", `<div class="chat-msg user">${esc(q)}</div>`);
    const typing = document.createElement("div");
    typing.className = "chat-msg assistant typing";
    typing.textContent = "Searching your transcript…";
    log.appendChild(typing);
    log.scrollTop = log.scrollHeight;
    try {
      const fd = new FormData();
      fd.append("job_id", currentJobId);
      fd.append("question", q);
      const res = await fetch("/api/chat", { method: "POST", body: fd });
      const data = await res.json();
      typing.classList.remove("typing");
      typing.innerHTML = nl2br(data.answer || "No answer returned.");
    } catch {
      typing.classList.remove("typing");
      typing.textContent = "Sorry, the chat request failed.";
    }
    log.scrollTop = log.scrollHeight;
  });
});
