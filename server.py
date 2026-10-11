"""VoxNote AI — FastAPI server.

Serves the HTML frontend and wraps the existing pipeline:
  POST /api/analyze  -> video intelligence report (background job)
  POST /api/evaluate -> interview judge report + extended stats (background job)
  POST /api/prep     -> pre-interview prep: resume + JD -> questions, GitHub score
  GET  /api/status/{job_id} -> poll job progress
  POST /api/chat     -> RAG chat over a finished video OR interview analysis

Run from the project root:
    uv pip install fastapi uvicorn python-multipart pypdf
    uvicorn server:app --reload
Then open http://localhost:8000
"""
import shutil
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles

from main import run_pipeline, ask_question
from core.interview_judge import evaluate_interview
from core.interview_stats import build_interview_stats
from core.prep import build_prep
from core.scout import scout_resume

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="VoxNote AI")

# In-memory job store. Fine for a local single-user app.
# (A production version would use Redis/a database.)
jobs: dict = {}


def _save_upload(file: UploadFile, prefix: str = "job") -> str:
    suffix = Path(file.filename or "").suffix or ".mp4"
    dest = UPLOAD_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return str(dest.resolve())


def _new_job() -> str:
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {"status": "running", "stage": "Starting…",
                    "result": None, "error": None}
    return job_id


def _video_job(job_id: str, source: str, language: str):
    try:
        jobs[job_id]["stage"] = "Transcribing audio…"
        result = run_pipeline(source, language)
        jobs[job_id]["stage"] = "Complete"
        jobs[job_id]["status"] = "complete"
        # The RAG chain isn't JSON-serializable — keep it server-side for /api/chat.
        jobs[job_id]["rag_chain"] = result.pop("rag_chain", None)
        jobs[job_id]["result"] = {
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "action_items": result.get("action_items", ""),
            "key_decisions": result.get("key_decisions", ""),
            "open_questions": result.get("open_questions", ""),
            "transcript": result.get("transcript", ""),
        }
    except Exception as e:  # noqa: BLE001
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


def _interview_job(job_id: str, source: str, language: str):
    try:
        jobs[job_id]["stage"] = "Transcribing audio…"
        result = run_pipeline(source, language)
        jobs[job_id]["stage"] = "Running the 3-judge panel…"
        evaluation = evaluate_interview(result["segments"])
        jobs[job_id]["stage"] = "Computing session statistics…"
        evaluation["extended"] = build_interview_stats(evaluation["qa_results"])
        # Keep the RAG chain so the interview page can chat over the transcript.
        jobs[job_id]["rag_chain"] = result.pop("rag_chain", None)
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["stage"] = "Complete"
        jobs[job_id]["result"] = {
            "title": result.get("title", ""),
            "evaluation": evaluation,  # plain dicts/lists — JSON-safe
        }
    except Exception as e:  # noqa: BLE001
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


def _prep_job(job_id: str, resume_path: str, jd_text: str, github_username: str):
    try:
        jobs[job_id]["stage"] = "Reading your resume…"
        result = build_prep(resume_path, jd_text, github_username)
        jobs[job_id]["stage"] = "Scouting your links…"
        result["scout"] = scout_resume(resume_path)
        jobs[job_id]["status"] = "complete"
        jobs[job_id]["stage"] = "Complete"
        jobs[job_id]["result"] = result
    except Exception as e:  # noqa: BLE001
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = f"{type(e).__name__}: {e}"


def _begin_media_job(file, source_url):
    if file is not None and file.filename:
        source = _save_upload(file)
    elif source_url and source_url.strip():
        source = source_url.strip()
    else:
        return {"error": "Provide a YouTube URL or upload a file."}
    return _new_job(), source


@app.post("/api/analyze")
def analyze(background: BackgroundTasks,
            source_url: str = Form(None),
            language: str = Form("english"),
            file: UploadFile = File(None)):
    out = _begin_media_job(file, source_url)
    if isinstance(out, dict):
        return out
    job_id, source = out
    background.add_task(_video_job, job_id, source, language)
    return {"job_id": job_id}


@app.post("/api/evaluate")
def evaluate(background: BackgroundTasks,
             source_url: str = Form(None),
             language: str = Form("english"),
             file: UploadFile = File(None)):
    out = _begin_media_job(file, source_url)
    if isinstance(out, dict):
        return out
    job_id, source = out
    background.add_task(_interview_job, job_id, source, language)
    return {"job_id": job_id}


@app.post("/api/prep")
def prep(background: BackgroundTasks,
         jd_text: str = Form(""),
         github_username: str = Form(None),
         resume: UploadFile = File(None)):
    if resume is None or not resume.filename:
        return {"error": "Upload your resume PDF first."}
    resume_path = _save_upload(resume, prefix="resume")
    job_id = _new_job()
    background.add_task(_prep_job, job_id, resume_path, jd_text, github_username)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return {"status": "error", "error": "Unknown job id."}
    return {"status": job["status"], "stage": job["stage"],
            "result": job["result"], "error": job["error"]}


@app.post("/api/chat")
def chat(job_id: str = Form(...), question: str = Form(...)):
    job = jobs.get(job_id)
    chain = job.get("rag_chain") if job else None
    if chain is None:
        return {"answer": "Chat needs a finished analysis for this session."}
    try:
        return {"answer": str(ask_question(chain, question))}
    except Exception as e:  # noqa: BLE001
        return {"answer": f"Sorry, I couldn't answer that. ({type(e).__name__})"}


# Serve the frontend LAST — this is the catch-all route.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
