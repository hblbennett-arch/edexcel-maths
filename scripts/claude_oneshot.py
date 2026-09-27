#!/usr/bin/env python3
"""One structured Claude call through `claude -p` on the user's Claude Code login (no API key).

Shared by the cheap single-call pipeline steps (extract_single.py, and later triage / notes /
tags). One call = one request/response: no agent loop, so the PDFs are paid for once instead of
being re-sent on every tool call. Claude Code reports the real cost of each call, which is logged
to logs/llm_calls.jsonl so every step's cost is measured, not estimated.

    from claude_oneshot import run, pdf_block, text_block
    out = run(system, [pdf_block(path), text_block("...")], schema=SCHEMA, model="claude-sonnet-5",
              step="extract", ref="P3_June2022_stats")
    out["result"]  # parsed JSON (schema) or text; out["cost_usd"], out["usage"]

Cache friendliness: keep `system` byte-identical across calls (it is cached for an hour and
re-read at a tenth of the price), and put per-item content after it.
"""
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "llm_calls.jsonl"
CWD = Path.home() / ".cache" / "edexcel-maths-devtools" / "claude-code-cwd"   # empty folder: no project context


def pdf_block(path: Path) -> dict:
    return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                           "data": base64.b64encode(Path(path).read_bytes()).decode()}}


def text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def run(system: str, content: list[dict], *, schema: dict | None = None, model: str = "claude-sonnet-5",
        max_usd: float = 2.0, thinking_tokens: int = 6000, step: str = "", ref: str = "",
        timeout: int = 900) -> dict:
    exe = shutil.which("claude") or str(Path.home() / ".npm-global" / "bin" / "claude")
    CWD.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
           "--model", model, "--tools", "", "--strict-mcp-config", "--no-session-persistence",
           "--max-budget-usd", str(max_usd), "--system-prompt", system]
    if schema:
        cmd += ["--json-schema", json.dumps(schema)]
    msg = {"type": "user", "message": {"role": "user", "content": content}}
    # DISABLE_PROMPT_CACHING=1: measured 2026-09-26 to cut input from ~$4 to ~$2.5 per million tokens
    # (no 1-hour cache writes) on one-shot calls, where there's little prefix to reuse anyway.
    env = dict(os.environ, MAX_THINKING_TOKENS=str(thinking_tokens), DISABLE_PROMPT_CACHING="1")
    t0 = time.time()
    proc = subprocess.run(cmd, input=json.dumps(msg) + "\n", capture_output=True, text=True,
                          cwd=CWD, timeout=timeout, env=env)
    events = [json.loads(l) for l in proc.stdout.splitlines() if l.strip().startswith("{")]
    res = next((e for e in reversed(events) if e.get("type") == "result"), None)
    record = {"step": step, "ref": ref, "model": model, "seconds": round(time.time() - t0, 1),
              "cost_usd": (res or {}).get("total_cost_usd"), "usage": (res or {}).get("usage"),
              "ok": bool(res and not res.get("is_error"))}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")
    if not record["ok"]:
        detail = (res or {}).get("result") or proc.stderr.strip()[:500] or f"exit code {proc.returncode}"
        raise RuntimeError(f"claude -p failed ({step} {ref}): {detail}")
    result = res.get("structured_output") if schema else res.get("result", "")
    if schema and result is None:
        raise RuntimeError(f"claude -p returned no structured output ({step} {ref})")
    return {"result": result, "cost_usd": record["cost_usd"], "usage": record["usage"], "seconds": record["seconds"]}
