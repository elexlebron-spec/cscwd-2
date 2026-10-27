import csv
import gzip
import hashlib
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone


def timestamp_us(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timezone missing; do not silently assume UTC')
    delta = dt.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds


def load_csv(path):
    cases, rejected = defaultdict(list), []
    invalid_cases = set()
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        if not {'case_id', 'timestamp', 'resource'}.issubset(reader.fieldnames or []):
            raise ValueError('Required columns: case_id,timestamp,resource')
        for line, row in enumerate(reader, 2):
            case = row['case_id']
            if not case:
                raise ValueError('Missing case_id at CSV line %s' % line)
            try:
                stamp = timestamp_us(row['timestamp'])
                if not row['resource']:
                    raise ValueError('Missing resource')
                cases[case].append((stamp, row['resource']))
            except (ValueError, TypeError) as e:
                invalid_cases.add(case)
                rejected.append({'line': line, 'case_id': case, 'reason': str(e)})
    # Whole-case exclusion avoids manufacturing adjacency across missing events.
    for case in invalid_cases:
        cases.pop(case, None)
    return dict(cases), {'invalid_cases': sorted(invalid_cases), 'invalid_rows': rejected}


def convert_xes(source, target, lifecycle):
    """Explicit event population; missing values preserved for CSV audit rejection.

    A lightweight converter for flat standard XES, not all XES extensions.
    Caller verifies lifecycle/resource meaning against dataset documentation.
    """
    opener = gzip.open if str(source).endswith('.gz') else open
    def tag(e):
        return e.tag.rsplit('}', 1)[-1]
    def attrs(e):
        return {x.attrib['key']: x.attrib.get('value', '') for x in e if 'key' in x.attrib}
    stats = {'traces': 0, 'events_seen': 0, 'events_written': 0, 'events_filtered': 0}
    seen = set()
    with opener(source, 'rb') as f, open(target, 'x', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(['case_id', 'timestamp', 'resource', 'activity', 'lifecycle', 'source_index'])
        context = ET.iterparse(f, events=('start', 'end'))
        _, root = next(context)
        for event, elem in context:
            if event != 'end' or tag(elem) != 'trace':
                continue
            case = attrs(elem).get('concept:name')
            if not case or case in seen:
                raise ValueError('Missing/duplicate trace ID; inspect source')
            seen.add(case)
            stats['traces'] += 1
            for i, child in enumerate(x for x in elem if tag(x) == 'event'):
                a = attrs(child)
                stats['events_seen'] += 1
                life = a.get('lifecycle:transition', '')
                if lifecycle != 'all' and life.lower() != lifecycle.lower():
                    stats['events_filtered'] += 1
                    continue
                writer.writerow([case, a.get('time:timestamp', ''), a.get('org:resource', ''),
                                 a.get('concept:name', ''), life, i])
                stats['events_written'] += 1
            root.clear()
    return stats


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
