"""The product marker: "Mark my working, explained" (docs/market-research-product-strategy.md §4.2 feature 2, §4.6).

Three separate, visible steps, so the student can trust each one:

    from chatbot import marker
    t = marker.transcribe("x^2-7x+6=0\\nx=1, 6")             # typed working -> numbered lines
    t = marker.transcribe_image(Path("photo.jpg"))            # photo -> LaTeX lines + per-line confidence,
                                                              #   needs_confirmation=True: show it to the student first
    facts = marker.final_answer_facts(item, part, t["lines"])  # deterministic sympy pre-checks (no model)
    out = marker.mark(item, "a", t, facts=facts)             # one model call, per-mark decisions
    out["decisions"]  # [{part, position, code, awarded, evidence, reason, convention, error_code, rewrite_to_earn,
                      #   confidence, overridden}], out["summary"], out["facts"], out["cost_usd"]
    events.record(user, "mark-my-working", item["id"], "a", marker.to_decisions(out, part), ...)

`part_label` None marks every part of the item (the working covers the whole question); a label marks that part
only. The system prompt lives in content/prompts/marker_system.md (our own words, loaded once, byte-identical
across calls). The only model path is scripts/claude_oneshot.run (`claude -p` on the Enterprise login).
Post-processing enforces the dependency chain (chatbot/marks.py) whatever the model returned: an awarded mark whose
chain predecessor was withheld is overridden to withheld and flagged `overridden`.
"""
from __future__ import annotations

import base64
import concurrent.futures
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "clean"))
import claude_oneshot  # noqa: E402
import gate_maths  # noqa: E402
from chatbot import marks  # noqa: E402
from chatbot.text import latex_to_plain  # noqa: E402

PROMPT_PATH = ROOT / "content" / "prompts" / "marker_system.md"
ERROR_CODES_PATH = ROOT / "content" / "error_codes.json"
BLUEPRINT_FILES = [ROOT / "content" / "blueprints" / f for f in ("exam.jsonl", "drills.jsonl", "mocks.jsonl")]
DEFAULT_MODEL = "claude-sonnet-5-5"
STEP = "marker-v2"
# Generic error codes every marking call may use, besides the item's pitfalls and the blueprint part's codes
GENERIC_CODES = ("arithmetic-slip", "premature-rounding", "wrong-final-accuracy", "not-in-required-form",
                 "decimal-not-exact", "missing-constant-of-integration")
CONVENTIONS = ("M", "A", "B", "dM", "ddM", "ft", "cso", "cao", "awrt", "oe", "isw", "show_that", "dependency",
               "bald_answer")
FACT_TIMEOUT = 4.0  # seconds per answer for the sympy pre-checks
MEDIA_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}

MARK_OBJ = {"type": "object", "properties": {
    "code": {"type": "string"},
    "evidence": {"type": "string"},
    "reason": {"type": "string"},
    "convention": {"type": "string", "enum": list(CONVENTIONS)},
    "error_code": {"type": ["string", "null"]},
    "rewrite_to_earn": {"type": ["string", "null"]},
    "confidence": {"type": "number"}},
    "required": ["code", "evidence", "reason", "convention", "error_code", "rewrite_to_earn", "confidence"]}
MARK_SCHEMA = {"type": "object", "properties": {"parts": {"type": "array", "items": {"type": "object", "properties": {
    "part": {"type": ["string", "null"]}, "marks": {"type": "array", "items": MARK_OBJ}},
    "required": ["part", "marks"]}}}, "required": ["parts"]}
TRANSCRIBE_SYSTEM = """You transcribe a photograph of a student's handwritten A level Mathematics working. Write exactly what is on
the page, line by line, in LaTeX (maths in $...$), in reading order. Do not correct, complete or simplify anything:
a wrong sign stays wrong, a crossed-out line is omitted, an unreadable symbol becomes "?" . Write every piece of
maths as LaTeX inside $...$, including integrals, limits, fractions and roots the student drew as symbols (an
integral sign from 1 to 6 is $\\int_1^6$, not the words "integral from 1 to 6"); keep only genuine words as words.
Do not add spacing macros or notation the student did not write. For each line give a confidence from 0 to 1 that
the transcription is exactly what was written."""
TRANSCRIBE_SCHEMA = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "object", "properties": {
    "text": {"type": "string"}, "confidence": {"type": "number"}}, "required": ["text", "confidence"]}}},
    "required": ["lines"]}


