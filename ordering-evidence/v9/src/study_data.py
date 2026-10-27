"""Frozen cohort extraction and explicit ordering-assumption blocks."""
import csv
import gzip
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from .io import sha256, timestamp_us


def code_key(code):
    match = re.fullmatch(r'(.+?)_(\d{3})(.*)', code)
    if not match:
        raise ValueError('Unparsed activity code; do not infer missing order')
    return match.group(1), int(match.group(2))


def event_key(event, policy):
    if policy == 'T':
        return (event['time'],)
    if policy == 'N':
        return (event['time'], *code_key(event['code']))
    if policy == 'F':
        return event['time'], event['code']
    raise ValueError(policy)


def make_blocks(events, policy):
    timestamps = defaultdict(list)
    for event in events:
        timestamps[event['time']].append(event)
    result = []
    for stamp in sorted(timestamps):
        block = timestamps[stamp]
        # A singleton has no internal ordering choice and needs no activity code.
        if len(block) == 1 or policy == 'T':
            result.append(block)
            continue
        groups = defaultdict(list)
        for event in block:
            groups[event_key(event, policy)].append(event)
        result.extend(groups[key] for key in sorted(groups))
    return result


def select_cohort(dataset, phase):
    if sha256(dataset['raw']) != dataset['sha256']:
        raise ValueError('Raw input hash changed')
    split = json.loads(Path(dataset['split']).read_text())
    selected = split['dev' if phase == 'dev' else 'reserved_test']
    assert set(split['dev']).isdisjoint(split['reserved_test'])
    wanted = set(selected)
    if len(wanted) != len(selected):
        raise ValueError('Duplicate selected case')
    root = ET.parse(gzip.open(dataset['raw'])).getroot()
    tag = lambda element: element.tag.rsplit('}', 1)[-1]
    attrs = lambda element: {x.get('key'): x.get('value') for x in element if x.get('key')}
    eligible, all_ids, resources = {}, set(), set()
    for trace in root:
        if tag(trace) != 'trace':
            continue
        case = attrs(trace).get('concept:name')
        if not case or case in all_ids:
            raise ValueError('Missing or duplicate case')
        all_ids.add(case)
        events, invalid = [], False
        for index, element in enumerate(x for x in trace if tag(x) == 'event'):
            row = attrs(element)
            if dataset['lifecycle'] != 'all' and row.get('lifecycle:transition', '').lower() != dataset['lifecycle']:
                continue
            resource = row.get('org:resource')
            invalid |= not resource or resource.upper() == 'UNKNOWN'
            raw_time = row.get('time:timestamp', '')
            fraction = re.search(r'\.(\d+)', raw_time)
            try:
                if fraction and len(fraction[1]) > 6:
                    raise ValueError('Unsupported precision')
                stamp = timestamp_us(raw_time)
            except ValueError:
                invalid = True
                continue
            events.append({'time':stamp, 'timestamp':raw_time, 'resource':resource,
                           'activity':row.get('concept:name', ''), 'code':row.get('action_code', ''),
                           'lifecycle':row.get('lifecycle:transition', ''), 'source_index':index})
        if events and not invalid:
            eligible[case] = events
            resources.update(event['resource'] for event in events)
    prior = json.loads(Path(dataset['prior_audit']).read_text())
    if (len(eligible), sum(map(len, eligible.values()))) != (prior['eligible_cases'], prior['eligible_events']):
        raise ValueError('Population differs from original pre-outcome audit')
    if not wanted <= set(eligible):
        raise ValueError('A frozen selected case is no longer eligible')
    # The original development extraction already used this global ID vocabulary.
    mapping = {resource: 'R%04d' % index for index, resource in enumerate(sorted(resources), 1)}
    result = {}
    for case in selected:
        result[case] = [dict(event, resource=mapping[event['resource']]) for event in eligible[case]]
    return result


def write_cohort(cases, path):
    with Path(path).open('x', newline='') as stream:
        fields = ['case_id','timestamp','resource','activity','lifecycle','source_index','code']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for case, events in cases.items():
            for event in events:
                writer.writerow(dict(case_id=case, **{key:event[key] for key in fields if key != 'case_id'}))
