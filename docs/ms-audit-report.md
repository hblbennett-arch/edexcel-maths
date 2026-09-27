# Mark Scheme & Question Text Audit Report (Phase 2d)

Every transcribed mark scheme and question was compared with the official Pearson PDFs (rules: `docs/ms-audit-spec.md`; raw change lists: `data/processed/_ms_audit/`).
- **Corrections** fix factual mismatches (wrong numbers, signs, mark codes, missing conditions); each cites the MS/QP page it was checked against.
- **Editorial** changes wrap extractor-added explanation as `[editor: …]`; nothing was deleted.

## Summary

| Paper | MS editorial | MS corrections | Question editorial | Question corrections |
|---|---|---|---|---|
| P1_June2018 | 18 | 7 | 0 | 4 |
| P1_June2019 | 16 | 2 | 0 | 5 |
| P1_June2022 | 8 | 2 | 0 | 0 |
| P1_June2023 | 1 | 5 | 1 | 3 |
| P1_June2024 | 10 | 8 | 0 | 0 |
| P1_Oct2020 | 2 | 4 | 1 | 1 |
| P1_Oct2021 | 1 | 4 | 0 | 0 |
| P2_June2018 | 12 | 6 | 0 | 2 |
| P2_June2019 | 6 | 11 | 0 | 2 |
| P2_June2022 | 9 | 2 | 0 | 3 |
| P2_June2023 | 11 | 8 | 0 | 1 |
| P2_June2024 | 16 | 11 | 0 | 0 |
| P2_Oct2020 | 7 | 6 | 0 | 1 |
| P2_Oct2021 | 8 | 8 | 0 | 0 |
| **Total** | 125 | 84 | 2 | 22 |

## Every correction (please spot-check a few against the PDFs)

### P1 June2018
- [ ] **P1_June2018_Q5** (MS): `.../(...+ C*sin(2theta))` → `.../(...C*sin(theta)cos(theta))`  
  _Official intermediate form has C sin(theta)cos(theta) in the denominator, not C sin(2theta)._ — evidence: MS.txt line ~689/753 (garbled) / PDF page 11
- [ ] **P1_June2018_Q11** (MS): `e.g. sqrt(6/(10/11)) type relation reducing to sqrt(6) = (15/10)*sqrt(1183/968)-type working` → `e.g. sqrt(15/10) = 1183/968 oe sqrt(6) = 2*1183/968`  
  _Official A1: sqrt(15/10) = 1183/968 oe sqrt(6) = 2 x 1183/968; transcription garbled._ — evidence: MS.txt lines ~1895-1905 / PDF pages 20-21
- [ ] **P1_June2018_Q11** (MS): `final answer sqrt(6) ≈ 1183/968 (accept equivalent unsimplified fractions such as 2904/2368 before final simplification)` → `sqrt(6) = 1183/484 or sqrt(6) = 2904/1183 (sqrt(6) = 2*1183/968 = 1183/484 would imply all 3 marks)`  
  _Official final A1 is sqrt(6) = 1183/484 or 2904/1183; 1183/968 approximates sqrt(3/2), and 2904/2368 is not in the MS._ — evidence: MS.txt lines ~1905-1915 / PDF pages 20-21
- [ ] **P1_June2018_Q12** (MS): `about 6.58% each year` → `about 6.6% each year`  
  _Official scheme: 'Accept that the value rises by 6.6 % a year (ft on their p)'._ — evidence: MS.txt line ~1987 / PDF page 22
- [ ] **P1_June2018_Q13** (MS): `Alternative (by parts): M1: uses integration by parts` → `Alternative (by parts): M1: chooses by parts, applied the correct way round, and uses limits. B1: integral of (x+2)^(1/2) dx = (2/3)(x+2)^(3/2). M1: uses integr`  
  _Official by-parts scheme has M1 (choose method), B1 (integrate sqrt(x+2)), M1 (by parts) - transcription omitted the first M1/B1 and mislabelled._ — evidence: MS.txt lines ~2476-2560 / PDF page 25
- [ ] **P1_June2018_Q13** (MS): `A*x*(x+2)^(3/2) + C*(x+2)^(5/2). ddM1` → `A*x*(x+2)^(3/2) - C*(x+2)^(5/2). A1: (4/3)x(x+2)^(3/2) - (8/15)(x+2)^(5/2), which may be unsimplified. ddM1`  
  _Official sign is minus; official A1 for the correct integrated expression was omitted (alt only summed to 5 marks)._ — evidence: PDF page 25
- [ ] **P1_June2018_Q14** (MS): `A1: k = 37/4. Final range of values: {k : 7 <= k < 37/4}.` → `leading to k = 37/4. A1: range of values {k : 7 <= k < 37/4}.`  
  _Official: k=37/4 is reached within the discriminant M1; the final A1 is for the range in set notation._ — evidence: MS.txt line ~2593 / PDF page 26

### P1 June2018 (question-text pass)
- [ ] **P1_June2018_Q5** (question): `-3*pi/4 < theta < pi/4` → `-pi/4 < theta < 3*pi/4`  
  _Domain reversed; QP gives -pi/4 < theta < 3pi/4 (for both y and dy/dtheta)._ — evidence: QP PDF page 10
- [ ] **P1_June2018_Q7** (question): `(a) Show that the integral from x=k` → `Given that k ∈ Z^+, (a) show that the integral from x=k`  
  _Omitted stem condition 'Given that k ∈ Z+' from the QP._ — evidence: QP PDF page 16
- [ ] **P1_June2018_Q8** (question): `2*sin(30*t) degrees` → `2*sin(30*t)°`  
  _QP has sin(30t)° (argument in degrees); trailing 'degrees' after the formula reads as if D were measured in degrees (D is in metres)._ — evidence: QP PDF page 20
