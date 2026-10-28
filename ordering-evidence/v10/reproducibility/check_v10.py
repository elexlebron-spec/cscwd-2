"""Data-free consistency check; not a substitute for full event-level replay."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--manifest', action='store_true'); a = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest_count = 0
    if a.manifest:
        for line in (root/'MANIFEST.sha256').read_text().splitlines():
            digest, name = line.split('  ', 1)
            p = (root/name).resolve(); assert p.is_relative_to(root)
            assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
            manifest_count += 1
    ev = root/'evidence/v10'; rows = list(csv.DictReader((ev/'all-components.csv').open()))
    assert len(rows) == 450
    indep = certs = retention = 0
    for label in ['M1', 'M3']:
        data = json.loads((ev/label/'queries.json').read_text())
        old = json.loads((root/'evidence/revision-v7'/label/'queries.json').read_text())
        summary = json.loads((ev/label/'summary.json').read_text())
        assert len(data) == len(old) == 45
        for q, oq in zip(data, old):
            assert (q['query'], q['edge_e'], q['edge_f']) == (oq['query'], oq['edge_e'], oq['edge_f'])
            m = q['models']
            for weaker, stronger in [('T','P'), ('T','W'), ('P','N'), ('W','N'), ('N','F')]:
                x, y = m[weaker], m[stronger]
                assert x['status'] == y['status'] == 'exact'
                assert x['lower'] <= y['lower'] <= y['upper'] <= x['upper']
            for model in m:
                v = m[model]
                assert v['certified'] == (v['lower'] > 0)
                assert v['positive_loss_cases'] >= 0 and v['total_loss'] == v['lower']-m['T']['lower']
                if v['certified']:
                    assert v['retention_count'] is not None and v['retention_minimum'] > 0
                    assert (v['reversal_count'] is None) == (m['T']['lower'] >= 0)
                else:
                    assert v['retention_count'] is None and v['reversal_count'] is None
                row = next(r for r in rows if r['dataset'] == label and int(r['query']) == q['query'] and r['model'] == model)
                for k in ['lower','upper','positive_loss_cases','retention_count','reversal_count']:
                    assert row[k] == ('' if v[k] is None else str(v[k])), (label, q['query'], model, k)
            for model in ['N','F']:
                assert [m[model]['lower'],m[model]['upper']] == oq['models'][model]['range']
                assert m[model]['certified'] == oq['models'][model]['strict_priority_certified']
                if m[model]['certified']:
                    assert m[model]['reversal_count'] == oq['models'][model]['reversal_radius']
        for model, v in summary['models'].items():
            assert v['certified'] == sum(q['models'][model]['certified'] for q in data)
            assert v['finite_reversals'] == sum(q['models'][model]['reversal_count'] is not None for q in data)
        oracle = json.loads((ev/label/'independent.json').read_text())
        assert oracle['all_passed']
        indep += sum(oracle['query_bound_checks'].values())
        certificates = json.loads((ev/label/'certificates.json').read_text())
        for c in certificates['witnesses']:
            assert c['baseline_margin'] > 0 and c['negative_margin'] < 0
            assert c['all_other_case_orders_identical']
        certs += len(certificates['witnesses'])
        retention += certificates['independent_retention_arithmetic_queries']
    assert (indep, certs, retention) == (113580,14,360)
    release = json.loads((ev/'release-case-check.json').read_text())
    assert release['event_multiset_matches'] and release['critical_block_full_code_nondecreasing']
    assert not release['business_execution_order_verified']
    m1 = json.loads((ev/'M1/queries.json').read_text())[11]['models']
    assert (m1['N']['lower'], m1['N']['retention_count'], m1['N']['reversal_count']) == (1,20,1)
    assert [m1['W']['lower'],m1['W']['upper']] == [-6,35]
    print(json.dumps(dict(component_rows=450, independent_case_query_bounds=indep,
        new_replayed_certificates=certs, retention_arithmetic_checks=retention,
        manifest_files=manifest_count, business_execution_order_verified=False,
        scope='aggregate consistency; run the documented raw-data route for independent event-level reconstruction'), indent=2))


if __name__ == '__main__': main()
