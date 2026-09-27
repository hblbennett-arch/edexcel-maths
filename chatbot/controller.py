"""The conversation logic, independent of any interface.

Conversation.handle(text) returns a list of messages (plain dicts) describing what to show.
The terminal chat (chatbot/chat.py) prints them; the local web UI (chatbot/web.py) renders
them with KaTeX. Message types:

  {"type": "text", "md": ...}                         Markdown + LaTeX ($...$)
  {"type": "question", "title", "link", "stem", "parts": [text...], "figures": [page...]}
  {"type": "part_intro", "label", "marks", "how_to_start", "insights": [{quote, comment, other}]}
  {"type": "step", "label", "n", "of", "text", "marks": [...], "final_answer"}
  {"type": "list", "title", "items": [{"n", "summary", "part", "why"}]}   (picked by typing a number)
  {"type": "confirm", "md"}                           expects yes / no
  {"type": "warning", "md"}
  {"type": "actions", "options": [...]}               suggested next inputs
"""
import re
from dataclasses import dataclass, field

from . import recommend
from .identify import identify, parse_reference, summary
from .retrieve import generic_bundle, question_bundle
from .search import get_index
from .session import Session
from .tutor import explain, explain_offline, explain_topic, follow_up

PRACTICE_RE = re.compile(r"\b(give me|find me|show me|i want|can i have|suggest|recommend)\b.*\bquestions?\b|"
                         r"\bpractice\b|\bquestions? (on|about|to do with|involving|for|with)\b", re.I)
SMALL_TALK_RE = re.compile(r"^\s*(hi|hello|hey|hiya|yo|good (morning|afternoon|evening)|thanks?( you)?|cheers|ok(ay)?|"
                           r"help|what can you do\??|who are you\??)[\s!.?]*$", re.I)
ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
            "fifth": 5, "5th": 5, "last": -1}
WELCOME = ("Hi! I can help with Edexcel A Level Maths (Pure) past-paper questions. Try:\n"
           "- a question reference, e.g. *2022 paper 1 question 15*\n"
           "- pasting a question you're stuck on\n"
           "- *give me a question on integration by parts*\n"
           "- a general question, e.g. *how do I find the equation of a normal to a curve?*")
STEP_ACTIONS = ["next", "show all", "hardest", "new"]


def pick_number(msg: str, n: int) -> int | None:
    """Index into the last numbered list: "2", "#2", "number 2", "the first one",
    "give me all of 5". None if the message isn't a pick."""
    low = msg.lower().strip()
    m = re.fullmatch(r"(?:#|no\.?\s*|number\s*|option\s*|open\s*)?(\d{1,2})[.)]?", low)
    if m:
        k = int(m.group(1))
        return k - 1 if 1 <= k <= n else None
    nums = re.findall(r"(?<![\d.])\d{1,2}(?![\d.])", low)
    if len(nums) == 1 and len(low.split()) <= 8 and not re.search(r"\b20\d\d\b|\bpaper\b|\bq\s*\d", low):
        k = int(nums[0])
        if 1 <= k <= n:
            return k - 1
    for word, k in ORDINALS.items():
        if re.search(rf"\b{word}\b( one| question| suggestion)?", low) and len(low.split()) <= 12:
            return (n - 1) if k == -1 else (k - 1 if k <= n else None)
    return None


