# Stats & Mechanics taxonomy: DRAFT for your review

Built 2026-09-26 in one Opus 5.5 call (`scripts/draft_taxonomy.py`, $0.98) from the 88 kept 9MA0 Paper 3 questions (15 papers), the 9MA0 Stats/Mech spec statements, and the existing Pure vocabulary's shared skills (reused, not duplicated). **Nothing has been tagged yet.** Tagging waits for your OK.

Same design as Pure: **question types** (narrow, "the same kind of question", one per question) and **skills** (broad, several per part, for the "practise the step you struggled with" ladder). Formula-booklet flags were checked against the real booklet PDF (15 of them by hand, noted in the JSON).

How to review (~20 min): skim the topic and type tables (is each question in a sensible bucket?), then the decisions. Reply e.g. "merge X and Y", "rename Z", "decision 3: two types".

## Topics

| id | title |
|---|---|
| stats-data-and-sampling | Sampling, Data Presentation & Summary Statistics |
| stats-bivariate-data | Correlation & Regression |
| stats-probability | Probability |
| stats-distributions | Statistical Distributions (Discrete, Binomial, Normal) |
| stats-hypothesis-testing | Hypothesis Testing |
| mech-constant-acceleration | Kinematics with Constant Acceleration |
| mech-variable-acceleration | Kinematics using Calculus |
| mech-projectiles | Projectiles |
| mech-forces-and-friction | Forces, Newton's Laws & Friction |
| mech-moments | Moments & Rigid Body Equilibrium |

## Question types (with the questions drafted into each)

