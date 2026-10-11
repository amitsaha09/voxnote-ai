"""Pre-interview prep: resume + JD -> tailored questions; GitHub -> profile score."""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-6-luna")


def _get_llm():
    # NOTE: GPT-6 Luna does not accept a temperature parameter — don't pass it
    return ChatOpenAI(model=JUDGE_MODEL, api_key=os.getenv("OPENAI_API_KEY"))


def _parse_json(raw: str):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    return json.loads(text.strip())


def extract_resume_text(pdf_path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def generate_questions(resume_text: str, jd_text: str, n: int = 10) -> list:
    """Tailored interview questions: resume deep-dives + JD requirements + behavioral."""
    prompt = """You are a senior hiring manager preparing interview questions.

Candidate resume:
{resume}

Job description:
{jd}

Write {n} interview questions tailored to THIS candidate for THIS role.
Mix resume deep-dives ("you built X — how did you handle Y?"), JD requirements,
and 2-3 behavioral questions. Order easy -> hard.
Return a JSON array: [{{"question": "...", "focus": "technical|behavioral|jd-fit", "based_on": "resume|jd|general", "difficulty": "easy|medium|hard"}}]
Return ONLY the JSON array."""
    chain = ChatPromptTemplate.from_template(prompt) | _get_llm() | StrOutputParser()
    out = _parse_json(chain.invoke({"resume": resume_text[:8000], "jd": jd_text[:8000], "n": n}))
    return out if isinstance(out, list) else []


def fetch_github_profile(username: str) -> dict:
    """Public GitHub data — free API, no auth needed."""
    u = requests.get(f"https://api.github.com/users/{username}", timeout=20).json()
    if u.get("message") == "Not Found":
        raise ValueError(f"GitHub user '{username}' not found.")
    repos = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100",
                         timeout=20).json()
    langs, stars = {}, 0
    for r in repos if isinstance(repos, list) else []:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
        stars += r.get("stargazers_count", 0)
    return {
        "username": username,
        "name": u.get("name") or username,
        "bio": u.get("bio") or "",
        "public_repos": u.get("public_repos", 0),
        "followers": u.get("followers", 0),
        "top_languages": sorted(langs, key=langs.get, reverse=True)[:5],
        "total_stars": stars,
        "profile_url": u.get("html_url", ""),
    }


def judge_github(profile: dict) -> dict:
    prompt = """You are a hiring manager reviewing a candidate's GitHub profile.

Profile data:
{profile}

Score this GitHub presence for a software engineering role.
Return JSON: {{"score": 0-100, "summary": "2-3 sentences", "strengths": ["...", "..."], "gaps": ["...", "..."]}}
Return ONLY the JSON."""
    chain = ChatPromptTemplate.from_template(prompt) | _get_llm() | StrOutputParser()
    return _parse_json(chain.invoke({"profile": json.dumps(profile)}))


def build_prep(resume_path: str, jd_text: str, github_username: str = None) -> dict:
    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        raise ValueError("Could not read any text from the resume PDF.")
    result = {"questions": generate_questions(resume_text, jd_text), "github": None}
    if github_username and github_username.strip():
        profile = fetch_github_profile(github_username.strip().lstrip("@"))
        result["github"] = {"profile": profile, "judgment": judge_github(profile)}
    return result