# ---- step 1: transcription ------------------------------------------------------------------------
def transcribe(text: str) -> dict:
    """Typed working -> {"lines": [...], "confidence": 1.0, "needs_confirmation": False}. Whitespace is
    normalised and each non-empty line becomes one numbered line; the text itself is never changed."""
    lines = []
    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line:
            lines.append(line)
    return {"lines": lines, "confidence": 1.0, "needs_confirmation": False, "source": "typed"}


def image_block(path: Path) -> dict:
    p = Path(path)
    media = MEDIA_TYPES.get(p.suffix.lower())
    if not media:
        raise ValueError(f"unsupported image type {p.suffix!r}; use one of {sorted(MEDIA_TYPES)}")
    return {"type": "image", "source": {"type": "base64", "media_type": media,
                                        "data": base64.b64encode(p.read_bytes()).decode()}}


def transcribe_image(path: Path, *, model: str = DEFAULT_MODEL, ref: str = "") -> dict:
    """Photo -> the same shape as transcribe(), with a per-line confidence and needs_confirmation=True (the
    research says transcription is the dominant error source: the student must confirm before marking)."""
    out = claude_oneshot.run(TRANSCRIBE_SYSTEM, [image_block(path), claude_oneshot.text_block(
        "Transcribe this working line by line.")], schema=TRANSCRIBE_SCHEMA, model=model, max_usd=0.5,
        thinking_tokens=2000, step=f"{STEP}-transcribe", ref=ref or Path(path).name)
    rows = [r for r in out["result"].get("lines", []) if (r.get("text") or "").strip()]
    lines = [re.sub(r"\s+", " ", r["text"]).strip() for r in rows]
    confs = [max(0.0, min(1.0, float(r.get("confidence", 0)))) for r in rows]
    return {"lines": lines, "line_confidence": confs, "confidence": round(min(confs), 3) if confs else 0.0,
            "needs_confirmation": True, "source": "image", "cost_usd": out.get("cost_usd"), "model": model}


def _lines_of(working) -> list[str]:
    if isinstance(working, dict):
        return list(working.get("lines") or [])
    return transcribe(str(working))["lines"]


def numbered(lines: list[str]) -> str:
    return "\n".join(f"L{i + 1}: {l}" for i, l in enumerate(lines))


# ---- step 2: deterministic facts ------------------------------------------------------------------
_TEX_FIXES = [(r"\\left|\\right|\\big|\\Big|\\quad|\\qquad|\\,|\\;|\\!|\\ ", " "),
              (r"\\(?:d|t)?frac(\d)(\d)", r"(\1)/(\2)"),             # \frac13 -> (1)/(3)
              (r"\\(?:d|t)?frac(\d)\{([^{}]*)\}", r"(\1)/(\2)"),
              (r"\\(?:d|t)?frac\{([^{}]*)\}(\d)", r"(\1)/(\2)"),
              (r"\\cdot", "*"), (r"\\times", "*"), (r"\^\{([^{}]*)\}", r"^(\1)"), (r"\\%", "")]
_WORD = re.compile(r"[A-Za-z]{3,}")
_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _tex_to_expr(fragment: str) -> str:
    t = fragment
    for pat, rep in _TEX_FIXES:
        t = re.sub(pat, rep, t)
    t = latex_to_plain(t)
    t = re.sub(r"\b(?:sqrt)\s+(\w+)", r"sqrt(\1)", t)
    t = t.replace("[", "(").replace("]", ")")
    return t.strip().rstrip(".,;:")


