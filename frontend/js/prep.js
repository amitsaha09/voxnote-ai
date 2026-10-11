/* Interview prep page: resume + JD -> tailored questions; GitHub -> profile score. */
const FOCUS_COLOR = { technical: "#68e0e5", behavioral: "#f6a6d7", "jd-fit": "#9b8cff" };
const DIFF_COLOR = { easy: "#66e1b7", medium: "#f5c542", hard: "#f27e7e" };

document.addEventListener("DOMContentLoaded", () => {
  const resumeInput = document.getElementById("resume-file");
  const resumeLabel = document.getElementById("resume-label");
  resumeInput.addEventListener("change", () => {
    resumeLabel.textContent = resumeInput.files[0] ? resumeInput.files[0].name : "Choose your resume PDF…";
  });

  document.getElementById("prep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    hide("results"); hide("error-panel"); show("progress"); setStage("Starting…");
    try {
      const f = resumeInput.files[0];
      if (!f) throw new Error("Upload your resume PDF first.");
      const fd = new FormData();
      fd.append("resume", f);
      fd.append("jd_text", document.getElementById("jd-text").value.trim());
      fd.append("github_username", document.getElementById("github-username").value.trim());
      const jobId = await startJob("/api/prep", fd);
      const result = await pollJob(jobId, setStage);
      renderPrep(result);
      hide("progress"); show("results");
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      hide("progress"); show("error-panel");
      document.getElementById("error-msg").textContent = err.message;
    }
  });

  function renderPrep(r) {
    const wrap = document.getElementById("r-questions");
    wrap.innerHTML = "";
    (r.questions || []).forEach((q, i) => {
      const fc = FOCUS_COLOR[q.focus] || "#9ca8c6";
      const dc = DIFF_COLOR[q.difficulty] || "#9ca8c6";
      const card = document.createElement("div");
      card.className = "prep-qcard";
      card.innerHTML = `
        <span class="qnum">Q${i + 1}</span>
        <div class="prep-qbody">
          <p>${esc(q.question)}</p>
          <div class="prep-tags">
            <span class="mini-badge" style="color:${fc};border-color:${fc}55;background:${fc}11;">${esc(q.focus || "")}</span>
            <span class="mini-badge" style="color:${dc};border-color:${dc}55;background:${dc}11;">${esc(q.difficulty || "")}</span>
            <span class="mini-badge dim">from ${esc(q.based_on || "general")}</span>
          </div>
        </div>`;
      wrap.appendChild(card);
    });

    const gh = r.github;
    const ghSection = document.getElementById("github-section");
    if (gh && gh.profile) {
      show("github-section");
      document.getElementById("gh-name").textContent = gh.profile.name || gh.profile.username;
      const link = document.getElementById("gh-link");
      link.textContent = "@" + gh.profile.username;
      link.href = gh.profile.profile_url;
      document.getElementById("gh-score").textContent = gh.judgment.score ?? "–";
      document.getElementById("gh-summary").textContent = gh.judgment.summary || "";
      document.getElementById("gh-strengths").innerHTML =
        (gh.judgment.strengths || []).map(s => `<li>${esc(s)}</li>`).join("");
      document.getElementById("gh-gaps").innerHTML =
        (gh.judgment.gaps || []).map(s => `<li>${esc(s)}</li>`).join("");
      document.getElementById("gh-meta").innerHTML =
        `<span>📦 ${gh.profile.public_repos} repos</span><span>⭐ ${gh.profile.total_stars} stars</span>` +
        `<span>👥 ${gh.profile.followers} followers</span>` +
        `<span>💻 ${(gh.profile.top_languages || []).join(" · ")}</span>`;
    } else {
      hide("github-section");
    }
  }
});
