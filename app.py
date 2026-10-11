import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import traceback

from main import run_pipeline, ask_question

load_dotenv()

# ---------------------------- Page setup ----------------------------
st.set_page_config(
    page_title="VoxNote AI | Video Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------- Premium dark UI ----------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --bg: #080b14;
        --panel: rgba(18, 23, 39, .82);
        --panel2: rgba(24, 30, 50, .72);
        --line: rgba(166, 180, 220, .14);
        --text: #f2f5ff;
        --muted: #9ca8c6;
        --purple: #9b8cff;
        --cyan: #68e0e5;
        --pink: #f6a6d7;
    }
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 12% 0%, rgba(99, 78, 210, .23), transparent 32%),
            radial-gradient(ellipse at 88% 14%, rgba(46, 188, 205, .13), transparent 30%),
            linear-gradient(135deg, #080b14 0%, #0b1020 55%, #090d18 100%);
        color: var(--text);
    }
    [data-testid="stHeader"] { background: rgba(8,11,20,.65); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(17,21,37,.98), rgba(10,14,26,.98));
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] > div { padding-top: 1.4rem; }
    .block-container { padding-top: 2.1rem; padding-bottom: 3rem; max-width: 1440px; }
    h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -.035em; color: var(--text); }
    p, label, li { color: #d5dcf2; }
    .brand {
        display:flex; align-items:center; gap:12px; margin: 0 0 1.8rem 0;
    }
    .brand-mark {
        width:44px;height:44px;border-radius:15px;display:flex;align-items:center;justify-content:center;
        background:linear-gradient(135deg,#a08bff,#56dfe5);color:#101326;font-size:23px;font-weight:900;
        box-shadow:0 8px 28px rgba(117,116,255,.25);
    }
    .brand-name {font-family:'Manrope',sans-serif;font-weight:800;font-size:20px;letter-spacing:-.7px;color:#f7f8ff;}
    .brand-sub {font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#8995b6;margin-top:2px;}
    .hero {
        position:relative; overflow:hidden; border:1px solid rgba(174,183,255,.18);
        border-radius:28px; padding:32px 34px 30px;
        background:linear-gradient(115deg,rgba(34,34,67,.91),rgba(17,37,53,.82) 68%,rgba(24,28,51,.88));
        box-shadow:0 24px 80px rgba(0,0,0,.22); margin-bottom:24px;
    }
    .hero:after {
        content:""; position:absolute; width:280px;height:280px;border-radius:50%;
        right:-70px;top:-130px;background:rgba(110,220,232,.11);filter:blur(3px);
    }
    .eyebrow {
        display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border-radius:100px;
        border:1px solid rgba(104,224,229,.24); background:rgba(104,224,229,.07);
        color:#8de9ed; font-size:11px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
    }
    .hero h1 {font-size:clamp(32px,4vw,51px);line-height:1.08;margin:17px 0 12px;max-width:780px;}
    .gradient-text {background:linear-gradient(90deg,#c4baff,#7fe8ec 58%,#f6b3dc);-webkit-background-clip:text;background-clip:text;color:transparent;}
    .hero-copy {max-width:720px;color:#aeb9d5;font-size:15px;line-height:1.75;margin-bottom:22px;}
    .hero-pills {display:flex;flex-wrap:wrap;gap:9px;}
    .pill {font-size:12px;color:#d7def5;border:1px solid rgba(178,190,230,.14);background:rgba(8,12,25,.3);padding:8px 11px;border-radius:10px;}
    .section-kicker {color:#8d9bbb;font-size:11px;text-transform:uppercase;letter-spacing:1.7px;font-weight:700;margin:0 0 10px;}
    .section-title {font-family:'Manrope',sans-serif;font-size:23px;font-weight:800;color:#f4f6ff;letter-spacing:-.7px;margin-bottom:5px;}
    .section-sub {color:#929fbd;font-size:13px;margin-bottom:18px;}
    .panel {
        background:linear-gradient(145deg,rgba(22,28,47,.9),rgba(14,19,34,.84));
        border:1px solid var(--line);border-radius:21px;padding:21px 22px;
        box-shadow:0 14px 40px rgba(0,0,0,.13);margin-bottom:16px;
    }
    .metric-card {
        background:linear-gradient(145deg,rgba(29,35,60,.9),rgba(15,21,37,.9));
        border:1px solid rgba(169,183,231,.13);border-radius:17px;padding:17px 18px;min-height:105px;
    }
    .metric-label {font-size:11px;letter-spacing:1.1px;text-transform:uppercase;color:#96a3c3;font-weight:700;}
    .metric-value {font-family:'Manrope',sans-serif;font-size:24px;font-weight:800;color:#f7f8ff;margin-top:8px;}
    .metric-note {font-size:11px;color:#7786aa;margin-top:3px;}
    .result-heading {display:flex;align-items:center;gap:10px;margin-bottom:12px;}
    .result-icon {width:35px;height:35px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:rgba(155,140,255,.13);border:1px solid rgba(155,140,255,.2);font-size:17px;}
    .result-title {font-family:'Manrope',sans-serif;font-size:17px;font-weight:800;color:#f4f6ff;}
    .result-desc {font-size:12px;color:#8e9bbb;margin-top:2px;}
    .status {display:inline-flex;align-items:center;gap:7px;font-size:11px;font-weight:700;color:#86e7ca;background:rgba(74,220,177,.08);border:1px solid rgba(74,220,177,.2);padding:7px 10px;border-radius:100px;}
    .dot {width:6px;height:6px;background:#66e1b7;border-radius:50%;box-shadow:0 0 10px #66e1b7;}
    .stButton > button {
        border-radius:12px !important;border:1px solid rgba(178,168,255,.28) !important;
        background:linear-gradient(110deg,#a395ff,#6ddfe4) !important;color:#0c1222 !important;
        font-weight:800 !important;min-height:46px;box-shadow:0 8px 25px rgba(120,132,255,.15);
        transition:transform .15s ease,filter .15s ease;
    }
    .stButton > button:hover {transform:translateY(-1px);filter:brightness(1.06);}
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div {
        background:rgba(7,11,23,.72) !important;border:1px solid rgba(160,174,220,.19) !important;
        border-radius:12px !important;color:#f2f5ff !important;
    }
    [data-testid="stFileUploader"] {
        background:rgba(7,11,23,.36);border:1px dashed rgba(153,166,216,.28);border-radius:14px;padding:8px;
    }
    [data-testid="stTabs"] button {color:#9eabc9 !important;font-weight:700;}
    [data-testid="stTabs"] button[aria-selected="true"] {color:#a99bff !important;}
    [data-testid="stExpander"] {border:1px solid var(--line) !important;border-radius:14px !important;background:rgba(14,19,34,.55);}
    .footer {text-align:center;color:#697797;font-size:11px;padding:26px 0 8px;letter-spacing:.4px;}
    .empty-state {border:1px dashed rgba(160,174,220,.2);border-radius:20px;padding:34px;text-align:center;background:rgba(16,21,37,.38);}
    .empty-symbol {font-size:34px;margin-bottom:10px;}
    .empty-title {font-family:'Manrope',sans-serif;font-size:18px;font-weight:800;color:#e9edff;}
    .empty-copy {font-size:13px;color:#8e9bbb;max-width:480px;margin:7px auto 0;line-height:1.7;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Session state ----------------------------
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processing" not in st.session_state:
    st.session_state.processing = False


def render_result_header(icon: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="result-heading">
          <div class="result-icon">{icon}</div>
          <div><div class="result-title">{title}</div><div class="result-desc">{subtitle}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


# ---------------------------- Sidebar ----------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-mark">✦</div>
          <div><div class="brand-name">VoxNote AI</div><div class="brand-sub">Video intelligence</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-kicker">Workspace</div>', unsafe_allow_html=True)
    st.markdown("**New analysis**")
    st.caption("Turn long videos into clear, searchable knowledge.")
    input_mode = st.radio("Source type", ["YouTube link", "Local audio / video"], label_visibility="collapsed")
    source_url = ""
    uploaded_file = None

    if input_mode == "YouTube link":
        source_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=…",
            help="Paste a public YouTube video URL.",
        )
    else:
        uploaded_file = st.file_uploader(
            "Choose a media file",
            type=["mp4", "mov", "mkv", "webm", "mp3", "wav", "m4a", "mpeg", "mpga"],
            help="The file will be saved temporarily so your existing processing pipeline can read it.",
        )

    language = st.selectbox("Transcript language", ["english", "hinglish"], index=0)
    st.markdown("")
    run_clicked = st.button("✦  Analyze video", use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-kicker">Included in your report</div>', unsafe_allow_html=True)
    st.markdown("`01`  Video title & summary")
    st.markdown("`02`  Action items & owners")
    st.markdown("`03`  Key decisions")
    st.markdown("`04`  Open questions")
    st.markdown("`05`  Chat with the transcript")
    st.markdown("---")
    st.caption("Powered by your existing Whisper · LangChain · vector search pipeline")

# ---------------------------- Header ----------------------------
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">✧ &nbsp; Your personal video intelligence studio</div>
      <h1>From hours of video<br>to <span class="gradient-text">clear thinking.</span></h1>
      <div class="hero-copy">
        Transform recordings and YouTube videos into useful summaries, decisions, action items,
        and a searchable conversation — all in one elegant workspace.
      </div>
      <div class="hero-pills">
        <div class="pill">◈ &nbsp; Whisper transcription</div>
        <div class="pill">✧ &nbsp; AI-powered summaries</div>
        <div class="pill">⌕ &nbsp; Ask your video</div>
        <div class="pill">↗ &nbsp; Actionable insights</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------- Pipeline execution ----------------------------
if run_clicked:
    if input_mode == "YouTube link":
        source = source_url.strip()
        if not source:
            st.sidebar.error("Paste a YouTube URL first.")
            st.stop()
    else:
        if uploaded_file is None:
            st.sidebar.error("Upload an audio or video file first.")
            st.stop()
        suffix = Path(uploaded_file.name).suffix or ".mp4"
        temp_path = Path("uploads") / f"streamlit_upload{suffix}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(uploaded_file.getbuffer())
        source = str(temp_path.resolve())

    st.session_state.analysis = None
    st.session_state.chat_history = []
    with st.status("Preparing your video intelligence report…", expanded=True) as status:
        st.write("Processing audio and generating the transcript.")
        try:
            result = run_pipeline(source, language)
            st.write("Building your searchable transcript.")
            status.update(label="Analysis complete", state="complete", expanded=False)
            st.session_state.analysis = result
        except Exception as exc:
            status.update(label="Analysis failed", state="error", expanded=True)
            st.error(f"{type(exc).__name__}: {exc}")
            st.caption("Check the terminal for the full traceback. Verify your API key, media file, and dependencies.")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()

# ---------------------------- Results ----------------------------
analysis = st.session_state.analysis
if analysis:
    title = clean_text(analysis.get("title", "Video analysis"))
    transcript = clean_text(analysis.get("transcript"))
    summary = clean_text(analysis.get("summary"))
    actions = clean_text(analysis.get("action_items"))
    decisions = clean_text(analysis.get("key_decisions"))
    questions = clean_text(analysis.get("open_questions"))

    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 18px;">
          <div><div class="section-kicker">Your latest report</div><div class="section-title">{title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</div></div>
          <div class="status"><span class="dot"></span> Analysis ready</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        (c1, "TRANSCRIPT", f"{len(transcript.split()):,}", "words captured"),
        (c2, "INSIGHTS", "3", "structured outputs"),
        (c3, "LANGUAGE", language.title(), "transcription mode"),
        (c4, "CHAT", "Ready", "ask the video"),
    ]
    for col, label, value, note in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    summary_col, action_col = st.columns([1.15, 0.85], gap="large")
    with summary_col:
        with st.container(border=False):
            st.markdown('<div class="panel">', unsafe_allow_html=True)
            render_result_header("✧", "Executive summary", "The essential story, without the noise")
            st.markdown(summary or "_No summary was returned._")
            st.markdown("</div>", unsafe_allow_html=True)
    with action_col:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        render_result_header("↗", "Action items", "Tasks to take forward")
        st.markdown(actions or "_No action items were returned._")
        st.markdown("</div>", unsafe_allow_html=True)

    tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
        ["🔑  Key decisions", "❔  Open questions", "▤  Full transcript", "✦  Ask your video"]
    )

    with tab_decisions:
        st.markdown("")
        render_result_header("◈", "Key decisions", "Important choices and conclusions identified")
        st.markdown(decisions or "_No key decisions were returned._")
    with tab_questions:
        st.markdown("")
        render_result_header("?", "Open questions", "Topics that may need follow-up")
        st.markdown(questions or "_No open questions were returned._")
    with tab_transcript:
        st.markdown("")
        render_result_header("▤", "Transcript library", "Search and inspect the source text")
        transcript_search = st.text_input("Search transcript", placeholder="Find a name, topic, or phrase…", key="transcript_search")
        if transcript_search:
            lower = transcript.lower()
            needle = transcript_search.lower()
            positions = []
            start = 0
            while True:
                idx = lower.find(needle, start)
                if idx < 0:
                    break
                positions.append(idx)
                start = idx + len(needle)
                if len(positions) >= 30:
                    break
            if positions:
                st.caption(f"Showing up to {len(positions)} matching passage(s).")
                for idx in positions:
                    excerpt = transcript[max(0, idx - 180):min(len(transcript), idx + len(needle) + 260)]
                    st.markdown(f"> …{excerpt}…")
            else:
                st.info("No matching text found.")
        with st.expander("Read the complete transcript", expanded=not bool(transcript_search)):
            st.text_area("Transcript text", transcript, height=420, label_visibility="collapsed")
        st.download_button(
            "⬇  Download transcript (.txt)",
            data=transcript,
            file_name="video_transcript.txt",
            mime="text/plain",
        )

    with tab_chat:
        st.markdown("")
        render_result_header("✦", "Ask your video", "Get answers grounded in the transcript")
        st.markdown('<div class="section-sub">Ask about a person, a moment, a decision, or a detail. Your RAG chain will search the transcript.</div>', unsafe_allow_html=True)
        for entry in st.session_state.chat_history:
            with st.chat_message(entry["role"]):
                st.markdown(entry["content"])

        user_question = st.chat_input("Ask something about this video…")
        if user_question:
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.markdown(user_question)
            with st.chat_message("assistant"):
                with st.spinner("Searching your transcript…"):
                    try:
                        answer = ask_question(analysis["rag_chain"], user_question)
                        answer = clean_text(answer)
                    except Exception as exc:
                        answer = f"Sorry, I couldn't answer that right now. ({type(exc).__name__}: {exc})"
                    st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

    report_text = (
        f"TITLE\n{title}\n\nSUMMARY\n{summary}\n\nACTION ITEMS\n{actions}"
        f"\n\nKEY DECISIONS\n{decisions}\n\nOPEN QUESTIONS\n{questions}\n\nTRANSCRIPT\n{transcript}"
    )
    st.download_button(
        "⬇  Download complete report (.txt)",
        data=report_text,
        file_name="video_intelligence_report.txt",
        mime="text/plain",
    )
else:
    st.markdown(
        """
        <div class="empty-state">
          <div class="empty-symbol">✧</div>
          <div class="empty-title">Your next big insight starts here</div>
          <div class="empty-copy">
            Add a YouTube link or upload a media file in the left panel, then select
            <b>Analyze video</b>. Your summary, action items, decisions, and transcript chat
            will appear here.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("")
    feature_cols = st.columns(3)
    features = [
        ("✧", "Understand faster", "Turn lengthy recordings into a concise executive summary."),
        ("↗", "Know what to do", "Pull out action items, owners, and deadlines when mentioned."),
        ("⌕", "Find answers", "Ask follow-up questions instead of replaying the entire video."),
    ]
    for col, (icon, heading, body) in zip(feature_cols, features):
        with col:
            st.markdown(
                f'<div class="panel"><div class="result-icon">{icon}</div><div class="result-title" style="margin-top:12px">{heading}</div><div class="result-desc" style="line-height:1.7;margin-top:7px">{body}</div></div>',
                unsafe_allow_html=True,
            )

st.markdown('<div class="footer">VOXNOTE AI &nbsp;·&nbsp; TURN VIDEO INTO KNOWLEDGE &nbsp;·&nbsp; YOUR WORKSPACE</div>', unsafe_allow_html=True)
