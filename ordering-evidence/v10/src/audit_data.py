"""Source audit and predeclared hash-selected development cohort; no test outcomes."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from .io import sha256, timestamp_us
from .core import blocks_from_events


def audit(source, out, lifecycle, seed='20261027', size=200):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    tag = lambda e: e.tag.rsplit('}', 1)[-1]
    attrs = lambda e: {x.get('key'): x.get('value') for x in e if x.get('key')}
    root = ET.parse(gzip.open(source)).getroot()
    all_cases, eligible, excluded = [], {}, []
    life, keys, fractions = Counter(), Counter(), Counter()
    raw_count = selected_count = missing = inversions = 0
    resources = set()
    for trace in root:
        if tag(trace) != 'trace':
            continue
        case = attrs(trace).get('concept:name')
        if not case or case in all_cases:
            raise ValueError('Missing or duplicate case ID')
        all_cases.append(case)
        events, reasons = [], set()
        for i, event in enumerate(x for x in trace if tag(x) == 'event'):
            row = attrs(event)
            raw_count += 1
            life[row.get('lifecycle:transition', '')] += 1
            keys.update(row.keys())
            if lifecycle != 'all' and row.get('lifecycle:transition', '').lower() != lifecycle:
                continue
            selected_count += 1
            resource = row.get('org:resource')
            if not resource or resource.upper() == 'UNKNOWN':
                missing += 1
                reasons.add('missing_or_UNKNOWN_resource')
            raw_time = row.get('time:timestamp', '')
            match = re.search(r'\.(\d+)', raw_time)
            precision = len(match.group(1)) if match else 0
            fractions[precision] += 1
            try:
                if precision > 6:
                    raise ValueError('unsupported precision')
                stamp = timestamp_us(raw_time)
            except ValueError:
                reasons.add('invalid_timestamp')
                continue
            events.append((stamp, resource, raw_time, row.get('concept:name', ''),
                           row.get('lifecycle:transition', ''), i))
        if not events:
            reasons.add('no_selected_events')
        if reasons:
            excluded.append({'case_id': case, 'reasons': sorted(reasons), 'selected_events': len(events)})
        else:
            inversions += sum(a[0] > b[0] for a, b in zip(events, events[1:]))
            eligible[case] = events
            resources.update(e[1] for e in events)
    # Pseudonyms in derived files: do not expose source names in the report.
    mapping = {r: 'R%04d' % i for i, r in enumerate(sorted(resources), 1)}
    ids = sorted(eligible, key=lambda c: hashlib.sha256((c + seed).encode()).hexdigest())
    dev = ids[:size]
    (out / 'split.json').write_text(json.dumps({'seed': seed, 'rule': 'sha256(case_id + seed)',
                                               'dev': dev, 'reserved_test': ids[size:size+2000]}, indent=2))
    (out / 'excluded.json').write_text(json.dumps(excluded, indent=2))
    rows = []
    for case in dev:
        events = eligible[case]
        b = blocks_from_events([(e[0], mapping[e[1]]) for e in events])
        rows.append({'case_id': case, 'events': len(events),
                     'tied_events': sum(len(x) for x in b if len(x)>1),
                     'mixed_tied_events': sum(len(x) for x in b if len(set(x))>1),
                     'mixed_blocks': sum(len(set(x))>1 for x in b), 'max_block': max(map(len,b))})
    with open(out / 'dev.csv', 'x', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['case_id','timestamp','resource','activity','lifecycle','source_index'])
        for case in dev:
            for _, resource, stamp, activity, state, i in eligible[case]:
                writer.writerow([case,stamp,mapping[resource],activity,state,i])
    report = {'input': str(source), 'sha256': sha256(source), 'raw_cases': len(all_cases),
              'raw_events': raw_count, 'lifecycle_counts': dict(life), 'event_keys': dict(keys),
              'population': lifecycle, 'selected_events_before_case_exclusion': selected_count,
              'missing_or_UNKNOWN_selected_resources': missing, 'excluded_cases': len(excluded),
              'eligible_cases': len(eligible), 'eligible_events': sum(map(len,eligible.values())),
              'fractional_digits': dict(fractions), 'timestamp_inversions': inversions,
              'source_order_reliability': 'unknown', 'interpretation': 'timestamp-only sensitivity',
              'dev_cases': len(dev), 'dev_events': sum(x['events'] for x in rows),
              'dev_tied_events': sum(x['tied_events'] for x in rows),
              'dev_mixed_tied_events': sum(x['mixed_tied_events'] for x in rows),
              'dev_mixed_cases': sum(x['mixed_blocks']>0 for x in rows),
              'dev_max_block': max(x['max_block'] for x in rows),
              'script_sha256': sha256(__file__)}
    (out/'audit.json').write_text(json.dumps(report,indent=2))
    (out/'dev_cases.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--lifecycle',required=True)
    a=p.parse_args()
    audit(a.input,a.out,a.lifecycle)