def _candidates(lines: list[str]) -> list[tuple[int, str]]:
    """(line number, plain expression) for every maths fragment and every side of an '=' in the working."""
    out = []
    for i, line in enumerate(lines, 1):
        frags = re.findall(r"\$([^$]+)\$", line) or [line]
        for frag in frags:
            plain = _tex_to_expr(frag)
            pieces = re.split(r"=>|==|=|~|<=|>=|<|>|\\Rightarrow|\bso\b|\bthen\b|\bor\b|\band\b|,", plain)
            for piece in pieces:
                p = piece.strip().strip("()") if piece.count("(") != piece.count(")") else piece.strip()
                p = re.sub(r"\b(?:as required|QED|approx|units?|cm|m|s|kg|N)\b.*$", "", p).strip().rstrip(".,;:")
                if p and len(p) <= gate_maths.MAX_LEN and not _WORD.search(re.sub(r"\b(?:sqrt|sin|cos|tan|ln|log|exp|pi|sec|cot|cosec|arcsin|arccos|arctan|abs)\b", "", p)):
                    out.append((i, p))
    return out


def _is_const(e) -> bool:
    return not getattr(e, "free_symbols", None)


def _equivalent(target, cand, degrees: bool) -> bool:
    """Exact equivalence: constants are compared numerically in this process (fast, guarded), expressions with
    symbols go through gate_maths.equal in its time-limited worker."""
    if _is_const(target) and _is_const(cand):
        return gate_maths.equal(target, cand)
    if _is_const(target) != _is_const(cand):
        return False
    errs, ok = gate_maths.run_job(("check", {"type": "equals", "lhs": str(target), "rhs": str(cand),
                                             "degrees": degrees}, {}, []))
    return ok and not errs


def _answer_facts(answer: dict, part: dict, cands: list[tuple[int, str]], degrees: bool) -> str:
    import sympy as sp
    name, expr, form = answer.get("name") or "answer", str(answer.get("expr")), answer.get("form") or ""
    target = gate_maths.parse(expr, degrees)
    exact = gate_maths.parse(answer["exact"], degrees) if answer.get("exact") else None
    label = f"{name} = {expr}" + (f" ({form})" if form else "")
    found, decimal_of, last_numeric = None, None, None
    for ln, c in cands:
        try:
            e = gate_maths.parse(c, degrees)
        except ValueError:
            continue
        if _is_const(e) and e.is_real is not False:
            last_numeric = (ln, c)
        try:
            if _equivalent(target, e, degrees):
                found = (ln, c)
                break
            if exact is not None and _is_const(e) and gate_maths.is_decimal(c) and gate_maths.matches(exact, c) is None:
                found = found or (ln, c)  # a correct rounding of the exact value, to the places written
            if exact is None and form == "exact" and _is_const(e) and _is_const(target) and gate_maths.is_decimal(c) \
                    and gate_maths.matches(target, c) is None:
                decimal_of = decimal_of or (ln, c)
        except Exception:  # sympy oddities: keep scanning
            continue
    if found:
        return f"sympy: the final answer {label} appears (line {found[0]}: {found[1]})"
    if decimal_of:
        return (f"sympy: no exact expression equivalent to {label} found; {decimal_of[1]} (line {decimal_of[0]}) is its "
                f"decimal value, so the exact form is not shown")
    tail = f"; last numeric value seen {last_numeric[1]} (line {last_numeric[0]})" if last_numeric else "; no numeric value seen"
    return f"sympy: no expression equivalent to {label} found{tail}"


def final_answer_facts(item: dict, part: dict, lines: list[str]) -> list[str]:
    """Deterministic pre-checks: for each expected answer of `part`, is an equivalent expression in the working?
    Never raises: a sympy failure or time-out becomes an 'inconclusive' fact."""
    answers = part.get("answers") or []
    if not answers:
        return []
    degrees = any(bool(a.get("degrees")) for a in answers) or any(bool(c.get("degrees")) for c in part.get("checks") or [])
    try:
        cands = _candidates(list(lines or []))
    except Exception as ex:
        return [f"sympy: check inconclusive (could not read the working: {type(ex).__name__})"]
    facts = []
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        for a in answers:
            label = f"{a.get('name') or 'answer'} = {a.get('expr')}"
            fut = pool.submit(_answer_facts, a, part, cands, degrees)
            try:
                facts.append(fut.result(timeout=FACT_TIMEOUT))
            except concurrent.futures.TimeoutError:
                facts.append(f"sympy: check for {label} inconclusive (timed out)")
            except Exception as ex:
                facts.append(f"sympy: check for {label} inconclusive ({type(ex).__name__})")
    finally:
        pool.shutdown(wait=False)
    return facts