- [ ] **P1_June2018_Q11** (question): `sqrt((1+4x)/(1-x)) = 1 + (5/2)x - (5/8)x^2 + ...` → `sqrt((1+4x)/(1-x)) ≈ 1 + (5/2)x - (5/8)x^2`  
  _Part (a) on QP is an approximation '≈ 1 + 5/2 x - 5/8 x^2' with no '+ ...'._ — evidence: QP PDF page 30

### P1 June2019
- [ ] **P1_June2019_Q8** (MS): `referencing that between two relevant x-values` → `explaining that between x = -2 and x = 5.442 the area above the x-axis equals the area below the x-axis, or equivalent`  
  _Official main statement for B1 omitted/garbled in transcription._ — evidence: MS.txt lines 1608-1611, 1746 / PDF page 17-18
- [ ] **P1_June2019_Q9** (MS): `ab - a = -b^2 (or ab = a - b times b... i.e. a(b-1) = -b^2... rearranging to isolate a)` → `a/b = a - b => ... => ab - a = b^2, then a(b-1) = b^2`  
  _Wrong sign (official: ab - a = b^2, a(b-1) = b^2) plus transcription aside._ — evidence: MS.txt lines 1783-1786 / PDF page 19

### P1 June2019 (question-text pass)
- [ ] **P1_June2019_Q3** (question): `y = 5 - 5/(x+1)^2 (equivalently y = (5x^2+10x)/(x+1)^2)` → `y = (5x^2+10x)/(x+1)^2`  
  _Paper prints only y = (5x^2 + 10x)/(x + 1)^2; the '5 - 5/(x+1)^2' form and '(equivalently ...)' are extractor additions that give away the simplification._ — evidence: QP PDF page 6
- [ ] **P1_June2019_Q4** (question): `approximation related to 1/sqrt(2).` → `approximation to sqrt(2).`  
  _Paper: 'The expansion can be used to find an approximation to sqrt(2)'._ — evidence: QP PDF page 8
- [ ] **P1_June2019_Q4** (question): `Three possible values of x that could be substituted into the expansion are suggested: x = -14, x = 2, and x = -1/2 (each chosen because 1/sqrt(4-x) evaluates t` → `Possible values of x that could be substituted into this expansion are: x = -14 because 1/sqrt(4-x) = 1/sqrt(18) = sqrt(2)/6; x = 2 because 1/sqrt(4-x) = 1/sqrt`  
  _Paper lists each value with its explicit evaluation (sqrt(2)/6, sqrt(2)/2, sqrt(2)/3); transcription replaced these with an extractor paraphrase in brackets._ — evidence: QP PDF page 8
- [ ] **P1_June2019_Q4** (question): `most accurate approximation (1 mark)` → `most accurate approximation to sqrt(2) (1 mark)`  
  _Paper (b)(ii): '...would lead to the most accurate approximation to sqrt(2)'._ — evidence: QP PDF page 8
- [ ] **P1_June2019_Q12** (question): `The function H(t) = |10*e^(-t/4)*sin(t)|, t >= 0, is used to model the height, in metres, of a ball above the ground t seconds after it has been kicked. (b) Ske` → `(b) Sketch the graph of H against t where H(t) = |10*e^(-t/4)*sin(t)|, t >= 0, showing the long-term behaviour of this curve. (2 marks) The function H(t) is use`  
  _Sentence order: on the paper H(t) is defined inside part (b), and the modelling sentence comes after (b), before 'Using this model, find'._ — evidence: QP PDF page 34

### P1 June2022
- [ ] **P1_June2022_Q10** (MS): `multiplies/rearranges to remove the negative exponential term` → `simplifies the constant terms`  
  _Official M1 is for setting the equations equal and simplifying the constant terms (its example 220e^(0.05t)+35-800e^(-0.05t)=0 still contains the negative exponential); forming the quadratic is the A1._ — evidence: MS.txt line 1816 / PDF pages 21-22
- [ ] **P1_June2022_Q15** (MS): `A1ft: d^2S/dr^2 > 0` → `A1: d^2S/dr^2 > 0`  
  _Official scheme gives this mark as A1 (not A1ft); notes make it dependent on r = awrt 10 and a correct second derivative._ — evidence: MS PDF page 30 (Q15(c) marks column: M1, A1); MS.txt ~line 2952-2969

### P1 June2023
- [ ] **P1_June2023_Q2** (MS): `x = 0 is a solution (this mark cannot be scored if they proceed directly to the roots without taking a factor of x out first)` → `x = 0 is a solution`  
  _Official MS attaches 'This mark cannot be scored if they proceed directly to the roots ... without taking a factor of or dividing by x' to the A1, not the B1 (examples: '...=>0, (-5±sqrt185)/8 is M1B1A0'; '...=>4x^2+5x-10=0=>... is M1B0A1')._ — evidence: MS.txt lines 782-814 / PDF page 10
- [ ] **P1_June2023_Q2** (MS): `(and these values only), or exact equivalent;` → `(and these values only), or exact equivalent (ignore 0 for this mark); this mark cannot be scored if they proceed directly to the roots from 4x^3+5x^2-10x witho`  
  _Restores the A1 condition (moved from B1) and official "ignore 0 for this mark"._ — evidence: MS.txt lines 785-792 / PDF page 10
- [ ] **P1_June2023_Q4** (MS): `into the derivative and sets equal to 0, e.g. 2α + (1/2)(1 - α^2/2) = 0` → `into the derivative, e.g. 2α + (1/2)(1 - α^2/2)`  
  _Official M1 is just 'Fully substitutes cos x = 1 - x^2/2 into the derivative'; scheme line for M1 is 2α + ½(1 − α²/2) with no '= 0' (the =0 belongs to the dM1 3TQ line)._ — evidence: MS.txt lines 980-1049 / PDF page 12
