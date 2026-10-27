"""Recreate the original M1 core cohort without rerunning historical backgrounds."""
import hashlib
import json
from pathlib import Path
from src.audit_data import audit
from src.study_data import select_cohort,write_cohort


def main():
    source=json.loads(Path('configs/study_v4_0_1.json').read_text())['datasets']['2015']
    audit(source['raw'],'results/dev2015-audit','complete')
    cases=select_cohort(source,'test')
    out=Path('results/resumed-study/test2015-v4.0.1');out.mkdir(parents=True,exist_ok=False)
    write_cohort(cases,out/'cohort.csv')
    config=json.loads(Path('configs/core_v7_M1.json').read_text())
    assert hashlib.sha256((out/'cohort.csv').read_bytes()).hexdigest()==config['cohort_sha256']
    assert len(cases)==999 and sum(map(len,cases.values()))==43322
    print('PASS: original 999-case M1 core population and exact cohort digest reconstructed.')


if __name__=='__main__':main()
