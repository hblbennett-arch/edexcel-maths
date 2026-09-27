#!/usr/bin/env node
/*
 * Check LaTeX notation conversions (Phase 2e; see docs/notation-spec.md).
 *
 * Conversion agents write data/processed/_latex/<paper>_<sitting>.json:
 *   { "_paper": "P1", "_sitting": "June2022",
 *     "units": { "<question_id>|stem": "...", "<question_id>|<label>|text": "...",
 *                "<question_id>|<label>|ms": "..." } }
 * (label "-" for a single-part question). This script compares every unit with the
 * current plain-text version in data/processed/questions/<paper>_<sitting>.json and fails if:
 *   1. any $...$ span does not render with KaTeX (throwOnError), or $ signs are unbalanced;
 *   2. the multiset of numbers changed (catches dropped/altered values);
 *   3. the number of [editor: ...] markers changed;
 *   4. a part label marker like "(a)" or "(ii)" was lost;
 *   5. a unit is missing or unexpected.
 *
 *   node scripts/check_notation.js P1_June2022      # one file
 *   node scripts/check_notation.js                  # all files in data/processed/_latex/
 */
const fs = require("fs");
const path = require("path");
// Prefer the repo's devDependency; fall back to a copy installed outside the repo
// (npm install --prefix ~/.cache/edexcel-maths-devtools katex@0.16.9) when node_modules
// can't be written.
let katex;
try {
  katex = require("katex");
} catch {
  katex = require(path.join(require("os").homedir(), ".cache", "edexcel-maths-devtools", "node_modules", "katex"));
}

const ROOT = path.resolve(__dirname, "..");
const QUESTIONS_DIR = path.join(ROOT, "data", "processed", "questions");
const LATEX_DIR = path.join(ROOT, "data", "processed", "_latex");

// Numbers as written, ignoring digits inside LaTeX command names (none exist) and
// treating "0.5" and ".5" alike. Superscript/subscript braces don't matter: x^{2} -> "2".
const UNICODE_DIGITS = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7",
  "⁸": "8", "⁹": "9", "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8",
  "₉": "9", "½": " 1/2 ", "⅓": " 1/3 ", "⅔": " 2/3 ", "¼": " 1/4 ", "¾": " 3/4 ", "⅛": " 1/8 " };

function numbers(text) {
  text = text.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹₀-₉½⅓⅔¼¾⅛]/g, (c) => UNICODE_DIGITS[c] || c);
  return (text.match(/\d+(?:\.\d+)?/g) || []).map((n) => n.replace(/^0+(?=\d)/, "")).sort();
}

function mathSpans(text) {
  const spans = [];
  const re = /\$([^$]+)\$/g;
  let m;
  while ((m = re.exec(text))) spans.push(m[1]);
  return spans;
}

function labelMarkers(text) {
  text = text.replace(/\$[^$]*\$/g, " ");  // "(a)" inside maths, e.g. $g(a) > 0$, isn't a part label
  return (text.match(/(?<![A-Za-z0-9^_'])\((?:[a-h]|iv|v|i{1,3})\)/g) || []).sort();
}

function expectedUnits(questions) {
  const units = {};
  for (const q of questions) {
    // A single-part question's stem is the same text as its one part: convert it once, as the part.
    const singleSame = q.parts.length === 1 && q.parts[0].label === null && q.stem === q.parts[0].text;
    if (q.stem && !singleSame) units[`${q.id}|stem`] = q.stem;
    for (const p of q.parts) {
      const label = p.label === null ? "-" : p.label;
      units[`${q.id}|${label}|text`] = p.text;
      units[`${q.id}|${label}|ms`] = p.mark_scheme;
    }
  }
  return units;
}

function checkFile(stem) {
  const latex = JSON.parse(fs.readFileSync(path.join(LATEX_DIR, `${stem}.json`), "utf8"));
  const paper = JSON.parse(fs.readFileSync(path.join(QUESTIONS_DIR, `${latex._paper}_${latex._sitting}.json`), "utf8"));
  const before = expectedUnits(paper.questions);
  const after = latex.units;
  const errors = [];

  for (const key of Object.keys(before)) if (!(key in after)) errors.push(`${key}: missing`);
  for (const key of Object.keys(after)) if (!(key in before)) errors.push(`${key}: unexpected unit`);

  for (const [key, text] of Object.entries(after)) {
    if (!(key in before)) continue;
    if ((text.match(/\$/g) || []).length % 2) errors.push(`${key}: unbalanced $`);
    for (const span of mathSpans(text)) {
      try {
        katex.renderToString(span, { throwOnError: true, strict: "ignore" });
      } catch (e) {
        errors.push(`${key}: KaTeX error in $${span.slice(0, 60)}$ — ${e.message.split("\n")[0]}`);
      }
    }
    const nb = numbers(before[key]).join(","), na = numbers(text).join(",");
    if (nb !== na) errors.push(`${key}: numbers changed\n      before: ${nb}\n      after:  ${na}`);
    const eb = (before[key].match(/\[editor:/g) || []).length, ea = (text.match(/\[editor:/g) || []).length;
    if (eb !== ea) errors.push(`${key}: [editor:] markers ${eb} -> ${ea}`);
    const lb = labelMarkers(before[key]).join(""), la = labelMarkers(text).join("");
    if (lb !== la) errors.push(`${key}: part label markers changed ${lb} -> ${la}`);
  }
  return { stem, units: Object.keys(after).length, errors };
}

// --questions: render-check every $...$ span in the current question files (no before/after
// comparison) — use after any direct edit to data/processed/questions/.
// --file <path>: the same check on one question file anywhere (e.g. data/processed/_staging/).
if (process.argv[2] === "--questions" || process.argv[2] === "--file") {
  let bad = 0, spans = 0;
  const files = process.argv[2] === "--file"
    ? [path.resolve(process.argv[3])]
    : fs.readdirSync(QUESTIONS_DIR).filter((f) => f.endsWith(".json")).map((f) => path.join(QUESTIONS_DIR, f));
  for (const f of files) {
    for (const q of JSON.parse(fs.readFileSync(f, "utf8")).questions) {
      for (const field of ["question_text", "mark_scheme_text"]) {
        if ((q[field].match(/\$/g) || []).length % 2) { bad++; console.log(`${q.id} ${field}: unbalanced $`); }
        for (const span of mathSpans(q[field])) {
          spans++;
          try { katex.renderToString(span, { throwOnError: true, strict: "ignore" }); }
          catch (e) { bad++; console.log(`${q.id} ${field}: $${span.slice(0, 60)}$ — ${e.message.split("\n")[0]}`); }
        }
      }
    }
  }
  console.log(`${bad ? "FAIL" : "OK  "} ${spans} math span(s) across all questions, ${bad} problem(s)`);
  process.exit(bad ? 1 : 0);
}

const stems = process.argv.slice(2).length
  ? process.argv.slice(2)
  : fs.readdirSync(LATEX_DIR).filter((f) => f.endsWith(".json")).map((f) => f.replace(/\.json$/, ""));
let failed = false;
for (const stem of stems) {
  const { units, errors } = checkFile(stem);
  if (errors.length) {
    failed = true;
    console.log(`FAIL ${stem}: ${errors.length} problem(s) in ${units} unit(s)`);
    for (const e of errors.slice(0, 40)) console.log(`    ${e}`);
    if (errors.length > 40) console.log(`    ... ${errors.length - 40} more`);
  } else {
    console.log(`OK   ${stem}: ${units} unit(s)`);
  }
}
process.exit(failed ? 1 : 0);
