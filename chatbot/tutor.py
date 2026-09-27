"""Phase 5: turn retrieved material into a scaffolded, mark-labelled explanation.

explain(question_id=...)          one structured call for a question in the knowledge base
explain(text=..., new=True)       a question we don't have (no official mark scheme)
follow_up(session, message)       a free-text follow-up in the same conversation
Pass dry_run=True to get the exact request instead of calling the API (no key needed).

Cost design: one model call per question. The chat reveals the steps one at a time
from that single reply, and recommendations come from chatbot.recommend (no model call).
"""
import base64
import json
import time
from dataclasses import dataclass, field

from . import config, db
from .prompts import FOLLOW_UP_SYSTEM_SUFFIX, SYSTEM_PROMPT, TUTOR_SCHEMA, schema_for
from .retrieve import figure_images, generic_bundle, question_bundle
from .validate import validate

# Warnings serious enough to ask the model to fix its answer once before showing it.
RETRY_ON = ("mark codes", "steps award", "matches no value", "parts missing", "did not parse")


@dataclass
class TutorResult:
    reply: dict | None
    warnings: list[str] = field(default_factory=list)
    verified: bool = False
    usage: dict = field(default_factory=dict)
    request: dict | None = None      # the request that was (or would be) sent
    bundle: dict | None = None
    history: list = field(default_factory=list)  # messages so far, for follow_up()


# ---------- context ----------

def _fmt_note(n: dict, prefix: str = "") -> str:
    return f"  - [{n['id']}] ({n['kind']}{prefix}) {n['text']}"


def build_context(bundle: dict, detail: str) -> str:
    """Question-specific material for the user message. Deterministic (same input, same text)."""
    L = [f"Detail level: {detail}", "", f"# Question {bundle['summary'].split(':')[0]}"]
    if bundle["question_type"]:
        L.append(f"Question type: {bundle['question_type']['title']}")
    if bundle["stem"] and bundle["parts"][0]["label"] is not None:
        L += ["", "## Stem", bundle["stem"]]
    perf = bundle["performance"]
    if perf:
        L += ["", "## How the cohort did (examiner report)", json.dumps(perf, ensure_ascii=False)]
    for n in bundle["general_examiner_notes"]:
        L.append(_fmt_note(n))
    for p in bundle["parts"]:
        label = p["label"] or "-"
        L += ["", f"## Part {label} ({p['marks']} marks)", p["text"], "", "Official mark scheme:", p["mark_scheme"],
              "", "Skills: " + "; ".join(f"{s['title']} (booklet: {'yes' if s['formula_booklet'] else 'no'})"
                                         for s in p["skills"])]
        if p["performance"]:
            L.append("Cohort on this part: " + json.dumps(p["performance"], ensure_ascii=False))
        if p["examiner_notes"]:
            L.append("Examiner notes on this part:")
            L += [_fmt_note(n) for n in p["examiner_notes"]]
        if p["related_pitfalls"]:
            L.append("Pitfalls examiners reported on similar parts of OTHER questions:")
            L += [_fmt_note(n, f", {n['question_id']} {n['part_label']}") for n in p["related_pitfalls"]]
    if bundle["has_figure"]:
        L += ["", "The question's figure page(s) are attached as images."]
    L += ["", "Explain this question following your instructions."]
    return "\n".join(L)


def build_new_question_context(text: str, detail: str) -> tuple[str, set[str]]:
    g = generic_bundle(text)
    L = [f"Detail level: {detail}", "", "# A question that is NOT in our past-paper database",
         "There is no official mark scheme for it: label marks as 'likely ...' and say the allocation is your estimate.",
         "", "## The question", text, "", "## Skills it most likely tests"]
    for s in g["skills"]:
        L.append(f"- {s['title']} (booklet: {'yes' if s['formula_booklet'] else 'no'}): {s['description']}")
    L += ["", "## Examiner notes from similar past questions (cite only these, by note_id)"]
    L += [_fmt_note(n, f", {n['question_id']} {n.get('part_label') or ''}") for n in g["examiner_notes"]]
    L += ["", "Split your explanation into the question's parts (label '-' if it has none)."]
    return "\n".join(L), {n["id"] for n in g["examiner_notes"]}


def _allowed_notes(bundle: dict) -> set[str]:
    ids = {n["id"] for n in bundle["general_examiner_notes"]}
    for p in bundle["parts"]:
        ids |= {n["id"] for n in p["examiner_notes"]} | {n["id"] for n in p["related_pitfalls"]}
    return ids


