"""Independent raw XML check for the first two fixed development cohorts.

Uses no core/io/audit_data functions. Checks raw tied-block composition and
derived edge envelopes directly. A structural certificate is sufficient here:
if each timestamp group is resource-homogeneous, every allowed permutation
has the same resource sequence.
"""
import csv
import gzip
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    reports = []
    for year, life in [(2013, 'all'), (2012, 'complete')]:
        base = Path('results/dev%s-audit' % year)
        selected = set(json.loads((base/'split.json').read_text())['dev'])
        root = ET.parse(gzip.open('data/raw/mirror-BPI_Challenge_%s.xes.gz' % year)).getroot()
        events = tied = mixed = cases = 0
        for trace in root:
            if trace.tag.rsplit('}', 1)[-1] != 'trace':
                continue
            case = next(x.get('value') for x in trace if x.get('key') == 'concept:name')
            if case not in selected:
                continue
            cases += 1
            groups = defaultdict(list)
            for event in trace:
                if event.tag.rsplit('}', 1)[-1] != 'event':
                    continue
                attrs = {x.get('key'): x.get('value') for x in event}
                if life != 'all' and attrs['lifecycle:transition'].lower() != life:
                    continue
                instant = datetime.fromisoformat(attrs['time:timestamp']).astimezone(timezone.utc)
                groups[instant].append(attrs['org:resource'])
                events += 1
            tied += sum(len(v) for v in groups.values() if len(v)>1)
            mixed += sum(len(v) for v in groups.values() if len(set(v))>1)
        audit = json.loads((base/'audit.json').read_text())
        assert (cases,events,tied,mixed) == tuple(audit[k] for k in
            ['dev_cases','dev_events','dev_tied_events','dev_mixed_tied_events'])
        assert mixed == 0, 'Structural invariant not applicable; do not assert stability'
        checks = {}
        for k in [5,10]:
            folder = Path('results/dev%s-k%s' % (year,k))
            rows = list(csv.DictReader((folder/'edges.csv').open()))
            for row in rows:
                value = int(row['source_order_count'])
                assert value == int(row['lex_count']) == int(row['reverse_count'])
                assert float(value) == float(row['uniform_expectation'])
                assert value == int(row['full_log_safe_low']) == int(row['full_log_safe_high'])
            profile = json.loads((folder/'top_k_profiles.json').read_text())
            assert all(p == profile['source'] for p in profile.values())
            p = profile['source']
            checks[str(k)] = {'edges_checked':len(rows),'strict':len(p['strict']),
                              'boundary':len(p['boundary']),'slots':p['slots'],
                              'unique_top_k':p['unique'], 'all_edge_weights_invariant':True}
        reports.append({'dataset':year,'cases':cases,'events':events,'tied_events':tied,
                        'mixed_tied_events':mixed,'checks':checks})
    target=Path('results/development-independent-check.json')
    with target.open('x') as f:
        json.dump(reports,f,indent=2)
    print(json.dumps(reports,indent=2))


if __name__ == '__main__':
    main()
