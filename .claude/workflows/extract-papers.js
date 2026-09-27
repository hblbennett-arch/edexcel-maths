export const meta = {
  name: 'extract-papers',
  description: 'Extract papers to data/processed/_staging (one Sonnet agent per paper, max 5 at a time). args: {prompt_dir, papers: [paper_id]}',
  phases: [{ title: 'Extract', detail: 'one agent per paper; each self-validates with check_questions.py' }],
}
const DIR = args.prompt_dir   // from scripts/make_prompts.py (<scratch>/prompts)
const SCHEMA = {
  type: 'object',
  properties: {
    paper_id: { type: 'string' },
    check_ok: { type: 'boolean', description: 'true only if check_questions.py printed OK on the final file' },
    questions: { type: 'integer' }, parts: { type: 'integer' }, marks: { type: 'integer' },
    low_confidence: { type: 'array', items: { type: 'string' }, description: 'question id + what is uncertain' },
    pearson_errors: { type: 'array', items: { type: 'string' } },
    spec_feedback: { type: 'string', description: 'anything in the extraction spec that was unclear or did not fit' },
  },
  required: ['paper_id', 'check_ok', 'questions', 'marks', 'low_confidence', 'pearson_errors', 'spec_feedback'],
}
const papers = args.papers
phase('Extract')
// Worker pool: the user's rule is at most 5 agents in parallel.
const results = []
let next = 0
async function worker() {
  while (next < papers.length) {
    const pid = papers[next++]
    const r = await agent(
      `Your complete task instructions are in ${DIR}/extract_${pid}.txt — read that file first and follow it exactly. Work in /Users/i1003721/edexcel-maths. Your final structured output replaces the "Final reply" described in that file.`,
      { label: `extract ${pid}`, phase: 'Extract', schema: SCHEMA, model: 'sonnet' })
    results.push(r || { paper_id: pid, check_ok: false, questions: 0, marks: 0, low_confidence: [], pearson_errors: [], spec_feedback: 'AGENT FAILED' })
    log(`${results.length}/${papers.length} done: ${pid} ${r && r.check_ok ? 'OK' : 'NOT OK'}`)
  }
}
await parallel([1, 2, 3, 4, 5].map(() => () => worker()))
return results