@dataclass
class Conversation:
    mode: str = "live"                      # "live" | "offline" | "dry-run"
    s: Session = field(default_factory=Session)
    pending_confirm: tuple[str, str | None, list] | None = None   # (qid, part, other candidates)

    # ---------- message builders ----------
    def _list(self, title: str, items: list[tuple[str, str | None, str]]) -> dict:
        self.s.suggestions = [(q, l) for q, l, _ in items]
        return {"type": "list", "title": title,
                "items": [{"n": i, "question_id": q, "summary": summary(q), "part": l, "why": why}
                          for i, (q, l, why) in enumerate(items, 1)]}

    def _practice_questions(self, message: str, k: int = 5) -> list[tuple[str, str | None, str]]:
        """Questions tagged with what was asked for (see recommend.find_practice), never ones
        already seen in this conversation."""
        found = recommend.find_practice(message, exclude_questions=self.s.seen | {self.s.question_id or ""}, k=k)
        return [(it["question_id"], it["part_label"], it["reason"]) for it in found["items"]]

    def _question_msg(self, qid: str) -> dict:
        b = question_bundle(qid, with_related=False)
        return {"type": "question", "question_id": qid, "title": b["summary"].split(":")[0],
                "link": b["links"]["question_paper_page"],
                "stem": b["stem"] if b["stem"] and b["parts"][0]["label"] is not None else "",
                "parts": [p["text"] for p in b["parts"]], "figures": b["figure_pages"]}

    def _part_intro(self, part: dict) -> dict:
        self.s.intros_shown.add(part["label"])
        return {"type": "part_intro", "label": part["label"], "marks": part["marks"],
                "how_to_start": part["how_to_start"],
                "insights": [{"quote": i["quote"], "comment": i["comment"],
                              "other": None if i["from_question"] == self.s.question_id else i["from_question"]}
                             for i in self.s.insights_for(part["label"])]}

    def _step(self, part: dict, step: dict, n: int) -> dict:
        return {"type": "step", "label": part["label"], "n": n, "of": len(part["steps"]), "text": step["text"],
                "marks": step["marks_awarded"],
                "final_answer": part.get("final_answer") if n == len(part["steps"]) else ""}

    def _recommendations(self, qid: str, hardest: str | None) -> dict:
        r = recommend.refocus(qid, hardest)
        items = [(st["question_id"], st["part_label"], f"{st['step']}: {st['reason']}") for st in r["ladder"]
                 if st["question_id"] not in self.s.seen]
        seen = {(q, l) for q, l, _ in items}
        for group in r["by_skill"][:3]:
            for x in group["parts"]:
                if (x["question_id"], x["part_label"]) not in seen and x["question_id"] not in self.s.seen:
                    items.append((x["question_id"], x["part_label"], f"more on {group['skill']}"))
                    seen.add((x["question_id"], x["part_label"]))
        return self._list(f"Practice{f' for part ({hardest})' if hardest else ''}, easiest first:", items[:9])

    def _hardest_options(self) -> list[str]:
        labels = [l for l in self.s.labels() if l != "-"]
        return [f"hardest {l}" for l in labels] or ["hardest"]

    # ---------- flow ----------
    def _open(self, qid: str, part_label: str | None) -> list[dict]:
        s = self.s
        s.question_id, s.reply, s.suggestions = qid, None, []
        s.seen.add(qid)
        out = [self._question_msg(qid)]
        if self.mode == "offline":
            result = explain_offline(qid)
        elif self.mode == "dry-run":
            req = explain(question_id=qid, detail=s.detail, dry_run=True).request
            n_img = sum(b["type"] == "image" for b in req["messages"][-1]["content"])
            out.append({"type": "text", "md": f"*[dry run] would call {req['model']} with the mark scheme, skills and "
                                              f"examiner notes as context ({n_img} figure image(s)).*"})
            return out + [self._recommendations(qid, part_label)]
        else:
            result = explain(question_id=qid, detail=s.detail)
        s.reply, s.history, s.part_index, s.steps_shown = result.reply, result.history, 0, {}
        s.verified, s.warnings, s.intros_shown = result.verified, result.warnings, set()
        out.append({"type": "text", "md": s.reply["intro"]})
        if s.reply["how_students_did"]:
            out.append({"type": "text", "md": f"📊 {s.reply['how_students_did']}"})
        if not s.verified:
            out.append({"type": "warning", "md": "Some checks against the official mark scheme didn't pass — treat the working with care."})
        if part_label:
            s.go_to(part_label)
        if s.detail == "tutor":
            for p in s.parts:
                out.append(self._part_intro(p))
                out += [self._step(p, st, i) for i, st in enumerate(p["steps"], 1)]
            s.reveal_all()
            out.append({"type": "text", "md": s.reply["follow_up"]})
            out.append({"type": "actions", "options": self._hardest_options() + ["new"]})
        elif s.current:
            out.append(self._part_intro(s.current))
            out.append({"type": "actions", "options": STEP_ACTIONS})
        return out

    def _start(self, message: str) -> list[dict]:
        s = self.s
        if SMALL_TALK_RE.match(message):
            return [{"type": "text", "md": WELCOME}]
        found = identify(message)
        if found.kind == "ambiguous":
            return [self._list("Which paper did you mean?", [(q, None, "") for q, _ in found.candidates])]
        if found.message and not found.question_id:
            return [{"type": "text", "md": found.message}]
        if found.kind == "generic":
            if PRACTICE_RE.search(message):
                return [self._list("Here are past-paper questions on that:", self._practice_questions(message))]
            out = []
            g = generic_bundle(message)
            if self.mode == "live":
                answer, s.history = explain_topic(message)
                out.append({"type": "text", "md": answer})
            items = []
            for sk in g["skills"]:
                items += [(e["question_id"], e["part_label"], sk["title"].lower()) for e in sk["example_parts"]]
            out.append({"type": "text", "md": "Skills: " + ", ".join(
                sk["title"] + (" *(formula in booklet)*" if sk["formula_booklet"] else "") for sk in g["skills"])})
            return out + [self._list("Practice questions for these:", items[:8])]
        if found.kind == "new_question":
            if self.mode != "live":
                return [{"type": "text", "md": "That question isn't in the past-paper database. In live mode I'd explain it "
                                               "without an official mark scheme."}]
            s.question_id = None
            result = explain(text=message, detail=s.detail)
            s.reply, s.history, s.part_index, s.steps_shown = result.reply, result.history, 0, {}
            out = [{"type": "text", "md": s.reply["intro"]}, self._part_intro(s.current),
                   {"type": "actions", "options": STEP_ACTIONS}]
            return out
        self.pending_confirm = (found.question_id, found.part_label, [c for c, _ in found.candidates[1:4]])
        return [{"type": "confirm", "md": f"Is this **{summary(found.question_id)}**?"}]

    def handle(self, text: str) -> list[dict]:
        s, msg = self.s, text.strip()
        low = msg.lower()
        if self.pending_confirm:
            qid, part, others = self.pending_confirm
            self.pending_confirm = None
            if low in ("y", "yes", "yep", "yeah", "correct", ""):
                return self._open(qid, part)
            out = [{"type": "text", "md": "OK — could you give the paper, year and question number?"}]
            if others:
                out.append(self._list("Or did you mean one of these?", [(c, None, "") for c in others]))
            if low not in ("n", "no", "nope"):
                out = self.handle(msg)  # they typed something else instead: treat it as a new message
            return out
        if low in ("/tutor", "/student"):
            s.detail = low[1:]
            return [{"type": "text", "md": f"Detail level: **{s.detail}**"}]
        pick = pick_number(msg, len(s.suggestions)) if s.suggestions else None
        if pick is not None:
            qid, label = s.suggestions[pick]
            return self._open(qid, label)
        if low == "new":
            self.s = Session(detail=s.detail, seen=s.seen)
            return [{"type": "text", "md": "Ready for another question."}]
        if not s.reply:
            return self._start(msg) if msg else []
        if low in ("", "more", "next", "m", "next step"):
            before = s.current
            part, step = s.next_step()
            if step:
                return [self._step(part, step, s.steps_shown[part["label"]])]
            if part is not None and part is not before:
                return [self._part_intro(part)]
            return [{"type": "text", "md": f"That's the whole question. {s.reply['follow_up']}"},
                    {"type": "actions", "options": self._hardest_options() + ["new"]}]
        if low == "show all":
            out = []
            for p in s.parts:
                shown = s.steps_shown.get(p["label"], 0)
                if p["label"] not in s.intros_shown:
                    out.append(self._part_intro(p))
                out += [self._step(p, st, i) for i, st in enumerate(p["steps"][shown:], shown + 1)]
            s.reveal_all()
            return out + [{"type": "text", "md": s.reply["follow_up"]},
                          {"type": "actions", "options": self._hardest_options() + ["new"]}]
        if low.startswith("part "):
            part = s.go_to(msg.split(maxsplit=1)[1].strip("() "))
            return [self._part_intro(part)] if part else [{"type": "text", "md": f"Parts are: {', '.join(s.labels())}"}]
        if low.startswith("hardest") or (s.finished() and low.strip("() ") in s.labels()):
            label = low.replace("hardest", "").strip(" ()") or None
            if s.labels() == ["-"]:
                label = None
            if label and label not in s.labels():
                return [{"type": "text", "md": f"Parts are: {', '.join(s.labels())}"}]
            s.hardest_part = label
            return [self._recommendations(s.question_id, label)] if s.question_id else []
        if parse_reference(msg) or PRACTICE_RE.search(msg):
            self.s = Session(detail=s.detail, seen=s.seen, question_id=s.question_id)
            self.s.question_id = None if parse_reference(msg) else s.question_id
            return self._start(msg)
        if self.mode != "live":
            return [{"type": "text", "md": "*(Follow-up questions need live mode.)*"}]
        answer, s.history = follow_up(s.history, msg, question_id=s.question_id)
        return [{"type": "text", "md": answer}]
