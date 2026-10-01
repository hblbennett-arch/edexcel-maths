/*
 * Interactive scene renderer (docs/learn-layer-spec.md §2, "Renderer"). Plain ES2017, no build step.
 * Needs JSXGraph 1.8.0 on the page (window.JXG); uses KaTeX (window.katex) when present.
 *
 *   var h = window.renderScene('scene-1', sceneJSON, {theme: 'auto'});
 *   h.setParam('k', 6);  h.showStep(2);  h.destroy();  h.board  (the JXG board)
 *   window.renderSceneWhenVisible('scene-1', sceneJSON, opts) -> the same handle once the container has a size
 *   (opts.onReady(handle) fires when the board exists).
 *
 * The optional scene.guide block (spec §2 "Guide") is rendered around the board: an intro line, a hint under each
 * slider, a legend with colour swatches, "How to use this", "How this links to the question" and read-off notes.
 * Every field falls back to text built from the elements, so a scene without a guide still explains itself.
 *
 * The scene JSON is model-written data: expressions are compiled by the whitelist compiler below and never
 * reach eval/new Function as raw text. Any rejected token replaces the scene by an error card.
 *
 * The section between SCENE COMPILER BEGIN / END is a verbatim copy of chatbot/static/scene_compile.js and the
 * two MUST stay byte-identical (eval/scene_selftest.py checks). Edit scene_compile.js, then paste here.
 */