| type | topic | definition | questions |
|---|---|---|---|
| **summary-statistics-and-lds** | stats-data-and-sampling | Find the mean and standard deviation from Σx and Σx² (sometimes coded), then interpret, compare or choose measures, often with sampling, data-cleaning or large-data-set context. | June2018_Q4, June2022_stats_Q3, June2023_stats_Q3, June2024_stats_Q3, June2025_stats_Q2, Oct2020_stats_Q3, Oct2021_stats_Q3 |
| **box-plot-outliers-and-percentiles** | stats-data-and-sampling | Complete or read a box plot, find outlier limits using a given rule, and link the data to the large data set or to a normal percentile range. | June2019_stats_Q2 |
| **regression-and-correlation-test** | stats-bivariate-data | Interpret a scatter diagram or regression line in context and test ρ = 0 against a one- or two-tailed alternative using a critical value or p-value. | June2018_Q2, June2024_stats_Q2, June2025_stats_Q4, Oct2020_stats_Q2, Oct2021_stats_Q2 |
| **log-coded-regression-model** | stats-bivariate-data | Data coded with logarithms give a linear regression line; convert it back to a power or exponential model and find the constants, often with a correlation test too. | June2019_stats_Q3, June2022_stats_Q6 |
| **venn-diagram-unknown-probabilities** | stats-probability | Use a Venn diagram of three or four events with unknown regions, and use independence, conditional probabilities and total probability = 1 to find the unknowns and further probabilities. | June2023_stats_Q1, June2024_stats_Q6, Oct2020_stats_Q1, Oct2021_stats_Q4 |
| **tree-diagram-conditional-probability** | stats-probability | Build or complete a tree diagram for successive selections, find combined probabilities, and then a 'given that' probability. | June2019_stats_Q1, June2025_stats_Q1 |
| **two-way-table-probability** | stats-probability | Read probabilities from a frequency table, extend it with percentages, and find union, intersection, complement and conditional probabilities. | June2022_stats_Q5 |
| **discrete-distribution-unknown-constant** | stats-distributions | A probability function or table has an unknown constant found from Σp = 1 (often via series, logs or algebra), then used for probabilities, including for two independent observations or linked to a Pure condition. | June2018_Q3, June2023_stats_Q5, June2025_stats_Q6, Oct2020_stats_Q4, Oct2021_stats_Q6 |
| **distribution-model-vs-data** | stats-distributions | Propose a uniform or binomial model for a large-data-set variable, calculate probabilities or expected frequencies with it, compare them with observed data and suggest refinements. | June2018_Q1, June2019_stats_Q4 |
| **binomial-probabilities-in-context** | stats-distributions | State the conditions for a binomial model, find exact and cumulative probabilities, possibly in two stages or using a normal approximation for large n. | June2022_stats_Q1, June2023_stats_Q2, June2024_stats_Q1, June2025_stats_Q3, Oct2021_stats_Q1 |
| **binomial-critical-region-test** | stats-hypothesis-testing | State hypotheses for p, find a one- or two-tailed critical region, give the actual significance level and draw a conclusion from an observed value. | June2022_stats_Q4, June2024_stats_Q4 |
| **normal-unknown-parameters** | stats-distributions | Find normal probabilities and use inverse normal z-values to find an unknown value, mean or standard deviation (sometimes solving simultaneous equations), possibly followed by a follow-on binomial or test part. | June2019_stats_Q5, June2022_stats_Q2, June2024_stats_Q5, June2025_stats_Q5 |
| **normal-conditional-probability** | stats-distributions | Find normal probabilities and then conditional probabilities such as P(X > a | X > b), often critiquing or refining the model, and often ending with a test for the mean. | June2018_Q5, Oct2020_stats_Q5, Oct2021_stats_Q5 |
| **normal-mean-hypothesis-test** | stats-hypothesis-testing | Test μ using the sample mean distribution N(μ, σ²/n), including one- or two-tailed tests and p-values, as the main part of the question. | June2023_stats_Q4 |
| **histogram-and-distribution-models** | stats-distributions | Estimate probabilities from a histogram (area = frequency), then compare a normal model and a fitted curve model (using integration) against the data. | June2023_stats_Q6 |
| **suvat-straight-line** | mech-constant-acceleration | Use suvat formulae for motion in one dimension, sometimes combined with a simple F = ma to find a driving force. | June2023_mech_Q1, June2025_mech_Q1 |
| **velocity-time-graph** | mech-constant-acceleration | Use the gradient and area of a piecewise-linear speed-time graph to find accelerations, distances and an unknown speed. | June2024_mech_Q2 |
| **vector-constant-acceleration** | mech-constant-acceleration | Use vector suvat (v = u + at, r = ut + ½at²) to find velocities, positions, distances, speeds, bearings or the time when motion is parallel to a given vector. | June2018_Q8, June2019_mech_Q2, June2023_mech_Q4, June2025_mech_Q3, Oct2020_mech_Q2, Oct2021_mech_Q1 |
| **vector-forces-newtons-second-law** | mech-forces-and-friction | Add force vectors, use the direction of the resultant to form an equation, then apply F = ma and vector suvat. | June2022_mech_Q3 |
| **variable-acceleration-vectors** | mech-variable-acceleration | Differentiate or integrate r, v or a given as functions of t in i-j form, using initial conditions, speed, direction or perpendicular/parallel conditions. | June2018_Q6, June2019_mech_Q1, June2022_mech_Q1, June2023_mech_Q3, June2024_mech_Q4, June2025_mech_Q4, Oct2020_mech_Q3, Oct2021_mech_Q5 |
| **projectile-range-and-greatest-height** | mech-projectiles | A projectile launched from level ground: show results linking U and α, find the range and greatest height or the equation of the path, and comment on modelling. | June2022_mech_Q5, June2024_mech_Q5 |
| **projectile-through-given-point** | mech-projectiles | Use horizontal and vertical motion to eliminate time for a projectile that passes through a target point (or meets another projectile), usually leading to an equation in tan α. | June2018_Q10, June2019_mech_Q5, June2023_mech_Q5 |
| **projectile-from-cliff** | mech-projectiles | A projectile launched from above the ground lands at a known horizontal distance; find the time, height, speed or greatest height using signed vertical displacement. | June2025_mech_Q5, Oct2020_mech_Q5, Oct2021_mech_Q4 |
| **rough-horizontal-plane-dynamics** | mech-forces-and-friction | Resolve forces (often a force at an angle) to find the normal reaction, use F = μR and F = ma, and then deceleration or stopping distance once the force is removed. | June2018_Q7, June2023_mech_Q2, June2024_mech_Q1, June2025_mech_Q2 |
| **inclined-plane-friction** | mech-forces-and-friction | Resolve parallel and perpendicular to an inclined plane for equilibrium or motion, find the friction or μ, and decide whether the particle moves. | June2022_mech_Q2, June2024_mech_Q3, Oct2020_mech_Q1 |
| **connected-particles-pulley** | mech-forces-and-friction | Write equations of motion for two particles joined by a string over a pulley (one on a rough plane), find the tension and acceleration, then look at what happens after the string goes slack or the particle hits the ground. | June2019_mech_Q3, Oct2021_mech_Q2 |
| **rod-ladder-equilibrium** | mech-moments | A rod on rough ground resting against a wall, peg, rail or drum (or held by a string): take moments, resolve, and use F = μR to find reactions, μ or the resultant force. | June2019_mech_Q4, June2022_mech_Q4, June2023_mech_Q6, June2024_mech_Q6, June2025_mech_Q6, Oct2020_mech_Q4, Oct2021_mech_Q3 |
| **horizontal-beam-rope-and-wall** | mech-moments | A horizontal plank hinged or pressed against a wall and supported by an inclined rope with a load: find the tension by moments, the wall reaction and its direction, and limits on where the load can go. | June2018_Q9 |

