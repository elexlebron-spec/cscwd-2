"""Exact component models; no claim that code hints establish execution order."""
from collections import Counter, defaultdict, deque

from extensions.order_evidence import solve, Unsupported
from src.study_data import code_key, make_blocks


def p_blocks(events):
    result = []
    for block in make_blocks(events, 'T'):
        groups = defaultdict(list)
        for e in block:
            groups[code_key(e['code'])[0] if len(block) > 1 else ''].append(e)
        result.extend([[(e['source_index'], e['resource']) for e in groups[p]]
                       for p in sorted(groups)])
    return result


def retain(constrained_lows, timestamp_lows):
    """Fewest case constraints sufficient for a strictly positive hybrid minimum.

    None means even all A constraints fail to certify. Zero means T suffices.
    This is conditional on validating every assumed precedence in retained cases.
    """
    if len(constrained_lows) != len(timestamp_lows):
        raise ValueError('different case sets')
    losses = [a-t for a, t in zip(constrained_lows, timestamp_lows)]
    if any(v < 0 for v in losses):
        raise ValueError('A must refine T')
    value = sum(timestamp_lows)
    chosen = []
    if value > 0:
        return dict(count=0, indices=[], minimum=value)
    for i in sorted(range(len(losses)), key=lambda i: (-losses[i], i)):
        if not losses[i]:
            break
        chosen.append(i)
        value += losses[i]
        if value > 0:
            return dict(count=len(chosen), indices=chosen, minimum=value)
    return None


def solve_w(events, weights, cap=2000000, witness=False, stats=None):
    """Within-subprocess ordinal precedence; distinct subprocesses interleave.

    State is used multiplicities by (subprocess,ordinal,objective category), and
    last category. Only smaller ordinals of the same subprocess are prerequisites.
    Original indices are expanded from queues, retaining every original event.
    """
    active = sorted({r for edge, weight in weights.items() if weight for r in edge})
    category = {r: i+1 for i, r in enumerate(active)}
    label = {i+1: r for i, r in enumerate(active)}
    def q(a, b):
        return weights.get((label[a], label[b]), 0) if a and b and a != b else 0
    previous = {None: (0, 0)}
    prefixes = {None: ()}
    for block in make_blocks(events, 'T'):
        # A zero-transition block still needs its original event multiplicities
        # when it interleaves with other categories; do not delete those events.
        groups = defaultdict(list)
        for e in block:
            p, n = code_key(e['code']) if len(block) > 1 else ('', 0)
            groups[p, n, category.get(e['resource'], 0)].append(e['source_index'])
        slots = sorted(groups)
        amounts = tuple(len(groups[k]) for k in slots)
        prerequisites = [tuple(j for j, other in enumerate(slots)
                               if other[0] == key[0] and other[1] < key[1])
                         for key in slots]
        start = (0,) * len(slots)
        table = {(start, a): bounds for a, bounds in previous.items()}
        paths = {(start, a): prefixes[a] for a in previous} if witness else {}
        seen = {start}
        for _ in range(len(block)):
            nxt = {}
            nextpaths = {}
            for (used, last), (lo, hi) in table.items():
                for j, (_, _, c) in enumerate(slots):
                    if used[j] == amounts[j] or any(used[k] != amounts[k] for k in prerequisites[j]):
                        continue
                    after = list(used); after[j] += 1; after = tuple(after)
                    if after not in seen:
                        seen.add(after)
                        if len(seen) > cap:
                            raise Unsupported('W reachable count-vector limit')
                    key = (after, c)
                    low, high = lo+q(last, c), hi+q(last, c)
                    if key not in nxt:
                        nxt[key] = (low, high)
                        if witness:
                            nextpaths[key] = paths[used, last]+(groups[slots[j]][used[j]],)
                    else:
                        oldlow, oldhigh = nxt[key]
                        if witness and low < oldlow:
                            nextpaths[key] = paths[used, last]+(groups[slots[j]][used[j]],)
                        nxt[key] = (min(oldlow, low), max(oldhigh, high))
            if stats is not None:
                stats['max_layer_states'] = max(stats.get('max_layer_states', 0), len(nxt))
            table = nxt
            if witness:
                paths = nextpaths
        if stats is not None:
            stats['max_count_vectors'] = max(stats.get('max_count_vectors', 0), len(seen))
            stats['blocks'] = stats.get('blocks', 0)+1
        previous = {last: bound for (used, last), bound in table.items()}
        if witness:
            prefixes = {last: paths[used, last] for used, last in table}
    if not previous:
        return 0, 0, () if witness else None
    end = min(previous, key=lambda a: (previous[a][0], -1 if a is None else a))
    return (min(b[0] for b in previous.values()), max(b[1] for b in previous.values()),
            prefixes[end] if witness else None)