def _images(question_id: str) -> list[dict]:
    blocks = []
    for path in figure_images(question_id):
        with open(path, "rb") as f:
            blocks.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                        "data": base64.standard_b64encode(f.read()).decode()}})
    return blocks


def _system(follow_up: bool = False) -> list[dict]:
    blocks = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
    if follow_up:
        blocks.append({"type": "text", "text": FOLLOW_UP_SYSTEM_SUFFIX})
    return blocks


def build_request(user_content: list[dict], messages_before: list[dict] | None = None, structured: bool = True,
                  schema: dict | None = None) -> dict:
    req = {
        "model": config.MODEL,
        "max_tokens": config.MAX_TOKENS,
        "system": _system(follow_up=not structured),
        "messages": (messages_before or []) + [{"role": "user", "content": user_content}],
        "output_config": {},
    }
    if config.is_haiku_45(config.MODEL):
        # Haiku 4.5: fixed thinking budget (must be < max_tokens, >= 1024); `effort` is rejected.
        req["thinking"] = {"type": "enabled", "budget_tokens": config.THINKING_BUDGET}
    else:
        req["thinking"] = {"type": "adaptive"}
        req["output_config"]["effort"] = config.EFFORT
        if config.USE_FALLBACKS:
            req["betas"] = [config.FALLBACK_BETA]
            req["fallbacks"] = "default"
    if structured:
        req["output_config"]["format"] = {"type": "json_schema", "schema": schema or TUTOR_SCHEMA}
    if not req["output_config"]:
        del req["output_config"]
    return req


# ---------- API ----------

_client = None


def _call(req: dict):
    """Send a request built by build_request() to the configured backend.
    Returns (json/text answer, usage dict, assistant content for the history)."""
    if config.BACKEND == "claude-code":
        return _call_claude_code(req)
    return _call_api(req)


def _flatten(messages: list[dict]) -> list[dict]:
    """Claude Code's scripted mode takes user turns only, so earlier turns (the tutor's previous
    answer, earlier follow-ups) are replayed as text inside one user message. Images from the
    first turn are kept."""
    if len(messages) == 1:
        return messages[0]["content"]
    blocks, transcript = [], []
    for i, m in enumerate(messages):
        content = m["content"] if isinstance(m["content"], list) else [{"type": "text", "text": str(m["content"])}]
        for b in content:
            b = b if isinstance(b, dict) else {"type": getattr(b, "type", "text"), "text": getattr(b, "text", "")}
            if b.get("type") == "image" and i == 0:
                blocks.append(b)
            elif b.get("type") == "text" and b.get("text"):
                speaker = "Student / app" if m["role"] == "user" else "Tutor (you, earlier)"
                transcript.append(f"--- {speaker} ---\n{b['text']}")
    last = transcript.pop() if messages[-1]["role"] == "user" else ""
    text = "Conversation so far:\n\n" + "\n\n".join(transcript) + "\n\n--- Now respond to this ---\n" + last.split("\n", 1)[-1]
    return blocks + [{"type": "text", "text": text}]


def _call_claude_code(req: dict):
    """Run the request through `claude -p` on the user's Claude Code login (no API key)."""
    import shutil
    import subprocess
    exe = shutil.which("claude") or str(config.Path.home() / ".npm-global" / "bin" / "claude")
    config.CLAUDE_CODE_CWD.mkdir(parents=True, exist_ok=True)
    system = "\n\n".join(b["text"] for b in req["system"])
    cmd = [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--model", req["model"], "--tools", "", "--strict-mcp-config", "--no-session-persistence",
           "--max-budget-usd", config.MAX_USD_PER_CALL, "--system-prompt", system]
    schema = req.get("output_config", {}).get("format", {}).get("schema")
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    message = {"type": "user", "message": {"role": "user", "content": _flatten(req["messages"])}}
    import os
    env = dict(os.environ, MAX_THINKING_TOKENS=str(config.THINKING_BUDGET))  # cap thinking, as on the API route
    proc = subprocess.run(cmd, input=json.dumps(message) + "\n", capture_output=True, text=True,
                          cwd=config.CLAUDE_CODE_CWD, timeout=600, env=env)
    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip().startswith("{")]
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None or result.get("is_error"):
        detail = (result or {}).get("result") or proc.stderr.strip()[:500] or f"exit code {proc.returncode}"
        raise RuntimeError(f"claude-code backend failed: {detail}")
    answer = json.dumps(result["structured_output"]) if schema else result.get("result", "")
    if schema and result.get("structured_output") is None:
        raise RuntimeError("claude-code backend returned no structured output")
    u = result.get("usage", {})
    usage = {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
             "cache_read_input_tokens": u.get("cache_read_input_tokens"),
             "cache_creation_input_tokens": u.get("cache_creation_input_tokens"),
             "cost_usd": result.get("total_cost_usd"), "backend": "claude-code"}
    return answer, usage, [{"type": "text", "text": answer}]


