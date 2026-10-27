import argparse
import json
from .io import convert_xes, sha256

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--lifecycle', required=True, help='e.g. complete or all; verify dataset semantics')
    a = p.parse_args()
    stats = convert_xes(a.input, a.output, a.lifecycle)
    stats.update(source_sha256=sha256(a.input), output_sha256=sha256(a.output), lifecycle=a.lifecycle)
    with open(a.output + '.manifest.json', 'x') as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats))
