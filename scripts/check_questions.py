#!/usr/bin/env python3
"""Validate one extracted paper (docs/question-extraction-spec.md, v3 fields) without
touching questions.db, so extraction agents can self-check in parallel.

    .venv/bin/python scripts/check_questions.py IAL2018_WST01_Jan2020     # _staging/ file
    .venv/bin/python scripts/check_questions.py --final P3_June2019_stats # questions/ file

Checks:
- file shape and paper-level fields (qualification, unit, component, status, paper_total);
- question ids are <paper_id>_Q<n>, numbers are 1..N with none missing;
- part labels are valid and unique; part marks sum to each question's total_marks;
  question totals sum to paper_total;
- against the question paper's own text (when it has a text layer): every
  "(Total for Question N is M marks)" matches, and "TOTAL FOR PAPER IS T MARKS";
- question_text / mark_scheme_text are exactly derived from stem + parts;
- every part has spec_refs from data/processed/spec_9ma0.json, or (legacy papers only)
  an out_of_spec entry with reason + technique;
- every $...$ span renders in KaTeX (via scripts/check_notation.js --file);
- no transcription asides ("wait", "hmm", "actually,") in any text.
"""
import json
import re
from collections import Counter
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
SPEC = PROC / "spec_9ma0.json"
LABEL_RE = re.compile(r"^(?:[a-h](?:\((?:i|ii|iii|iv|v|vi)\))?|(?:i|ii|iii|iv|v|vi)(?:\([a-h]\))?)$")
ASIDE_RE = re.compile(r"\b(wait|hmm+|actually,)\b", re.I)
QUALS = {"9MA0", "IAL-2018", "IAL-2013", "GCE-2008"}
COMPONENTS = {"pure", "stats", "mech"}


EXPECTED_TOTALS = {"9MA0": {50, 100}, "IAL-2018": {75, 125}, "IAL-2013": {75, 125}, "GCE-2008": {72, 73, 74, 75}}
UNICODE_MATH = re.compile(r"[√≤≥≠±×÷θπμσλαβ∫∑²³⁻¹½¼¾→∈ℝ]")
# M1, A1, B2, dM1, ddM1, dddM1, and Pearson's occasional "M(A)1" (a second A mark printed as M(A)1).
MARK_CODE = re.compile(r"(?<![A-Za-z])(?:[abc](?=[dD]?[MAB]\d))?(?:[dD]{1,3})?(M\(A\)|[MAB])(\d)(?![\d])")  # GCE "aM1"/"bA1" = method a/b
LABEL_ORDER = "abcdefgh"


# Common words as they come out of a font pdftotext can't map: every letter shifted by 29 code points
# ("the" -> "WKH", "and" -> "DQG"), with digits lost. A few of these mean part of the page is unreadable.
SHIFTED_WORDS = re.compile(r"\b(?:WKH|DQG|ZLWK|IRU|WKDW|IURP|ZKHUH|YDOXH|ILQG|VKRZ|JLYHQ|FXUYH)\b")


def usable_text(t: str) -> bool:
    """False for scanned PDFs (no text layer) and for fonts pdftotext can't map (shifted glyphs, no
    digits), even when only part of the paper is affected."""
    if len(SHIFTED_WORDS.findall(t)) >= 3:
        return False
    words = re.findall(r"[A-Za-z]+", t)
    common = sum(w.lower() in ("the", "and", "of", "question", "marks", "is") for w in words)
    return len(t) > 2000 and common > 0.02 * max(1, len(words))