- [ ] **P1_June2023_Q9** (MS): `with a comment that the numbers are getting smaller in magnitude` → `(do not withhold the mark if they add a comment such as "the numbers are getting smaller", which is condoned as referring to magnitude)`  
  _Official MS: listing two correct consecutive terms is sufficient; a comment like "the numbers are getting smaller" is condoned, not required._ — evidence: MS.txt lines 1983-1988 / PDF page 21
- [ ] **P1_June2023_Q9** (MS): `and k=2/3 (giving r=5/3>1) must be rejected with a reason` → `and reasoning which excludes k=2/3 (e.g. r=5/3, which is greater than 1) is allowed`  
  _Official MS: 'Allow reasoning which excludes k = 2/3 e.g. r = 5/3 which is greater than 1' - it is an allowed route, not a requirement._ — evidence: MS.txt lines 1994-1997 / PDF page 21
- [ ] **P1_June2023_Q13** (question): `around a track.
•` → `around a track.
On the ride, carriages complete multiple circuits of the track such that
•`  
  _QP: the sentence 'On the ride, carriages complete multiple circuits of the track such that' introduces the three bullets; transcription had moved it to the alternative-model paragraph._ — evidence: QP.txt line 1882 / QP PDF page 34
- [ ] **P1_June2023_Q13** (question): `On the ride, carriages complete multiple circuits of the track such that in an alternative model` → `In an alternative model`  
  _QP reads 'In an alternative model, the vertical height, H m, ...' (sentence fragment misplaced here)._ — evidence: QP PDF page 34
- [ ] **P1_June2023_Q15** (question): `x > (1/3)ln 2` → `x > ln(2^(1/3))`  
  _QP prints the domain as x > ln ∛2; transcription had rewritten it as (1/3)ln 2 (equivalent value, but not what the paper shows)._ — evidence: QP PDF page 40

### P1 June2024
- [ ] **P1_June2024_Q5** (MS): `P,Q ≠ 0` → `P,Q > 0`  
  _Official MS 5(a) M1: 'P,Q > 0'._ — evidence: MS.txt ~line 1081 / PDF page 13
- [ ] **P1_June2024_Q6** (MS): ` (tangency to the left-hand branch)` → ``  
  _Extractor aside and factually wrong: official k_min = ("5"-4)/"2" is the gradient of the line through (0,4) and the vertex P, not a tangency._ — evidence: PDF page 15 (6(c) scheme row)
- [ ] **P1_June2024_Q6** (MS): `Correct range k < 1/2 or k > 3 (acceptable notation joining the regions with 'and'/'∪', not 'or'/',')` → `Correct range 1/2 < k < 3 (acceptable notation: allow 'and' or '∩' to join the regions, but not 'or', ',' or '∪')`  
  _Official A1 answer is 1/2 < k < 3, joined with 'and'/'∩', not 'or'/','/'∪'; transcription had the complementary range and wrong symbol._ — evidence: MS.txt lines 1371-1372 / PDF pages 15-16
- [ ] **P1_June2024_Q9** (MS): `M1: Deduces expressions for the first term a and common ratio r using k=5/2 in the correct formulae. M1: Finds at least one of a = 243 or r = 1/3 (may be unproc` → `M1: Deduces expressions for the first term a and common ratio r using k=5/2 in the correct formulae and finds at least one of a = 243 or r = 1/3 (may be implied`  
  _Mark allocation mixed up: official first M1 = expressions AND at least one of a=243/r=1/3; second M1 = recall S∞ and substitute (|r|<1); A1 = cao 729/2._ — evidence: MS.txt lines 2104-2125 / PDF pages 21-22
- [ ] **P1_June2024_Q13** (MS): `(attempt at sqrt(a-a sin^2θ), not attempted first)` → `(attempt at sqrt(a-a sin^2θ), but not sqrt(a)-sqrt(a sin^2θ) unless sqrt(a-a sin^2θ) is attempted first)`  
  _Garbled: official g(θ) is an attempt at sqrt(a-a sin^2θ) but not sqrt(a)-sqrt(a sin^2θ) unless sqrt(a-a sin^2θ) attempted first._ — evidence: MS.txt line 3158 / PDF page 29
- [ ] **P1_June2024_Q13** (MS): `to convert an integral of the form ∫sinθcosθ*sinθcosθ dθ to the form ∫sin^2θcos^2θ dθ or ∫...sin^2(2θ) dθ` → `to convert an integral of the form ∫sin^2θcos^2θ dθ (or e.g. ∫sinθcosθ sin2θ dθ) to the form ∫...sin^2(2θ) dθ`  
  _Official dM1: converts ∫sin^2θcos^2θ dθ or ∫sinθcosθ sin2θ dθ to ∫...sin^2 2θ dθ; transcription had the target form wrong._ — evidence: MS.txt line 3188 / PDF page 30
- [ ] **P1_June2024_Q13** (MS): `θ/4 - (1/8)sin4θ` → `θ/2 - (1/8)sin4θ`  
  _Official A1: μ∫sin^2 2θ dθ → (μ/2)(θ - (1/4)sin4θ); with μ=1 this is θ/2 - (1/8)sin4θ._ — evidence: MS.txt line 3238 / PDF pages 29-30
- [ ] **P1_June2024_Q15** (MS): `3x+2y≤2x-5y` → `3x+2y>2x-5y`  
  _Official ddM1 justification is 3x+2y > 2x-5y (because x and y are positive)._ — evidence: MS.txt line 4150 / PDF page 37

### P1 Oct2020
- [ ] **P1_Oct2020_Q2** (MS): `210log(4/5) +/- 1` → `210log(5/4) +/- 1`  
  _Official MS dM0 example: '3p = 210 log(5/4) ± 1'._ — evidence: PDF page 7 (MS.txt notes for Q2, 'Use of incorrect log laws')
