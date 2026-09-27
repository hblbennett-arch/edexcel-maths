"""Interactive tutor in the terminal (the web version is chatbot/web.py; both use
chatbot/controller.py for the conversation logic).

    .venv/bin/python -m chatbot.chat              # live: Claude via the configured backend
    .venv/bin/python -m chatbot.chat --offline    # no model: official mark scheme step by step
    .venv/bin/python -m chatbot.chat --dry-run    # no model: shows what would be sent

Type a question reference ("2022 paper 1 Q15"), paste a question, or ask a general
question. Then:
  more (or Enter)   next hint / step          show all   everything
  part b            jump to part (b)          hardest b  practise what you found hardest
  a number          open a suggestion         /tutor /student  change detail level
  new               start another question    quit       exit
  anything else: ask a follow-up question
"""
import os
import re
import sys

from . import config
from .controller import Conversation, pick_number  # noqa: F401  (pick_number re-exported for tests)

HELP = "[Enter]=next  'show all'  'part b'  'hardest b'  a number  '/tutor' '/student'  'new'  'quit'  or ask a question"


def say(text: str = "") -> None:
    print(text, flush=True)


def _plain(md: str) -> str:
    return re.sub(r"\*\*?([^*]+)\*\*?", r"\1", md)


def render(msg: dict) -> None:
    t = msg["type"]
    if t == "text":
        say(_plain(msg["md"]))
    elif t == "warning":
        say(f"⚠️  {msg['md']}")
    elif t == "confirm":
        say(f"{_plain(msg['md'])} [y/n]")
    elif t == "question":
        say(f"\n══ {msg['title']} ══   (paper: {msg['link']})")
        if msg["stem"]:
            say(msg["stem"])
        for p in msg["parts"]:
            say(p)
        if msg["figures"]:
            say("(This question has a figure — open the paper link above to see it.)")
    elif t == "part_intro":
        name = "The question" if msg["label"] == "-" else f"Part {msg['label']}"
        say(f"\n── {name} ({msg['marks']} mark{'s' if msg['marks'] != 1 else ''}) ──")
        say(f"💡 How to start: {msg['how_to_start']}")
        for ins in msg["insights"]:
            where = f" (on a similar question, {ins['other']})" if ins["other"] else ""
            say(f"⚠️  Examiners{where}: \"{ins['quote']}\"\n    → {ins['comment']}")
    elif t == "step":
        marks = f"  [{', '.join(msg['marks'])}]" if msg["marks"] else ""
        say(f"  Step {msg['n']}: {msg['text']}{marks}")
        if msg["final_answer"]:
            say(f"  ✅ Answer: {msg['final_answer']}")
    elif t == "list":
        say(msg["title"])
        for it in msg["items"]:
            say(f"  {it['n']}. {it['summary'][:95]}" + (f" — part ({it['part']})" if it["part"] else "")
                + (f"  [{it['why']}]" if it["why"] else ""))
        say("  (Type a number to open one.)")
    elif t == "actions":
        say(f"\n({HELP})")


def main() -> None:
    mode = "offline" if "--offline" in sys.argv else "dry-run" if "--dry-run" in sys.argv else "live"
    if mode == "live" and not config.has_credentials():
        say("The tutor backend isn't available: " + ("the `claude` command wasn't found." if config.BACKEND == "claude-code"
            else "no ANTHROPIC_API_KEY in .env.") + " Run with --offline or --dry-run instead.")
    conv = Conversation(mode=mode)
    say(f"A Level maths tutor ({mode} mode, model {config.MODEL}, backend {config.BACKEND}). "
        "Ask about a past-paper question, paste one, or ask a general question.")
    while True:
        try:
            msg = input("\nyou> ")
        except EOFError:
            break
        if msg.strip().lower() in ("quit", "exit", "q"):
            break
        try:
            for m in conv.handle(msg):
                render(m)
        except RuntimeError as e:  # backend failures: show and carry on
            say(f"⚠️  {e}")
    sys.stdout.flush()
    os._exit(0)  # onnxruntime can abort during interpreter teardown


if __name__ == "__main__":
    main()