## Decisions for you

1. Sampling (S1.1) has no question type of its own: it only appears as parts inside summary-statistics or regression questions. Should there be a separate 'sampling-methods' type, or is it fine as skills only?
2. summary-statistics-and-lds is the biggest stats type (7 questions). Should it be split into 'summary statistics from sums/coding' and 'large data set cleaning & knowledge'?
3. The normal questions are split three ways: unknown parameters, conditional probability, and the mean test. Many of them also end with a mean test or a binomial part. Is this three-way split right, or should they merge into one or two types?
4. normal-mean-hypothesis-test and two-way-table-probability each have only one question in the dump. Keep them as separate types, or fold them into their neighbouring types?
5. Correlation tests are placed under the Bivariate topic, but the hypothesis-testing skills (state-hypotheses-correlation-test) sit in the hypothesis-testing group. Is it acceptable for this to cross topics?
6. P3_June2018_Q3 (darts: binomial plus first-success plus a model with an arithmetic series) is tagged discrete-distribution-unknown-constant. Should it be distribution-model-vs-data instead?
7. Projectiles are split into range/height (from the ground), through a given point/collision, and from a cliff. Is three the right number, and does the 2019 collision question belong with 'through a given point'?
8. The 2018 horizontal plank held by a rope has its own type (horizontal-beam-rope-and-wall). Should it merge into rod-ladder-equilibrium, which already covers the 2022 rod held by a string?
9. Friction is its own skill group, separate from forces-and-newtons-laws. Merge them to cut the number of groups from 16 to 15?
10. ~~formula_booklet flags~~ **Resolved by Claude against the real booklet (2026-09-26):** 11 are in the booklet (📘 below: SD from summary statistics, IQR, probability rules, conditional probability, binomial P(X=x), mean np, the binomial, normal and PMCC critical-value tables, the sample-mean distribution, scalar suvat). Not printed: standardising Z = (X−μ)/σ, the normal approximation, vector suvat, F = μR. Evidence is in the JSON.

## Skills by group

### Sampling (`sampling`)
- **identify-sampling-method**: Name a sampling method. Recognise opportunity, quota, systematic, stratified or simple random sampling from a description.
- **describe-sampling-method**: Describe how to carry out a sampling method. Explain step by step how to take a quota, stratified, systematic or random sample in context.
- **sampling-advantages-disadvantages**: Compare sampling methods and census. Give an advantage or disadvantage of a sampling method, or of a census compared with a sample.
- **identify-sample-and-population**: Identify the sample and population. Say exactly what the sample is and what population it could be used to make inferences about.