- [ ] **P1_Oct2020_Q6** (MS): `(a version with a coefficient slip, e.g. missing the factor of 2 inside the sine term, can score M1 A0 A1 as a special case)` → `(a version missing the pi/12 chain-rule factors, d(theta)/dt = cos(pi*t/12-3) - 2*sin(pi*t/12-3) = 0 => tan(pi*t/12-3) = 1/2 => t = 13.23 = 13:14, can score M1 `  
  _Official SC line is dθ/dt = cos(πt/12−3) − 2sin(πt/12−3) = 0, i.e. the π/12 factors are missing, not the factor of 2._ — evidence: PDF page 11 (MS.txt Q6 notes, differentiation alternative)
- [ ] **P1_Oct2020_Q11** (MS): `(10^2+10^2-39/4)` → `(10^2+10^2-39)`  
  _Official: cos AOB = (10^2+10^2-(sqrt39)^2)/(2*10*10) = 161/200; AB^2 = 39, not 39/4._ — evidence: PDF page 18
- [ ] **P1_Oct2020_Q11** (MS): `10*2*pi + 40*2*pi - 10*0.635` → `10*2*pi + sqrt(40)*2*pi - 10*0.635`  
  _Official embedded example: 2π10 + 2π√40 − 10×0.635 (radius of C2 is sqrt(40))._ — evidence: PDF page 18

### P1 Oct2020 (question-text pass)
- [ ] **P1_Oct2020_Q4** (question): `x != 2.` → `x in R, x != 2.`  
  _Official QP p.8 gives the domain as 'x ∈ ℝ, x ≠ 2'; transcription omitted 'x ∈ ℝ'._ — evidence: QP PDF page 8

### P1 Oct2021
- [ ] **P1_Oct2021_Q4** (MS): `2x(2x^2-4x+5) ± g(x) = 0` → `ax(2x^2-4x+5) ± g(x) = 0`  
  _Official dM1 note: 'Look for ax(2x^2 - 4x + 5) ± g(x) = 0 o.e.' (general coefficient a, not 2)._ — evidence: MS.txt lines 688-692 / PDF page 11
- [ ] **P1_Oct2021_Q8** (MS): `(just the answer with no model shown scores SC 1,0)` → `(just the answer from a correct model equation scores SC 1,0)`  
  _Official note: 'Just the answer from a correct model equation score SC 1,0.' Transcription reversed the condition._ — evidence: MS.txt lines 1546-1549 / PDF page 17
- [ ] **P1_Oct2021_Q10** (MS): `cos2θ = 2cos2x-1` → `cos2θ = 2cos^2x-1`  
  _Official example of mixed variables is 'cos2θ = 2cos²x − 1' (squared cos x); transcription dropped the square._ — evidence: MS.txt line 1929 / PDF page 21
- [ ] **P1_Oct2021_Q10** (MS): `sin2x=1/3 or cos2x=1/3 forms may also appear en route after use of double angle formulae` → `sin^2 x = 1/3 or cos^2 x = 2/3 may also be seen after use of double angle formulae`  
  _Official A1 note: 'You may see sin² x = 1/3 or cos² x = 2/3 after use of double angle formulae.'_ — evidence: MS.txt lines 1933-1940 / PDF page 21

### P2 June2018
- [ ] **P2_June2018_Q1** (MS): `(or 4.4/4.44...)` → `(or 4 4/9 or 4.4 recurring; 4.4 or 4.444... without reference to an exact form is A0)`  
  _Official MS accepts 40/9, 4 4/9 or 4.4-recurring; note says 'Give A0 for 4.4 or 4.444... without reference to 40/9 or 4 4/9 or 4.4-recurring'._ — evidence: PDF page 8 (Q1(a) A1 and Note)
- [ ] **P2_June2018_Q4** (MS): `(a=8, d=5, n=16, i.e. 5r term starting at 5 with common difference 5, using the AP sum formula)` → `(a=8, d=5, n=16, for the sum of (3+5r))`  
  _Extractor's aside was wrong: Way 1 AP is sum of (3+5r), first term 8, not a '5r term starting at 5'. Official: 'Correct method for finding the sum of an AP with a=8, d=5, n=16' = 16/2(2(8)+15(5))._ — evidence: PDF pages 14-15 (Q4(i) Way 1 scheme and 2nd M1 note)
- [ ] **P2_June2018_Q5** (MS): `(equivalently, f'(0)=0 so the formula is undefined — division by zero)` → `(isolated reasons such as 'you cannot divide by 0', 'the NR formula is undefined at x=0' or 'at x=0, f'(x1)=0' score B0)`  
  _Transcription contradicts MS: the official note gives B0 for these isolated division-by-zero / f'(x1)=0 reasons._ — evidence: PDF page 17 (Q5(c) Note)
- [ ] **P2_June2018_Q12** (MS): `and factorises out tan(x)*sin(2x), leaving (sec^2(x)-5-3tan(x))=0 as the remaining factor to solve. A1: uses sec^2(x)=1+tan^2(x) to reach the correct 3-term qua` → `uses the key step sec^2(x)=1+tan^2(x) and cancels/factorises out tan(x) (or (1-cos(2x)) or sin(2x)) to produce a quadratic in tan(x), e.g. 1+tan^2(x)-5=3tan(x).`  
  _Mark allocation mixed up: official M1 is 'the key step of sec^2x=1+tan^2x and cancels/factorises out tan x or (1-cos2x) or sin2x to produce a quadratic'; A1 is just 'Correct 3TQ in tan x'._ — evidence: PDF pages 34-35 (Q12(b) scheme and notes)
