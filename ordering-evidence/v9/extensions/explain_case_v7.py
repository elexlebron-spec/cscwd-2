"""Recreate the fixed permit-case excerpt from raw XES and paired core witnesses.

Exports only the aggregate pattern and five selected source labels, not case ID,
raw personnel IDs or full event-index permutations.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True)
    parser.add_argument('--raw',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    assert hashlib.sha256(Path(args.raw).read_bytes()).hexdigest()=='d5847a409cec1de1b7382b59365aec6af8e53e1c2ac083201e7679c22a6ef525'
    run=Path(args.run);config=json.loads((run/'config.json').read_text())
    cohort=defaultdict(dict)
    for row in csv.DictReader(Path(config['cohort']).open()):cohort[row['case_id']][int(row['source_index'])]=row
    e=('R0006','R0015');f=('R0013','R0006');totals=Counter();selected=None;unrelaxed=0
    for line in (run/'witnesses-private.jsonl').open():
        record=json.loads(line)
        if record['query']!=12 or record['base_model']!='N':continue
        events=cohort[record['case_id']]
        for key in ['baseline','negative']:
            resources=[events[i]['resource'] for i in record[key]];c=Counter(zip(resources,resources[1:]))
            totals[key]+=c[e]-c[f]
        if record['relaxed']:
            assert record['case_alias']=='C0261' and selected is None;selected=record
        else:assert record['baseline']==record['negative'];unrelaxed+=1
    assert totals==dict(baseline=1,negative=-1) and unrelaxed==998
    attrs=lambda node:{x.get('key'):x.get('value') for x in node if x.get('key')}
    root=ET.parse(gzip.open(args.raw)).getroot()
    trace=next(t for t in root if t.tag.endswith('trace') and attrs(t).get('concept:name')==selected['case_id'])
    raw=[attrs(x) for x in trace if x.tag.endswith('event')];events=cohort[selected['case_id']]
    assert len(raw)==len(events)==75
    bytime={}
    for mode in ['baseline','negative']:
        groups=defaultdict(list)
        for i in selected[mode]:groups[raw[i]['time:timestamp']].append(i)
        bytime[mode]=groups
    changed=[stamp for stamp,b in bytime['baseline'].items() if
             [events[i]['resource'] for i in b]!=[events[i]['resource'] for i in bytime['negative'][stamp]]]
    assert len(changed)==1;stamp=changed[0];block=bytime['baseline'][stamp];assert len(block)==37
    output=dict(case_alias='C0261',case_events=75,block_events=37,recorded_timestamp=stamp,
                global_margins=dict(totals),unrelaxed_case_orders_identical=998,patterns={})
    for mode in ['baseline','negative']:
        resources=[events[i]['resource'] for i in bytime[mode][stamp]]
        rle=[(r,len(list(g))) for r,g in itertools.groupby(resources)]
        sequence=selected[mode];start=sequence.index(bytime[mode][stamp][0]);end=start+37
        before=events[sequence[start-1]]['resource'];after=events[sequence[end]]['resource']
        counts=Counter(zip([events[i]['resource'] for i in sequence],[events[i]['resource'] for i in sequence][1:]))
        output['patterns'][mode]=dict(rle=rle,before=before,after=after,case_e=counts[e],case_f=counts[f])
    codes={'01_HOOFD_491','01_HOOFD_495','01_HOOFD_500','01_HOOFD_510_0','08_AWB45_005'}
    output['selected_source_labels']=[dict(code=raw[i]['action_code'],label=raw[i]['activityNameEN'],resource=events[i]['resource']) for i in block if raw[i]['action_code'] in codes]
    output['dateFinished_all_same']=len(set(raw[i]['dateFinished'] for i in block))==1
    output['planned_distinct_values']=len(set(raw[i].get('planned') for i in block))
    output['interpretation']='Timestamp-admissible counterexample; business precedence and planned-field semantics remain unverified.'
    with Path(args.out).open('x') as stream:json.dump(output,stream,indent=2)
    print('Verified fixed 37-event case excerpt, +1/-1 global margins, and 998 identical other case orders.')


if __name__=='__main__':main()