# ---- step 3: the marking call -----------------------------------------------------------------------
@lru_cache(maxsize=1)
def system_prompt() -> str:
    return PROMPT_PATH.read_text()


@lru_cache(maxsize=1)
def _blueprints() -> dict:
    bps = {}
    for f in BLUEPRINT_FILES:
        if f.exists():
            for line in f.read_text().splitlines():
                if line.strip():
                    bp = json.loads(line)
                    bps[bp["id"]] = bp
    return bps


@lru_cache(maxsize=1)
def _generic_codes() -> list[str]:
    d = json.loads(ERROR_CODES_PATH.read_text())
    star = [c["id"] for c in d.get("codes", []) if "*" in (c.get("groups") or [])]
    return list(dict.fromkeys(list(GENERIC_CODES) + star))


@lru_cache(maxsize=1)
def _code_definitions() -> dict:
    d = json.loads(ERROR_CODES_PATH.read_text())
    return {c["id"]: c.get("definition", "") for c in d.get("codes", [])}


def norm_label(label) -> str:
    t = re.sub(r"(?i)^part\s*", "", str(label or "-"))
    return re.sub(r"[()\s]", "", t).lower() or "-"


def select_parts(item: dict, part_label) -> list[dict]:
    if part_label is None or part_label == "all":
        return list(item["parts"])
    want = norm_label(part_label)
    parts = [p for p in item["parts"] if norm_label(p.get("label")) == want]
    if not parts:
        raise ValueError(f"item {item.get('id')} has no part {part_label!r}")
    return parts


def candidate_error_codes(item: dict, parts: list[dict]) -> list[str]:
    """Pitfall codes of the item, the blueprint parts' codes, then the generic set (deduplicated, in that order)."""
    codes = [pf.get("error_code") for pf in item.get("pitfalls") or [] if pf.get("error_code")]
    bp = _blueprints().get(item.get("blueprint_id"))
    labels = {norm_label(p.get("label")) for p in parts}
    for bpp in (bp or {}).get("parts", []):
        if norm_label(bpp.get("label")) in labels:
            codes += [e["code"] for e in bpp.get("error_codes", []) if e.get("code")]
    codes += _generic_codes()
    return list(dict.fromkeys(codes))


def scheme_text(parts: list[dict]) -> str:
    lines = []
    for p in parts:
        lines.append(f"Part {p.get('label') or '-'} ({p['marks']} marks; command: {p.get('command') or '-'}"
                     + (f"; answer forms: {', '.join(p['forms'])}" if p.get("forms") else "") + ")")
        for i, m in enumerate(p["mark_scheme"], 1):
            extra = []
            if m.get("notes"):
                extra.append(m["notes"])
            if m.get("depends_on"):
                extra.append(f"depends on {m['depends_on']}")
            if m.get("ft_of"):
                extra.append(f"ft: {m['ft_of']}")
            lines.append(f"  {i}. {m['code']}: {m['for']}" + (f" [{' | '.join(extra)}]" if extra else ""))
        for alt in p.get("alternatives") or []:
            lines.append(f"  {alt.get('name', 'Alternative method')} (same positions as the main scheme):")
            for i, m in enumerate(alt.get("marks", []), 1):
                lines.append(f"    {i}. {m['code']}: {m['for']}" + (f" [{m['notes']}]" if m.get("notes") else ""))
    return "\n".join(lines)


def question_text(item: dict) -> str:
    lines = [item.get("stem") or ""] + [(f"({p['label']}) " if p.get("label") else "") + p["text"] for p in item["parts"]]
    return "\n\n".join(l for l in lines if l)