- [ ] **P2_June2018_Q13** (MS): `M1: attempts the area under the curve (region R1, from x=1 — where the curve crosses the x-axis, since x*ln(x)=0 at x=1 — to x=e) using integration by parts: in` → `M1: attempts either the area under the curve, integral from 1 to e of x*ln(x) dx, with limits e and 1 and some attempt to substitute these and subtract, or the `  
  _Transcription dropped a mark (listed 9 marks for a 10-mark question) and merged marks: official has separate M1 (area attempt: curve from 1 to e or area under line), M1 (by parts the correct way round), dM1 (integrates second term), A1. Also removed extractor aside about x=1._ — evidence: PDF page 36 (Q13 scheme and notes)
- [ ] **P2_June2018_Q14** (MS): `B1: P = 300` → `B1: P = 300 (or accept 299)`  
  _Official scheme: 'either one of 299 or 300'; note '300 (or accept 299)'._ — evidence: PDF pages 38-39 (Q14(d))

### P2 June2018 (question-text pass)
- [ ] **P2_June2018_Q11** (question): `f(x) = (1 + 11x - 6x^2) / [(x-3)(1-2x)], x > 3, where (1+11x-6x^2)/[(x-3)(1-2x)] = A + B/(x-3) + C/(1-2x). (a) Find the values of the constants A, B and C. (4 m` → `(1 + 11x - 6x^2) / [(x-3)(1-2x)] ≡ A + B/(x-3) + C/(1-2x). (a) Find the values of the constants A, B and C. (4 marks) f(x) = (1 + 11x - 6x^2) / [(x-3)(1-2x)], x`  
  _Official QP p.30: the identity (with ≡, not =) is stated first, then part (a); f(x) = ..., x > 3 is defined only after part (a), before part (b). Transcription had moved the f(x) definition ahead of (a) and joined the identity with 'where ... ='._ — evidence: QP PDF page 30
- [ ] **P2_June2018_Q12** (question): `1 - cos(2*theta) =` → `1 - cos(2*theta) ≡`  
  _Official QP p.34: '1 − cos 2θ ≡ tan θ sin 2θ' is an identity (≡), not an equation._ — evidence: QP PDF page 34

### P2 June2019
- [ ] **P2_June2019_Q8** (MS): `(ii) M1: Some evidence of applying the subtraction law of logs and beginning to solve the problem, e.g. writing (or combining) at least three terms of the sum, ` → `(ii) Way 1: M1: Some evidence of applying the addition law of logarithms as part of a valid proof, e.g. log_5(3/2 * 4/3 * ... * 50/49). M1: Begins to solve the `  
  _Methods mixed up: official Way 1 1st M1 is the addition law of logs and 2nd M1 is writing at least three terms; the subtraction law and the bracketed telescoping form belong to Way 2 (M1 subtraction law, M1 three terms of each)._ — evidence: MS.txt lines 2549-2552, 2648-2659 / PDF pages 22-24
- [ ] **P2_June2019_Q9** (MS): `(ft on their k, n provided a sensible model results)` → `(a thinking distance of awrt 13 and a value of d in the range [81.5, 88.5] are required for A1ft)`  
  _Official A1ft condition is stated specifically, not 'sensible model'._ — evidence: MS.txt line 2964 / PDF page 26
- [ ] **P2_June2019_Q12** (MS): `[cos(3theta)*cos(theta) - sin(3theta)*sin(theta)] / [sin(theta)*cos(theta)]` → `[cos(3theta)*cos(theta) + sin(3theta)*sin(theta)] / [sin(theta)*cos(theta)]`  
  _Sign error: cos3θ/sinθ + sin3θ/cosθ gives numerator cos3θcosθ + sin3θsinθ._ — evidence: PDF page 33 (Way 1, MS.txt line 3740)
- [ ] **P2_June2019_Q12** (MS): `cos(3theta+theta) = cos(4theta)` → `cos(3theta-theta) = cos(2theta)`  
  _Official: numerator = cos(3θ − θ) = cos 2θ, not cos 4θ._ — evidence: PDF page 33 / MS.txt lines 3743-3744, 3951
- [ ] **P2_June2019_Q12** (MS): `cos(4theta) / [(1/2)*sin(2theta)] = 2*cot(2theta)` → `cos(2theta) / [(1/2)*sin(2theta)] = 2*cot(2theta)`  
  _Official final line cos2θ / (½ sin2θ) = 2cot2θ._ — evidence: PDF page 33 / MS.txt lines 3749-3752
- [ ] **P2_June2019_Q13** (MS): `A = 2*pi*r^2 + 2*pi*r*h + (2/3)*pi*r^2, using h from the volume constraint` → `A = 2*pi*r^2 + 2*pi*r*(6/(pi*r^2) - (2/3)*r) + pi*r^2`  
  _Wrong expression: official A1 is 2πr² (hemisphere) + 2πr(6/(πr²) − 2r/3) (curved surface) + πr² (base); '(2/3)πr²' term is wrong._ — evidence: PDF page 36 / MS.txt lines 4180, 4287
- [ ] **P2_June2019_Q13** (MS): `differentiates r^-1 and r^2 terms correctly in form/sign` → `differentiates lambda/r + mu*r^2 to give alpha*r^-2 + beta*r; lambda, mu, alpha, beta not equal to 0`  
  _Official M1 requires only the form alpha*r^-2 + beta*r, not correct signs._ — evidence: PDF page 36 / MS.txt line 4302
- [ ] **P2_June2019_Q13** (MS): `A1: minimum surface area = awrt (nearest integer) m^2, consistent with their r.` → `A1ft: A = 17 (m^2) or awrt 17 (m^2) (ft only for 0.6 <= their r <= 1.3 found from dA/dr = 0 in (b)).`  
  _Value 17 missing and mark code is A1ft in official MS._ — evidence: PDF pages 36-37 / MS.txt lines 4224, 4264, 4410-4411
