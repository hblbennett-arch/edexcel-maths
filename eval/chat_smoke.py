#!/usr/bin/env python3
"""Replays real conversations through the offline chat and checks the key behaviours.
Each case came from a bug found by hand-testing (2026-09-25). Run after changing chatbot/.

    .venv/bin/python -m eval.chat_smoke
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    ("a unit that isn't covered says so (S1/M1 only for legacy Stats/Mech)",
     "S2 June 2012 Q2\nquit\n", ["isn't in the knowledge base"]),
    ("an IAL paper with an A version asks which one",
     "IAL P1 June 2025 Q1\nquit\n", ["WMA11A", "WMA11"]),
    ("practice request lists real questions, then 'the first one' opens it with its text",
     "Can you give me a question to do with calculating arc length / area using radians\n"
     "give me the full question for the first one\nquit\n",
     ["Here are past-paper questions on that:", "[Find arc lengths (radians)", "══ "]),
    ("missing paper number asks which paper; a number picks it",
     "june 2023 q3\n1\nquit\n", ["Which paper did you mean?", "══ P1 June 2023 Q3"]),
    ("the bot's own ids are understood", "P1_June2023_Q8(a)\ny\nquit\n", ["Is this P1 June 2023 Q8"]),
    ("hardest on a single-part question gives a numbered practice path",
     "P1 June 2018 Q3\ny\nhardest a\nquit\n", ["Practice, easiest first:", "1. "]),
    ("a new reference mid-question switches question",
     "P1 June 2018 Q3\ny\njune 2022 paper 1 q15\ny\nquit\n", ["Is this P1 June 2022 Q15"]),
    ("a greeting gets the welcome message, not a topic search", "hi\nquit\n", ["I can help with Edexcel A Level Maths"]),
    ("'give me all of 5' opens suggestion 5",
     "Can you give me a question to do with calculating areas/ perimeters with radians\ngive me all of 5\nquit\n",
     ["Here are past-paper questions on that:", "══ "]),
    ("'2nd derivative test' practice opens a part that really has the test",
     "give me a question including the 2nd derivative test\n1\nquit\n",
     ["Determine the nature of a stationary point", "── Part c"]),
    ("normal-distribution hypothesis-test request lists normal mean tests, and a seen question isn't repeated",
     "Hi give me a stats question on hypothesis testing with the normal districutuon\n1\nshow all\n"
     "Okay nice, but I asked for a question with normal distribution hypothesis testing, not a binomial\nquit\n",
     ["State hypotheses for a normal mean test", "══ P3 Statistics June 2023 Q4"]),
    ("topic question hides exam-technique skills", "how do I find the equation of a normal to a curve\nquit\n",
     ["Find the equation of a normal"]),
]
FORBIDDEN = {"topic question hides exam-technique skills": ["Present a full \"show that\"", "Use a previous part"],
             "normal-distribution hypothesis-test request lists normal mean tests, and a seen question isn't repeated":
                 ["State hypotheses for a binomial test"]}
# The June 2023 Q4 must appear exactly once (opened), not again in the second list:
ONCE = {"normal-distribution hypothesis-test request lists normal mean tests, and a seen question isn't repeated":
            "P3 Statistics June 2023 Q4"}


def main() -> None:
    failed = 0
    for name, script, expect in CASES:
        out = subprocess.run([sys.executable, "-m", "chatbot.chat", "--offline"], input=script, text=True,
                             capture_output=True, cwd=ROOT, timeout=600).stdout
        missing = [e for e in expect if e not in out]
        bad = [f for f in FORBIDDEN.get(name, []) if f in out]
        once = ONCE.get(name)
        second_list = out[out.rfind("Here are past-paper questions on that:"):] if once else ""
        if once and out.count("Here are past-paper questions on that:") >= 2 and once in second_list:
            bad.append(f"'{once}' was suggested again after being done")
        ok = not missing and not bad
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name}" + (f"\n     missing: {missing}" if missing else "")
              + (f"\n     should not appear: {bad}" if bad else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    from eval import licence_gate
    licence_gate()
    main()
