"""Mark-code ontology and board profiles (docs/market-research-product-strategy.md §5.2).

Items store the board's rendered codes ("M1", "A1ft", "dM1", "A1*"). This module parses them into one canonical
vocabulary, so the marker, the "Be the examiner" exercises and the mark-leakage profile work in the same terms
whichever board's notation is in use, and so a new board is a profile file, not a rewrite.

    from chatbot import marks
    m = marks.parse("dM1")            # Mark(kind='DEPENDENT_METHOD', worth=1, awarded=True, ...)
    marks.parse("A0ft").awarded       # False
    marks.render(m)                   # 'dM1'
    marks.chain(["M1", "A1", "M1", "dM1", "A1*"])   # which marks each mark depends on
    marks.explain("dM1")              # our own convention text, from content/boards/<id>.json
    marks.profile().conventions["ft"]["write_to_earn"]

Canonical kinds (a superset of what any one board uses):
    METHOD, ACCURACY, INDEPENDENT, DEPENDENT_METHOD, DOUBLY_DEPENDENT_METHOD, DEPENDENT_INDEPENDENT,
    REASONING, EXPLANATION, PROCESS, COMMUNICATION, MARKING_POINT, LEVEL_BAND
Modifiers: ft (follow-through), show_that (starred), cso, cao.

Profiles live in content/boards/<id>.json; the default is edexcel-9ma0 (BOARD_PROFILE in the environment or
.env overrides it). The convention texts in a profile are our own words: never a board's marking guidance.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARDS_DIR = ROOT / "content" / "boards"
DEFAULT_PROFILE = "edexcel-9ma0"

KINDS = ("METHOD", "ACCURACY", "INDEPENDENT", "DEPENDENT_METHOD", "DOUBLY_DEPENDENT_METHOD",
         "DEPENDENT_INDEPENDENT", "REASONING", "EXPLANATION", "PROCESS", "COMMUNICATION", "MARKING_POINT",
         "LEVEL_BAND")
METHOD_KINDS = ("METHOD", "DEPENDENT_METHOD", "DOUBLY_DEPENDENT_METHOD", "PROCESS")
# The leakage profile groups kinds into what a student would recognise
FAMILY = {"METHOD": "method", "DEPENDENT_METHOD": "method", "DOUBLY_DEPENDENT_METHOD": "method", "PROCESS": "method",
          "ACCURACY": "accuracy", "INDEPENDENT": "independent", "DEPENDENT_INDEPENDENT": "independent",
          "REASONING": "reasoning", "EXPLANATION": "reasoning", "COMMUNICATION": "communication",
          "MARKING_POINT": "point", "LEVEL_BAND": "level"}


@dataclass(frozen=True)
class BoardProfile:
    id: str
    board: str
    qualification: str
    subject: str
    notation: dict
    code_pattern: re.Pattern
    dependency: dict
    conventions: dict
    answer_forms: dict
    paper_structure: dict
    legal: dict
    disclaimer: str
    bald_answer_policy: str
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def letter_to_kind(self) -> dict:
        return {v: k for k, v in self.notation.items() if k in KINDS}

    def convention(self, key: str) -> dict:
        return self.conventions.get(key) or {}


def load_profile(name: str | None = None) -> BoardProfile:
    name = name or os.environ.get("BOARD_PROFILE") or DEFAULT_PROFILE
    path = BOARDS_DIR / f"{name}.json"
    if not path.exists():
        known = sorted(p.stem for p in BOARDS_DIR.glob("*.json"))
        raise SystemExit(f"unknown board profile {name!r} (no {path}); known: {known}")
    d = json.loads(path.read_text())
    return BoardProfile(id=d["id"], board=d["board"], qualification=d["qualification"], subject=d.get("subject", ""),
                        notation=d["notation"], code_pattern=re.compile(d["code_pattern"]),
                        dependency=d.get("dependency", {}), conventions=d.get("conventions", {}),
                        answer_forms=d.get("answer_forms", {}), paper_structure=d.get("paper_structure", {}),
                        legal=d.get("legal", {}), disclaimer=d.get("disclaimer", ""),
                        bald_answer_policy=d.get("bald_answer_policy", ""), raw=d)


@lru_cache(maxsize=4)
def profile(name: str | None = None) -> BoardProfile:
    return load_profile(name)


@dataclass(frozen=True)
class Mark:
    """One mark of a scheme, or one awarded/withheld mark of a marked script."""
    kind: str               # one of KINDS
    worth: int              # marks available (the digit in M1, B2, ...)
    awarded: bool           # True for M1, False for M0 (a scheme code is written as awarded)
    ft: bool = False        # follow-through
    show_that: bool = False  # starred: the final mark of a show-that part
    cso: bool = False
    cao: bool = False
    raw: str = ""

    @property
    def family(self) -> str:
        return FAMILY.get(self.kind, "other")

    @property
    def depth(self) -> int:
        """How many earlier method marks this one depends on (dM = 1, ddM = 2)."""
        return {"DEPENDENT_METHOD": 1, "DOUBLY_DEPENDENT_METHOD": 2, "DEPENDENT_INDEPENDENT": 1}.get(self.kind, 0)

    @property
    def is_method(self) -> bool:
        return self.kind in METHOD_KINDS

    @property
    def convention_key(self) -> str:
        """The profile convention that describes this mark's letter (dM, A, B, ...)."""
        return profile().notation.get(self.kind, self.kind)

    def as_dict(self) -> dict:
        return {"code": render(self), "kind": self.kind, "family": self.family, "worth": self.worth,
                "awarded": self.awarded, "ft": self.ft, "show_that": self.show_that, "cso": self.cso, "cao": self.cao}


