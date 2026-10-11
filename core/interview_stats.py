"""Extended interview statistics, Fireflies-style.

- speaking: talk-time split + WPM per side, computed from Q&A pairs.
  NOTE: for single-file uploads this is an estimate; true per-speaker
  timing needs the dual-channel capture (mic vs loopback).
- sentiment: positive/neutral/negative % over the candidate's answers (1 LLM call)
- confidence: per-answer confidence + average (1 LLM call)
"""
import json
import os

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


def _ts_to_sec(ts: str) -> float:
    try:
        parts = str(ts).split(":")
        return int(parts[0]) * 60 + float(parts[1])
    except Exception:  # noqa: BLE001
        return 0.0


def calculate_speaking_stats(qa_results: list) -> dict:
    """Talk-time split + words-per-minute, estimated from Q&A pairs."""
    iv_words, cand_words, iv_secs, cand_secs = 0, 0, 0.0, 0.0
    for r in qa_results:
        q, a = r.get("question", ""), r.get("answer", "")
        qw, aw = len(q.split()), len(a.split())
        iv_words += qw
        cand_words += aw
        dur = max(0.0, _ts_to_sec(r.get("end", "0:00")) - _ts_to_sec(r.get("start", "0:00")))
        total_w = max(1, qw + aw)
        iv_secs += dur * qw / total_w
        cand_secs += dur * aw / total_w
    total = iv_secs + cand_secs
    return {
        "interviewer_words": iv_words,
        "candidate_words": cand_words,
        "interviewer_talk_pct": round(iv_secs / total * 100, 1) if total else 0,
        "candidate_talk_pct": round(cand_secs / total * 100, 1) if total else 0,
        "interviewer_wpm": round(iv_words / (iv_secs / 60), 1) if iv_secs else 0,
        "candidate_wpm": round(cand_words / (cand_secs / 60), 1) if cand_secs else 0,
        "note": "Estimated from Q&A pairs — true per-speaker stats need dual-channel capture.",
    }


def analyze_sentiment(qa_results: list) -> dict:
    """Positive/neutral/negative split over the candidate's answers."""
    answers = "\n\n".join(f"A{i + 1}: {r.get('answer', '')}" for i, r in enumerate(qa_results))
    if not answers.strip():
        return {"positive": 0, "neutral": 0, "negative": 0, "note": "No answers to analyze."}
    prompt = """You are analyzing the emotional tone of a job candidate's interview answers.

Answers:
{answers}

Estimate the overall sentiment split across the answers.
Return JSON: {{"positive": 0-100, "neutral": 0-100, "negative": 0-100, "note": "one sentence on the dominant tone"}}
The three numbers must sum to 100. Return ONLY the JSON."""
    chain = ChatPromptTemplate.from_template(prompt) | _get_llm() | StrOutputParser()
    out = _parse_json(chain.invoke({"answers": answers[:12000]}))
    return {
        "positive": out.get("positive", 0),
        "neutral": out.get("neutral", 0),
        "negative": out.get("negative", 0),
        "note": out.get("note", ""),
    }


def judge_confidence(qa_results: list) -> dict:
    """How confidently each answer was delivered, 0-100."""
    pairs = "\n\n".join(
        f"Q{i + 1}: {r.get('question', '')}\nA{i + 1}: {r.get('answer', '')}"
        for i, r in enumerate(qa_results)
    )
    if not pairs.strip():
        return {"average": 0, "per_question": []}
    prompt = """You are a hiring manager rating how CONFIDENTLY a candidate answered.

Q&A pairs:
{pairs}

Rate each answer's confidence 0-100: decisive language and direct answers score high;
hedging ("I guess", "maybe", "uh"), rambling, or deflecting score low.
Return JSON: {{"per_question": [0-100, ...], "average": 0-100}}
"per_question" must contain exactly {n} numbers, in order. Return ONLY the JSON."""
    chain = ChatPromptTemplate.from_template(prompt) | _get_llm() | StrOutputParser()
    out = _parse_json(chain.invoke({"pairs": pairs[:15000], "n": len(qa_results)}))
    per_q = out.get("per_question", [])
    avg = out.get("average", round(sum(per_q) / len(per_q), 1) if per_q else 0)
    return {"average": round(avg, 1), "per_question": per_q}


def build_interview_stats(qa_results: list) -> dict:
    """All extended stats in one call. Adds 2 LLM calls (sentiment + confidence)."""
    return {
        "speaking": calculate_speaking_stats(qa_results),
        "sentiment": analyze_sentiment(qa_results),
        "confidence": judge_confidence(qa_results),
    }