def _call_api(req: dict):
    global _client
    import anthropic
    import truststore
    truststore.inject_into_ssl()  # TLS-inspecting networks: verify with the macOS trust store
    if _client is None:
        _client = anthropic.Anthropic()
    api = _client.beta.messages if "betas" in req else _client.messages  # beta endpoint only when needed
    with api.stream(**req) as stream:
        response = stream.get_final_message()
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {getattr(response.stop_details, 'category', None)}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("reply was cut off (max_tokens) — raise TUTOR_MAX_TOKENS")
    text = next(b.text for b in response.content if b.type == "text")
    usage = {k: getattr(response.usage, k, None) for k in
             ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
    return text, usage, response.content


def _log(record: dict) -> None:
    config.LOG_PATH.parent.mkdir(exist_ok=True)
    with config.LOG_PATH.open("a") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def explain(question_id: str | None = None, text: str | None = None, detail: str = "student",
            dry_run: bool = False) -> TutorResult:
    """Structured explanation of a stored question (question_id) or a new one (text)."""
    if question_id:
        bundle = question_bundle(question_id)
        context, allowed = build_context(bundle, detail), _allowed_notes(bundle)
        content = _images(question_id) + [{"type": "text", "text": context}]
    else:
        bundle = None
        context, allowed = build_new_question_context(text, detail)
        content = [{"type": "text", "text": context}]
    labels = [p["label"] or "-" for p in bundle["parts"]] if bundle else None
    schema = schema_for(labels)
    req = build_request(content, schema=schema)
    if dry_run:
        return TutorResult(None, request=req, bundle=bundle)

    raw, usage, assistant_content = _call(req)
    reply = json.loads(raw)
    reply, warnings = validate(reply, question_id, allowed)
    serious = [w for w in warnings if any(k in w for k in RETRY_ON)]
    if serious:  # one targeted retry, in the same conversation
        fix = [{"type": "text", "text": "Your answer failed these checks against the official mark scheme:\n- "
                + "\n- ".join(serious) + "\nFix them and return the full answer again in the same format."}]
        retry = build_request(fix, messages_before=req["messages"] + [{"role": "assistant", "content": assistant_content}],
                              schema=schema)
        raw, usage2, assistant_content = _call(retry)
        req = dict(req, messages=retry["messages"])
        usage = {k: (usage.get(k) or 0) + (usage2.get(k) or 0) if isinstance(usage.get(k), (int, float)) or usage.get(k) is None
                 else usage[k] for k in usage}
        reply, warnings = validate(json.loads(raw), question_id, allowed)
        serious = [w for w in warnings if any(k in w for k in RETRY_ON)]
    result = TutorResult(reply, warnings, verified=not serious, usage=usage, request=req, bundle=bundle,
                         history=req["messages"] + [{"role": "assistant", "content": assistant_content}])
    _log({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": config.MODEL, "question_id": question_id,
          "text": text, "detail": detail, "verified": result.verified, "warnings": warnings,
          "usage": usage, "reply": reply})
    return result


def booklet_facts(question_id: str) -> str:
    """One line per skill in the question: is its key formula printed in the 9MA0 booklet?"""
    notes = {sk["id"]: sk.get("formula_booklet_note") for sk in
             json.loads((config.ROOT / "data" / "processed" / "tags.json").read_text())["skills"]}
    rows = db.rows("SELECT DISTINCT s.id, s.title, s.formula_booklet FROM question_tags t JOIN skills s ON s.id = t.tag_value "
                   "WHERE t.question_id = ? AND t.tag_type = 'skill' AND s.group_id != 'exam-technique'", (question_id,))
    lines = []
    for r in rows:
        if not r["formula_booklet"]:
            lines.append(f"- {r['title']}: NOT in the formula booklet (must be learnt)")
        else:
            note = notes.get(r["id"]) or ""
            lines.append(f"- {r['title']}: " + (f"PARTLY in the booklet ({note[len('partly: '):]})" if note.startswith("partly")
                                                 else f"IN the formula booklet ({note})" if note else "IN the formula booklet"))
    return "\n".join(lines)


def follow_up(history: list[dict], message: str, dry_run: bool = False,
              question_id: str | None = None) -> tuple[str, list[dict]]:
    """Free-text follow-up. `history` is the running messages list (user/assistant turns).
    With a question_id, the question's formula-booklet facts travel with the message."""
    text = message
    if question_id:
        text = f"{message}\n\n[Formula booklet facts for this question, from the official 9MA0 booklet:\n{booklet_facts(question_id)}]"
    req = build_request([{"type": "text", "text": text}], messages_before=history, structured=False)
    if dry_run:
        return f"[dry run: would send {len(req['messages'])} message(s) to {config.MODEL}]", history
    text, usage, content = _call(req)
    new_history = req["messages"] + [{"role": "assistant", "content": content}]
    _log({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": config.MODEL, "follow_up": message,
          "usage": usage, "answer": text})
    return text, new_history


# ---------- no-API modes ----------

def offline_reply(bundle: dict) -> dict:
    """A reply built only from the knowledge base (no model): the official mark scheme split
    into its marks as the steps, and the first examiner pitfall per part as insights. Used by
    `python -m chatbot.chat --offline` to test the whole chat flow without an API key."""
    import re
    parts, insights = [], []
    for p in bundle["parts"]:
        label = p["label"] or "-"
        pieces = [x.strip() for x in re.split(r"(?=\b(?:dd?M\d|M\d|A\d\*?|B\d\*?)(?:ft|cso|cao)?:)", p["mark_scheme"]) if x.strip()]
        pieces = [re.sub(r"\s*\[editor:[^\]]*\]", "", x) for x in pieces if not re.fullmatch(r"\([a-z()iv]+\)", x)]
        steps = [{"text": piece, "marks_awarded": [m.group(0).rstrip(":") for m in
                  re.finditer(r"\b(?:dd?M\d|M\d|A\d\*?|B\d\*?)(?:ft|cso|cao)?(?=:)", piece)]} for piece in pieces]
        skills = ", ".join(s["title"].lower() for s in p["skills"][:3])
        parts.append({"label": label, "marks": p["marks"],
                      "how_to_start": f"(offline preview) This part tests: {skills}.",
                      "steps": steps, "final_answer": "", "final_answer_sympy": ""})
        note = next((n for n in p["examiner_notes"] if n["kind"] == "pitfall"), None)
        if note:
            insights.append({"note_id": note["id"], "part_label": label, "comment": "(offline preview)"})
    perf = bundle["performance"]
    return {"intro": f"Offline preview of {bundle['summary']} — official mark scheme shown step by step.",
            "parts": parts, "examiner_insights": insights,
            "how_students_did": f"Mean mark {perf['mean_mark']}/{perf['max_mark']}." if perf.get("mean_mark") else "",
            "follow_up": "Which part did you find hardest?"}


def explain_offline(question_id: str) -> TutorResult:
    bundle = question_bundle(question_id)
    reply, warnings = validate(offline_reply(bundle), question_id, _allowed_notes(bundle))
    return TutorResult(reply, warnings, verified=True, bundle=bundle)


def explain_topic(text: str, dry_run: bool = False) -> tuple[str, list[dict]]:
    """A generic query ("how do I integrate x e^x?"): plain-text explanation grounded in the
    matching skills, example parts and examiner notes."""
    g = generic_bundle(text)
    ctx = ["A student asks a general question (not a specific exam question).", "", f"Question: {text}", "",
           "## Relevant skills"]
    ctx += [f"- {s['title']} (booklet: {'yes' if s['formula_booklet'] else 'no'}): {s['description']}" for s in g["skills"]]
    ctx += ["", "## Examiner notes on related past questions (quote only these, citing the note id)"]
    ctx += [_fmt_note(n, f", {n['question_id']}") for n in g["examiner_notes"]]
    ctx += ["", "Explain the method with a short worked example in the mark-scheme style, then list common mistakes."]
    return follow_up([], "\n".join(ctx), dry_run=dry_run)