def user_message(item: dict, parts: list[dict], lines: list[str], facts: list[str], codes: list[str]) -> str:
    which = ", ".join(str(p.get("label") or "-") for p in parts)
    defs = _code_definitions()
    code_lines = "\n".join(f"- {c}: {defs.get(c, '')}".rstrip(": ") for c in codes)
    return (f"# Question\n{question_text(item)}\n\n# Mark the part(s): {which}\n\n# Mark scheme\n{scheme_text(parts)}\n\n"
            f"# Student's working (numbered lines)\n{numbered(lines) or '(no working)'}\n\n"
            f"# Sympy facts\n{chr(10).join('- ' + f for f in facts) if facts else '- none'}\n\n"
            f"# Candidate error codes\n{code_lines}\n\n"
            f"Return one object per scheme mark for each part listed, in scheme order.")


def _awarded(code: str) -> bool | None:
    m = marks.try_parse(code)
    return None if m is None else m.awarded


def _align(scheme_codes: list[str], returned: list[dict]) -> list[dict]:
    """Model marks by position against the scheme's codes; missing positions become low-confidence withheld."""
    out = []
    for i, sc in enumerate(scheme_codes):
        r = returned[i] if i < len(returned) else None
        aw = _awarded(r["code"]) if r else None
        if r is None or aw is None:
            out.append({"scheme_code": sc, "awarded": False, "evidence": "none",
                        "reason": "the marker returned no decision for this mark" if r is None else f"unreadable code {r.get('code')!r}",
                        "convention": marks.parse(sc).convention_key, "error_code": None, "rewrite_to_earn": None,
                        "confidence": 0.0, "missing": True})
            continue
        d = {"scheme_code": sc, "awarded": aw, "evidence": r.get("evidence") or "none", "reason": r.get("reason") or "",
             "convention": r.get("convention") if r.get("convention") in CONVENTIONS else marks.parse(sc).convention_key,
             "error_code": r.get("error_code") or None, "rewrite_to_earn": r.get("rewrite_to_earn") or None,
             "confidence": max(0.0, min(1.0, float(r.get("confidence") or 0)))}
        # eval 2026-09-30: 0.3% of decisions had a reason contradicting the code ("... so it should be awarded" next
        # to A0). Flag them and cap the confidence so the UI can say "check this one".
        if _contradicts(d["awarded"], d["reason"]):
            d["self_contradiction"] = True
            d["confidence"] = min(d["confidence"], 0.5)
        out.append(d)
    return out


_SAYS_AWARDED = re.compile(r"\b(should be|is|was) (awarded|earned|given)\b|\bearns? (the|this) mark\b|\bmark (is )?awarded\b", re.I)
_SAYS_WITHHELD = re.compile(r"\b(not|cannot be|can't be|isn't|is not|was not) (awarded|earned|given)\b|\bwithheld\b|\bloses? (the|this) mark\b", re.I)


def _contradicts(awarded: bool, reason: str) -> bool:
    """True when the one-line reason says the opposite of the code (a withheld mark whose reason says it is
    earned, or an awarded mark whose reason says it is lost)."""
    # Conditional phrasing ("earns the mark only if...", "would be awarded if...") describes the rule, not the
    # verdict, so it is not a contradiction (false positive seen in the 2026-09-30 smoke test).
    if _CONDITIONAL.search(reason):
        return False
    if awarded:
        return bool(_SAYS_WITHHELD.search(reason)) and not _SAYS_AWARDED.search(reason)
    return bool(_SAYS_AWARDED.search(reason)) and not _SAYS_WITHHELD.search(reason)


_CONDITIONAL = re.compile(r"\bonly if\b|\bwould\b|\bunless\b|\bif (the|they|it|a|an|no)\b|\bhad\b", re.I)


