/* Interview evaluator page: submit job, poll, render judge-panel report + extended stats + chat. */
const VERDICT_COLOR = { correct: "#66e1b7", partially_correct: "#f5c542", incorrect: "#f27e7e" };
const VERDICT_LABEL = { correct: "Correct", partially_correct: "Partially correct", incorrect: "Incorrect" };

document.addEventListener("DOMContentLoaded", () => {
  window.__sourceMode = setupSourceToggle();
  let currentJobId = null;

  document.getElementById("eval-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    hide("results"); hide("error-panel"); show("progress"); setStage("Starting…");
    try {
      const jobId = await startJob("/api/evaluate", buildSourceForm());
      currentJobId = jobId;
      const result = await pollJob(jobId, setStage);
      renderEvaluation(result.evaluation, result.title);
      hide("progress"); show("results");
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      hide("progress"); show("error-panel");
      document.getElementById("error-msg").textContent = err.message;
    }
  });

  function renderEvaluation(ev, title) {
    const stats = ev.statistics || {};
    document.getElementById("r-title").textContent = title || "Interview evaluation";
    document.getElementById("m-total").textContent = stats.total_questions ?? 0;
    document.getElementById("m-acc").textContent = (stats.accuracy_pct ?? 0) + "%";
    document.getElementById("m-acc-note").textContent = `${stats.correct ?? 0} correct`;
    document.getElementById("m-avg").textContent = stats.avg_score ?? 0;
    document.getElementById("m-bad").textContent = stats.incorrect ?? 0;

    document.getElementById("r-strengths").innerHTML =
      (stats.strengths || []).map(s => `<li>${esc(s)}</li>`).join("") || "<li>–</li>";
    document.getElementById("r-weaknesses").innerHTML =
      (stats.weaknesses || []).map(s => `<li>${esc(s)}</li>`).join("") || "<li>–</li>";

    renderExtended(ev.extended || {});
    renderQuestions(ev.qa_results || []);
    document.getElementById("chat-log").innerHTML = "";
  }

  function renderExtended(ext) {
    /* Sentiment bars */
    const se = ext.sentiment || {};
    const bars = [["Positive", se.positive || 0, "#66e1b7"], ["Neutral", se.neutral || 0, "#9ca8c6"], ["Negative", se.negative || 0, "#f27e7e"]];
    document.getElementById("r-sentiment").innerHTML = bars.map(([label, pct, color]) => `
      <div class="sent-row"><span class="sent-label">${label}</span>
        <div class="sent-track"><div class="sent-fill" style="width:${pct}%;background:${color}"></div></div>
        <span class="sent-pct">${pct}%</span></div>`).join("");
    document.getElementById("r-sentiment-note").textContent = se.note || "";

    /* Talk time & pace */
    const sp = ext.speaking || {};
    document.getElementById("r-speaking").innerHTML = `
      <div class="talk-row"><span>Candidate</span><b>${sp.candidate_talk_pct ?? 0}%</b><span class="dim">· ${sp.candidate_wpm ?? 0} wpm · ${sp.candidate_words ?? 0} words</span></div>
      <div class="talk-row"><span>Interviewer</span><b>${sp.interviewer_talk_pct ?? 0}%</b><span class="dim">· ${sp.interviewer_wpm ?? 0} wpm · ${sp.interviewer_words ?? 0} words</span></div>`;
    document.getElementById("r-speaking-note").textContent = sp.note || "";

    /* Confidence meter */
    const cf = ext.confidence || {};
    const avg = cf.average || 0;
    document.getElementById("r-confidence-fill").style.width = avg + "%";
    document.getElementById("r-confidence-val").textContent = avg + "/100";
  }

  function renderQuestions(qaResults) {
    const wrap = document.getElementById("r-questions");
    wrap.innerHTML = "";
    qaResults.forEach((r, i) => {
      const color = VERDICT_COLOR[r.verdict] || "#9ca8c6";
      const label = VERDICT_LABEL[r.verdict] || r.verdict;
      const judges = [["Technical", "technical"], ["Communication", "communication"], ["Depth", "depth"]]
        .map(([name, key]) => {
          const j = r[key] || {};
          return `<div class="judge-box"><h4>${name}</h4><div class="score">${j.score ?? 0}/100</div><p>${esc(j.explanation || "")}</p></div>`;
        }).join("");
      const card = document.createElement("details");
      card.className = "qcard";
      if (i === 0) card.open = true;
      card.innerHTML = `
        <summary>
          <span class="qnum">Q${i + 1}</span>
          <span class="qtext">${esc(r.question).slice(0, 110)}</span>
          <span class="verdict-badge" style="color:${color};border-color:${color}66;background:${color}11;">${label} · ${r.overall_score ?? 0}/100</span>
        </summary>
        <div class="qbody">
          <div class="qtime">⏱ ${esc(r.start || "?")} → ${esc(r.end || "?")}</div>
          <p><strong>Q:</strong> ${esc(r.question)}</p>
          <p><strong>A:</strong> ${esc(r.answer) || "<em>No answer given.</em>"}</p>
          <div class="judge-grid">${judges}</div>
          <div class="head-judge"><p><strong>Head judge:</strong> ${esc(r.summary)}</p></div>
        </div>`;
      wrap.appendChild(card);
    });
  }

  /* RAG chat over the interview transcript */
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
