"""Conversation state for one student working through one question.

Holds the tutor's structured reply and what has been revealed so far, so hints and
steps can be shown one at a time without further model calls.
"""
from dataclasses import dataclass, field


@dataclass
class Session:
    question_id: str | None = None
    detail: str = "student"            # "student" (hints first, one step at a time) or "tutor" (everything)
    reply: dict | None = None
    part_index: int = 0                # current part
    steps_shown: dict[str, int] = field(default_factory=dict)  # part label -> steps revealed
    hardest_part: str | None = None
    history: list = field(default_factory=list)  # model conversation, for follow-ups
    verified: bool = True
    warnings: list[str] = field(default_factory=list)
    suggestions: list[tuple[str, str | None]] = field(default_factory=list)  # last numbered list shown
    intros_shown: set[str] = field(default_factory=set)   # parts whose hint card is already on screen
    seen: set[str] = field(default_factory=set)           # questions opened this conversation (never re-suggested)

    # --- navigation ---
    @property
    def parts(self) -> list[dict]:
        return self.reply["parts"] if self.reply else []

    @property
    def current(self) -> dict | None:
        return self.parts[self.part_index] if self.part_index < len(self.parts) else None

    def labels(self) -> list[str]:
        return [p["label"] for p in self.parts]

    def insights_for(self, label: str) -> list[dict]:
        if not self.reply:
            return []
        cited = self.reply.get("examiner_insights", self.reply.get("pitfalls", []))  # pitfalls: commercial pack
        return [i for i in cited if i["part_label"] == label]

    def next_step(self) -> tuple[dict | None, dict | None]:
        """Reveal the next step of the current part. Returns (part, step), or (next part, None)
        when the current part is finished, or (None, None) when everything is shown."""
        part = self.current
        if part is None:
            return None, None
        shown = self.steps_shown.get(part["label"], 0)
        if shown < len(part["steps"]):
            self.steps_shown[part["label"]] = shown + 1
            return part, part["steps"][shown]
        self.part_index += 1
        return self.current, None

    def go_to(self, label: str) -> dict | None:
        if label in self.labels():
            self.part_index = self.labels().index(label)
            return self.current
        return None

    def reveal_all(self) -> None:
        for p in self.parts:
            self.steps_shown[p["label"]] = len(p["steps"])
        self.part_index = len(self.parts)

    def finished(self) -> bool:
        return all(self.steps_shown.get(p["label"], 0) >= len(p["steps"]) for p in self.parts)
