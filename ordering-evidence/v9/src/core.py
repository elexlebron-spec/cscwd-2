"""Timestamp-block sensitivity audit. No causal or probabilistic truth claims."""
from collections import Counter, defaultdict
from bisect import bisect_left, bisect_right
from fractions import Fraction
from itertools import permutations, product
import random


def blocks_from_events(events):
    """Events: (integer UTC microseconds, resource); preserve source tie order."""
    groups = defaultdict(list)
    for stamp, resource in events:
        if not isinstance(stamp, int) or not isinstance(resource, str) or not resource:
            raise ValueError('Expected integer timestamp and nonempty resource')
        groups[stamp].append(resource)
    return [groups[t] for t in sorted(groups)]


def counts(sequence):
    return Counter((u, v) for u, v in zip(sequence, sequence[1:]) if u != v)


def linearize(blocks, mode='source', seed=0):
    rng = random.Random(seed)
    output = []
    for block in blocks:
        b = list(block)
        if mode == 'lex':
            b.sort()
        elif mode == 'reverse':
            b.sort(reverse=True)
        elif mode == 'random':
            rng.shuffle(b)
        elif mode != 'source':
            raise ValueError(mode)
        output.extend(b)
    return output


def expected_counts(blocks):
    """Exact expectation under independent uniform event permutations per block.

    It is an explicit sensitivity reference, not an estimated real order law.
    Self transitions are excluded; they still occupy adjacency positions.
    """
    out = defaultdict(Fraction)
    previous = None
    for block in blocks:
        if not block:
            raise ValueError('Empty block')
        c, m = Counter(block), len(block)
        for u, nu in c.items():
            for v, nv in c.items():
                if u != v:
                    out[u, v] += Fraction(nu * nv, m)
        if previous is not None:
            p, n = previous
            for u, nu in p.items():
                for v, nv in c.items():
                    if u != v:
                        out[u, v] += Fraction(nu * nv, n * m)
        previous = c, m
    return dict(out)


def cheap_edge_bounds(blocks):
    """Safe per-edge envelopes for the COMPLETE possible-edge set, not tight bounds."""
    low, high = Counter(), Counter()
    previous = None
    for block in blocks:
        if not block:
            raise ValueError('Empty block')
        c = Counter(block)
        for u in c:
            for v in c:
                if u != v:
                    high[u, v] += min(c[u], c[v])
        if previous is not None:
            for u in previous:
                for v in c:
                    if u != v:
                        high[u, v] += 1
                        if len(previous) == len(c) == 1:
                            low[u, v] += 1
        previous = c
    return {edge: (low[edge], upper) for edge, upper in high.items()}


def top_k_profile(scores, k):
    """Return all boundary ties; never choose edges by their resource IDs."""
    if k < 1:
        raise ValueError('k must be positive')
    if not scores:
        return {'cutoff': None, 'strict': [], 'boundary': [], 'slots': 0, 'unique': True}
    k = min(k, len(scores))
    cutoff = sorted(scores.values(), reverse=True)[k - 1]
    strict = sorted(e for e, score in scores.items() if score > cutoff)
    boundary = sorted(e for e, score in scores.items() if score == cutoff)
    slots = k - len(strict)
    return {'cutoff': str(cutoff), 'strict': strict, 'boundary': boundary,
            'slots': slots, 'unique': slots == len(boundary)}


def screen_top_k(intervals, k):
    """Safe full-universe screening/certification, including adversarial score ties."""
    if k < 1:
        raise ValueError('k must be positive')
    if any(lo > hi for lo, hi in intervals.values()):
        raise ValueError('Invalid interval')
    lows = sorted(lo for lo, hi in intervals.values())
    highs = sorted(hi for lo, hi in intervals.values())
    result = {}
    for e, (lo, hi) in intervals.items():
        excluded = len(lows) - bisect_right(lows, hi) >= k
        certified = len(highs) - bisect_left(highs, lo) - 1 < k
        result[e] = 'excluded' if excluded else ('certified' if certified else 'unknown')
    return result


def score_bounds(blocks, weights, max_block=10):
    """Exact bounds of any linear edge score, including pairwise rank margins.

    Subset dynamic programming retains the LAST resource across block boundaries.
    Return None when unsupported, never substitute sampled extrema for bounds.
    Exponential in largest mixed-resource block. All-same blocks are compressed.
    """
    possible = cheap_edge_bounds(blocks)
    if not any(value and edge in possible for edge, value in weights.items()):
        return (0, 0)
    states = {None: (0, 0)}
    def w(u, v):
        return 0 if u is None or u == v else weights.get((u, v), 0)
    for original in blocks:
        if not original:
            raise ValueError('Empty block')
        block = list(original)
        if len(set(block)) == 1:
            block = block[:1]
        if len(block) > max_block:
            return None
        n = len(block)
        table = {}
        for j, resource in enumerate(block):
            low = min(lo + w(prev, resource) for prev, (lo, hi) in states.items())
            high = max(hi + w(prev, resource) for prev, (lo, hi) in states.items())
            table[1 << j, j] = low, high
        for mask in range(1, 1 << n):
            for last in range(n):
                if (mask, last) not in table:
                    continue
                lo, hi = table[mask, last]
                for j in range(n):
                    if mask & (1 << j):
                        continue
                    key = mask | (1 << j), j
                    delta = w(block[last], block[j])
                    old = table.get(key)
                    pair = lo + delta, hi + delta
                    table[key] = pair if old is None else (min(old[0], pair[0]), max(old[1], pair[1]))
        states = {}
        for j, resource in enumerate(block):
            lo, hi = table[(1 << n) - 1, j]
            if resource in states:
                old = states[resource]
                lo, hi = min(lo, old[0]), max(hi, old[1])
            states[resource] = lo, hi
    return min(x[0] for x in states.values()), max(x[1] for x in states.values())


def exhaustive_counts(blocks):
    """Tiny independent reference; duplicates intentionally retain event weights."""
    for choices in product(*(permutations(b) for b in blocks)):
        yield counts([r for b in choices for r in b])
