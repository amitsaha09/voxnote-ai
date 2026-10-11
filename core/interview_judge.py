"""Interview evaluation: Q&A extraction + 3-judge panel + head judge + stats."""
import json
import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# If OpenAI lists the model under a different ID, change ONLY this string.
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-6-luna")


def get_llm():
    # NOTE: GPT-6 Luna does not accept a temperature parameter — don't pass it
    return ChatOpenAI(
        model=JUDGE_MODEL,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

def _parse_json(raw: str):
    """LLMs often wrap JSON in ```json fences — strip them before parsing."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        raise ValueError(f"Judge returned non-JSON output:\n{raw[:500]}")


def _fmt(ts: float) -> str:
    m, s = divmod(int(ts), 60)
    return f"{m:02d}:{s:02d}"


def format_timestamped_transcript(segments: list) -> str:
    return "\n".join(
        f"[{_fmt(s['start'])} - {_fmt(s['end'])}] {s['text']}" for s in segments
    )


def _run_chain(prompt_text: str, inputs: dict):
    chain = (
        ChatPromptTemplate.from_template(prompt_text)
        | get_llm()
        | StrOutputParser()
    )
    return _parse_json(chain.invoke(inputs))


# ---------------- Q&A extraction ----------------

def extract_qa_pairs(segments: list) -> list:
    """Find interviewer questions + candidate answers with timestamps."""
    prompt = """You are an interview analyst. Below is a timestamped transcript of a technical interview.

Transcript:
{transcript}

Identify each interviewer QUESTION and the candidate's ANSWER that follows it.
Return a JSON array. Each item:
{{
  "question": "the interviewer's question, verbatim or near-verbatim",
  "answer": "the candidate's full answer",
  "start": "MM:SS timestamp when the question was asked",
  "end": "MM:SS timestamp when the answer ended"
}}
Rules:
- Only include real Q&A exchanges. Skip greetings, small talk, introductions.
- If a question got no answer, include it with "answer": "".
- Return ONLY the JSON array, no other text."""
    result = _run_chain(prompt, {"transcript": format_timestamped_transcript(segments)})
    return result if isinstance(result, list) else []


# ---------------- The 3 judges ----------------

def judge_technical(question: str, answer: str) -> dict:
    prompt = """You are a senior technical interviewer grading a candidate's answer.

Question: {question}
Candidate's answer: {answer}

Grade ONLY technical correctness:
- "correct": technically accurate and complete
- "partially_correct": on the right track but missing key details or has minor errors
- "incorrect": technically wrong or evades the question

Return JSON: {{"verdict": "...", "score": 0-100, "explanation": "2-3 sentences: what was right, what was wrong or missing"}}
Return ONLY the JSON."""
    return _run_chain(prompt, {"question": question, "answer": answer})


def judge_communication(question: str, answer: str) -> dict:
    prompt = """You are a communication coach grading an interview answer.

Question: {question}
Candidate's answer: {answer}

Grade ONLY communication quality: clarity, structure (did they frame the answer?), conciseness (no rambling), confidence.

Return JSON: {{"score": 0-100, "explanation": "2-3 sentences on clarity, structure, and delivery"}}
Return ONLY the JSON."""
    return _run_chain(prompt, {"question": question, "answer": answer})


def judge_depth(question: str, answer: str) -> dict:
    prompt = """You are a staff engineer grading answer depth.

Question: {question}
Candidate's answer: {answer}

Grade ONLY depth: did the candidate go beyond the surface? Trade-offs? Real examples? Why, not just what?

Return JSON: {{"score": 0-100, "explanation": "2-3 sentences on depth vs superficiality"}}
Return ONLY the JSON."""
    return _run_chain(prompt, {"question": question, "answer": answer})


# ---------------- Head judge ----------------

def head_judge(question: str, answer: str, technical: dict, communication: dict, depth: dict) -> dict:
    prompt = """You are the head judge of an interview panel. Three specialists scored one answer:

Technical: {technical}
Communication: {communication}
Depth: {depth}

Question: {question}
Answer: {answer}

Give the FINAL verdict:
- verdict: "correct" | "partially_correct" | "incorrect" (weight technical most, but downgrade if communication/depth reveal shallow understanding)
- overall_score: 0-100 (weighted: 50% technical, 25% communication, 25% depth)
- summary: 2-3 sentences the candidate can act on

Return JSON: {{"verdict": "...", "overall_score": 0-100, "summary": "..."}}
Return ONLY the JSON."""
    return _run_chain(prompt, {
        "question": question, "answer": answer,
        "technical": json.dumps(technical),
        "communication": json.dumps(communication),
        "depth": json.dumps(depth),
    })


# ---------------- Statistics ----------------

def calculate_statistics(results: list) -> dict:
    total = len(results)
    if total == 0:
        return {"total_questions": 0}
    counts = {"correct": 0, "partially_correct": 0, "incorrect": 0}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    avg = lambda k: round(sum(r[k] for r in results) / total, 1)
    ranked = sorted(results, key=lambda r: r["overall_score"])
    return {
        "total_questions": total,
        "correct": counts["correct"],
        "partially_correct": counts["partially_correct"],
        "incorrect": counts["incorrect"],
        "accuracy_pct": round(counts["correct"] / total * 100, 1),
        "avg_score": avg("overall_score"),
        "avg_technical": avg("technical_score"),
        "avg_communication": avg("communication_score"),
        "avg_depth": avg("depth_score"),
        # weakest 2 and strongest 2 — no extra LLM call, just ranked scores
        "weaknesses": [r["question"][:80] for r in ranked[:2]],
        "strengths": [r["question"][:80] for r in ranked[-2:]][::-1],
    }


# ---------------- Orchestrator ----------------

def evaluate_interview(segments: list) -> dict:
    """Full pipeline: extract Q&A → 3 judges per question → head judge → stats."""
    qa_pairs = extract_qa_pairs(segments)
    print(f"Found {len(qa_pairs)} Q&A pairs. Judging...")
    results = []
    for i, qa in enumerate(qa_pairs):
        print(f"  Judging Q&A {i + 1}/{len(qa_pairs)}...")
        q, a = qa.get("question", ""), qa.get("answer", "")
        technical = judge_technical(q, a)
        communication = judge_communication(q, a)
        depth = judge_depth(q, a)
        final = head_judge(q, a, technical, communication, depth)
        results.append({
            "question": q, "answer": a,
            "start": qa.get("start", ""), "end": qa.get("end", ""),
            "technical": technical, "communication": communication, "depth": depth,
            "technical_score": technical.get("score", 0),
            "communication_score": communication.get("score", 0),
            "depth_score": depth.get("score", 0),
            "verdict": final.get("verdict", "incorrect"),
            "overall_score": final.get("overall_score", 0),
            "summary": final.get("summary", ""),
        })
    return {"qa_results": results, "statistics": calculate_statistics(results)}