(function () {
  'use strict';

// ---- SCENE COMPILER BEGIN ----
var SCENE_FUNCS = {
  sin: 'Math.sin', cos: 'Math.cos', tan: 'Math.tan', asin: 'Math.asin', acos: 'Math.acos', atan: 'Math.atan',
  sinh: 'Math.sinh', cosh: 'Math.cosh', tanh: 'Math.tanh', exp: 'Math.exp', ln: 'Math.log', log: 'Math.log10',
  sqrt: 'Math.sqrt', abs: 'Math.abs', floor: 'Math.floor',
  // statistics helpers (spec §2): pure functions on S = SCENE_STATS, passed into the compiled function
  binom_pmf: 'S.binom_pmf', binom_le: 'S.binom_le', binom_ge: 'S.binom_ge',
  norm_cdf: 'S.norm_cdf', norm_pdf: 'S.norm_pdf', norm_inv: 'S.norm_inv'
};
var SCENE_ARITY = { binom_pmf: 3, binom_le: 3, binom_ge: 3, norm_cdf: 3, norm_pdf: 3, norm_inv: 3 };   // default 1
var SCENE_CONSTS = { pi: 'Math.PI', e: 'Math.E' };
var SCENE_VARS = { x: true, t: true };
var SCENE_ID_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

function sceneArity(name) { return Object.prototype.hasOwnProperty.call(SCENE_ARITY, name) ? SCENE_ARITY[name] : 1; }

/* Numeric runtime for the statistics helpers. n and k are rounded to integers; out-of-domain arguments give NaN
   (the renderer prints '?'). Binomial terms use log-gamma so nothing overflows; erf/erfc to ~1e-15;
   the normal inverse is Acklam's rational approximation refined by one Halley step. */
var SCENE_STATS = (function () {
  var SQRT2 = Math.SQRT2, SQRT2PI = Math.sqrt(2 * Math.PI), MAX_N = 100000;
  function lgamma(z) {   // Lanczos (g = 7, n = 9), relative error ~1e-15 for z > 0
    var c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
      12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
    if (z < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * z))) - lgamma(1 - z);
    z -= 1;
    var a = c[0], t = z + 7.5;
    for (var i = 1; i < 9; i++) a += c[i] / (z + i);
    return 0.5 * Math.log(2 * Math.PI) + (z + 0.5) * Math.log(t) - t + Math.log(a);
  }
  function erfc(x) {   // Taylor series of erf for |x| < 2.5, continued fraction beyond: |error| < 1e-14
    var ax = Math.abs(x), r;
    if (ax < 2.5) {
      var sum = 0, term = ax, n = 0;
      while (Math.abs(term) > 1e-17 * Math.abs(sum) || n < 3) {
        sum += term / (2 * n + 1);
        n++;
        term *= -ax * ax / n;
        if (n > 200) break;
      }
      r = 1 - 2 * sum / Math.sqrt(Math.PI);
    } else {
      var t = ax;
      for (var i = 80; i >= 1; i--) t = ax + (i / 2) / t;
      r = Math.exp(-ax * ax) / (Math.sqrt(Math.PI) * t);
    }
    return x < 0 ? 2 - r : r;
  }
  function okBinom(n, p) { return isFinite(n) && n >= 0 && n <= MAX_N && p >= 0 && p <= 1; }
  function pmf(n, p, k) {
    n = Math.round(n); k = Math.round(k);
    if (!okBinom(n, p)) return NaN;
    if (k < 0 || k > n) return 0;
    if (p === 0) return k === 0 ? 1 : 0;
    if (p === 1) return k === n ? 1 : 0;
    return Math.exp(lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) + k * Math.log(p) + (n - k) * Math.log1p(-p));
  }
  function sumPmf(n, p, a, b) { var s = 0; for (var i = a; i <= b; i++) s += pmf(n, p, i); return Math.min(1, Math.max(0, s)); }
  function le(n, p, k) {
    n = Math.round(n); k = Math.round(k);
    if (!okBinom(n, p)) return NaN;
    if (k < 0) return 0;
    if (k >= n) return 1;
    return k <= n / 2 ? sumPmf(n, p, 0, k) : 1 - sumPmf(n, p, k + 1, n);
  }
  function ge(n, p, k) {
    n = Math.round(n); k = Math.round(k);
    if (!okBinom(n, p)) return NaN;
    if (k <= 0) return 1;
    if (k > n) return 0;
    return k > n / 2 ? sumPmf(n, p, k, n) : 1 - sumPmf(n, p, 0, k - 1);
  }
  function cdf(x, mu, sigma) {
    if (!(sigma > 0) || !isFinite(x) || !isFinite(mu) || !isFinite(sigma)) return NaN;
    var z = (x - mu) / sigma;
    return z < 0 ? 0.5 * erfc(-z / SQRT2) : 1 - 0.5 * erfc(z / SQRT2);
  }
  function pdf(x, mu, sigma) {
    if (!(sigma > 0) || !isFinite(x) || !isFinite(mu) || !isFinite(sigma)) return NaN;
    var z = (x - mu) / sigma;
    return Math.exp(-0.5 * z * z) / (sigma * SQRT2PI);
  }
  function inv(q, mu, sigma) {
    if (!(sigma > 0) || !(q > 0 && q < 1) || !isFinite(mu) || !isFinite(sigma)) return NaN;
    var a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    var b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    var c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    var d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    var pl = 0.02425, z, r;
    if (q < pl) {
      r = Math.sqrt(-2 * Math.log(q));
      z = (((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]) / ((((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1);
    } else if (q <= 1 - pl) {
      r = q - 0.5; var s = r * r;
      z = (((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * r / (((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1);
    } else {
      r = Math.sqrt(-2 * Math.log(1 - q));
      z = -(((((c[0] * r + c[1]) * r + c[2]) * r + c[3]) * r + c[4]) * r + c[5]) / ((((d[0] * r + d[1]) * r + d[2]) * r + d[3]) * r + 1);
    }
    var e = cdf(z, 0, 1) - q, u = e * SQRT2PI * Math.exp(z * z / 2);   // one Halley refinement
    z = z - u / (1 + z * u / 2);
    return mu + sigma * z;
  }
  return { binom_pmf: pmf, binom_le: le, binom_ge: ge, norm_cdf: cdf, norm_pdf: pdf, norm_inv: inv, erfc: erfc, lgamma: lgamma };
})();

function SceneExprError(message, token) {
  this.name = 'SceneExprError';
  this.message = message;
  this.token = token === undefined ? null : token;
}
SceneExprError.prototype = Object.create(Error.prototype);

/* tokenise("2*x") -> [{type:'num',value:'2'},{type:'op',value:'*'},{type:'id',value:'x'}]
   types: num, id, op (+ - * / ^), lp, rp, comma. Throws SceneExprError on any other character. */
function sceneTokenise(src) {
  if (typeof src === 'number') src = String(src);
  if (typeof src !== 'string') throw new SceneExprError('expression is not a string', String(src));
  var out = [], i = 0, n = src.length, m;
  var numRe = /^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?/, idRe = /^[A-Za-z_][A-Za-z0-9_]*/;
  while (i < n) {
    var c = src[i];
    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') { i++; continue; }
    var rest = src.slice(i);
    if ((m = numRe.exec(rest))) {
      // a number directly followed by a letter is implicit multiplication (2x): caught later as adjacency,
      // but 2e3 would be read as scientific notation, so forbid exponent forms followed by a letter too
      out.push({ type: 'num', value: m[0] }); i += m[0].length; continue;
    }
    if ((m = idRe.exec(rest))) { out.push({ type: 'id', value: m[0] }); i += m[0].length; continue; }
    if ('+-*/^'.indexOf(c) >= 0) { out.push({ type: 'op', value: c }); i++; continue; }
    if (c === '(') { out.push({ type: 'lp', value: c }); i++; continue; }
    if (c === ')') { out.push({ type: 'rp', value: c }); i++; continue; }
    if (c === ',') { out.push({ type: 'comma', value: c }); i++; continue; }
    throw new SceneExprError('character not allowed in an expression: ' + JSON.stringify(c), c);
  }
  return out;
}

/* Validate tokens against the grammar. paramIds: array of allowed parameter ids. Throws SceneExprError.
   Commas may only separate the arguments of a function, and each function gets exactly its arity. */
function sceneValidate(tokens, paramIds) {
  var params = {};
  (paramIds || []).forEach(function (p) { params[p] = true; });
  var stack = [];   // one frame per open bracket: {func: name or null, args: count so far}
  for (var i = 0; i < tokens.length; i++) {
    var tk = tokens[i], next = tokens[i + 1], prev = tokens[i - 1];
    if (tk.type === 'id') {
      var isFunc = Object.prototype.hasOwnProperty.call(SCENE_FUNCS, tk.value);
      var isVal = SCENE_VARS[tk.value] || Object.prototype.hasOwnProperty.call(SCENE_CONSTS, tk.value) || params[tk.value];
      if (!isFunc && !isVal) throw new SceneExprError('unknown identifier ' + JSON.stringify(tk.value), tk.value);
      if (isFunc && !(next && next.type === 'lp')) throw new SceneExprError('function ' + tk.value + ' must be followed by (', tk.value);
      if (!isFunc && next && next.type === 'lp') throw new SceneExprError('implicit multiplication is not allowed: ' + tk.value + '(', tk.value + '(');
    }
    // implicit multiplication: a value token directly followed by a value-start token
    var endsValue = tk.type === 'num' || tk.type === 'rp' || (tk.type === 'id' && !SCENE_FUNCS[tk.value]);
    var startsValue = next && (next.type === 'num' || next.type === 'id' || next.type === 'lp');
    if (endsValue && startsValue) throw new SceneExprError('implicit multiplication is not allowed: ' + tk.value + next.value, tk.value + next.value);
    if (tk.type === 'lp') {
      var isCall = prev && prev.type === 'id' && Object.prototype.hasOwnProperty.call(SCENE_FUNCS, prev.value);
      stack.push({ func: isCall ? prev.value : null, args: 1 });
    } else if (tk.type === 'rp') {
      var fr = stack.pop();
      if (!fr) throw new SceneExprError('unbalanced )', ')');
      if (fr.func && fr.args !== sceneArity(fr.func)) {
        var want = sceneArity(fr.func);
        throw new SceneExprError('function ' + fr.func + ' takes ' + want + ' argument' + (want === 1 ? '' : 's') + ' (got ' + fr.args + ')', fr.func);
      }
    } else if (tk.type === 'comma') {
      var top = stack[stack.length - 1];
      if (!top || !top.func) throw new SceneExprError('commas are only allowed between the arguments of a function', ',');
      top.args++;
    }
  }
  if (stack.length) throw new SceneExprError('unbalanced (', '(');
  return tokens;
}

/* Shunting-yard: validated tokens -> a JS expression string built only from whitelisted pieces.
   Variables and params are read from the object `v` (v.x, v.k, ...). `^` becomes Math.pow. */
function sceneToJS(tokens) {
  var PREC = { '+': 1, '-': 1, '*': 2, '/': 2, 'neg': 3, 'pos': 3, '^': 4 };
  var RIGHT = { '^': true, 'neg': true, 'pos': true };
  var out = [], ops = [];
  function popOp() {
    var op = ops.pop();
    if (op.type === 'unary') {
      if (out.length < 1) throw new SceneExprError('missing operand', op.value);
      var a = out.pop();
      out.push(op.value === 'neg' ? '(-' + a + ')' : '(' + a + ')');
    } else if (op.type === 'func') {
      var n = op.nargs || 1;
      if (out.length < n) throw new SceneExprError('missing argument to ' + op.value, op.value);
      var args = out.splice(out.length - n, n);
      out.push(SCENE_FUNCS[op.value] + '(' + args.join(',') + ')');
    } else {
      if (out.length < 2) throw new SceneExprError('missing operand for ' + op.value, op.value);
      var b = out.pop(), a2 = out.pop();
      out.push(op.value === '^' ? 'Math.pow(' + a2 + ',' + b + ')' : '(' + a2 + op.value + b + ')');
    }
  }
  var prev = null;
  for (var i = 0; i < tokens.length; i++) {
    var tk = tokens[i];
    var expectValue = !prev || prev.type === 'op' || prev.type === 'lp' || prev.type === 'unary' || prev.type === 'comma';
    if (tk.type === 'num') {
      if (!/^(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(tk.value)) throw new SceneExprError('bad number', tk.value);
      out.push('(' + tk.value + ')');
    } else if (tk.type === 'id') {
      if (SCENE_FUNCS[tk.value]) { ops.push({ type: 'func', value: tk.value, prec: 5, nargs: 1 }); }
      else if (SCENE_CONSTS[tk.value]) out.push(SCENE_CONSTS[tk.value]);
      else {
        if (!SCENE_ID_RE.test(tk.value)) throw new SceneExprError('bad identifier', tk.value);
        out.push('v[' + JSON.stringify(tk.value) + ']');
      }
    } else if (tk.type === 'op') {
      if (expectValue) {
        if (tk.value === '-' || tk.value === '+') {
          ops.push({ type: 'unary', value: tk.value === '-' ? 'neg' : 'pos', prec: PREC.neg });
          prev = { type: 'unary' }; continue;
        }
        throw new SceneExprError('operator ' + tk.value + ' has no left operand', tk.value);
      }
      var p = PREC[tk.value];
      while (ops.length) {
        var top = ops[ops.length - 1];
        if (top.type === 'lp') break;
        var tp = top.type === 'func' ? 5 : PREC[top.value];
        if (tp > p || (tp === p && !RIGHT[tk.value])) popOp(); else break;
      }
      ops.push({ type: 'binary', value: tk.value, prec: p });
    } else if (tk.type === 'lp') {
      if (!expectValue && !(prev && prev.type === 'id' && SCENE_FUNCS[prev.value])) throw new SceneExprError('unexpected (', '(');
      ops.push({ type: 'lp', value: '(' });
    } else if (tk.type === 'comma') {
      if (expectValue) throw new SceneExprError('unexpected ,', ',');
      while (ops.length && ops[ops.length - 1].type !== 'lp') popOp();
      var fnOp = ops.length >= 2 ? ops[ops.length - 2] : null;
      if (!ops.length || !fnOp || fnOp.type !== 'func') throw new SceneExprError('commas are only allowed between the arguments of a function', ',');
      fnOp.nargs++;
    } else if (tk.type === 'rp') {
      if (expectValue) throw new SceneExprError('unexpected )', ')');
      var found = false;
      while (ops.length) {
        if (ops[ops.length - 1].type === 'lp') { ops.pop(); found = true; break; }
        popOp();
      }
      if (!found) throw new SceneExprError('unbalanced )', ')');
      if (ops.length && ops[ops.length - 1].type === 'func') popOp();
    } else {
      throw new SceneExprError('unexpected token', tk.value);
    }
    prev = tk;
  }
  if (!prev || prev.type === 'op' || prev.type === 'lp' || prev.type === 'unary' || prev.type === 'comma') throw new SceneExprError('expression ends early', prev ? prev.value : '');
  while (ops.length) {
    if (ops[ops.length - 1].type === 'lp') throw new SceneExprError('unbalanced (', '(');
    popOp();
  }
  if (out.length !== 1) throw new SceneExprError('malformed expression', '');
  return out[0];
}

/* sceneCompile("k - 1", ["k"]) -> {fn: function(vars) -> number, js: "..."}.
   vars is an object such as {x: 2, k: 6}. Only whitelisted tokens ever reach new Function.
   The statistics runtime is passed in as `S`, so the compiled code never looks anything up by global name. */
function sceneCompile(expr, paramIds) {
  var tokens = sceneValidate(sceneTokenise(expr), paramIds);
  if (!tokens.length) throw new SceneExprError('empty expression', '');
  var js = sceneToJS(tokens);
  var raw = new Function('v', 'S', 'return (' + js + ');');   // js is built only from validated pieces above
  var fn = function (v) { return raw(v, SCENE_STATS); };
  return { fn: fn, js: js };
}
// ---- SCENE COMPILER END ----

  // ---- colours -------------------------------------------------------------------------------------------
  var COLOUR_VARS = { primary: '--primary', secondary: '--accent', success: '--success', warning: '--warning',
    muted: '--muted', mark: '--mark' };
  var COLOUR_FALLBACK = { primary: '#1a365d', secondary: '#2b6cb0', success: '#276749', warning: '#c05621',
    muted: '#718096', mark: '#805ad5' };

  function colour(token) {
    var tok = COLOUR_VARS[token] ? token : 'primary';
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(COLOUR_VARS[tok]).trim();
      if (v) return v;
    } catch (e) { /* no DOM styles */ }
    return COLOUR_FALLBACK[tok];
  }

  // Any CSS token on :root (dark mode flips them); used for the board chrome that JSXGraph would otherwise draw in fixed greys.
  function cssVar(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      if (v) return v;
    } catch (e) { /* no DOM styles */ }
    return fallback;
  }

  function fmt(v) {
    if (typeof v !== 'number' || !isFinite(v)) return '?';
    if (v === 0) return '0';
    var s = Number(v.toPrecision(3));
    return String(s);
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // "$...$" spans -> KaTeX HTML; plain text escaped. Falls back to the raw text when KaTeX is absent.
  function texToHtml(text) {
    var parts = String(text).split(/(\$[^$]+\$)/g);
    return parts.map(function (p) {
      if (p.length > 2 && p[0] === '$' && p[p.length - 1] === '$') {
        var tex = p.slice(1, -1);
        if (window.katex) {
          try { return window.katex.renderToString(tex, { throwOnError: false, strict: 'ignore' }); } catch (e) { /* fall through */ }
        }
        return '<code>' + esc(tex) + '</code>';
      }
      return esc(p);
    }).join('');
  }

  // ---- guide (docs/learn-layer-spec.md §2 "Guide"): the scene explains itself on screen -------------------
  // Everything here degrades to defaults built from the elements when scene.guide (or a field of it) is absent.
  var GUIDE_CSS = [
    '.scene .scene-intro{font-size:.92rem;color:var(--text,#2d3748);margin:0 0 .5rem;line-height:1.45}',
    '.scene .scene-kicker{display:inline-block;color:var(--muted,#718096);font-weight:600;font-size:.74rem;text-transform:uppercase;letter-spacing:.04em;margin-right:.45em}',
    '.scene .scene-params{display:flex;flex-wrap:wrap;gap:.6rem 1.4rem;align-items:flex-start;margin:0 0 .5rem;max-width:100%}',
    '.scene .scene-param{display:flex;flex-direction:column;gap:.1rem;font-size:.9rem;max-width:100%;min-width:0}',
    '.scene .scene-param-row{display:flex;flex-wrap:wrap;align-items:center;gap:.4rem .5rem;min-height:40px}',
    '.scene .scene-param-row>span:first-child{white-space:nowrap}',
    '.scene .scene-param-row input[type=range]{cursor:ew-resize;flex:1 1 120px;min-width:120px;max-width:260px;height:40px;margin:0}',
    '.scene .scene-param-hint{font-size:.875rem;color:var(--muted,#718096);max-width:28rem}',
    '.scene .scene-drag-cue{font-size:.75rem;color:var(--mark,#805ad5);border:1px dashed var(--mark,#805ad5);border-radius:10px;padding:0 .45em;white-space:nowrap;transition:opacity .7s}',
    '.scene .scene-drag-cue.faded{opacity:0}',
    '.scene .scene-guide{margin-top:.6rem;display:grid;gap:.5rem}',
    '.scene .scene-box{border:1px solid var(--border,#e2e8f0);border-radius:8px;padding:.5rem .75rem;background:var(--card,#fff);color:var(--text,#2d3748);font-size:.9rem;line-height:1.45}',
    '.scene .scene-box h5{margin:0 0 .3rem;font-size:.74rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted,#718096);font-weight:600}',
    '.scene .scene-legend-items{display:flex;flex-wrap:wrap;gap:.35rem 1.2rem}',
    '.scene .scene-legend-item{display:inline-flex;align-items:center;gap:.5rem;font-size:.88rem}',
    '.scene .scene-legend-item .meaning{color:var(--muted,#718096)}',
    '.scene .scene-swatch{display:inline-block;width:22px;height:14px;flex:none;position:relative;box-sizing:border-box}',
    '.scene .scene-swatch.line{height:0;border-top:3px solid currentColor}',
    '.scene .scene-swatch.dashed{height:0;border-top:3px dashed currentColor}',
    '.scene .scene-swatch.block{background:currentColor;opacity:.35;border-radius:2px}',
    '.scene .scene-swatch.ring{width:14px;height:14px;border:2px solid currentColor;border-radius:50%;margin:0 4px}',
    '.scene .scene-swatch.dot{width:10px;height:10px;border-radius:50%;background:currentColor;margin:0 6px}',
    '.scene .scene-swatch.halo{outline:1.5px dashed currentColor;outline-offset:3px}',
    '.scene .scene-swatch.arrow::after{content:"\\25B6";position:absolute;right:-7px;top:-9px;font-size:10px;line-height:1;color:currentColor}',
    '.scene .scene-swatch.text{width:auto;height:auto;font-weight:700;font-size:.85rem;line-height:1;padding:0 3px}',
    '.scene .scene-box ul{margin:0;padding-left:1.1rem}',
    '.scene .scene-box li{margin:.15rem 0}',
    '.scene .scene-watch{color:var(--muted,#718096)}',
    '.scene .scene-chip{display:inline-block;color:#fff;border-radius:12px;font-size:12px;padding:1px 9px;font-weight:600;background:var(--mark,#805ad5);margin:2px 4px 2px 0;white-space:nowrap;vertical-align:middle}',
    '.scene .scene-chip.part{background:var(--accent,#2b6cb0)}',
    '.scene .scene-chips{margin-bottom:.25rem}',
    '.scene .scene-readoff{font-size:.875rem;color:var(--muted,#718096)}',
    '.scene .scene-readoff b{color:var(--text,#2d3748)}',
    '.scene .scene-steps{margin-top:.6rem;border-top:1px solid var(--border,#e2e8f0);padding-top:.5rem}',
    '.scene .scene-step-set{font-size:.875rem;color:var(--muted,#718096);margin-top:.2rem;min-height:1em}',
    '.scene .scene-steps button{font:inherit;font-size:.9rem;min-height:40px;padding:0 1rem;border-radius:20px;border:1px solid var(--accent,#2b6cb0);background:var(--card,#fff);color:var(--accent,#2b6cb0);cursor:pointer}',
    '.scene .scene-steps button:disabled{opacity:.45;cursor:default;border-color:var(--border,#e2e8f0);color:var(--muted,#718096)}',
    '.scene .scene-board{max-width:100%;overflow:hidden}',
    '.scene .scene-board .JXGtext{color:var(--text,#2d3748);white-space:nowrap}'
  ].join('\n');

  function injectGuideCss() {
    if (!document.head || document.getElementById('scene-guide-css')) return;
    var st = document.createElement('style');
    st.id = 'scene-guide-css';
    st.textContent = GUIDE_CSS;
    document.head.appendChild(st);
  }

  // the colour token an element is drawn in (same defaults as the element switch below)
  function elColour(el) {
    if (el.color) return colour(el.color);
    switch (el.type) {
      case 'point': return colour('success');
      case 'glider': return colour('warning');
      case 'tangent': case 'normal': return colour('secondary');
      case 'text': case 'vline': case 'hline': return colour('muted');
      default: return colour('primary');
    }
  }

  function nameOf(meta, id) {
    var e = meta[id];
    return e && e.label ? e.label : String(id);
  }

  // short noun for the intro list ("the curve C, the shaded region R")
  function shortType(el) {
    switch (el.type) {
      case 'function': case 'parametric': return 'curve';
      case 'point': return el.draggable ? 'draggable point' : 'point';
      case 'glider': return 'draggable point';
      case 'segment': return 'segment'; case 'line': return 'line'; case 'vector': return 'arrow';
      case 'tangent': return 'tangent'; case 'normal': return 'normal';
      case 'integral': return 'shaded region'; case 'circle': return 'circle'; case 'polygon': return 'shaded shape';
      case 'text': return 'label'; case 'vline': case 'hline': return 'dashed guide line';
    }
    return String(el.type);
  }

  // fallback legend meaning in words when the guide has none
  function typeWords(el, meta) {
    switch (el.type) {
      case 'function': case 'parametric': return 'curve' + (el.dash ? ' (dashed)' : '');
      case 'point': return el.draggable ? 'point you can drag' : 'fixed point';
      case 'glider': return 'point you can drag along ' + nameOf(meta, el.on);
      case 'segment': return 'line segment' + (el.dash ? ' (dashed)' : '');
      case 'line': return 'straight line' + (el.dash ? ' (dashed)' : '');
      case 'vector': return 'arrow (vector)';
      case 'tangent': return 'tangent to ' + nameOf(meta, el.of) + ' at ' + nameOf(meta, el.at) + '; it moves with that point';
      case 'normal': return 'normal to ' + nameOf(meta, el.of) + ' at ' + nameOf(meta, el.at) + '; it moves with that point';
      case 'integral': return 'shaded area ' + (el.between ? 'between ' + nameOf(meta, el.between[0]) + ' and ' + nameOf(meta, el.between[1])
        : 'under ' + nameOf(meta, el.of)) + ' from x = ' + el.from + ' to x = ' + el.to;
      case 'circle': return 'circle';
      case 'polygon': return 'shaded shape';
      case 'text': return 'label that updates as you drag';
      case 'vline': return 'dashed vertical guide at x = ' + el.at;
      case 'hline': return 'dashed horizontal guide at y = ' + el.at;
    }
    return String(el.type);
  }

  function swatchClass(el) {
    switch (el.type) {
      case 'point': return 'dot' + (el.draggable ? ' halo' : '');
      case 'glider': return 'dot halo';
      case 'integral': case 'polygon': return 'block';
      case 'circle': return el.opacity ? 'block' : 'ring';
      case 'vector': return 'line arrow';
      case 'vline': case 'hline': return 'dashed';
      case 'text': return 'text';
      default: return el.dash ? 'dashed' : 'line';
    }
  }

  // element types that always deserve a legend entry (spec rule) plus the visible helpers a student may wonder about
  var LEGEND_TYPES = { integral: 1, glider: 1, tangent: 1, normal: 1, vector: 1, vline: 1, hline: 1, polygon: 1, circle: 1 };

  // [{el, meaning}] in guide order first, then every other element that needs one (fallback meaning = '')
  function legendRows(scene, meta) {
    var g = scene.guide || {}, rows = [], seen = {};
    (g.legend || []).forEach(function (r) {
      if (r && r.id && meta[r.id] && !seen[r.id]) { seen[r.id] = 1; rows.push({ el: meta[r.id], meaning: r.meaning || '' }); }
    });
    (scene.elements || []).forEach(function (el) {
      if (seen[el.id] || el.type === 'text') return;
      if (el.label || LEGEND_TYPES[el.type] || (el.type === 'point' && el.draggable)) { seen[el.id] = 1; rows.push({ el: el, meaning: '' }); }
    });
    return rows;
  }

  function isControl(el) { return el.type === 'glider' || (el.type === 'point' && !!el.draggable); }

  // [{head, doText, watch}] one per slider and per draggable element, guide text where given
  function interactLines(scene, meta) {
    var g = scene.guide || {}, byControl = {}, used = {}, lines = [];
    (g.interact || []).forEach(function (it) { if (it && it.control) byControl[it.control] = it; });
    (scene.params || []).forEach(function (p) {
      var it = byControl[p.id], name = p.label || p.id;
      used[p.id] = 1;
      lines.push({
        head: 'Slider ‘' + name + '’',
        doText: it && it['do'] ? it['do'] : 'Drag it left or right to change ' + name + ' between ' + fmt(Number(p.min)) + ' and ' + fmt(Number(p.max)) + '.',
        watch: it && it.watch ? it.watch : 'Everything drawn using ' + p.id + ' moves with it.'
      });
    });
    (scene.elements || []).forEach(function (el) {
      if (!isControl(el)) return;
      var it = byControl[el.id], name = el.label || el.id;
      used[el.id] = 1;
      lines.push({
        head: 'Point ' + name,
        doText: it && it['do'] ? it['do'] : (el.type === 'glider' ? 'Drag the point ' + name + ' along ' + nameOf(meta, el.on) + '.' : 'Drag the point ' + name + ' anywhere on the board.'),
        watch: it && it.watch ? it.watch : 'Anything attached to it (labels, tangents, segments) follows.'
      });
    });
    (g.interact || []).forEach(function (it) {     // entries for controls we did not recognise: still show them
      if (!it || !it.control || used[it.control]) return;
      lines.push({ head: String(it.control), doText: it['do'] || '', watch: it.watch || '' });
    });
    return lines;
  }

  // ---- numerics ------------------------------------------------------------------------------------------
  function simpson(f, a, b, n) {
    n = n || 200;
    if (n % 2) n++;
    var h = (b - a) / n, s = f(a) + f(b);
    for (var i = 1; i < n; i++) s += f(a + i * h) * (i % 2 ? 4 : 2);
    return s * h / 3;
  }

  function derivative(f, x) {
    var h = 1e-5;
    return (f(x + h) - f(x - h)) / (2 * h);
  }

  // ---- renderer ------------------------------------------------------------------------------------------
  function errorCard(container, title, detail) {
    container.innerHTML = '';
    var card = document.createElement('div');
    card.className = 'scene-error';
    card.setAttribute('role', 'alert');
    card.style.cssText = 'border:1px solid var(--danger,#c53030);border-radius:8px;padding:.75rem 1rem;color:var(--danger,#c53030);background:var(--card,#fff);font-size:.95rem';
    card.innerHTML = '<strong>' + esc(title) + '</strong><div style="margin-top:.25rem;color:var(--text,#2d3748)">' + esc(detail) + '</div>';
    container.appendChild(card);
    return card;
  }

  function renderScene(containerId, scene, opts) {
    opts = opts || {};
    var container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    if (!container) throw new Error('renderScene: no element ' + containerId);
    if (!window.JXG || !JXG.JSXGraph) { errorCard(container, 'Diagram unavailable', 'JSXGraph did not load.'); return null; }
    container.innerHTML = '';
    container.classList.add('scene');

    var paramIds = (scene.params || []).map(function (p) { return p.id; });
    var values = {};                      // live param values
    (scene.params || []).forEach(function (p) { values[p.id] = Number(p.value); });
    function env(x, t) {
      var v = {};
      for (var k in values) v[k] = values[k];
      if (x !== undefined) v.x = x;
      if (t !== undefined) v.t = t;
      return v;
    }
    var compiled = [];                    // for error reporting
    function comp(expr, what) {
      try { return sceneCompile(expr, paramIds); }
      catch (e) { e.what = what; throw e; }
    }
    function scalar(expr, what) {          // expression with no x/t -> function() -> number
      if (typeof expr === 'number') return function () { return expr; };
      var c = comp(String(expr), what);
      return function () { return c.fn(env()); };
    }
    function fx(expr, what) {              // expression in x -> function(x) -> number
      var c = comp(String(expr), what);
      return function (x) { return c.fn(env(x)); };
    }
    function ft(expr, what) {
      var c = comp(String(expr), what);
      return function (t) { return c.fn(env(undefined, t)); };
    }

    // pre-compile everything first: a rejected token means an error card and nothing else
    var elements = scene.elements || [];
    var byId = {}, meta = {};
    try {
      if (!scene.board || !scene.board.x || !scene.board.y) throw new SceneExprError('scene.board needs x and y ranges', 'board');
      elements.forEach(function (el, i) {
        if (!el || !el.id) throw new SceneExprError('element ' + i + ' has no id', 'id');
        if (byId[el.id] !== undefined) throw new SceneExprError('duplicate id ' + el.id, el.id);
        byId[el.id] = null;
        meta[el.id] = el;
        var w = el.id;
        var m = {};
        switch (el.type) {
          case 'function': m.f = fx(el.expr, w);
            if (el.domain && el.domain.length === 2) { m.d0 = scalar(el.domain[0], w); m.d1 = scalar(el.domain[1], w); } break;
          case 'parametric': m.fx = ft(el.x_expr, w); m.fy = ft(el.y_expr, w); break;
          case 'point': m.x = scalar(el.x, w); m.y = scalar(el.y, w); break;
          case 'glider': m.x = scalar(el.x === undefined ? 0 : el.x, w); break;
          case 'segment': case 'line': case 'vector': m.from = endpoint(el.from, w); m.to = endpoint(el.to, w); break;
          case 'tangent': case 'normal': break;
          case 'integral': m.from = scalar(el.from, w); m.to = scalar(el.to, w); break;
          case 'circle': m.c = endpoint(el.centre, w); m.r = scalar(el.radius, w); break;
          case 'polygon': m.pts = (el.points || []).map(function (p) { return endpoint(p, w); }); break;
          case 'text': m.x = scalar(el.x, w); m.y = scalar(el.y, w); m.tpl = template(el.value === undefined ? '' : String(el.value), w); break;
          case 'vline': case 'hline': m.at = scalar(el.at, w); break;
          default: throw new SceneExprError('unknown element type ' + JSON.stringify(el.type), String(el.type));
        }
        compiled.push([el.id, m]);
      });
    } catch (e) {
      var tok = e.token !== undefined && e.token !== null ? ' Bad token: ' + JSON.stringify(e.token) + '.' : '';
      errorCard(container, 'This diagram could not be drawn', (e.what ? 'In element ' + e.what + ': ' : '') + e.message + tok);
      return null;
    }

    // [x, y] of expressions, or a point id -> {x: fn, y: fn} resolved lazily against created points
    function endpoint(spec, what) {
      if (typeof spec === 'string' && meta[spec] === undefined && !/^[-+.\d(]/.test(spec.trim())) {
        // a point id that is not compiled as an expression: resolved after creation
        var id = spec;
        if (!(elements.some(function (e) { return e.id === id; }))) throw new SceneExprError('unknown point id ' + JSON.stringify(id), id);
        return { ref: id };
      }
      if (typeof spec === 'string' && meta[spec] !== undefined) return { ref: spec };
      if (!Array.isArray(spec) || spec.length !== 2) throw new SceneExprError('expected [x, y] or a point id', JSON.stringify(spec));
      return { x: scalar(spec[0], what), y: scalar(spec[1], what) };
    }

    // "Area so far = {area(R)}" -> function() -> string; {x(ID)}, {y(ID)}, {expr}
    // placeholders are only read outside $...$ spans (TeX braces are not placeholders)
    function template(s, what) {
      var pieces = [];
      String(s).split(/(\$[^$]+\$)/g).forEach(function (chunk) {
        if (chunk.length > 2 && chunk[0] === '$' && chunk[chunk.length - 1] === '$') { pieces.push(chunk); return; }
        var re = /\{([^{}]+)\}/g, last = 0, m;
        while ((m = re.exec(chunk))) {
          pieces.push(chunk.slice(last, m.index));
          var inner = m[1].trim(), sm = /^(area|x|y)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$/.exec(inner);
          if (sm) {
            if (!elements.some(function (e) { return e.id === sm[2]; })) throw new SceneExprError('unknown id in {' + inner + '}', sm[2]);
            pieces.push({ kind: sm[1], id: sm[2] });
          } else {
            pieces.push({ kind: 'expr', f: scalar(inner, what) });
          }
          last = re.lastIndex;
        }
        pieces.push(chunk.slice(last));
      });
      return function () {
        return pieces.map(function (p) {
          if (typeof p === 'string') return p;
          if (p.kind === 'expr') return fmt(p.f());
          var o = byId[p.id], mt = meta[p.id];
          if (p.kind === 'area') return fmt(o && o.sceneArea ? o.sceneArea() : NaN);
          if (!o || typeof o.X !== 'function') return '?';
          return fmt(p.kind === 'x' ? o.X() : o.Y());
        }).join('');
      };
    }

    // ---- guide data (defaults from the elements when scene.guide is missing) ------------------------------
    injectGuideCss();
    var guide = scene.guide || {};
    var legend = legendRows(scene, meta);
    var inLegend = {};
    legend.forEach(function (r) { inLegend[r.el.id] = true; });
    // on-board name: the element's label, else its id when the legend lists it (so the legend can be matched to the picture)
    function labelFor(el) { return el.label ? String(el.label) : (inLegend[el.id] ? String(el.id) : ''); }
    var interactByControl = {};
    (guide.interact || []).forEach(function (it) { if (it && it.control) interactByControl[it.control] = it; });

    // ---- DOM: intro, sliders row, board, guide boxes, steps -----------------------------------------------
    var intro = document.createElement('div');
    intro.className = 'scene-intro';
    var introText;
    if (guide.what_you_see) introText = texToHtml(guide.what_you_see);
    else {
      var names = legend.map(function (r) { return 'the ' + shortType(r.el) + ' ' + esc(labelFor(r.el) || r.el.id); });
      introText = names.length ? 'The picture shows ' + names.join(', ').replace(/, ([^,]*)$/, ' and $1') + '.' : 'The picture shows the situation in the question.';
    }
    intro.innerHTML = '<span class="scene-kicker">What you’re looking at</span>' + introText;

    var sliderRow = document.createElement('div');
    sliderRow.className = 'scene-params';
    var boardDiv = document.createElement('div');
    boardDiv.id = (container.id || 'scene') + '-board';
    boardDiv.className = 'scene-board jxgbox';
    var h = Math.max(320, Math.min(420, Math.round((container.clientWidth || 600) * 0.62)));
    boardDiv.style.cssText = 'width:100%;height:' + h + 'px;border:1px solid var(--border,#e2e8f0);border-radius:8px;background:var(--card,#fff)';
    var guideDiv = document.createElement('div');
    guideDiv.className = 'scene-guide';
    var stepsDiv = document.createElement('div');
    stepsDiv.className = 'scene-steps';
    if (scene.title && !(opts && opts.showTitle === false)) {
      var t = document.createElement('div');
      t.className = 'scene-title';
      t.style.cssText = 'font-weight:600;margin-bottom:.35rem';
      t.textContent = scene.title;
      container.appendChild(t);
    }
    container.appendChild(intro);
    container.appendChild(sliderRow);
    container.appendChild(boardDiv);
    container.appendChild(guideDiv);
    container.appendChild(stepsDiv);

    var sliders = {}, dragCues = [];
    function fadeDragCues() { dragCues.forEach(function (c) { c.classList.add('faded'); }); }
    (scene.params || []).forEach(function (p) {
      var wrap = document.createElement('div');
      wrap.className = 'scene-param';
      var row = document.createElement('label');
      row.className = 'scene-param-row';
      var name = document.createElement('span');
      name.textContent = (p.label || p.id) + ':';
      var input = document.createElement('input');
      input.type = 'range'; input.min = p.min; input.max = p.max; input.step = p.step || 'any'; input.value = p.value;
      input.setAttribute('aria-label', p.label || p.id);
      input.title = 'Drag to change ' + (p.label || p.id);
      var out = document.createElement('output');
      out.style.cssText = 'min-width:2.5em;font-variant-numeric:tabular-nums';
      out.textContent = fmt(Number(p.value));
      var cue = document.createElement('span');
      cue.className = 'scene-drag-cue';
      cue.setAttribute('aria-hidden', 'true');
      cue.textContent = '⇔ drag';
      dragCues.push(cue);
      var hint = document.createElement('div');
      hint.className = 'scene-param-hint';
      var it = interactByControl[p.id];
      hint.innerHTML = it && it['do'] ? texToHtml(it['do']) : 'Drag to change ' + esc(p.label || p.id) + '.';
      input.addEventListener('input', function () {
        values[p.id] = Number(input.value);
        out.textContent = fmt(values[p.id]);
        fadeDragCues();
        board.update();
      });
      row.appendChild(name); row.appendChild(input); row.appendChild(out); row.appendChild(cue);
      wrap.appendChild(row); wrap.appendChild(hint);
      sliderRow.appendChild(wrap);
      sliders[p.id] = { input: input, out: out, label: p.label || p.id };
    });
    if (!(scene.params || []).length) sliderRow.style.display = 'none';

    var bx = scene.board.x, by = scene.board.y;
    // Axis and grid colours follow the page tokens so they stay visible in dark mode (JSXGraph's defaults are fixed greys).
    var axisCol = cssVar('--text', '#2d3748'), gridCol = cssVar('--border', '#e2e8f0');
    var axisAttr = { strokeColor: axisCol, highlight: false, ticks: { minorTicks: 0, strokeColor: axisCol, label: { color: axisCol, fontSize: 12, cssStyle: 'color:' + axisCol } } };
    var board = JXG.JSXGraph.initBoard(boardDiv.id, {
      boundingbox: [bx[0], by[1], bx[1], by[0]],
      axis: scene.board.axis !== false,
      grid: scene.board.grid ? { strokeColor: gridCol, strokeOpacity: 1, highlight: false } : false,
      keepaspectratio: scene.board.aspect === 'equal',
      showCopyright: false, showNavigation: false, showZoom: false,
      pan: { enabled: false }, zoom: { enabled: false },
      defaultAxes: { x: axisAttr, y: axisAttr }
    });

    // ---- elements ----------------------------------------------------------------------------------------
    function pt(ep, attrs) {       // endpoint -> a JXG point (hidden helper for expression pairs)
      if (ep.ref) {
        var o = byId[ep.ref];
        if (!o || typeof o.X !== 'function') throw new SceneExprError(ep.ref + ' is not a point', ep.ref);
        return o;
      }
      return board.create('point', [ep.x, ep.y], Object.assign({ visible: false, fixed: true, name: '' }, attrs || {}));
    }
    function curveOf(id) {
      var o = byId[id];
      if (!o) throw new SceneExprError('unknown id ' + JSON.stringify(id), id);
      return o;
    }
    function fOf(id) {
      var m = meta[id];
      if (!m || m.type !== 'function') throw new SceneExprError(JSON.stringify(id) + ' is not a function element', id);
      return compiledMeta[id].f;
    }
    var compiledMeta = {};
    compiled.forEach(function (pair) { compiledMeta[pair[0]] = pair[1]; });

    // a draggable point/glider gets a dashed halo (so the student sees what moves) and a "Drag me" tooltip
    var helpers = {};                      // element id -> [extra JXG objects] shown/hidden with it
    function addDragCue(el, obj, col) {
      var halo = board.create('point', [function () { return obj.X(); }, function () { return obj.Y(); }],
        { size: 9, fillOpacity: 0, strokeColor: col, strokeWidth: 1.5, dash: 2, fixed: true, highlight: false, withLabel: false, name: '', layer: 8 });
      helpers[el.id] = (helpers[el.id] || []).concat([halo]);
      try { halo.rendNode.style.pointerEvents = 'none'; } catch (e) { /* the halo must never catch the drag */ }
      var what = 'Drag me' + (el.type === 'glider' ? ' along ' + nameOf(meta, el.on) : '') + (el.label ? ' (' + el.label + ')' : '');
      try {
        var node = obj.rendNode;
        if (node) {
          node.setAttribute('title', what);
          var tt = document.createElementNS('http://www.w3.org/2000/svg', 'title');
          tt.textContent = what;
          node.appendChild(tt);
          node.style.cursor = 'grab';
        }
      } catch (e) { /* tooltip is a nicety */ }
      obj.on('drag', fadeDragCues);
    }
    // a small on-board name for filled regions (integral, polygon) that have no natural JSXGraph label
    function regionLabel(el, obj, col, xf, yf) {
      var name = labelFor(el);
      if (!name) return;
      var lbl = board.create('text', [xf, yf, name], { anchorX: 'middle', anchorY: 'middle', color: col, fontSize: 13, fixed: true, highlight: false,
        cssStyle: 'color:' + col + ';font-weight:600;pointer-events:none', parse: false });
      helpers[el.id] = (helpers[el.id] || []).concat([lbl]);
    }

    try {
      elements.forEach(function (el) {
        var m = compiledMeta[el.id], col = colour(el.color), dash = el.dash ? 2 : 0, obj, nm = labelFor(el);
        var base = { strokeColor: col, fillColor: col, fillOpacity: 0, strokeWidth: 2, dash: dash, name: nm, fixed: true, highlight: false };  // fillOpacity 0: JSXGraph fills curves at 1 by default, which painted whole parabolas (seen 2026-09-30)
        switch (el.type) {
          case 'function': {
            var args = m.d0 ? [m.f, m.d0, m.d1] : [m.f];
            obj = board.create('functiongraph', args, Object.assign({}, base, { withLabel: !!nm,
              label: { color: col, fontSize: 13, autoPosition: true } }));
            break;
          }
          case 'parametric': {
            var tr = el.t_range || [0, 1];
            obj = board.create('curve', [m.fx, m.fy, scalar(tr[0], el.id), scalar(tr[1], el.id)],
              Object.assign({}, base, { withLabel: !!nm, label: { color: col, fontSize: 13 } }));
            break;
          }
          case 'point': {
            var pc = colour(el.color || 'success');
            var drag = !!el.draggable;
            obj = board.create('point', drag ? [m.x(), m.y()] : [m.x, m.y], { name: nm, size: 3, fixed: !drag,
              strokeColor: pc, fillColor: pc, highlight: drag, withLabel: !!nm, label: { offset: [8, 8], color: pc, fontSize: 13 } });
            if (drag) addDragCue(el, obj, pc);
            break;
          }
          case 'glider': {
            var on = curveOf(el.on), x0 = m.x(), y0 = 0, gc = colour(el.color || 'warning');
            if (meta[el.on].type === 'function') y0 = compiledMeta[el.on].f(x0);
            else if (typeof on.Y === 'function' && on.Y.length === 1) { try { y0 = on.Y(x0); } catch (e) { y0 = 0; } }
            obj = board.create('glider', [x0, y0, on], { name: nm, size: 4, strokeColor: gc, fillColor: gc,
              withLabel: !!nm, label: { offset: [8, 8], color: gc, fontSize: 13 } });
            addDragCue(el, obj, gc);
            break;
          }
          case 'segment': case 'line': case 'vector': {
            var p1 = pt(m.from), p2 = pt(m.to);
            var kind = el.type === 'line' ? 'line' : el.type === 'vector' ? 'arrow' : 'segment';
            obj = board.create(kind, [p1, p2], Object.assign({}, base, { withLabel: !!nm, label: { color: col, fontSize: 13 } }));
            break;
          }
          case 'tangent': case 'normal': {
            var at = byId[el.at];
            if (!at || typeof at.X !== 'function') throw new SceneExprError(JSON.stringify(el.at) + ' is not a point or glider', el.at);
            var g = fOf(el.of), isTan = el.type === 'tangent', tcol = colour(el.color || 'secondary');
            var q1 = board.create('point', [function () { return at.X(); }, function () { return g(at.X()); }], { visible: false, fixed: true, name: '' });
            var q2 = board.create('point', [
              function () { var x = at.X(); return isTan ? x + 1 : x - derivative(g, x); },
              function () { var x = at.X(); return isTan ? g(x) + derivative(g, x) : g(x) + 1; }
            ], { visible: false, fixed: true, name: '' });
            obj = board.create('line', [q1, q2], Object.assign({}, base, { strokeColor: tcol, withLabel: !!nm, label: { color: tcol, fontSize: 13 } }));
            break;
          }
          case 'integral': {
            var fTop, fBot;
            if (el.between) { fTop = fOf(el.between[0]); fBot = fOf(el.between[1]); }
            else { fTop = fOf(el.of); fBot = function () { return 0; }; }
            var a = m.from, b = m.to;
            obj = board.create('curve', [[0], [0]], { strokeWidth: 0, strokeColor: col, fillColor: col,
              fillOpacity: el.opacity === undefined ? 0.25 : el.opacity, highlight: false, fixed: true, name: '' });
            obj.updateDataArray = function () {
              var lo = a(), hi = b(), N = 120, xs = [], ys = [], i, x;
              for (i = 0; i <= N; i++) { x = lo + (hi - lo) * i / N; xs.push(x); ys.push(fTop(x)); }
              for (i = N; i >= 0; i--) { x = lo + (hi - lo) * i / N; xs.push(x); ys.push(fBot(x)); }
              this.dataX = xs; this.dataY = ys;
            };
            // signed integral of (top - bottom) from `from` to `to`, Simpson's rule
            obj.sceneArea = function () { return simpson(function (x) { return fTop(x) - fBot(x); }, a(), b(), 200); };
            regionLabel(el, obj, col,
              function () { return (a() + b()) / 2; },
              function () { var xm = (a() + b()) / 2; return (fTop(xm) + fBot(xm)) / 2; });
            break;
          }
          case 'circle': {
            var c = pt(m.c);
            obj = board.create('circle', [c, m.r], Object.assign({}, base, { fillOpacity: el.opacity === undefined ? 0 : el.opacity, withLabel: !!nm, label: { color: col, fontSize: 13 } }));
            break;
          }
          case 'polygon': {
            var ps = m.pts.map(function (ep) { return pt(ep); });
            obj = board.create('polygon', ps, { fillColor: col, fillOpacity: el.opacity === undefined ? 0.2 : el.opacity, highlight: false, fixed: true,
              borders: { strokeColor: col, strokeWidth: 2, highlight: false }, vertices: { visible: false } });
            regionLabel(el, obj, col,
              function () { var s = 0; ps.forEach(function (p) { s += p.X(); }); return s / ps.length; },
              function () { var s = 0; ps.forEach(function (p) { s += p.Y(); }); return s / ps.length; });
            break;
          }
          case 'text': {
            var tpl = m.tpl, tc = colour(el.color || 'muted');
            // Labels placed in the right third of the picture hang off the board on a phone: anchor them on the right instead.
            var tx0 = typeof m.x === 'function' ? m.x() : m.x, rightSide = typeof tx0 === 'number' && isFinite(tx0) && tx0 > bx[0] + 0.62 * (bx[1] - bx[0]);
            obj = board.create('text', [m.x, m.y, function () { return texToHtml(tpl()); }],
              { parse: false, useMathJax: false, useKatex: false, display: 'html', anchorX: rightSide ? 'right' : 'left', color: tc, fontSize: 14, fixed: true, highlight: false, cssStyle: 'color:' + tc + ';white-space:nowrap' });
            break;
          }
          case 'vline': case 'hline': {
            var atF = m.at, isV = el.type === 'vline';
            var r1 = board.create('point', [isV ? atF : function () { return 0; }, isV ? function () { return 0; } : atF], { visible: false, fixed: true, name: '' });
            var r2 = board.create('point', [isV ? atF : function () { return 1; }, isV ? function () { return 1; } : atF], { visible: false, fixed: true, name: '' });
            var gcol = colour(el.color || 'muted');
            obj = board.create('line', [r1, r2], Object.assign({}, base, { strokeColor: gcol, dash: 2, strokeWidth: 1.5, withLabel: !!nm, label: { color: gcol, fontSize: 13 } }));
            break;
          }
        }
        if (el.visible === false) { obj.setAttribute({ visible: false }); (helpers[el.id] || []).forEach(function (o) { o.setAttribute({ visible: false }); }); }
        byId[el.id] = obj;
      });
    } catch (e) {
      try { JXG.JSXGraph.freeBoard(board); } catch (e2) { /* ignore */ }
      var tok2 = e.token !== undefined && e.token !== null ? ' Bad token: ' + JSON.stringify(e.token) + '.' : '';
      errorCard(container, 'This diagram could not be drawn', e.message + tok2);
      return null;
    }
    board.update();

    // ---- guide boxes under the board: legend, how to use, question link, read-off ------------------------
    function box(cls, heading, inner) {
      var d = document.createElement('div');
      d.className = 'scene-box ' + cls;
      d.innerHTML = (heading ? '<h5>' + esc(heading) + '</h5>' : '') + inner;
      guideDiv.appendChild(d);
      return d;
    }
    if (legend.length) {
      box('scene-legend', 'Legend', '<div class="scene-legend-items">' + legend.map(function (r) {
        var el = r.el, name = labelFor(el) || el.id, meaning = r.meaning ? texToHtml(r.meaning) : esc(typeWords(el, meta));
        var sw = '<span class="scene-swatch ' + swatchClass(el) + '" style="color:' + elColour(el) + '" aria-hidden="true">' + (el.type === 'text' ? 'T' : '') + '</span>';
        return '<span class="scene-legend-item">' + sw + '<span><b>' + esc(name) + '</b> <span class="meaning">— ' + meaning + '</span></span></span>';
      }).join('') + '</div>');
    }
    var lines = interactLines(scene, meta);
    var stepsLine = (scene.steps || []).length
      ? '<li><b>Previous / Next</b> under the picture walk you through ' + (scene.steps || []).length + ' steps; a step may move a slider for you (it says so in small print).</li>' : '';
    if (lines.length || stepsLine) {
      box('scene-howto', 'How to use this', '<ul>' + lines.map(function (l) {
        return '<li><b>' + esc(l.head) + '</b>' + (l.doText ? ' — ' + texToHtml(l.doText) : '') +
          (l.watch ? ' <span class="scene-watch"><b>Watch:</b> ' + texToHtml(l.watch) + '</span>' : '') + '</li>';
      }).join('') + stepsLine + '</ul>');
    }
    var ql = guide.question_link || {}, links = scene.links || {};
    var partLabel = ql.part !== undefined && ql.part !== null ? ql.part : scene.part;
    var markCodes = Array.isArray(ql.marks) && ql.marks.length ? ql.marks : (Array.isArray(links.marks) ? links.marks : []);
    var linkText;
    if (ql.text) linkText = texToHtml(ql.text);
    else {
      var ss = Array.isArray(links.solution_steps) ? links.solution_steps : [];
      linkText = esc('This picture goes with ' + (partLabel ? 'part (' + partLabel + ')' : 'the question') +
        (ss.length ? ' and illustrates step' + (ss.length > 1 ? 's ' : ' ') + ss.join(', ') + ' of the solution' : '') +
        (markCodes.length ? '; the marks it helps you earn are shown above.' : '.'));
    }
    var chipsHtml = (partLabel ? '<span class="scene-chip part">Part (' + esc(partLabel) + ')</span>' : '') +
      markCodes.map(function (c) { return '<span class="scene-chip">' + esc(c) + '</span>'; }).join('');
    box('scene-link', 'How this links to the question', (chipsHtml ? '<div class="scene-chips">' + chipsHtml + '</div>' : '') + '<div>' + linkText + '</div>');
    var readOff = Array.isArray(guide.read_off) ? guide.read_off.filter(Boolean) : [];
    if (!readOff.length && elements.some(function (e) { return e.type === 'text' && /\{/.test(String(e.value || '')); })) {
      readOff = ['The labels on the picture update live as you drag: read the current values from them.'];
    }
    if (readOff.length) {
      var ro = document.createElement('div');
      ro.className = 'scene-readoff';
      ro.innerHTML = '<b>Read off:</b> ' + readOff.map(texToHtml).join(' · ');
      guideDiv.appendChild(ro);
    }

    // ---- steps UI ----------------------------------------------------------------------------------------
    var steps = scene.steps || [], current = 0;
    var stepText = document.createElement('div');
    stepText.className = 'scene-step-text';
    stepText.style.cssText = 'min-height:2.5em;line-height:1.5';
    var setNote = document.createElement('div');
    setNote.className = 'scene-step-set';
    var nav = document.createElement('div');
    nav.style.cssText = 'display:flex;gap:.5rem;align-items:center;margin-top:.4rem';
    var prev = document.createElement('button'), next = document.createElement('button'), counter = document.createElement('span');
    prev.type = 'button'; next.type = 'button';
    prev.textContent = 'Previous'; next.textContent = 'Next';
    prev.setAttribute('aria-label', 'Previous step'); next.setAttribute('aria-label', 'Next step');
    counter.style.cssText = 'font-size:.85rem;color:var(--muted,#718096);margin-left:auto';
    nav.appendChild(prev); nav.appendChild(next); nav.appendChild(counter);
    stepsDiv.appendChild(stepText); stepsDiv.appendChild(setNote); stepsDiv.appendChild(nav);
    if (!steps.length) stepsDiv.style.display = 'none';

    function setParam(id, value) {
      if (!(id in values)) return;
      values[id] = Number(value);
      if (sliders[id]) { sliders[id].input.value = value; sliders[id].out.textContent = fmt(Number(value)); }
      board.update();
    }

    var highlightTimers = [];
    function highlight(ids) {
      ids.forEach(function (id) {
        var o = byId[id];
        if (!o) return;
        var sw = o.getAttribute('strokeWidth'), sz = o.getAttribute('size');
        var isPoint = typeof o.getAttribute('size') === 'number' && o.elementClass === JXG.OBJECT_CLASS_POINT;
        if (isPoint) o.setAttribute({ size: sz + 3 }); else o.setAttribute({ strokeWidth: (sw || 2) + 3 });
        highlightTimers.push(setTimeout(function () {
          if (isPoint) o.setAttribute({ size: sz }); else o.setAttribute({ strokeWidth: sw });
        }, 1200));
      });
    }

    function showStep(n) {
      if (!steps.length) return;
      var i = Math.max(0, Math.min(steps.length - 1, (typeof n === 'number' ? n : 1) - 1));
      current = i;
      var s = steps[i];
      stepText.innerHTML = '<span class="scene-kicker">Step ' + (i + 1) + ' of ' + steps.length + '</span>' + texToHtml(s.text || '');
      counter.textContent = 'Step ' + (i + 1) + ' of ' + steps.length;
      prev.disabled = i === 0; next.disabled = i === steps.length - 1;
      var changes = [];
      if (s.set) Object.keys(s.set).forEach(function (k) {
        setParam(k, s.set[k]);
        changes.push('sets ' + (sliders[k] ? sliders[k].label : k) + ' = ' + fmt(Number(s.set[k])));
      });
      if (s.show && s.show.length) changes.push('shows ' + s.show.map(function (id) { return meta[id] ? (labelFor(meta[id]) || id) : id; }).join(', '));
      if (s.hide && s.hide.length) changes.push('hides ' + s.hide.map(function (id) { return meta[id] ? (labelFor(meta[id]) || id) : id; }).join(', '));
      setNote.textContent = changes.length ? 'This step ' + changes.join('; ') + '.' : '';
      function setVis(id, v) {
        if (byId[id]) byId[id].setAttribute({ visible: v });
        (helpers[id] || []).forEach(function (o) { o.setAttribute({ visible: v }); });
      }
      (s.show || []).forEach(function (id) { setVis(id, true); });
      (s.hide || []).forEach(function (id) { setVis(id, false); });
      board.update();
      if (s.highlight) highlight(s.highlight);
    }
    prev.addEventListener('click', function () { showStep(current); });       // current is 0-based: step n = current+1
    next.addEventListener('click', function () { showStep(current + 2); });
    if (steps.length) showStep(1);

    function destroy() {
      highlightTimers.forEach(clearTimeout);
      try { JXG.JSXGraph.freeBoard(board); } catch (e) { /* ignore */ }
      container.innerHTML = '';
    }

    return { board: board, setParam: setParam, showStep: showStep, destroy: destroy, elements: byId, values: values };
  }

  // Lazy init: JSXGraph cannot measure a display:none container. Render once the container has a size.
  function renderSceneWhenVisible(containerId, scene, opts) {
    opts = opts || {};
    var container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    if (!container) throw new Error('renderSceneWhenVisible: no element ' + containerId);
    var done = false, handle = { board: null, setParam: function () {}, showStep: function () {}, destroy: function () { done = true; } };
    function go() {
      if (done) return;
      done = true;
      setTimeout(function () {
        var h = renderScene(container, scene, opts);
        if (h) { Object.assign(handle, h); if (opts.onReady) opts.onReady(handle); }
      }, 50);
    }
    function visible() { return container.offsetWidth > 0 && container.offsetHeight >= 0 && container.offsetParent !== null; }
    if (visible()) { go(); return handle; }
    if (window.IntersectionObserver) {
      var io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting && container.offsetWidth > 0; })) { io.disconnect(); go(); }
      });
      io.observe(container);
      // display:none containers never intersect: poll too
    }
    var poll = setInterval(function () {
      if (done) { clearInterval(poll); return; }
      if (visible()) { clearInterval(poll); go(); }
    }, 50);
    return handle;
  }

  window.renderScene = renderScene;
  window.renderSceneWhenVisible = renderSceneWhenVisible;
  window.sceneCompile = sceneCompile;
})();
