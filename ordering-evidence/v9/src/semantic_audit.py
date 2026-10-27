"""Development-only metadata and ordering-hint audit; no causal-order inference."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--cohort', required=True)
    parser.add_argument('--split', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--code-key', choices=['full', 'numeric'], default='full')
    args = parser.parse_args()
    target = Path(args.out)
    if target.exists():
        raise FileExistsError(target)
    selected = set(json.loads(Path(args.split).read_text())['dev'])
    derived = defaultdict(dict)
    with open(args.cohort) as stream:
        for row in csv.DictReader(stream):
            derived[row['case_id']][int(row['source_index'])] = row['resource']
    assert set(derived) == selected
    metrics = Counter()
    missing = Counter()
    totals = {mode: Counter() for mode in ['source', 'lex', 'code_source', 'code_lex', 'code_reverse']}
    code_violations = Counter({mode: 0 for mode in totals})
    def tag(element):
        return element.tag.rsplit('}', 1)[-1]
    def attrs(element):
        return {child.get('key'): child.get('value') for child in element if child.get('key')}
    def instant(event):
        value = datetime.fromisoformat(event['time:timestamp'])
        assert value.tzinfo is not None
        return value.astimezone(timezone.utc)
    def code_key(event):
        code = event['action_code']
        if args.code_key == 'full':
            return code
        match = re.fullmatch(r'(.+?)_(\d{3})(.*)', code)
        assert match, 'Unparsed action code: do not invent its order'
        # Leave suffix variants unordered; do not infer an order between _030_1 and _030_2.
        return match.group(1), int(match.group(2))
    with gzip.open(args.input) as stream:
        root = ET.parse(stream).getroot()
    for trace in root:
        if tag(trace) != 'trace':
            continue
        case = attrs(trace).get('concept:name')
        if case not in selected:
            continue
        metrics['cases'] += 1
        events = []
        for index, element in enumerate(child for child in trace if tag(child) == 'event'):
            event = attrs(element)
            assert event['lifecycle:transition'].lower() == 'complete'
            event['_index'] = index
            event['_resource'] = derived[case][index]
            events.append(event)
            metrics['events'] += 1
            stamp = datetime.fromisoformat(event['time:timestamp'])
            metrics['local_midnight_events'] += stamp.time().isoformat() == '00:00:00'
            for name in ['dateFinished', 'dateStop', 'planned', 'dueDate', 'action_code']:
                missing[name] += not bool(event.get(name))
            code = event.get('action_code')
            assert code, 'Do not invent codes for an incomplete ordering-hint baseline'
            metrics['code_equals_concept_name'] += code == event.get('concept:name')
            if event.get('dateFinished'):
                # dateFinished has no offset: compare calendar dates only, never UTC instants.
                finished = datetime.fromisoformat(event['dateFinished'])
                metrics['dateFinished_without_timezone'] += finished.tzinfo is None
                relation = ('before' if finished.date() < stamp.date() else
                            'after' if finished.date() > stamp.date() else 'same')
                metrics['dateFinished_calendar_' + relation] += 1
        assert len(events) == len(derived[case])
        groups = defaultdict(list)
        for event in events:
            groups[instant(event)].append(event)
        ordered_groups = [groups[t] for t in sorted(groups)]
        refined = []
        for block in ordered_groups:
            if len(set(event['_resource'] for event in block)) > 1:
                metrics['mixed_timestamp_blocks'] += 1
                metrics['source_code_nondecreasing_mixed_blocks'] += (
                    [code_key(event) for event in block] ==
                    sorted(code_key(event) for event in block))
            code_groups = defaultdict(list)
            for event in block:
                code_groups[code_key(event)].append(event)
            for code in sorted(code_groups):
                refined.append(code_groups[code])
        metrics['refined_mixed_blocks'] += sum(
            len(set(event['_resource'] for event in block)) > 1 for block in refined)
        metrics['refined_mixed_events'] += sum(len(block) for block in refined
            if len(set(event['_resource'] for event in block)) > 1)
        metrics['max_refined_block'] = max(metrics['max_refined_block'], max(map(len, refined)))
        for mode in totals:
            blocks = refined if mode.startswith('code_') else ordered_groups
            sequence = []
            for block in blocks:
                if mode.endswith('lex'):
                    block = sorted(block, key=lambda event: event['_resource'])
                elif mode.endswith('reverse'):
                    block = sorted(block, key=lambda event: event['_resource'], reverse=True)
                if not mode.startswith('code_'):
                    code_violations[mode] += [code_key(event) for event in block] != sorted(
                        code_key(event) for event in block)
                sequence.extend(block)
            indices = [event['_index'] for event in sequence]
            assert len(indices) == len(set(indices)) == len(events)
            assert set(indices) == set(derived[case])
            assert [instant(event) for event in sequence] == sorted(instant(event) for event in events)
            resources = [event['_resource'] for event in sequence]
            totals[mode].update((a, b) for a, b in zip(resources, resources[1:]) if a != b)
    e, f = ('R0015', 'R0006'), ('R0006', 'R0017')
    candidates = set().union(*(set(counts) for counts in totals.values()))
    report = {'scope': 'fixed development cohort only; no reserved-test outcomes',
              'code_key': args.code_key,
              'ordering_hint_assumption': 'Within timestamp, ascending code key; equal-key events may permute. Full key orders the entire string; numeric key orders subprocess and three-digit ordinal, leaving suffix variants free. Neither is validated causality.',
              'metrics': dict(metrics), 'missing_attributes': dict(missing),
              'timestamp_blocks_violating_ascending_code_by_mode': dict(code_violations),
              'date_comparison': 'calendar dates only; dateFinished offset unknown',
              'illustrative_development_pair': {'edge_e': e, 'edge_f': f,
                  'counts': {mode: {'e': counts[e], 'f': counts[f], 'difference': counts[e]-counts[f]}
                             for mode, counts in totals.items()}},
              'source_vs_code_source_edge_l1': sum(abs(totals['source'][edge]-totals['code_source'][edge]) for edge in candidates),
              'code_lex_vs_code_reverse_edge_l1': sum(abs(totals['code_lex'][edge]-totals['code_reverse'][edge]) for edge in candidates),
              'hashes': {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                         for name in [args.input, args.cohort, args.split, __file__]}}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