### Summary Statistics (`summary-statistics`)
- **mean-from-summary-statistics**: Mean from Σx. Calculate the mean from Σx and n, including estimates from grouped data.
- **standard-deviation-from-summary-statistics**: Standard deviation from Σx and Σx². Find the standard deviation using √(Σx²/n − x̄²) or √(Sxx/n). 📘 in booklet
- **coding-mean-and-sd**: Coding and its effect on mean and SD. Undo a linear coding such as y = x − 1010 to recover the mean, knowing that adding a constant leaves the standard deviation unchanged.
- **median-quartiles-iqr**: Median, quartiles, range and IQR. Read or calculate the median, quartiles, range and interquartile range, including by interpolation for grouped data. 📘 in booklet
- **choose-appropriate-average-and-spread**: Choose mean/SD or median/IQR. Decide which measures best describe the data, giving skew or outliers as the reason.
- **effect-of-changing-data-on-statistics**: Effect of adding or changing values. Reason, without recalculating everything, how changing or adding data values affects the mean, median, quartiles or standard deviation.
- **compare-distributions-in-context**: Compare distributions in context. Compare the location and spread of two data sets and draw a conclusion in context.

### Data Presentation, Outliers & the Large Data Set (`data-presentation-and-cleaning`)
- **histogram-area-frequency**: Histogram area represents frequency. Use frequency density × class width to find frequencies and estimate probabilities from a histogram.
- **box-plot-reading-and-drawing**: Read and draw box plots. Read values from a box plot, or complete one with whiskers and outliers marked correctly.
- **identify-outliers-using-rule**: Identify outliers using a given rule. Apply a rule such as Q1 − 1.5×IQR or mean ± 3 SD to decide which values are outliers.
- **clean-data**: Clean data. Deal with missing values, errors and entries such as 'tr' (trace) before calculating statistics.
- **large-data-set-knowledge**: Use knowledge of the large data set. Use facts about the large data set (locations, the May–Oct months, variables, units, typical values) to explain or identify data.

### Correlation & Regression (`bivariate-data`)
- **describe-correlation**: Describe correlation. Describe correlation as positive, negative or none, and as strong or weak, from a scatter diagram or r.
- **suggest-reason-for-correlation**: Suggest a reason for correlation. Give a sensible reason in context for a correlation, remembering that correlation does not imply causation.
- **explanatory-response-variables**: Explanatory and response variables. Identify the explanatory variable by explaining which variable affects the other.
- **interpret-regression-coefficients**: Interpret regression gradient and intercept. Interpret the gradient as a rate of change per unit (with units) and the intercept in context.
- **interpolation-and-extrapolation**: Interpolation and extrapolation. Use a regression line to make predictions and explain why extrapolating outside the data range is unreliable.
- **assess-linear-model-fit**: Judge whether a linear model fits. Use a scatter diagram shape or the size of r to decide whether a linear model is suitable.
- **log-coding-to-nonlinear-model**: Convert a log-coded line to y = ax^n or y = kb^x. Substitute the log codings into the regression line and remove logs to find the constants of a power or exponential model.

