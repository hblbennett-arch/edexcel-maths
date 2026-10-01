/*
 * Safe expression compiler for interactive scenes (docs/learn-layer-spec.md §2, "Expression grammar").
 *
 * The section between SCENE COMPILER BEGIN / END is copied verbatim into chatbot/static/scene.js: the two
 * copies MUST stay byte-identical (eval/scene_selftest.py checks this). Edit here, then paste into scene.js.
 *
 * Node use (eval/scene_selftest.py):
 *   echo '[{"expr":"-x^2 + 8*x - 5","vars":{"x":2},"params":[]}]' | node scene_compile.js
 *   -> [{"ok":true,"value":7,"js":"..."}]  or  [{"ok":false,"error":"...","token":"..."}]
 */
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

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { tokenise: sceneTokenise, validate: sceneValidate, toJS: sceneToJS, compile: sceneCompile,
    SceneExprError: SceneExprError, FUNCS: SCENE_FUNCS, CONSTS: SCENE_CONSTS, STATS: SCENE_STATS };
  if (require.main === module) {
    var input = '';
    process.stdin.on('data', function (d) { input += d; });
    process.stdin.on('end', function () {
      var cases = JSON.parse(input || '[]');
      var res = cases.map(function (c) {
        try {
          var r = sceneCompile(c.expr, c.params || []);
          return { ok: true, value: r.fn(c.vars || {}), js: r.js };
        } catch (e) {
          return { ok: false, error: e.message, token: e.token === undefined ? null : e.token };
        }
      });
      process.stdout.write(JSON.stringify(res));
    });
  }
}