def enforce_dependencies(scheme_codes: list[str], decisions: list[dict]) -> list[dict]:
    """An awarded mark whose chain predecessor was withheld is overridden to withheld (unless it is ft)."""
    links = marks.chain(scheme_codes)
    for i, (link, d) in enumerate(zip(links, decisions)):
        d.setdefault("overridden", False)
        if not d["awarded"] or marks.parse(scheme_codes[i]).ft or not link["depends_on"]:
            continue
        lost = [decisions[j] for j in link["depends_on"] if not decisions[j]["awarded"]]
        if lost:
            before = marks.withheld(lost[0]["scheme_code"])
            d.update(awarded=False, overridden=True, convention="dependency",
                     reason=f"dependency: {before} before it was not earned",
                     rewrite_to_earn=d.get("rewrite_to_earn") or lost[0].get("rewrite_to_earn")
                     or marks.profile().convention("dependency").get("write_to_earn"),
                     error_code=d.get("error_code") or lost[0].get("error_code"))
    for d in decisions:
        d["code"] = d["scheme_code"] if d["awarded"] else marks.withheld(d["scheme_code"])
        if d["awarded"]:
            d["error_code"], d["rewrite_to_earn"] = None, None
        elif not d.get("rewrite_to_earn"):
            d["rewrite_to_earn"] = marks.explain(d["scheme_code"], part="write_to_earn") or None
    return decisions


def mark(item: dict, part_label, working, *, facts: list[str] | None = None, model: str = DEFAULT_MODEL,
         max_usd: float = 0.5, thinking_tokens: int = 4000, ref: str = "") -> dict:
    """One model call marking `working` (a string or a transcribe() dict) against the item's scheme for
    `part_label` (None = every part). Returns {"decisions", "summary", "facts", "model", "cost_usd", "vectors"}."""
    parts = select_parts(item, part_label)
    lines = _lines_of(working)
    if facts is None:
        facts = [f for p in parts for f in final_answer_facts(item, p, lines)]
    codes = candidate_error_codes(item, parts)
    out = claude_oneshot.run(system_prompt(), [claude_oneshot.text_block(user_message(item, parts, lines, facts, codes))],
                             schema=MARK_SCHEMA, model=model, max_usd=max_usd, thinking_tokens=thinking_tokens,
                             step=STEP, ref=ref or f"{item.get('id')}/{part_label or 'all'}")
    by_part = {norm_label(r.get("part")): r.get("marks", []) for r in out["result"].get("parts", [])}
    if len(parts) == 1 and len(by_part) == 1:  # a single part: accept whatever label the model used
        by_part = {norm_label(parts[0].get("label")): next(iter(by_part.values()))}
    decisions, summary, vectors, overrides = [], {}, {}, 0
    for p in parts:
        label = norm_label(p.get("label"))
        scheme_codes = [m["code"] for m in p["mark_scheme"]]
        decs = enforce_dependencies(scheme_codes, _align(scheme_codes, by_part.get(label, [])))
        overrides += sum(d["overridden"] for d in decs)
        for i, d in enumerate(decs):
            d.update(part=p.get("label"), position=i, skill=(p.get("skills") or [None])[0])
            if d["error_code"] not in codes:  # only codes from our taxonomy reach the leakage profile
                d["error_code"] = None
        vec = [d["code"] for d in decs]
        vectors[label] = vec
        summary[label] = marks.vector_summary(scheme_codes, vec)
        decisions += decs
    total = sum(s["total"] for s in summary.values())
    earned = sum(s["earned"] for s in summary.values())
    return {"decisions": decisions, "summary": summary, "vectors": vectors, "facts": facts, "model": model,
            "cost_usd": out.get("cost_usd"), "seconds": out.get("seconds"), "overrides": overrides,
            "total": total, "earned": earned, "lines": lines}


def to_decisions(result: dict, part: dict | None = None) -> list[dict]:
    """Rows for chatbot.events.record: code, kind, family, worth, awarded, error_code, skill, evidence, reason.
    With `part`, only that part's decisions (skill = the part's first skill)."""
    rows = []
    want = norm_label(part.get("label")) if part else None
    for d in result["decisions"]:
        if want is not None and norm_label(d.get("part")) != want:
            continue
        m = marks.parse(d["scheme_code"])
        rows.append({"code": d["scheme_code"], "kind": m.kind, "family": m.family, "worth": m.worth,
                     "awarded": d["awarded"], "error_code": d.get("error_code"),
                     "skill": (part.get("skills") or [None])[0] if part else d.get("skill"),
                     "evidence": d.get("evidence"), "reason": d.get("reason")})
    return rows