### Probability Rules & Diagrams (`probability`)
- **complement-and-addition-rules**: Complement and addition rules. Use P(A') = 1 − P(A) and P(A ∪ B) = P(A) + P(B) − P(A ∩ B). 📘 in booklet
- **draw-tree-diagram**: Draw and label a tree diagram. Draw a tree diagram with correct branches and probabilities for successive events.
- **combine-probabilities-on-tree**: Multiply along and add between branches. Find the probability of combined outcomes, such as 'at least one', by multiplying along branches and adding the paths you need.
- **venn-diagram-find-unknowns**: Find unknown Venn diagram regions. Set up equations from given probabilities and total probability = 1 to find unknown regions.
- **two-way-table-probability**: Probabilities from two-way tables. Read joint, marginal and conditional probabilities from a two-way table.
- **conditional-probability-formula**: Conditional probability. Use P(A | B) = P(A ∩ B) / P(B), choosing the right restricted denominator. 📘 in booklet
- **independence-test-and-use**: Use or test independence. Use P(A ∩ B) = P(A)P(B) to find unknowns or to show whether two events are independent.
- **mutually-exclusive-events**: Mutually exclusive events. Recognise events that cannot happen together, for example non-overlapping regions on a Venn diagram.
- **set-notation-for-events**: Describe events in set notation. Read and write events using ∩, ∪ and complements, such as [A ∪ B]' ∩ C.

### Discrete Random Variables (`discrete-distributions`)
- **probability-distribution-sum-to-one**: Find a constant using Σp = 1. Set the sum of all probabilities equal to 1 to find an unknown constant, using series, logs or algebra where needed.
- **discrete-uniform-distribution**: Discrete uniform distribution. Write down a discrete uniform distribution and find probabilities from it.
- **probabilities-from-distribution-table**: Probabilities from a distribution. List the values that satisfy an inequality or condition and add their probabilities.
- **combine-independent-observations**: Combine two independent observations. List the cases for two independent observations (such as a sum or equality) and multiply and add their probabilities.
- **first-success-probability**: Probability of the first success on trial n. Use (1 − p)^(n−1) × p for the first success happening on the nth independent trial.
- **expected-frequency-and-value**: Expected frequencies and expected income. Multiply probabilities by the number of trials or by values (such as prices) to get expected counts or totals.

### Binomial Distribution (`binomial-distribution`)
- **binomial-conditions**: State binomial conditions in context. State in context that trials are independent, with a fixed number of trials and a constant probability of success.
- **binomial-individual-probability**: Binomial P(X = x). Find an exact binomial probability with your calculator or nCx p^x (1 − p)^(n−x). 📘 in booklet
- **binomial-cumulative-probability**: Binomial cumulative probabilities. Turn phrases like 'more than' or 'fewer than' into P(X ≤ k) or 1 − P(X ≤ k) and evaluate them. 📘 in booklet
- **two-stage-binomial**: Two-stage binomial problems. Use a probability from one binomial model as p in a second binomial model, for example the number of boxes or days.
- **binomial-expected-value**: Binomial expectation np. Use np to estimate the expected number of successes. 📘 in booklet

### Normal Distribution (`normal-distribution`)
- **normal-probability-calculator**: Normal probabilities on a calculator. Find P(X > a) or P(a < X < b) for X ~ N(μ, σ²) using a calculator.
- **inverse-normal**: Inverse normal. Find the value of x for a given cumulative probability, or a percentile or interpercentile range. 📘 in booklet
- **standardise-to-find-mu-or-sigma**: Standardise to find μ or σ. Set (x − μ)/σ equal to the correct z-value, with the right sign, to find an unknown mean or standard deviation.
- **normal-simultaneous-mu-sigma**: Find μ and σ simultaneously. Form two standardised equations from two given probabilities and solve them simultaneously for μ and σ.
- **normal-conditional-probability**: Conditional normal probabilities. Find probabilities such as P(X > a | X > b) by writing the intersection over the given condition.
- **normal-approximation-to-binomial**: Normal approximation to binomial. Approximate B(n, p) by N(np, np(1 − p)) when n is large and p is close to 0.5.
- **continuity-correction**: Continuity correction. Adjust the boundary by 0.5 when using a continuous normal distribution to approximate a discrete one.
- **normal-shape-and-symmetry**: Shape, symmetry and inflection of the normal curve. Use the symmetry of the normal curve and its points of inflection at μ ± σ.
- **choose-appropriate-distribution**: Judge whether a binomial or normal model is suitable. Explain whether a binomial or normal model suits the data, for example because of skew, negative values, qualitative data or non-constant p.

### Hypothesis Testing (`hypothesis-testing`)
- **state-hypotheses-binomial-test**: State hypotheses for a binomial test. Write H0 and H1 in terms of the population proportion p, choosing a one- or two-tailed alternative.
- **binomial-test-probability**: Binomial test using a probability. Work out P(X ≤ x) or P(X ≥ x) under H0 and compare it with the significance level.
- **find-binomial-critical-region**: Find a binomial critical region. Find the critical region(s) using cumulative probabilities, with half the significance level in each tail for a two-tailed test.
- **actual-significance-level**: Actual significance level. Add the probabilities of the critical region(s) to find the actual significance level of a test.
- **state-hypotheses-correlation-test**: State hypotheses for a correlation test. Write H0: ρ = 0 and an H1 of ρ > 0, ρ < 0 or ρ ≠ 0.
- **correlation-test-critical-value**: Compare r with a critical value or p-value. Use the PMCC critical value table or a given p-value to decide whether r is significant. 📘 in booklet
- **calculate-pmcc-on-calculator**: Calculate r on a calculator. Enter paired data into your calculator to find the product moment correlation coefficient.
- **state-hypotheses-normal-mean-test**: State hypotheses for a normal mean test. Write H0 and H1 in terms of the population mean μ.
- **sample-mean-distribution**: Distribution of the sample mean. Use X̄ ~ N(μ, σ²/n) to find the probability of the observed sample mean under H0. 📘 in booklet
- **two-tailed-test-and-p-value**: Two-tailed tests and p-values. Split the significance level between the two tails, or double the one-tail probability to get the p-value.
- **conclude-test-in-context**: Conclude a test in context. State whether there is enough evidence to reject H0 and give the conclusion in the words of the question, without being too definite.

### Modelling in context (`modelling-in-context`) (existing shared group)
- **critique-probability-model**: Critique probability model assumptions. Question assumptions such as fairness, independence or constant probability, and describe the likely effect of more realistic ones.
- **refine-probability-model**: Suggest a refinement to a statistical model. Suggest a specific improvement to a model, such as using different months or locations or a non-uniform distribution.

### Trig identities (`trig-identities`) (existing shared group)
- **trig-ratios-from-given-tan**: Exact sin and cos from a given tan. Use a right-angled triangle to get exact sin α and cos α from a value such as tan α = 3/4.

### Constant Acceleration Kinematics (`kinematics-constant-acceleration`)
- **si-units-and-conversions**: SI units and conversions. Use the right SI units and convert, for example, km h⁻¹ to m s⁻¹.
- **suvat-scalar**: suvat in one dimension. Choose and apply the right constant-acceleration formula for straight-line motion. 📘 in booklet
- **velocity-time-graph-gradient-area**: Gradient and area of velocity-time graphs. Use the gradient for acceleration and the area under the graph for distance, including to find an unknown speed.
- **sketch-velocity-time-graph**: Sketch a velocity-time graph. Sketch a velocity-time graph with the correct shape and explain the shape using the acceleration.
- **suvat-vectors**: suvat with i-j vectors. Apply v = u + at and r = r0 + ut + ½at² to vectors, then equate components where needed.
- **speed-and-direction-from-velocity**: Speed, direction and bearing from a velocity vector. Find speed as the magnitude of velocity, and direction as an angle or three-figure bearing using trig.
- **direction-condition-on-vector**: Parallel or perpendicular direction conditions. Set a component to zero or a ratio of components equal to form an equation for t when motion is parallel or perpendicular to a given direction.

### Kinematics with Calculus (`kinematics-calculus`)
- **differentiate-kinematics-vectors**: Differentiate r or v with respect to t. Differentiate each component to go from position to velocity to acceleration.
- **integrate-kinematics-vectors**: Integrate a or v with respect to t. Integrate each component, including a vector constant found from the given initial conditions.
- **speed-equation-solve-for-t**: Solve a speed condition for t. Set the magnitude of a t-dependent velocity equal to a given speed and solve the resulting equation for t.

### Projectile Motion (`projectiles`)
- **resolve-projection-velocity**: Resolve the projection velocity. Split the initial velocity into horizontal U cos α and vertical U sin α components.
- **projectile-horizontal-motion**: Horizontal motion of a projectile. Use constant horizontal speed, x = (U cos α)t.
- **projectile-vertical-motion**: Vertical motion of a projectile. Apply suvat vertically with acceleration −g, taking care with signed displacement below the start point.
- **eliminate-time-projectile**: Eliminate t between the two motions. Substitute t from the horizontal equation into the vertical equation, often giving a quadratic in tan α using sec² = 1 + tan².
- **projectile-greatest-height**: Greatest height. Use a vertical velocity of zero at the top to find the greatest height.
- **projectile-time-of-flight-and-range**: Time of flight and range. Find when the projectile lands and how far it travels horizontally.
- **projectile-velocity-at-point**: Speed and direction during flight. Combine the horizontal and vertical velocity components at a given time to find the speed and angle of motion.
- **equation-of-trajectory**: Equation of the path. Derive y in terms of x for a projectile and use it to find range or height.

### Forces & Newton's Laws (`forces-and-newtons-laws`)
- **draw-force-diagram**: Draw a force diagram. Mark weight, normal reaction, tension, thrust and friction in the right directions.
- **resolve-force-at-angle**: Resolve a force at an angle. Split a pull or push at an angle into components, and see how it changes the normal reaction.
- **resolve-forces-on-inclined-plane**: Resolve forces on an inclined plane. Resolve weight and other forces parallel and perpendicular to the slope, e.g. R = mg cos α.
- **newtons-second-law-equation**: Form an F = ma equation. Write resultant force = mass × acceleration in the direction of motion, with the correct signs.
- **equilibrium-of-particle**: Equilibrium of a particle. Resolve in two perpendicular directions and set each resultant to zero.
- **connected-particles-equations**: Connected particles equations. Write separate equations of motion (or one whole-system equation) for particles joined by a string over a smooth pulley, and solve for T and a.
- **resultant-force-vectors**: Resultant of force vectors. Add forces given in i-j form, and use F = ma in vector form.
- **magnitude-and-direction-of-resultant**: Magnitude and direction of a resultant force. Use Pythagoras and tan on the perpendicular components to find the size and direction of a resultant or contact force.
- **weight-and-g**: Weight and the value of g. Use W = mg with the stated value of g, and give answers to an accuracy that suits it.

### Friction (`friction`)
- **friction-f-equals-mu-r**: Use F = μR. Use F = μR when sliding or in limiting equilibrium, after finding R by resolving.
- **limiting-equilibrium-friction**: Limiting equilibrium and F ≤ μR. Use F ≤ μR in equilibrium, and F = μR when on the point of slipping, to find μ or a force.
- **friction-direction**: Direction of friction. Decide which way friction acts by working out which way the body would tend to move.
- **will-it-move-check**: Decide whether a body moves. Compare the force trying to cause motion with maximum friction μR to decide whether the body stays at rest.

### Moments (`moments`)
- **take-moments-about-a-point**: Take moments about a point. Form a moments equation using force × perpendicular distance, choosing a point that removes unknown forces.
- **moments-with-angled-forces**: Moments of forces at an angle. Find perpendicular distances (or components) with sin and cos when the rod or force is inclined.
- **reaction-at-smooth-contact**: Reactions at smooth contacts. Know that a smooth wall, peg, rail or drum gives a reaction perpendicular to the surface or rod.
- **rigid-body-resolve-and-moments**: Combine resolving and moments. Use moments with resolving in two directions to find all unknown forces on a rigid body in equilibrium.
- **range-from-force-limit**: Positions allowed by a force limit. Set up and solve an inequality (for example tension ≤ maximum) to find where a load can be placed.
- **centre-of-mass-effect**: Effect of moving the centre of mass. Explain how a non-uniform rod, with its centre of mass closer to one end, changes the moments and reactions.

### Mechanics Modelling Assumptions (`mechanics-modelling`)
- **mechanics-modelling-assumptions**: Mechanics modelling assumptions. Explain the meaning and effect of the model terms particle, light, inextensible, smooth, uniform and rough.
- **refine-mechanics-model**: Refine a mechanics model. Suggest realistic refinements (air resistance, spin, size, rough pulley, weight of string) and say how they change the answers.