def decode_shifted(t: str) -> str:
    """Undo pdftotext's 29-code-point shift for the affected font: any token containing a shifted control
    character (a shifted space is \x03, a shifted digit '4' is \x17) is shifted back whole. This recovers
    words, spaces AND digits (measured on IAL2018_WMA12_Oct2019: 'Find the first 4 terms, in ascending…')."""
    def fix(m):
        tok = m.group(0)
        if re.search(r"[\x03-\x1f]", tok):
            return "".join(chr(ord(c) + 29) if 3 <= ord(c) <= 93 else c for c in tok)
        return tok
    # The same font maps the "fi" ligature to "¿" (IAL2013_WST01_Jan2015: "signi¿cant ¿gures", "¿nd")
    t = re.sub(r"[^ \n\f]+", fix, t).replace("¿", "fi")
    # Punctuation in this font is shifted the other way (+29): "(" -> E, ")" -> F, "," -> I, "." -> K, so
    # "(Solutions ... acceptable)." reads "ESolutions ... acceptableKF" (GCE C3 June 2016). Undo it only where
    # the capitals are glued to a lowercase word, which real English doesn't do.
    back = {"E": "(", "F": ")", "I": ",", "K": "."}
    t = re.sub(r"(?<=[a-z])[EFIK]{1,3}\b", lambda m: "".join(back[c] for c in m.group(0)), t)
    return re.sub(r"(?<![A-Za-z])E(?=[A-Z][a-z]{2,})", "(", t)


# Text a model writes when it did NOT transcribe but made something up: always a hard failure.
FABRICATION_RE = re.compile(r"reconstruct|not included in the (supplied|provided)|inferred from the mark scheme|"
                            r"could not (be )?(read|see|found)|page images?|not (shown|visible) in the (supplied|provided)", re.I)


def shifted_font(t: str) -> bool:
    """Part of the text is in a font pdftotext maps 29 code points low ('the' -> 'WKH'), losing spaces and digits."""
    return len(SHIFTED_WORDS.findall(t)) >= 3


def decoded_letter_stream(t: str) -> str:
    """For shifted-font text: decode runs of shifted characters (codes 33-93, i.e. '!'..']') and return all
    letters as one lowercase stream with no spaces (the shift also drops spaces, so words can't be
    separated). Real capitals in normal text decode to junk letters, which only makes matching looser."""
    dec = re.sub(r"[!-\]]{3,}", lambda m: "".join(chr(ord(c) + 29) for c in m.group(0)), t)
    return re.sub(r"[^a-z]", "", (t + " " + dec).lower())


def stream_gap(needle: list[str], stream: str) -> str | None:
    pos, seen = 0, []
    for w in needle:
        i = stream.find(w, pos)
        if i < 0:
            i = stream.find(w)                           # allow a jump back (captions printed elsewhere)
            if i < 0:
                return " ".join(seen[-4:]) + f" >>{w}<<"
        pos, seen = i + len(w), seen + [w]
    return None


def prose_words(t: str, source: bool = False) -> list[str]:
    """Lowercase prose words (3+ letters). For a transcription, $…$ maths is dropped first. For SOURCE text
    (a PDF text layer) it isn't: some fonts map letters to "$", and stripping between two such glyphs deleted
    whole paragraphs of reference text (GCE M1 June 2017; 29 source files contain "$")."""
    if not source:
        t = re.sub(r"\$[^$]*\$", " ", t)                   # maths garbles in pdftotext; check prose only
    t = re.sub(r"\[editor:[^\]]*\]", " ", t)
    t = re.sub(r"\\(begin|end)\{[a-z*]+\}", " ", t)            # environments (\begin{pmatrix}) outside $…$
    t = re.sub(r"\\[a-zA-Z]+", " ", t)                      # LaTeX commands outside $…$ (\textdegree, \qquad)
    t = t.replace("’", "'").replace("‘", "'").lower()
    return [w for w in re.findall(r"[a-z]{3,}", t) if not re.fullmatch(r"i{2,3}|iv|vi{1,3}", w)]   # part labels aren't prose


def subsequence_gap(needle: list[str], hay: list[str], restarts: int = 1) -> str | None:
    """None if needle's words appear in order in hay, allowing `restarts` jumps back (the QP sometimes
    prints a caption or instruction away from the text it belongs to); else the words at the miss."""
    it, seen = iter(hay), []
    for w in needle:
        if not any(w == h for h in it):
            if restarts and w in hay:
                restarts -= 1
                it = iter(hay[hay.index(w) + 1:])
                seen.append(w)
                continue
            return " ".join(seen[-4:]) + f" >>{w}<<"
        seen.append(w)
    return None


