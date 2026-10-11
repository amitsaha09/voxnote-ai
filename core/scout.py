"""Profile-scout agent: finds links in a resume, visits the worthwhile ones, judges each.

This is a genuine AGENT, not a chain: the links in a resume are unpredictable
(GitHub, portfolio, blog, anything), so the LLM must DECIDE which links to
visit and which tool to use for each — a fixed path can't do that.
Uses the same create_agent tool-loop pattern as the ResearchMind project.
"""
import json
import os
import re

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import tool

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-6-luna")
MAX_AGENT_STEPS = 15


def _get_llm():
    # NOTE: GPT-6 Luna does not accept a temperature parameter — don't pass it
    return ChatOpenAI(model=JUDGE_MODEL, api_key=os.getenv("OPENAI_API_KEY"))


def extract_links(resume_text: str) -> list:
    """Find URLs in resume text and classify them. Returns [{url, kind}]."""
    found = re.findall(r"https?://[^\s)>\]\"']+", resume_text)
    # bare domains without scheme, e.g. "github.com/user"
    for m in re.findall(r"(?<![/:])(github\.com/[A-Za-z0-9_-]+|linkedin\.com/in/[A-Za-z0-9_-]+)",
                        resume_text):
        if not any(m in u for u in found):
            found.append("https://" + m)
    seen, links = set(), []
    for url in found:
        url = url.rstrip(".,;")
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        kind = "other"
        if "github.com" in key:
            kind = "github"
        elif "linkedin.com" in key:
            kind = "linkedin"
        links.append({"url": url, "kind": kind})
    return links


@tool
def fetch_github(username: str) -> str:
    """Fetch a GitHub user's public profile: repos, languages, stars, bio.
    Input: just the username, e.g. 'octocat' (a full profile URL also works)."""
    username = username.strip().lstrip("@")
    if "github.com/" in username:
        username = username.split("github.com/")[-1].strip("/").split("/")[0].split("?")[0]
    u = requests.get(f"https://api.github.com/users/{username}", timeout=20).json()
    if u.get("message") == "Not Found":
        return f"GitHub user '{username}' not found."
    repos = requests.get(
        f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated",
        timeout=20).json()
    langs, stars, notable = {}, 0, []
    for r in repos if isinstance(repos, list) else []:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
        stars += r.get("stargazers_count", 0)
        if len(notable) < 8:
            notable.append(f"{r['name']}: {r.get('description') or 'no description'} "
                           f"(stars {r.get('stargazers_count', 0)}, {r.get('language')})")
    return json.dumps({
        "username": username, "name": u.get("name"), "bio": u.get("bio"),
        "public_repos": u.get("public_repos"), "followers": u.get("followers"),
        "top_languages": sorted(langs, key=langs.get, reverse=True)[:5],
        "total_stars": stars, "recent_repos": notable,
    })


@tool
def fetch_webpage(url: str) -> str:
    """Fetch a webpage and return its main text (truncated). Use for portfolios,
    personal sites, and blogs."""
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))
        if len(text) < 200:
            return f"Page fetched but contained almost no readable text ({len(text)} chars)."
        return text[:4000]
    except Exception as e:  # noqa: BLE001
        return f"Could not fetch {url}: {type(e).__name__}. The site may block scraping."


SCOUT_PROMPT = """You are a hiring manager's scout. A candidate's resume contains these links:

{links}

Your job:
1. Visit the links that reveal the candidate's professional quality: GitHub profiles
   (use fetch_github with just the username), portfolios, personal sites, blogs
   (use fetch_webpage).
2. SKIP links that aren't about the candidate (e.g. a former employer's homepage) —
   but DO visit personal and project links.
3. LinkedIn blocks scraping — don't waste tool calls on it; just note it can't be auto-reviewed.
4. For each link you visit, judge: what does it show? Quality signals or red flags?

Finish with a STRICT JSON report and nothing else:
{{"report": [{{"url": "...", "kind": "github|portfolio|blog|other", "visited": true, "judgment": "2-3 sentences", "score": 0-100}}],
 "skipped": [{{"url": "...", "reason": "..."}}],
 "overall": "2-3 sentences on the candidate's overall online presence"}}"""


def _parse_json(raw: str):
    text = raw.strip()
    if "```" in text:  # agent chatter may surround the JSON
        text = max(text.split("```"), key=len)
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text.strip())


def run_scout_agent(resume_text: str, links: list) -> dict:
    """Let the agent decide which links to visit and judge each one."""
    agent = create_agent(
        model=_get_llm(),
        tools=[fetch_github, fetch_webpage],
        system_prompt="You are a precise hiring assistant. Use tools to gather facts, "
                      "then output strict JSON and nothing else.",
    )
    link_lines = "\n".join(f"- [{l['kind']}] {l['url']}" for l in links)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": SCOUT_PROMPT.format(links=link_lines)}]},
        config={"recursion_limit": MAX_AGENT_STEPS},
    )
    final = result["messages"][-1].content
    if isinstance(final, list):  # content blocks
        final = " ".join(b.get("text", "") for b in final if isinstance(b, dict))
    try:
        return _parse_json(str(final))
    except Exception:  # noqa: BLE001
        return {"report": [], "skipped": [],
                "overall": "The scout agent did not return parseable JSON.",
                "raw": str(final)[:2000]}


def scout_resume(resume_path: str) -> dict:
    """Extract links from a resume PDF and scout them. Entry point for the server."""
    from core.prep import extract_resume_text
    text = extract_resume_text(resume_path)
    links = extract_links(text)
    if not links:
        return {"links": [], "report": [], "skipped": [],
                "overall": "No links found in the resume."}
    out = run_scout_agent(text, links)
    out["links"] = links
    return out