def parse(code: str, board: BoardProfile | None = None) -> Mark:
    """'dM1' -> dependent method, awarded; 'A0ft' -> accuracy, not awarded, follow-through. Tolerates the
    spellings a model may produce ('DM1', 'M1FT', 'A1 ft', 'A1 cso')."""
    b = board or profile()
    raw = code
    c = re.sub(r"\s+", "", code or "")
    c = re.sub(r"^DM", "dM", c)
    c = re.sub(r"(?i)ft$", "ft", c)
    c = re.sub(r"(?i)cso$", "cso", c)
    c = re.sub(r"(?i)cao$", "cao", c)
    m = b.code_pattern.match(c)
    if not m:
        raise ValueError(f"not a mark code for {b.id}: {code!r}")
    letter, digit, suffix = m.group(1), int(m.group(2)), m.group(3) or ""
    kind = b.letter_to_kind.get(letter)
    if kind is None:
        raise ValueError(f"letter {letter!r} has no canonical kind in profile {b.id}")
    # In a vector, 'M0' is "not awarded"; the scheme code itself carries the marks worth (1)
    awarded = digit > 0
    worth = digit if digit > 0 else 1
    return Mark(kind=kind, worth=worth, awarded=awarded, ft=(suffix == b.notation.get("ft_suffix", "ft")),
                show_that=(suffix == b.notation.get("show_that_suffix", "*")),
                cso=(suffix == b.notation.get("cso_suffix", "cso")), cao=(suffix == b.notation.get("cao_suffix", "cao")),
                raw=raw)


def try_parse(code: str, board: BoardProfile | None = None) -> Mark | None:
    try:
        return parse(code, board)
    except ValueError:
        return None


def render(mark: Mark, board: BoardProfile | None = None) -> str:
    b = board or profile()
    letter = b.notation.get(mark.kind, mark.kind)
    digit = mark.worth if mark.awarded else 0
    suffix = (b.notation.get("ft_suffix", "ft") if mark.ft else b.notation.get("show_that_suffix", "*") if mark.show_that
              else b.notation.get("cso_suffix", "cso") if mark.cso else b.notation.get("cao_suffix", "cao") if mark.cao else "")
    return f"{letter}{digit}{suffix}"