def plain_numbers(t: str) -> set[str]:
    """Decimals and integers >= 10 written in the text (inside or outside $...$), minus LaTeX noise."""
    # 44\,695.4 / 17{,}623 -> one number; but not after a decimal ("19.47,180" is a list, not 19.47180)
    t = re.sub(r"(?<![\d.])\d{1,3}(?:(?:\\,|\\ |\{,\}|,)\d{3})+(?!\d)",
               lambda m: re.sub(r"\\,|\\ |\{,\}|,", "", m.group(0)), t)
    t = re.sub(r"\\[a-zA-Z]+", " ", t)
    return {n for n in re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d])", t) if "." in n or int(float(n)) >= 10}


def num_in(n: str, hay: set[str]) -> bool:
    """n appears in the source numbers, allowing pdftotext's merged superscripts (6.8² -> '6.82', and
    two-digit powers: 2.025¹⁰ -> '2.02510', IAL C12 Jan 2015)."""
    return (any(x in hay for x in (n, n.lstrip("0"), f"0{n}"))
            or any(h.startswith(n) and len(h) in (len(n) + 1, len(n) + 2) and "." in n for h in hay)
            # integers: one merged digit at either end, the base or the power (81^{3/2} -> "812", 3^{600} -> "3600")
            or any("." not in n and len(h) == len(n) + 1 and (h.startswith(n) or h.endswith(n)) for h in hay))


def text_sentences(t: str) -> list[str]:
    """Sentences / lines of a part's text with 5+ words (maths kept, so restated equations differ by content)."""
    return [x.strip() for x in re.split(r"(?<=[.?!:])\s+|\n", t) if len(re.findall(r"[A-Za-z]{3,}", x)) >= 5]


def repeated_beyond_qp(q: dict, qp_prose: str) -> list[str]:
    """Sentences that appear in more of a question's parts than the QP prints them (the Tier 3 audit found an
    instruction copied into two parts, GCE C3 Jan 2008 Q4). Boilerplate the QP itself repeats is fine."""
    out, seen = [], set()
    for p in q["parts"]:
        for x in set(text_sentences(p.get("text", ""))):
            key = re.sub(r"\s+", "", re.sub(r"^\(?[a-z]{1,4}\)\s*", "", x.lower()))
            if key in seen:
                continue
            seen.add(key)
            n_tr = sum(any(re.sub(r"\s+", "", re.sub(r"^\(?[a-z]{1,4}\)\s*", "", y.lower())) == key
                           for y in text_sentences(pp.get("text", ""))) for pp in q["parts"])
            if n_tr > 1 and times_in(x, qp_prose) < n_tr:
                out.append(f"'{x[:60]}' is in {n_tr} parts but the QP prints it {times_in(x, qp_prose)}x")
    return out


def fraction_in_ms(a: str, b: str, lines: list[str], text: str) -> bool:
    """a/b visible in the MS text layout: a above b (stacked, centres within 4 columns, b within 3 lines) or a/b inline."""
    if re.search(rf"(?<![\d.]){a}\s*/\s*{b}(?![\d.])", text):
        return True
    ra, rb = re.compile(rf"(?<![\d.]){a}(?![\d.])"), re.compile(rf"(?<![\d.]){b}(?![\d.])")
    for i, ln in enumerate(lines):
        for m in ra.finditer(ln):
            for ln2 in lines[i + 1:i + 4]:
                if any(abs((m.start() + m.end()) / 2 - (m2.start() + m2.end()) / 2) <= 4 for m2 in rb.finditer(ln2)):
                    return True
    return False


def times_in(item: str, prose: str) -> int:
    """How often item's prose words occur, in order and contiguously, in prose (joined prose_words). An item with
    no prose (maths only) can't be counted, so it counts as unlimited."""
    w = " ".join(prose_words(item))
    return prose.count(w) if w else 10**6


def derived(q: dict) -> tuple[str, str]:
    parts = q["parts"]
    if len(parts) == 1 and parts[0]["label"] is None:
        qt = parts[0]["text"] if q.get("stem") in (None, "", parts[0]["text"]) else q["stem"] + "\n" + parts[0]["text"]
    else:
        qt = "\n".join(([q["stem"]] if q.get("stem") else []) + [p["text"] for p in parts])
    return qt, "\n".join(p["mark_scheme"] for p in parts)


