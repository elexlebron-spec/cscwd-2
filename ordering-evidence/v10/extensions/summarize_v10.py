"""Export all fixed component rows with conservative objective exposure."""
import csv
import json
from pathlib import Path


def main():
    root = Path('results/revision-v10')
    coverage = json.loads((root/'effective-coverage.json').read_text())
    rows = []
    for label in ['M1', 'M3']:
        byq = {q['query']: q for q in coverage[label]['queries']}
        for q in json.loads((root/label/'queries.json').read_text()):
            for model, data in q['models'].items():
                rows.append(dict(dataset=label, query=q['query'], model=model,
                    edge_e='>'.join(q['edge_e']), edge_f='>'.join(q['edge_f']),
                    N_source_margin=q['N_source_margin'],
                    target_exposed_blocks=byq[q['query']]['exposed_blocks'],
                    target_exposed_cases=byq[q['query']]['exposed_cases'], **data))
    with (root/'all-components.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print('450 component/query rows exported')


if __name__ == '__main__': main()
