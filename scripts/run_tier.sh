#!/bin/bash
# Run the cheap pipeline end to end for one tier: triage (legacy) + single-call extraction ->
# MS completeness pass -> MS visual verification -> page map (scans) -> spec filter -> examiner notes (kept questions only) -> triage review list.
#   scripts/run_tier.sh '^IAL2018_'   > logs/tier2.log 2>&1
set -u
cd "$(dirname "$0")"
RE="$1"
PY=../.venv/bin/python
echo "== extract $(date)"
$PY extract_single.py --todo --only "$RE" --parallel 5
echo "== MS completeness pass (Opus) $(date)"
$PY ms_complete.py --todo --only "$RE" --parallel 5
echo "== MS visual verification (Opus) $(date)"
$PY ms_verify.py --todo --only "$RE" --parallel 5
echo "== page map for scanned papers $(date)"
SCANS=$($PY -c "
import json,glob,re,os
import check_questions as cq
out=[]
for f in sorted(glob.glob('../data/processed/_staging/*.json')):
    pid=os.path.basename(f)[:-5]; d=json.load(open(f))
    if not re.search(r'$RE',pid) or not d['questions'] or any(q.get('page_map_source') for q in d['questions']): continue
    t=(cq.RAW/d['source_qp_file']).read_text(errors='ignore') if (cq.RAW/d.get('source_qp_file','')).is_file() else ''
    if not cq.usable_text(t) and not cq.shifted_font(t): out.append(pid)
print(' '.join(out))")
[ -n "$SCANS" ] && echo "$SCANS" | xargs $PY page_map.py
echo "== spec filter $(date)"
$PY apply_spec_filter.py --all | grep -E "$(echo "$RE" | tr -d '^')|TOTAL"
echo "== concept screen (model + text check) $(date)"
$PY concept_screen.py --only "$RE" --per-call 1
$PY concept_screen.py --only "$RE" --regex-only
$PY concept_screen.py --only "$RE" --apply
$PY apply_spec_filter.py --all | grep TOTAL
$PY park_units.py --park
echo "== notes $(date)"
IDS=$($PY -c "
import json,glob,re,os
out=[]
for f in sorted(glob.glob('../data/processed/questions/*.json')):
    pid=os.path.basename(f)[:-5]
    if re.search(r'$RE',pid) and json.load(open(f))['questions'] and not os.path.exists(f'../data/processed/examiner_notes/{pid}.json'):
        m=[d for d in json.load(open('../data/raw/pearson/manifest.json')) if d['paper_id']==pid and d['doc_type']=='ER' and d.get('local_pdf')]
        if m: out.append(pid)
print(' '.join(out))")
[ -n "$IDS" ] && $PY notes_single.py $IDS --parallel 5
echo "== tags $(date)"
$PY tag_single.py --todo --only "$RE" --parallel 4
echo "== triage review list $(date)"
$PY triage_spec.py --report
echo "== completeness $(date)"
$PY completeness.py "$RE"
echo "== done $(date)"