def check(path: Path) -> list[str]:
    errs = []
    d = json.loads(path.read_text())
    spec_refs = {s["ref"] for s in json.loads(SPEC.read_text())["statements"]}
    pid = d.get("_paper_id")
    if pid != path.stem:
        errs.append(f"_paper_id {pid!r} must equal the filename stem {path.stem!r}")
    for k in ("_paper", "_sitting", "qualification", "unit", "component", "status", "paper_total",
              "source_qp_file", "source_ms_file"):
        if d.get(k) in (None, ""):
            errs.append(f"missing paper field {k}")
    if d.get("qualification") not in QUALS:
        errs.append(f"qualification {d.get('qualification')!r} not in {sorted(QUALS)}")
    if d.get("status") != ("current" if d.get("qualification") == "9MA0" else "legacy"):
        errs.append("status must be 'current' for 9MA0 and 'legacy' otherwise")
    qs = d.get("questions", [])
    excluded = d.get("excluded_questions", [])            # staging: triaged-out questions (marks + reasons)
    ex_file = PROC / "_excluded" / path.name
    if path.parent.name == "questions" and ex_file.exists():   # final files: dropped ones live in _excluded/
        excluded = json.loads(ex_file.read_text()).get("summary", [])
    nums = sorted([int(q["q_num"]) for q in qs] + [int(x["q_num"]) for x in excluded])
    if nums != list(range(1, len(nums) + 1)):
        errs.append(f"question numbers {nums} are not 1..{len(nums)}")

    # --- against the QP's own totals --------------------------------------------------
    qp_txt = RAW / d.get("source_qp_file", "")
    ms_txt = RAW / d.get("source_ms_file", "")
    qp_raw = qp_txt.read_text() if qp_txt.is_file() else ""
    ms_raw = ms_txt.read_text() if ms_txt.is_file() else ""
    shifted = shifted_font(qp_raw)                          # partly unmappable font: decode it, then check normally
    if shifted:
        qp_raw = decode_shifted(qp_raw)
    if shifted_font(ms_raw):
        ms_raw = decode_shifted(ms_raw)
    has_text = usable_text(qp_raw)
    qp_stream = None
    shifted = shifted and not has_text                      # decoding failed: fall back to the letter stream
    if shifted:
        has_text, qp_stream = len(qp_raw) > 2000, decoded_letter_stream(qp_raw)
    qp_words = prose_words(qp_raw, source=True) if has_text else []
    qp_prose_src = " ".join(qp_words)
    # Numbers as printed AND with thousands-separators joined ("44 695.4", "60 000e", "17,623"): the joined
    # form alone wrongly fuses neighbours ("375 187.5"), so both are accepted.
    ungroup = lambda t: re.sub(r"(?<=\d)[ \u2009\u202f,](?=\d{3}(?!\d))", "", t)
    # and digit groups after a decimal point, where the last group can be short ("−0.354 030 19", GCE 2007 MS)
    ungroup_dec = lambda t: re.sub(r"\.\d{3}(?: \d{3})*(?: \d{1,3})", lambda m: m.group(0).replace(" ", ""), t)
    # and letter-spaced digits, as some MSs print them ("1 .5 6 9 6" = 1.5696, IAL C34 Jan 2016)
    unspace = lambda t: re.sub(r"(?<=[\d.]) (?=\.?\d\b)", "", t)
    numset = lambda t: (set(re.findall(r"\d+(?:\.\d+)?", t)) | set(re.findall(r"\d+(?:\.\d+)?", ungroup(t)))
                        | set(re.findall(r"\d+(?:\.\d+)?", ungroup_dec(t)))
                        | set(re.findall(r"\d+(?:\.\d+)?", unspace(t))))
    qp_nums, ms_nums = numset(qp_raw), numset(ms_raw)
    ms_has_text = usable_text(ms_raw)
    ms_prose = " ".join(prose_words(ms_raw, source=True))
    if ms_has_text:                                    # integer fractions in the MS that the MS layout doesn't show
        ms_lines = ms_raw.split("\n")                 # (a review signal only: GCE MSs often draw fractions as graphics)
        fsus = sorted({f"{q['id'].split('_')[-1]}({p.get('label') or '-'}) {a}/{b}" for q in qs for p in q.get("parts") or []
                       for a, b in re.findall(r"\\[dt]?frac\{(\d+)\}\{(\d+)\}", p.get("mark_scheme", ""))
                       if not fraction_in_ms(a, b, ms_lines, ms_raw)})
        if fsus:
            errs.append(f"NOTICE: {len(fsus)} MS fraction(s) not visible in the MS text layout (ms_verify.py checks them "
                        f"on the page): {fsus[:8]}")
    ms_decimals_checked = ms_has_text                  # off when the MS maths is images (text layer = mark codes only)
    if ms_has_text:
        decs = [n for q in qs for p in q.get("parts") or [] for n in plain_numbers(p.get("mark_scheme", "")) if "." in n]
        gone = [n for n in decs if not num_in(n, ms_nums)]
        # GCE C3/C4 MSs of ~2011-13 draw equations as vector art with no text (pdfimages finds nothing), so many
        # true decimals are "missing". On normal MSs almost none are, so a single miss still fails there.
        if len(gone) >= 4 and len(gone) > len(decs) / 4:
            ms_decimals_checked = False
            errs.append(f"NOTICE: {len(gone)}/{len(decs)} MS decimals are not in the MS text layer (equations drawn as "
                        f"graphics), so the MS decimal check was skipped. Spot-check these on the MS PDF: {sorted(set(gone))[:12]}")
    if d.get("paper_total") not in EXPECTED_TOTALS.get(d.get("qualification"), {d.get("paper_total")}):
        errs.append(f"paper_total {d.get('paper_total')} is unusual for {d.get('qualification')} — check it")
    printed, seq_by_q = {}, {}
    if has_text:
        t = qp_txt.read_text()
        for m in re.finditer(r"\(Total for [Qq]uestion (\d+) is (\d+) marks?\)", t):
            printed[int(m.group(1))] = int(m.group(2))
        # Printed part marks, in order, per question: right-aligned "(N)" at the end of a line, between
        # the previous question's Total line and this one's. Catches split/merged parts in both directions.
        seq_by_q, prev = {}, 0
        for m in re.finditer(r"\(Total for [Qq]uestion (\d+) is \d+ marks?\)", t):
            region = t[prev:m.start()]
            seq_by_q[int(m.group(1))] = [int(x) for x in re.findall(r"(?m)(?<![\w)])\((\d{1,2})\)[ \t]*$", region)]
            prev = m.end()
        if not printed:                                    # older GCE layout: "(Total 7 marks)" in order
            printed = {i + 1: int(n) for i, n in enumerate(re.findall(r"\(Total (\d+) marks?\)", t))}
            prev = 0                                       # and the same in-order part-mark check per question
            for i, m in enumerate(re.finditer(r"\(Total \d+ marks?\)", t), 1):
                seq_by_q[i] = [int(x) for x in re.findall(r"(?m)(?<![\w)])\((\d{1,2})\)[ \t]*$", t[prev:m.start()])]
                prev = m.end()
        tp = re.findall(r"TOTAL FOR (?:PAPER|STATISTICS|MECHANICS)(?: IS|:)? (\d+) MARKS", t, re.I)
        if tp and int(tp[-1]) != d.get("paper_total"):
            errs.append(f"paper_total {d.get('paper_total')} but the QP says TOTAL FOR PAPER IS {tp[-1]} MARKS")
    total = 0
    for q in qs:
        qid = q.get("id")
        exp = f"{pid}_Q{q['q_num']}"
        if qid != exp:
            errs.append(f"{qid}: id should be {exp}")
        for k in ("qualification", "unit", "status"):
            if q.get(k) != d.get(k):
                errs.append(f"{qid}: {k} {q.get(k)!r} differs from the paper's {d.get(k)!r}")
        if q.get("component") not in COMPONENTS:
            errs.append(f"{qid}: component {q.get('component')!r} not in {sorted(COMPONENTS)}")
        if q.get("paper_id") != pid:
            errs.append(f"{qid}: paper_id must be {pid}")
        parts = q.get("parts") or []
        if not parts:
            errs.append(f"{qid}: no parts")
            continue
        labels = [p.get("label") for p in parts]
        if len(set(labels)) != len(labels):
            errs.append(f"{qid}: duplicate labels {labels}")
        if None in labels and len(parts) > 1:
            errs.append(f"{qid}: null label mixed with other parts")
        for p in parts:
            lab = p.get("label")
            if lab is not None and not LABEL_RE.match(lab):
                errs.append(f"{qid}: bad part label {lab!r} (use a, b(i), ii, ii(a))")
            if not isinstance(p.get("marks"), int) or p["marks"] <= 0:
                errs.append(f"{qid}({lab}): marks must be a positive integer")
            tlines = [ln.strip() for ln in (p.get("text") or "").rstrip().split("\n")]
            mk = [j for j, ln in enumerate(tlines) if re.fullmatch(r"\(\d+(?: marks?)?\)", ln)]
            if mk and mk[0] != len(tlines) - 1:
                errs.append(f"{qid}({lab}): text continues after its printed mark {tlines[mk[0]]}: a lead-in for the "
                            f"next part belongs there (fix_parts.py --all-leadins)")
            ms_part = p.get("mark_scheme") or ""                # ms_complete.py's block: once, no repeated lines
            if ms_part.count("Official notes (completeness pass):") > 1:
                errs.append(f"{qid}({lab}): completeness-pass block added twice")
            # whole added items ("\n- ..."), not lines: alternative methods legitimately end on the same answer line
            added = [x.strip() for x in ("\n" + ms_part.partition("Official notes (completeness pass):")[2]).split("\n- ")
                     if x.strip()]
            for item, n in Counter(added).items():            # a repeat is fine if the official MS prints it that often
                if n > 1 and ms_has_text and times_in(item, ms_prose) < n:  # (Mech: "A1: Correct equation" per equation)
                    errs.append(f"{qid}({lab}): completeness pass added {item[:50]!r} {n}x, the MS prints it fewer times")
            refs = p.get("spec_refs") or []
            bad = [r for r in refs if r not in spec_refs]
            if bad:
                errs.append(f"{qid}({lab}): unknown spec_refs {bad}")
            oos = p.get("out_of_spec")
            if oos:
                if d.get("qualification") == "9MA0":
                    errs.append(f"{qid}({lab}): 9MA0 papers are in spec by definition; remove out_of_spec")
                if not (oos.get("reason") and oos.get("technique")):
                    errs.append(f"{qid}({lab}): out_of_spec needs reason and technique")
            elif not refs:
                errs.append(f"{qid}({lab}): needs spec_refs (or an out_of_spec entry)")
            # A part is the smallest unit with its OWN printed marks, so its text must end with them,
            # e.g. "... (3)" or "... (3 marks)". Splitting "(b)(i) ... (ii) ... (3)" into two parts breaks this.
            mt = re.search(r"\((\d+)(?: marks?)?\)\s*$", p.get("text", ""))
            if not mt:
                errs.append(f"{qid}({lab}): text doesn't end with its printed marks '(N)'. If the paper prints one "
                            f"mark total for several sub-parts, they are ONE part")
            elif int(mt.group(1)) != p.get("marks"):
                errs.append(f"{qid}({lab}): text ends with ({mt.group(1)}) but marks is {p.get('marks')}")
            for f in ("text", "mark_scheme"):
                if FABRICATION_RE.search(p.get(f, "")) or FABRICATION_RE.search(q.get("stem") or ""):
                    errs.append(f"{qid}({lab}) {f}: says it was reconstructed / not read from the paper: "
                                f"{FABRICATION_RE.search(p.get(f, '') + (q.get('stem') or '')).group(0)!r}. "
                                "Transcribe from the QP, never from the mark scheme")
                if ASIDE_RE.search(p.get(f, "")):
                    errs.append(f"{qid}({lab}) {f}: transcription aside {ASIDE_RE.search(p[f]).group(0)!r}")
        # labels in paper order: a, b, c ... (sub-labels share their letter), no gaps or repeats
        letters = []
        for lab in labels:
            if lab and lab[0] in LABEL_ORDER and (not letters or letters[-1] != lab[0]):
                letters.append(lab[0])
        if letters and letters != list(LABEL_ORDER[:len(letters)]):
            errs.append(f"{qid}: part letters {letters} are not a, b, c … in order")
        comp = q.get("component")
        allrefs = [r for p in parts for r in (p.get("spec_refs") or [])]
        need = {"stats": "S", "mech": "M", "pure": "P"}.get(comp)
        if allrefs and need and not any(r.startswith(need) for r in allrefs):
            errs.append(f"{qid}: a {comp} question with no {need}-refs ({sorted(set(allrefs))})")
        if q.get("uses_large_data_set") and not (d.get("qualification") == "9MA0" and comp == "stats"):
            errs.append(f"{qid}: uses_large_data_set is only for 9MA0 statistics questions")
        for f in re.findall(r"\bFigure (\d+)\b", q.get("question_text", "")):
            if qp_stream is not None:                       # undecodable shifted font: the letter stream has no digits
                if "figure" not in qp_stream:
                    errs.append(f"{qid}: mentions Figure {f}, but the QP has no 'Figure' at all")
            elif has_text and not re.search(rf"\bFigure {f}\b", qp_raw):
                errs.append(f"{qid}: mentions Figure {f}, which is not in the QP text")
        for p in parts:
            lab = p.get("label")
            codes = (sum(int(m.group(2)) for m in MARK_CODE.finditer(p.get("mark_scheme", "")))
                     + sum(int(m.group(1)) for m in re.finditer(r"(?<![A-Za-z])[MAB]\((\d)(?:,\d)+\)", p.get("mark_scheme", ""))))
            # ^ GCE "A(2,1,0)" / "M(2,1,0)": one mark worth up to 2 (M1 Jan 2011 Q6(b))
            if codes < p.get("marks", 0) and not p.get("out_of_spec"):
                errs.append(f"{qid}({lab}): mark scheme shows mark codes worth {codes}, part is worth {p.get('marks')}")
            for f in ("text", "mark_scheme"):
                if UNICODE_MATH.search(re.sub(r"\$[^$]*\$", "", p.get(f, ""))):
                    errs.append(f"{qid}({lab}) {f}: Unicode maths {UNICODE_MATH.search(re.sub(r'\$[^$]*\$', '', p[f])).group(0)!r} outside $…$ (use LaTeX)")
            if has_text:
                gap = (stream_gap(prose_words(p.get("text", "")), qp_stream) if shifted
                       else subsequence_gap(prose_words(p.get("text", "")), qp_words))
                if gap:
                    errs.append(f"{qid}({lab}): text not verbatim vs the QP near '{gap}'")
                miss = sorted(n for n in plain_numbers(p.get("text", "")) if not num_in(n, qp_nums))
                if miss and not shifted:                  # the shifted font loses digits: can't check numbers
                    errs.append(f"{qid}({lab}): numbers {miss} in the text are not in the QP")
            if ms_decimals_checked:
                miss = sorted(n for n in plain_numbers(p.get("mark_scheme", "")) if "." in n and not num_in(n, ms_nums))
                if miss:
                    errs.append(f"{qid}({lab}): decimals {miss} in the mark scheme are not in the MS")
        s = sum(p.get("marks", 0) for p in parts)
        if s != q.get("total_marks"):
            errs.append(f"{qid}: part marks sum to {s}, total_marks is {q.get('total_marks')}")
        n = int(q["q_num"])
        if printed and printed.get(n) not in (None, q.get("total_marks")):
            errs.append(f"{qid}: total_marks {q.get('total_marks')} but the QP prints {printed[n]}")
        if printed and n not in printed:
            errs.append(f"{qid}: no '(Total for Question {n} is ...)' line in the QP text — check numbering")
        seq = seq_by_q.get(n)
        if seq and sum(seq) == q.get("total_marks") and seq != [p.get("marks") for p in parts]:
            errs.append(f"{qid}: part marks {[p.get('marks') for p in parts]} but the QP prints {seq} in order. "
                        f"One part per printed mark bracket")
        if has_text and not shifted:
            for msg in repeated_beyond_qp(q, qp_prose_src):
                errs.append(f"{qid}: {msg}: remove the extra copy")
        if len(parts) > 1 and q.get("stem"):
            for p in parts:
                first = p.get("text", "").split("\n")[0].strip()
                if len(first) >= 20 and first in q["stem"]:
                    errs.append(f"{qid}: the stem repeats part ({p.get('label')})'s text; the stem is only the preamble before (a)")
                    break
        if len(parts) == 1 and q.get("stem") and q["stem"] != parts[0].get("text"):
            st, pt = " ".join(q["stem"].split()), " ".join(parts[0].get("text", "").split())
            if len(st) > 30 and (pt.startswith(st[:60]) or st[:60] in pt):
                errs.append(f"{qid}: single-part question repeats its wording in stem and part (set stem = the part text)")
        qt, mt = derived(q)
        if q.get("question_text") != qt:
            errs.append(f"{qid}: question_text is not stem + parts joined by newlines")
        if q.get("mark_scheme_text") != mt:
            errs.append(f"{qid}: mark_scheme_text is not the parts' mark_scheme joined by newlines")
        total += q.get("total_marks") or 0
    for x in excluded:                                     # triaged-out questions: marks + reasons only
        xp = x.get("parts") or []
        if not xp or any(not (e.get("reason") and e.get("technique")) for e in xp):
            errs.append(f"excluded Q{x.get('q_num')}: every entry in parts needs label, marks, reason, technique")
        if sum(e.get("marks", 0) for e in xp) != x.get("total_marks"):
            errs.append(f"excluded Q{x.get('q_num')}: parts' marks don't sum to total_marks")
        n = int(x["q_num"])
        if printed and printed.get(n) not in (None, x.get("total_marks")):
            errs.append(f"excluded Q{n}: total_marks {x.get('total_marks')} but the QP prints {printed[n]}")
    if excluded and d.get("qualification") == "9MA0":
        errs.append("9MA0 papers never have excluded_questions")
    if printed and set(printed) - set(nums):
        errs.append(f"QP has questions {sorted(set(printed) - set(nums))} missing from the file")
    total += sum(x["total_marks"] for x in excluded)
    if total != d.get("paper_total"):
        errs.append(f"question totals sum to {total}, paper_total is {d.get('paper_total')}")

    # --- KaTeX render check ------------------------------------------------------------
    r = subprocess.run(["node", str(ROOT / "scripts" / "check_notation.js"), "--file", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        errs += [f"notation: {l}" for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()][:30]
    # Human-verified exceptions, e.g. a number the text layer dropped but the PDF page shows. Each needs
    # evidence; matching errors are reported as notices, not failures.
    for o in d.get("check_overrides", []):
        if not (o.get("match") and o.get("evidence") and o.get("verified_by")):
            errs.append(f"check_override {o} needs match, evidence and verified_by")
            continue
        hit = [e for e in errs if o["match"] in e]
        errs = [e for e in errs if e not in hit] + [f"NOTICE: overridden ({o['evidence']}): {e}" for e in hit]
    if shifted and has_text:
        errs.append("NOTICE: the QP is partly in a scrambled font: wording checked against a decoded letter stream; "
                    "numbers in that font can't be checked")
    if not has_text:
        errs.append("NOTICE: the QP has no usable text layer, so the printed-totals, mark-sequence, verbatim and "
                    "number checks were skipped. Spot-check this paper against the PDF")
    return errs


def main() -> int:
    args = sys.argv[1:]
    final = "--final" in args
    stems = [a for a in args if not a.startswith("--")]
    base = PROC / ("questions" if final else "_staging")
    if not stems:
        stems = [p.stem for p in sorted(base.glob("*.json"))]
    bad = 0
    for stem in stems:
        allmsg = check(base / f"{stem}.json")
        notices = [e for e in allmsg if e.startswith("NOTICE")]
        errs = [e for e in allmsg if not e.startswith("NOTICE")]
        for n_ in notices:
            print(f"     {stem}: {n_}")
        if errs:
            bad += 1
            print(f"FAIL {stem}: {len(errs)} problem(s)")
            for e in errs[:60]:
                print("   ", e)
        else:
            d = json.loads((base / f"{stem}.json").read_text())
            n_oos = sum(1 for q in d["questions"] if any(p.get("out_of_spec") for p in q["parts"]))
            print(f"OK   {stem}: {len(d['questions'])} questions, {d['paper_total']} marks, "
                  f"{n_oos} question(s) flagged out of spec")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
