"""Fixed UCI 498 adapter; local clock only, no fabricated time zone."""
import csv
import datetime
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

RAW_SHA = '6294e29a311647306bfdfc85783f7df66517c197b9cd49aa5ee36ba9c525d1d6'


def local_clock(text):
    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError('invalid local update timestamp')


def contradictory(events):
    """Any decrease across *strictly* different local timestamp groups."""
    grouped=defaultdict(list)
    for e in events:grouped[e['time']].append(e['counter'])
    maximum=-1
    for stamp in sorted(grouped):
        if min(grouped[stamp])<maximum:return True
        maximum=max(maximum,max(grouped[stamp]))
    return False


def blocks(events,model):
    grouped=defaultdict(list)
    for e in events:
        key=(e['time'], e['counter'] if model=='C' and e['counter_supported']=='1' else 0)
        grouped[key].append(e)
    return [grouped[k] for k in sorted(grouped)]


def prepare(raw, out):
    raw=Path(raw);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==RAW_SHA
    with zipfile.ZipFile(raw) as z:
        data=z.read('incident_event_log.csv')
    cases=defaultdict(list);reasons=defaultdict(set);raw_counts=Counter();all_updaters=set();full_rows=[]
    for index,row in enumerate(csv.DictReader(io.StringIO(data.decode('utf-8-sig')))):
        full_rows.append(tuple(row.values()))
        cid=row['number'];raw_counts[cid]+=1
        if not cid or cid=='?':raise ValueError('Unidentifiable incident; cannot safely exclude whole case')
        try:stamp=local_clock(row['sys_updated_at'])
        except ValueError:reasons[cid].add('invalid_timestamp');stamp=None
        try:
            counter=int(row['sys_mod_count'])
            if counter<0:raise ValueError()
        except ValueError:reasons[cid].add('invalid_counter');counter=None
        updater=row['sys_updated_by']
        if not updater or updater=='?':reasons[cid].add('missing_updater')
        else:all_updaters.add(updater)
        cases[cid].append(dict(source_index=index,time=stamp,counter=counter,raw_resource=updater,
                               activity=row['incident_state']))
    aliases={r:'R%04d'%i for i,r in enumerate(sorted(all_updaters),1)}
    eligible={c:events for c,events in sorted(cases.items()) if not reasons[c]}
    conflicts=[];repeat_counter=0;repeat_mixed=0;metrics={}
    with (out/'cohort.csv').open('x',newline='') as f:
        fields=['case_id','source_index','timestamp','resource','activity','counter','counter_supported']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for cid,events in eligible.items():
            conflict=contradictory(events)
            if conflict:conflicts.append(cid)
            samecount=defaultdict(list)
            for e in events:samecount[e['counter']].append(e)
            repeat_counter+=sum(len(g)>1 for g in samecount.values())
            repeat_mixed+=sum(len(g)>1 and len({e['raw_resource'] for e in g})>1 for g in samecount.values())
            for e in events:
                e['resource']=aliases[e['raw_resource']];e['counter_supported']='0' if conflict else '1'
                writer.writerow(dict(case_id=cid,source_index=e['source_index'],timestamp=e['time'].isoformat(),
                                     resource=e['resource'],activity=e['activity'],counter=e['counter'],
                                     counter_supported=e['counter_supported']))
    for model in ('T','C'):
        bs=[b for events in eligible.values() for b in blocks(events,model)]
        mixed=[b for b in bs if len({e['resource'] for e in b})>1]
        metrics[model]=dict(blocks=len(bs),tied_blocks=sum(len(b)>1 for b in bs),
                           mixed_resource_blocks=len(mixed),mixed_events=sum(map(len,mixed)),
                           max_mixed_block=max(map(len,mixed),default=0))
    summary=dict(raw_cases=len(cases),raw_events=sum(raw_counts.values()),eligible_cases=len(eligible),
                 eligible_events=sum(map(len,eligible.values())),excluded_cases=len(cases)-len(eligible),
                 excluded_events=sum(raw_counts[c] for c in reasons if reasons[c]),
                 overlapping_case_exclusion_reasons=dict(Counter(r for rs in reasons.values() for r in rs)),
                 counter_conflict_cases=len(conflicts),counter_conflict_events=sum(len(eligible[c]) for c in conflicts),
                 repeated_counter_groups=repeat_counter,repeated_counter_mixed_resource_groups=repeat_mixed,
                 identical_full_rows_retained=len(full_rows)-len(set(full_rows)),resources=len(aliases),models=metrics,
                 raw_sha256=RAW_SHA,csv_sha256=hashlib.sha256(data).hexdigest(),
                 cohort_sha256=hashlib.sha256((out/'cohort.csv').read_bytes()).hexdigest(),
                 timestamp_semantics='publisher local clock; no time zone inferred')
    (out/'population.json').write_text(json.dumps(summary,indent=2))
    (out/'counter-conflicts-private.json').write_text(json.dumps(conflicts))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    prepare(a.raw,a.out)
