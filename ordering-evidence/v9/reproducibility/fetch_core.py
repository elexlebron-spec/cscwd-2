"""Download only fixed public core inputs; no credentials or private upload."""
import argparse
import base64
import hashlib
import json
import urllib.request
from pathlib import Path

SOURCES={
 'M1':('data/raw/mirror-BPI_Challenge_2015.xes.gz','https://api.github.com/repos/henrikkirchmann/semantic-aware-process-mining-distances/git/blobs/2a2d0087e5025db5cffc9d5376f72cfc45bac22b','d5847a409cec1de1b7382b59365aec6af8e53e1c2ac083201e7679c22a6ef525'),
 'M3':('data/raw/mirror-BPI_Challenge_2015_M3.xes.gz','https://api.github.com/repos/henrikkirchmann/semantic-aware-process-mining-distances/git/blobs/eab51d87c6b88747f08c5bc263678c4b323fc201','7ffc2552130921c6fbc0ffc6c519be56775a4352ea22b4ceba5db0f72bfa67d4'),
 'IT':('data/provenance/v8/uci498.zip','https://archive.ics.uci.edu/static/public/498/incident+management+process+enriched+event+log.zip','6294e29a311647306bfdfc85783f7df66517c197b9cd49aa5ee36ba9c525d1d6')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--log',choices=SOURCES,required=True);a=p.parse_args()
    name,url,expected=SOURCES[a.log];path=Path(name)
    if path.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        print('Already present with required SHA256:',name);return
    request=urllib.request.Request(url,headers={'User-Agent':'Ordering-evidence research reproduction'})
    data=urllib.request.urlopen(request,timeout=90).read()
    if 'api.github.com' in url:
        blob=json.loads(data);data=base64.b64decode(blob['content'])
        assert hashlib.sha1(('blob '+str(len(data))+'\0').encode()+data).hexdigest()==url.rsplit('/',1)[-1]
    assert hashlib.sha256(data).hexdigest()==expected
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)
    print('Saved public input with required SHA256:',name)


if __name__=='__main__':main()
