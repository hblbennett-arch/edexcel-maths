#!/usr/bin/env node
/*
 * Render-check a batch of LaTeX spans with KaTeX (used by scripts/clean/gate_style.py, one process per item).
 *   stdin:  JSON [{"tex": "...", "display": false}, ...]
 *   stdout: JSON [null | "error message", ...]  (same order)
 * katex: the repo's node_modules, else ~/.cache/edexcel-maths-devtools/node_modules/katex
 * (npm install --prefix ~/.cache/edexcel-maths-devtools katex@0.16.9), as in scripts/check_notation.js.
 */
const path = require("path");
let katex;
try {
  katex = require("katex");
} catch {
  katex = require(path.join(require("os").homedir(), ".cache", "edexcel-maths-devtools", "node_modules", "katex"));
}
let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  const out = JSON.parse(input || "[]").map(({ tex, display }) => {
    try {
      katex.renderToString(tex, { throwOnError: true, strict: "ignore", displayMode: !!display });
      return null;
    } catch (e) {
      return e.message.split("\n")[0];
    }
  });
  process.stdout.write(JSON.stringify(out));
});
