/* VoxNote AI — cinematic effects layer.
   Purely visual. Does not read, call, or change any app logic (app.js, video.js, interview.js, prep.js).
   Every block no-ops safely if its elements aren't on the page. */
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = window.matchMedia("(pointer: fine)").matches;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const pad = (n, l = 2) => String(n).padStart(l, "0");

  /* 1 ── Session timecode (HH:MM:SS:FF @ 24fps), shown in the nav and hero HUD */
  const tcEls = $$(".tc-live");
  if (tcEls.length) {
    const t0 = performance.now();
    const tick = () => {
      const ms = performance.now() - t0;
      const f = Math.floor((ms % 1000) / (1000 / 24));
      const s = Math.floor(ms / 1000);
      const txt = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}:${pad(f)}`;
      tcEls.forEach(el => (el.textContent = txt));
    };
    tick();
    if (!reduce) setInterval(tick, 42);
  }

  /* 2 ── Projector dust drifting through the beam */
  const dust = $("#fx-dust");
  if (dust) {
    const ctx = dust.getContext("2d");
    let w = 0, h = 0, dpr = 1, parts = [], running = true;
    const size = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = dust.width = innerWidth * dpr; h = dust.height = innerHeight * dpr;
      const n = Math.round(Math.min(90, (innerWidth * innerHeight) / 18000));
      parts = Array.from({ length: n }, () => ({
        x: Math.random() * w, y: Math.random() * h, r: (Math.random() * 1.6 + .4) * dpr,
        vx: (Math.random() - .35) * .25 * dpr, vy: (-Math.random() * .22 - .03) * dpr,
        a: Math.random() * .5 + .12, ph: Math.random() * 6.28,
      }));
    };
    const draw = (t) => {
      ctx.clearRect(0, 0, w, h);
      for (const p of parts) {
        if (!reduce) { p.x += p.vx; p.y += p.vy; }
        if (p.y < -10) { p.y = h + 10; p.x = Math.random() * w; }
        if (p.x < -10) p.x = w + 10; if (p.x > w + 10) p.x = -10;
        const tw = reduce ? 1 : .6 + .4 * Math.sin(t / 900 + p.ph);
        // warmer near the upper-right beam, cooler elsewhere
        const warm = Math.max(0, Math.min(1, (p.x / w) * .8 + (1 - p.y / h) * .5 - .35));
        ctx.fillStyle = `rgba(${Math.round(190 + 65 * warm)},${Math.round(215 - 35 * warm)},${Math.round(225 - 140 * warm)},${p.a * tw})`;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill();
      }
    };
    size(); addEventListener("resize", size);
    document.addEventListener("visibilitychange", () => { running = !document.hidden; if (running && !reduce) loop(); });
    const loop = (t = 0) => { if (!running) return; draw(t); if (!reduce) requestAnimationFrame(loop); };
    loop();
  }

  /* 3 ── Hero: live waveform with a sweeping playhead + hover parallax */
  const wave = $("#hero-wave");
  if (wave) {
    const ctx = wave.getContext("2d");
    let w = 0, h = 0, dpr = 1, running = true;
    const size = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      const r = wave.getBoundingClientRect(); w = wave.width = r.width * dpr; h = wave.height = r.height * dpr;
    };
    size(); addEventListener("resize", size);
    const LOOP = 16000;
    const env = (i) => .22 + .78 * Math.abs(Math.sin(i * .071) * Math.sin(i * .023 + 1.3)) * (.6 + .4 * Math.sin(i * .31));
    const draw = (t) => {
      ctx.clearRect(0, 0, w, h);
      const gap = 9 * dpr, bw = 4 * dpr, count = Math.floor(w / gap);
      const prog = reduce ? .42 : (t % LOOP) / LOOP;
      const ph = prog * 1.12 - .06;                // playhead overshoots slightly for a clean wrap
      const cy = h * .5, maxH = h * .26;
      for (let i = 0; i < count; i++) {
        const p = i / (count - 1), x = i * gap + (w - count * gap) / 2;
        const live = reduce ? 1 : .72 + .28 * Math.sin(t / 340 + i * .5) * Math.sin(t / 1900 + i * .09);
        const near = Math.max(0, 1 - Math.abs(p - ph) * 7);
        const bh = Math.max(2 * dpr, env(i) * maxH * live * (1 + near * .45));
        const played = p < ph;
        ctx.fillStyle = played ? `rgba(255,180,84,${.5 + near * .5})` : "rgba(120,150,170,.32)";
        if (played && near > .02) { ctx.shadowColor = "rgba(255,180,84,.9)"; ctx.shadowBlur = 18 * dpr * near; } else ctx.shadowBlur = 0;
        if (ctx.roundRect) { ctx.beginPath(); ctx.roundRect(x, cy - bh, bw, bh * 2, bw / 2); ctx.fill(); } else ctx.fillRect(x, cy - bh, bw, bh * 2);
      }
      ctx.shadowBlur = 0;
      const px = ph * w;
      if (px > 0 && px < w) {
        const g = ctx.createLinearGradient(0, 0, 0, h);
        g.addColorStop(0, "rgba(236,232,223,0)"); g.addColorStop(.5, "rgba(236,232,223,.9)"); g.addColorStop(1, "rgba(236,232,223,0)");
        ctx.fillStyle = g; ctx.fillRect(px - dpr, 0, 2 * dpr, h);
      }
    };
    const loop = (t = 0) => { if (!running) return; draw(t); if (!reduce) requestAnimationFrame(loop); };
    document.addEventListener("visibilitychange", () => { running = !document.hidden; if (running && !reduce) loop(); });
    loop();

    const frame = wave.closest(".frame");
    if (frame && fine && !reduce) {
      frame.addEventListener("pointermove", (e) => {
        const r = frame.getBoundingClientRect();
        const dx = (e.clientX - r.left) / r.width - .5, dy = (e.clientY - r.top) / r.height - .5;
        wave.style.transform = `translate(${dx * -22}px, ${dy * -14}px) scale(1.04)`;
      });
      frame.addEventListener("pointerleave", () => (wave.style.transform = ""));
    }
  }

  /* 4 ── Hero subtitles: sample captions typing in, like a film with burned-in subtitles */
  const capText = $("#cap-text");
  if (capText) {
    const tag = $("#cap-tag"), tc = $("#cap-tc");
    const lines = [
      ["Decision", "#5ee6d6", "00:04:24", "We ship the pilot in March, not February."],
      ["Action item", "#ffb454", "00:09:51", "Priya owns the vendor review by Friday."],
      ["Open question", "#b096ff", "00:17:08", "Who signs off on the budget?"],
    ];
    let li = 0;
    const show = () => {
      const [name, color, time, text] = lines[li];
      tag.textContent = name; tag.style.color = color; tc.textContent = time;
      if (reduce) { capText.textContent = text; return; }
      capText.textContent = ""; let i = 0;
      const type = setInterval(() => {
        capText.textContent = text.slice(0, ++i);
        if (i >= text.length) { clearInterval(type); setTimeout(() => { li = (li + 1) % lines.length; show(); }, 2600); }
      }, 34);
    };
    setTimeout(show, reduce ? 0 : 2600);
  }

  /* 5 ── Poster cards: cursor spotlight + gentle 3D tilt */
  if (fine) {
    $$("a.mode-card").forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        card.style.setProperty("--mx", `${x * 100}%`); card.style.setProperty("--my", `${y * 100}%`);
        if (!reduce) { card.style.setProperty("--ry", `${(x - .5) * 6}deg`); card.style.setProperty("--rx", `${(.5 - y) * 5}deg`); }
      });
      card.addEventListener("pointerleave", () => { card.style.setProperty("--rx", "0deg"); card.style.setProperty("--ry", "0deg"); });
    });
  }

  /* 6 ── Results: when the app reveals #results, trigger the staggered entrance (CSS does the rest) */
  const results = $("#results");
  if (results) {
    let wasHidden = results.style.display === "none";
    new MutationObserver(() => {
      const hidden = results.style.display === "none";
      if (wasHidden && !hidden) { results.classList.remove("in"); void results.offsetWidth; results.classList.add("in"); }
      wasHidden = hidden;
    }).observe(results, { attributes: true, attributeFilter: ["style"] });
  }
})();
