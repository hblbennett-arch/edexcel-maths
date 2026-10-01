You write two extra depths of a worked solution for one part of an A level Mathematics question, for students revising on their own. You are given the question (stem and this part), the part's mark scheme (codes in order, what each mark is for), the standard worked solution, and the final answers. Produce `brisk` and `every_step` in the requested JSON. Both must reach the same final answers as the standard solution, by the same route the mark scheme rewards.

## brisk
What a strong, confident student would actually write in the exam. One entry per mark or pair of marks. No prose beyond a word or two ("so", "at $x=1$:"). Each entry has `secures`: a list of the scheme codes that line earns. Every scheme code of the part must appear in exactly one `secures` list, in the scheme's order (the first entry earns the first code(s), and so on). Use the codes exactly as printed in the scheme (for example `M1`, `A1`, `dM1`, `A1ft`, `A1*`, `B1`).

## every_step
Every algebraic manipulation written out as its own line: no "simplifying gives", no "rearranging", no two moves in one line. Expanding a bracket, collecting terms, moving a term to the other side, factorising, substituting a value, evaluating a power, cancelling: each is its own line. Each entry has:
- `working`: the maths of that line, in `$...$` (a short label such as "At $x = 6$:" is fine).
- `why`: one or two sentences, in the second person ("you", "your"), in plain words, saying why you take this step and what you did to get from the previous line. Gloss any technical word the first time you use it ("integrate, which undoes differentiating"). Never empty.
- `secures`: the scheme code this line earns, or `null` when the line earns nothing on its own. Every code of the scheme should be secured by some line, in scheme order.
- `check`: an optional one-line way to verify the line (substitute back, differentiate back, check units, check the sign or the size of the number), or `null`.
Aim for two to four times as many lines as the standard solution, and never fewer.

## Both levels
- The last `working` of each level states the final answer(s) of the part in full, exactly matching the given answers (same exact form, or the same rounding where a number of decimal places or significant figures is asked for). If the part has several answers, the last line lists them all. For a hypothesis test or a comparison, the last line still shows the decisive number, e.g. "$p = 0.0304 < 0.05$, so reject $H_0$".
- For a "show that" part, the last line ends with the printed result, reached from the line before it.
- Maths goes in `$...$` only (`$$...$$` for a displayed line). No `\( \)` or `\[ \]`. Write LaTeX that KaTeX renders: `\frac{\mathrm{d}y}{\mathrm{d}x}`, `\ln`, `\sin`, `\int_1^6 \ldots \,\mathrm{d}x`, `\leqslant`, `\mathrm{P}(X \leqslant 3)`.
- Use this question's actual numbers and letters throughout; never speak generally when you can point at a value in the working.
- Your own words. Do not name any exam board, do not mention examiners, mark schemes, past papers or reports. Do not copy sentences from the mark scheme text you are given: say what the line does, not how a mark is awarded.
- Steps are numbered from 1 in each level.
