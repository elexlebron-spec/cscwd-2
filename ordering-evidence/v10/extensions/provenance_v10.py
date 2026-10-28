"""Inspect the fixed case in the original public CSV release; publish no IDs."""
import csv
import datetime
import gzip
import hashlib
import io
import json
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


def main():
    root = Path('results/revision-v10')
    config = json.loads(Path('configs/core_v7_M1.json').read_text())
    cases = defaultdict(list)
    for row in csv.DictReader(Path(config['cohort']).open()):
        cases[row['case_id']].append(row)
    case = list(cases)[260]
    attrs = lambda node: {x.get('key'): x.get('value') for x in node if x.get('key')}
    rawpath = Path('data/raw/mirror-BPI_Challenge_2015.xes.gz')
    assert hashlib.sha256(rawpath.read_bytes()).hexdigest() == 'd5847a409cec1de1b7382b59365aec6af8e53e1c2ac083201e7679c22a6ef525'
    rawroot = ET.parse(gzip.open(rawpath)).getroot()
    trace = next(t for t in rawroot if t.tag.endswith('trace') and attrs(t).get('concept:name') == case)
    raw = [attrs(e) for e in trace if e.tag.endswith('event')]
    zpath = Path('data/provenance/v10/fluxicon-BPI-Challenge-2015.zip')
    assert hashlib.sha256(zpath.read_bytes()).hexdigest() == '4ccd2eff858ffb1bf7fc4b88cdef02f1230686ba2fffe22720dfdecf03ad8ebb'
    with zipfile.ZipFile(zpath) as z:
        data = z.read('BPIC-2015/BPIC15_1_sorted.csv')
    rows = [r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''))
            if r['Case ID'] == case]
    # The release has wall-clock strings without timezone, so check local clock
    # components, not a guessed UTC offset. This is explicitly not byte identity.
    csvtime = lambda s: datetime.datetime.strptime(s, '%m/%d/%y %H:%M:%S')
    rawtime = lambda s: datetime.datetime.fromisoformat(s).replace(tzinfo=None)
    rawkeys = Counter((r['action_code'], r['org:resource'], rawtime(r['time:timestamp']),
                       r['activityNameEN']) for r in raw)
    csvkeys = Counter((r['action_code'], r['Resource'], csvtime(r['Complete Timestamp']),
                       r['activityNameEN']) for r in rows)
    assert len(raw) == len(rows) == 75 and rawkeys == csvkeys
    grouped = defaultdict(list)
    for r in rows:
        grouped[csvtime(r['Complete Timestamp'])].append(r)
    critical = grouped[datetime.datetime(2013, 10, 15)]
    assert len(critical) == 37
    codes = [r['action_code'] for r in critical]
    ordered = codes == sorted(codes)
    result = dict(case_alias='C0261', case_events=75, critical_block_events=37,
                  matched_fields=['activity code', 'raw resource', 'local wall clock', 'English label'],
                  event_multiset_matches=True, original_zip_sha256=hashlib.sha256(zpath.read_bytes()).hexdigest(),
                  csv_member_sha256=hashlib.sha256(data).hexdigest(),
                  critical_block_full_code_nondecreasing=ordered,
                  all_case_ties_full_code_nondecreasing=all([r['action_code'] for r in g] ==
                                                          sorted(r['action_code'] for r in g) for g in grouped.values()),
                  file_order_is_not_case_time_order=any(csvtime(a['Complete Timestamp']) > csvtime(b['Complete Timestamp'])
                                                       for a, b in zip(rows, rows[1:])),
                  interpretation='A documented and observed preprocessing convention; not an independent execution audit trail.',
                  business_execution_order_verified=False)
    assert ordered
    (root/'release-case-check.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