def withheld(code: str, board: BoardProfile | None = None) -> str:
    """The 'not awarded' spelling of a scheme code: 'A1ft' -> 'A0ft'."""
    m = parse(code, board)
    return render(Mark(m.kind, m.worth, False, m.ft, m.show_that, m.cso, m.cao), board)


def chain(codes: list[str], board: BoardProfile | None = None) -> list[dict]:
    """For each mark of a part's scheme (codes in order), which earlier marks it depends on, by position.
    A needs the nearest preceding method mark; dM needs the nearest preceding method mark; ddM the two nearest;
    B stands alone. Returns [{"code", "kind", "depends_on": [positions]}]."""
    b = board or profile()
    out, method_positions = [], []
    for i, code in enumerate(codes):
        m = parse(code, b)
        deps: list[int] = []
        if m.kind == "ACCURACY" and b.dependency.get("accuracy_needs_preceding_method", True):
            deps = method_positions[-1:]
        elif m.kind == "DEPENDENT_METHOD" and b.dependency.get("dependent_method_needs_previous_method", True):
            deps = method_positions[-1:]
        elif m.kind == "DOUBLY_DEPENDENT_METHOD":
            deps = method_positions[-2:]
        elif m.kind == "DEPENDENT_INDEPENDENT":
            deps = method_positions[-1:]
        out.append({"code": code, "kind": m.kind, "depends_on": deps})
        if m.is_method:
            method_positions.append(i)
    return out


def implied_losses(codes: list[str], awarded: list[bool], board: BoardProfile | None = None) -> list[int]:
    """Positions whose mark the dependency rules say cannot be awarded given the marks lost before them.
    Used to explain a chain ("the A1 went because the M1 before it went") and to sanity-check a marker."""
    links = chain(codes, board)
    lost = {i for i, a in enumerate(awarded) if not a}
    implied = []
    for i, link in enumerate(links):
        if link["depends_on"] and any(d in lost for d in link["depends_on"]) and not parse(codes[i], board).ft:
            implied.append(i)
    return implied


def explain(code: str, board: BoardProfile | None = None, *, part: str = "explain") -> str:
    """The convention text for a code, in our words: part = 'short' | 'explain' | 'write_to_earn'."""
    b = board or profile()
    m = parse(code, b)
    key = b.notation.get(m.kind, m.kind)
    texts = [b.convention(key).get(part, "")]
    if m.ft:
        texts.append(b.convention("ft").get(part, ""))
    if m.show_that:
        texts.append(b.convention("show_that").get(part, ""))
    if m.cso:
        texts.append(b.convention("cso").get(part, ""))
    if m.cao:
        texts.append(b.convention("cao").get(part, ""))
    return " ".join(t for t in texts if t)


def glossary(board: BoardProfile | None = None) -> list[dict]:
    """Every convention in the profile, for a 'How marks are awarded' page."""
    b = board or profile()
    return [{"key": k, **v} for k, v in b.conventions.items()]


def vector_summary(codes: list[str], awarded_codes: list[str], board: BoardProfile | None = None) -> dict:
    """Compare a scheme's codes with an awarded vector ('M1','A0',...): marks lost by family, and which losses
    the dependency rules imply from an earlier loss (so a student sees the chain, not five separate failures)."""
    b = board or profile()
    aw = [parse(c, b).awarded for c in awarded_codes]
    lost_by_family: dict[str, int] = {}
    total = earned = 0
    for code, ok in zip(codes, aw):
        m = parse(code, b)
        total += m.worth
        if ok:
            earned += m.worth
        else:
            lost_by_family[m.family] = lost_by_family.get(m.family, 0) + m.worth
    return {"total": total, "earned": earned, "lost_by_family": lost_by_family,
            "implied_positions": implied_losses(codes, aw, b), "chain": chain(codes, b)}