- [ ] **P2_June2019_Q14** (MS): `A1: Integrates to give -8*ln|u| + 2u {+c}` → `M1: Integrates to give an expression of the form D*ln(u) + E*u; D, E not equal to 0 (with or without a constant of integration). A1: Integrates to give -8*ln|u|`  
  _Missing mark: official (a) is B1 M1 M1 M1 A1 A1* (6 marks); the 3rd M1 (D ln u + Eu) was omitted._ — evidence: PDF pages 38-39 / MS.txt line 4711
- [ ] **P2_June2019_Q14** (MS): `Integrates t^0.25 to give (4/5)*t^1.25` → `Integrates t^0.25 to give lambda*t^1.25, lambda not equal to 0`  
  _Official M1 is for the form λt^1.25._ — evidence: PDF page 38 / MS.txt line 4832
- [ ] **P2_June2019_Q14** (MS): `-8*ln|4-sqrt(h)| - 2*sqrt(h) = (4/5)*t^1.25 {+ constant}` → `-8*ln|4-sqrt(h)| - 2*sqrt(h) = (1/25)*t^1.25 {+ constant} (or 20(-8*ln|4-sqrt(h)| - 2*sqrt(h)) = (4/5)*t^1.25)`  
  _Wrong coefficient: with dh/(4-sqrt(h)) = (t^0.25/20) dt the RHS integrates to (1/25)t^1.25; (4/5)t^1.25 only pairs with the LHS multiplied by 20 (Way 2)._ — evidence: PDF page 38 (Way 1 and Way 2)

### P2 June2019 (question-text pass)
- [ ] **P2_June2019_Q12** (question): `90° <= theta <= 180°` → `90° < theta < 180°`  
  _Paper prints the strict range 90° < θ < 180° for part (b)._ — evidence: QP PDF page 36
- [ ] **P2_June2019_Q9** (question): `with k = awrt 0.017` → `with k ≈ 0.017`  
  _Paper prints 'with k ≈ 0.017'; 'awrt' is mark-scheme language inserted by the extractor._ — evidence: QP PDF page 24

### P2 June2022
- [ ] **P2_June2022_Q9** (MS): `H = '±' 50 sin((1/4)t + 1.15)°` → `H = |'±' 50 sin((1/4)t + 1.15)°|`  
  _Official MS answer has modulus: H = |"±"50 sin(1/4 t + 1.15)°|._ — evidence: MS PDF page 22 (MS.txt ~line 2461)
- [ ] **P2_June2022_Q9** (question): `H = A sin(bt + alpha)°, where` → `H = |A sin(bt + alpha)°|, where`  
  _QP model is H = |A sin(bt + α)°| (modulus missing)._ — evidence: QP PDF page 22 (QP.txt line 1070)
- [ ] **P2_June2022_Q9** (question): `form H = A sin(bt + alpha)° + d` → `form H = |A sin(bt + alpha)°| + d`  
  _QP part (b) model is H = |A sin(bt + α)°| + d (modulus missing)._ — evidence: QP PDF page 22 (QP.txt line 1090)
- [ ] **P2_June2022_Q11** (MS): `Alternative valid approaches (via logic on odd×even parity, or by contradiction assuming n(n^2+5) is odd and deriving a contradiction) are also accepted and mar` → `Alternative approaches: a solution by contradiction (assume n(n^2+5) is odd, deduce n and n^2+5 are both odd, set n^2+5 = 2k+1 so n^2 = 2(k-2) is even, contradi`  
  _Official MS gives logic-only solutions a special case SC 1010 (max 2 marks), not the full structure._ — evidence: MS.txt lines 3076-3148 / PDF page 27
- [ ] **P2_June2022_Q14** (question): `0 <= t <= k` → `t >= k`  
  _QP states V ≥ 0, t ≥ k._ — evidence: QP PDF page 36

### P2 June2023
- [ ] **P2_June2023_Q4** (MS): `sets it equal to -7.5 (a decrease)` → `sets it equal to ±7.5`  
  _Official note: "sets = ±7.5" (Case 1 with +7.5 still scores M1M1A0); "(a decrease)" is an aside._ — evidence: MS PDF p.12 notes (b) second M1; MS.txt ~line 527
- [ ] **P2_June2023_Q5** (MS): `sets this equal to -10 (using the point P(3,-10))` → `sets this equal to ±10 [editor: using the point P(3,-10)]`  
  _Official dM1: "sets this equal to ±10"; parenthetical is extractor gloss._ — evidence: MS PDF p.13 notes (b) dM1
- [ ] **P2_June2023_Q9** (MS): `(depends on rearranging correctly first - e.g. t = sqrt(x+25) - 3 substituted directly is M0)` → `(e.g. t = sqrt(x+25) - 3 -> y = 6ln(sqrt(x+25) - 3) is M0)`  
  _Official example is an incorrect substitution y = 6ln(sqrt(x+25) - 3), not a ban on substituting t = sqrt(x+25) - 3; "depends on rearranging correctly first" is not in MS._ — evidence: MS PDF p.21 Way 1 second M1; MS.txt ~line 1183
- [ ] **P2_June2023_Q9** (MS): `dy/dt / dx/dt = 6/(2*2+6) = 3/25` → `dy/dt / dx/dt = (6/(2+3))/(2*2+6) = 6/50 = 3/25`  
  _Arithmetic wrong as transcribed (6/(2*2+6) = 3/5); official: (6/5)/(2x2+6) = 6/50 = 3/25._ — evidence: MS PDF p.20 (b) M1 and p.22 notes
- [ ] **P2_June2023_Q11** (MS): `...h^(3/2) = t + c oe` → `...h^(3/2) = λt + c oe`  
  _Official M1: "...h^(3/2) = λt {+c}" (λ dropped in pdftotext)._ — evidence: MS PDF p.26 (b) M1 and p.27 notes
- [ ] **P2_June2023_Q11** (MS): `A1: (2/3)h^(3/2) = t (+c) oe` → `A1: (2/3)h^(3/2) = λt (+c) oe`  
  _Official A1: "(2/3)h^(3/2) = λt (+c) oe" (λ dropped in pdftotext)._ — evidence: MS PDF p.26/27 (b) A1
