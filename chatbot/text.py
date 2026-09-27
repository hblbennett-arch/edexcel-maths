"""Plain-text versions of LaTeX question text, for keyword and semantic search.

Students paste questions as plain text ("find dy/dx when y = x^2 sqrt(x)"), so
the index is built from a plain rendering of the stored LaTeX.
"""
import re

_COMMANDS = {
    r"\sqrt": "sqrt", r"\frac": "frac", r"\pi": "pi", r"\theta": "theta", r"\alpha": "alpha",
    r"\beta": "beta", r"\lambda": "lambda", r"\mu": "mu", r"\delta": "delta", r"\infty": "infinity",
    r"\int": "integral", r"\sum": "sum", r"\ln": "ln", r"\log": "log", r"\sin": "sin", r"\cos": "cos",
    r"\tan": "tan", r"\sec": "sec", r"\csc": "cosec", r"\cot": "cot", r"\leqslant": "<=",
    r"\geqslant": ">=", r"\leq": "<=", r"\geq": ">=", r"\neq": "!=", r"\approx": "~", r"\times": "*",
    r"\pm": "+-", r"\circ": "degrees", r"\equiv": "==", r"\in": "in", r"\to": "->", r"\lim": "lim",
    r"\Rightarrow": "=>", r"\mathbb{R}": "R", r"\mathbb{Z}": "Z", r"\mathbb{N}": "N",
}


def latex_to_plain(text: str) -> str:
    """Rough plain-text rendering: good enough for matching, not for display."""
    out = text.replace("$", " ")
    for _ in range(4):  # nested fractions: innermost first
        new = re.sub(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}", r"(\1)/(\2)", out)
        if new == out:
            break
        out = new
    out = re.sub(r"\\sqrt\[(\d+)\]\{([^{}]*)\}", r"root\1(\2)", out)
    out = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt(\1)", out)
    out = re.sub(r"\\(?:mathrm|mathbf|text|operatorname|overrightarrow|left|right|dfrac|tfrac)\b", " ", out)
    for cmd, word in sorted(_COMMANDS.items(), key=lambda kv: -len(kv[0])):
        out = out.replace(cmd, f" {word} ")
    out = re.sub(r"\\[A-Za-z]+", " ", out)          # any remaining commands
    out = out.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", out).strip()


_TOKEN_RE = re.compile(r"[a-z]+|\d+(?:\.\d+)?")
_STOPWORDS = set("""a an and are as at be by for from given has have in is it its of on or that the this to
use using with where which find show hence your their what when how can you i my we our do does""".split())


def tokens(text: str) -> list[str]:
    """Lowercase word/number tokens for BM25, minus stopwords."""
    return [t for t in _TOKEN_RE.findall(latex_to_plain(text).lower()) if t not in _STOPWORDS]
