"""Recreate the fixed M3 population in a clean unpacked project, without ranking."""
from pathlib import Path
import hashlib,json
from src.audit_data import audit
from src.study_data import select_cohort,make_blocks,write_cohort

def main():
    raw='data/raw/mirror-BPI_Challenge_2015_M3.xes.gz'
    sha='7ffc2552130921c6fbc0ffc6c519be56775a4352ea22b4ceba5db0f72bfa67d4'
    assert hashlib.sha256(Path(raw).read_bytes()).hexdigest()==sha
    out=Path('results/revision-v7/M3');out.mkdir(parents=True,exist_ok=False)
    audit(raw,'results/revision-v7/m3-source-audit','complete')
    split=json.loads(Path('results/revision-v7/m3-source-audit/split.json').read_text());ids=split['dev']+split['reserved_test']
    target=out/'all-eligible-split-private.json';target.write_text(json.dumps(dict(dev=[],reserved_test=ids)))
    allcases=select_cohort(dict(raw=raw,sha256=sha,split=str(target),prior_audit='results/revision-v7/m3-source-audit/audit.json',lifecycle='complete'),'test')
    selected={}
    for case,events in allcases.items():
        try:make_blocks(events,'N')
        except ValueError:continue
        selected[case]=events
    assert len(allcases)==len(selected)==1409 and sum(map(len,selected.values()))==59681
    write_cohort(selected,out/'cohort.csv')
    config=json.loads(Path('configs/core_v7_M3.json').read_text())
    assert hashlib.sha256((out/'cohort.csv').read_bytes()).hexdigest()==config['cohort_sha256']
    print('All 1409 cases / 59681 events retained; frozen normalized-cohort digest matched.')
if __name__=='__main__':main()