- [ ] **P2_June2023_Q14** (MS): `360 <= x <= 540 (but not 450) for their cosx = k, k ≠ 1` → `360 < x < 540 (but not 450) for their cosx = k, |k| < 1`  
  _Official dM1: "range 360 < x < 540 (but not 450) for their cos x = k where |k| < 1"._ — evidence: MS PDF p.38 notes (b) dM1; MS.txt ~line 2855
- [ ] **P2_June2023_Q15** (MS): `sin^2x ∓ 2sinx cosx + cos^2x < 1 (i.e.` → `sin^2x ± k sinx cosx + cos^2x where k = 1 or 2 (e.g.`  
  _Official M1: "sin^2x ± k sinx cosx + cos^2x where k = 1 or 2 o.e."_ — evidence: MS PDF p.39 notes M1; MS.txt ~line 2886
- [ ] **P2_June2023_Q14** (question): `x ≠ 450° (4)` → `x ∈ ℝ, x ≠ 450° (4)`  
  _QP shows "x ∈ ℝ   x ≠ 450°"; x ∈ ℝ omitted in transcription._ — evidence: QP PDF p.42

### P2 June2024
- [ ] **P2_June2024_Q3** (MS): `(note B0B1 is not a valid mark profile — the x-coordinate must be correct to score the second mark)` → `(note B0B1 is not a possible mark profile)`  
  _Official MS says only 'Note that B0B1 is not a possible mark profile.' The added claim that only the x-coordinate must be correct is wrong: the second B1 needs both coordinates._ — evidence: MS.txt lines 565-566 / PDF page 10
- [ ] **P2_June2024_Q5** (MS): `but do not allow an incomplete denominator such as 1 − (3θ)^2/2 written as just (3θ)^2/2 without the '1 −'` → `but do not allow e.g. θ×2θ / [1 − (3θ)^2/2], as this suggests they are approximating θ tan 2θ / cos 3θ`  
  _Official MS disallows the denominator 1 − (3θ)^2/2 (missing the outer '1 −'), because it approximates θtan2θ/cos3θ; transcription described it the wrong way round._ — evidence: MS.txt lines 835-876 / PDF page 13
- [ ] **P2_June2024_Q6** (MS): `e^(4x^2-1) = 2/x^2` → `e^(4x^2-1) = 1/x^2`  
  _Official MS: 8xe^(4x^2-1) = 8/x => e^(4x^2-1) = 1/x^2 (general form '.../x^2')._ — evidence: MS.txt lines 1208, 1296 / PDF page 16
- [ ] **P2_June2024_Q6** (MS): `ln(2/x^2)` → `ln(1/x^2)`  
  _Official MS: 4x^2 − 1 = ln(1/x^2)._ — evidence: MS.txt lines 1208-1213 / PDF page 16
- [ ] **P2_June2024_Q6** (MS): `A,B ≠ 0` → `A×B > 0`  
  _Official MS condition is 'A × B > 0'._ — evidence: PDF page 16 (MS.txt line 1296 garbled)
- [ ] **P2_June2024_Q8** (MS): `2sinθ/(sinθcos^2θ) = 2/cos^2θ = 2tanθsecθ` → `(2/sinθ)×(sin^2θ/cos^2θ) = 2tanθsecθ, or 2sinθ/cos^2θ = 2tanθsecθ`  
  _Official MS Way 1: 2cosecθ/cot^2θ ≡ (2/sinθ)×(sin^2θ/cos^2θ) ≡ 2tanθsecθ, or 2sinθ/cos^2θ ≡ 2tanθsecθ. Transcribed chain was mathematically wrong (2/cos^2θ = 2sec^2θ, not 2tanθsecθ)._ — evidence: MS.txt lines 1872-1887 / PDF page 22
- [ ] **P2_June2024_Q9** (MS): `together with dH/dx=0 at x=9` → `or dH/dx=0 at x=9`  
  _Official M1 needs the constant term plus EITHER (20, 0.8) OR dH/dx = 0 at x = 9 (one equation in a and b); using both is the dM1._ — evidence: MS.txt lines 2433-2439 / PDF page 27
- [ ] **P2_June2024_Q9** (MS): `to set up equations in a and b` → `to give an equation in a and b`  
  _Official M1: 'to give an equation in a and b'._ — evidence: MS.txt lines 2433-2439 / PDF page 27
- [ ] **P2_June2024_Q12** (MS): `t = 4/3 hours = awrt 43 minutes (or exact 24 ln 6 minutes) — units must be minutes` → `t = awrt 43 minutes (or exact 24 ln 6); units are not required but if given must be minutes (the value in hours, 0.7167..., scores A0)`  
  _Official MS: 'Correct value of 43 or awrt 43.0 or exact value of 24ln6. Units are not required but if any are given it must be minutes... in hours the time is 0.7167037877... and scores A0'. '4/3 hours' is wrong (4/3 h = 80 min)._ — evidence: MS.txt lines 3592-3594 / PDF page 37
- [ ] **P2_June2024_Q13** (MS): `substitutes t=26` → `substitutes t = 25, 26 or 27 (scheme uses t = 26)`  
  _Official MS M1: 'Substitutes t = 25 or 26 or 27 into their model'._ — evidence: MS.txt line 3877 / PDF page 40
- [ ] **P2_June2024_Q15** (MS): `A1: correct term 3(x+y)^2(1 + dy/dx). A1: correct differentiation of the other side, 6x - 3(dy/dx).` → `A1: either 3(x+y)^2(1 + dy/dx) or 6x - 3(dy/dx) correct. A1: both 3(x+y)^2(1 + dy/dx) and 6x - 3(dy/dx) correct (seen separately or equated).`  
  _Official MS: first A1 for EITHER correct side, second A1 for BOTH; transcription allocated one A1 to each side._ — evidence: MS.txt lines 4414-4427 / PDF page 45

### P2 Oct2020
- [ ] **P2_Oct2020_Q4** (MS): `and 2^4 or 24 (may be implied)` → `and 2 or 2^4 (may be implied)`  
  _Official MS p.11: bullet reads '2 or 2^4 (may be implied)'._ — evidence: MS.txt line 677 / PDF page 11
- [ ] **P2_Oct2020_Q4** (MS): `attempt at 7C4 × 2^4,` → `attempt at 7C4 × 2 or 7C4 × 2^4,`  
  _Official MS p.11 dM1: 'their "560" must be an attempt at 7C4×2 or 7C4×2^4'._ — evidence: MS.txt lines 782-785 / PDF page 11
- [ ] **P2_Oct2020_Q7** (MS): `3sqrt(x) + 1/(2sqrt(x)) - 4/x` → `3sqrt(x) + 1/(4sqrt(x)) - 4/x`  
  _Official MS p.14: dy/dx = 3sqrt(x) + 1/(4sqrt(x)) - 4/x = (12x^2+x-16sqrt(x))/(4x sqrt(x))._ — evidence: MS.txt lines 1102-1110 / PDF page 14
- [ ] **P2_Oct2020_Q8** (MS): `and used f(-4)=0, or long` → `and used f(±4)=0, or long`  
  _Official MS p.16 second dM1: 'used f(±4) = 0 or long division/comparing coefficients'._ — evidence: MS.txt line 1469 / PDF page 16
- [ ] **P2_Oct2020_Q10** (MS): `cos 2x + 3cos x - 4cos^3 x = 0` → `cos^2 x + 3cos x - 4cos^3 x = 0`  
  _Official MS p.19: 1 - cos3x = sin^2 x => cos^2 x + 3cos x - 4cos^3 x = 0 (pdftotext dropped the superscript)._ — evidence: MS.txt line 1675 / PDF page 19
- [ ] **P2_Oct2020_Q14** (MS): `using y = 12 - 2x substituted` → `using y = 12 ± 2x substituted`  
  _Official MS M1 note: 'using y = 12 ± 2x and their circle equation'._ — evidence: MS.txt line 2393 / PDF page 26

### P2 Oct2020 (question-text pass)
- [ ] **P2_Oct2020_Q12** (question): `Figure 4 shows part of the curve used to model the profile of a small dam.` → `Part of the curve is used to model the profile of a small dam, shown shaded in Figure 4.`  
  _Official QP wording: 'Part of the curve is used to model the profile of a small dam, shown shaded in Figure 4.' Transcription said Figure 4 shows the curve; it shows the shaded dam._ — evidence: QP PDF page 34

### P2 Oct2021
- [ ] **P2_Oct2021_Q3** (MS): `still happens to reach the correct final equation and answer does not score full marks for the flawed step` → `still happens to reach the correct final equation and answer scores only B1M0A0`  
  _Official guidance on particular cases awards B1M0A0 for these flawed splits (not a vague 'not full marks')._ — evidence: MS.txt lines 440-466 / PDF page 8
- [ ] **P2_Oct2021_Q4** (MS): `3(1 - sin^2(θ/2))` → `3(1 - sin^2 θ)`  
  _Official dM1 example uses 3cos^2 θ = 3(1 - sin^2 θ) ≈ 3(1 - θ^2); sin^2(θ/2) would not give 3(1 - θ^2)._ — evidence: MS.txt line 558 / PDF page 9
- [ ] **P2_Oct2021_Q5** (MS): `(do not be too concerned with the exact interval chosen, as long as it stays within x<1.4)` → `(do not be too concerned with the interval for the method mark)`  
  _Official: 'Do not be too concerned with the interval for the method mark'; the x < 1.4 restriction applies to the A1, not the M1._ — evidence: MS.txt lines 866-882 / PDF page 11
- [ ] **P2_Oct2021_Q5** (MS): `(values given should be correct but be generous with accuracy)` → `(values given should be correct but be generous with accuracy; the interval must be where x < 1.4)`  
  _Official A1 note: 'The interval must be where x < 1.4' (moved from the M1 where it was misattributed)._ — evidence: MS.txt line 882 / PDF page 11
- [ ] **P2_Oct2021_Q9** (MS): `a = 9/16 and r = -3/4` → `a = 9/16 and r = ±3/4`  
  _Official M1 note: 'with a = 9/16 and r = ±3/4' (sign of r not required for M1)._ — evidence: MS.txt lines 1930-1934 / PDF page 18
- [ ] **P2_Oct2021_Q11** (MS): `i.e. reaches x = 5k/3` → `allow for reaching k = ... or x = ... as long as the required equation is being solved`  
  _Official M1 does not require the correct value: 'Allow this mark for reaching k = … or x = … as long as they are solving the required equation.'_ — evidence: MS.txt line 2190 / PDF page 20
- [ ] **P2_Oct2021_Q12** (MS): `Cao: Area = 104/3 - 2 ln 5` → `Cao: 104/3 - 2 ln 5 (allow equivalents e.g. 208/6)`  
  _Official A1 is 'Cao (Allow equivalents for 104/3 e.g. 208/6)'; the integral is not labelled an area._ — evidence: MS.txt line 2532 / PDF page 23
- [ ] **P2_Oct2021_Q13** (MS): `Obtains dx/dθ = 2cos2θ and attempts` → `Obtains dx/dθ = k cos2θ (or α cos^2θ + β sin^2θ from the product rule on sinθcosθ) and attempts`  
  _Official M1 requires only dx/dθ = k cos 2θ or α cos^2θ + β sin^2θ, not the exact 2cos2θ._ — evidence: MS.txt line 2663 / PDF page 24

