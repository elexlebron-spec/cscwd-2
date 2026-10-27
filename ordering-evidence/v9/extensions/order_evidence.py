"""Exact signed objectives and case-level dependence on ordering assumptions.

This extension leaves the frozen study engine unchanged. Multiplicity DP and
descending-loss selection are standard tools, not general algorithmic novelty.
"""
from collections import Counter, defaultdict, deque
from itertools import product
from math import prod


class Unsupported(Exception):
    pass


def solve(blocks, weights, max_count_states=2000000, witness=False):
    """Return exact (min,max,minimizing original-index order), or raise Unsupported.

    blocks: lists of (original_index, resource). Resources outside all nonzero
    objective endpoints have identical zero transition rows/columns and merge.
    A target category's multiplicity is retained in every mixed block.
    """
    active=sorted({r for edge,value in weights.items() if value for r in edge})
    category={r:i+1 for i,r in enumerate(active)}
    label={i+1:r for i,r in enumerate(active)}
    def q(a,b):
        return weights.get((label[a],label[b]),0) if a and b and a!=b else 0
    previous={None:(0,0)};prefix={None:()}
    for original in blocks:
        if not original:raise ValueError('Empty block')
        grouped=defaultdict(list)
        for index,resource in original:grouped[category.get(resource,0)].append(index)
        classes=sorted(grouped)
        amounts=tuple(len(grouped[c]) for c in classes)
        compressed=len(classes)==1
        if compressed:amounts=(1,)
        if prod(n+1 for n in amounts)>max_count_states:raise Unsupported('count-state limit')
        table={}
        for used in product(*(range(n+1) for n in amounts)):
            if not any(used):continue
            for last,c in enumerate(classes):
                if not used[last]:continue
                before=list(used);before[last]-=1;before=tuple(before)
                if not any(before):
                    lows=[v[0]+q(p,c) for p,v in previous.items()]
                    highs=[v[1]+q(p,c) for p,v in previous.items()]
                else:
                    lows=[];highs=[]
                    for end,a in enumerate(classes):
                        if before[end]:
                            low,high=table[before,end]
                            lows.append(low+q(a,c));highs.append(high+q(a,c))
                table[used,last]=(min(lows),max(highs))
        current={};paths={}
        for end,c in enumerate(classes):
            current[c]=table[amounts,end]
            if not witness:continue
            used=amounts;last=end;reverse_path=[]
            while True:
                reverse_path.append(classes[last])
                before=list(used);before[last]-=1;before=tuple(before)
                if not any(before):
                    first=classes[last]
                    prev=min(previous,key=lambda a:(previous[a][0]+q(a,first),-1 if a is None else a))
                    break
                candidates=[j for j,a in enumerate(classes) if before[j] and
                            table[before,j][0]+q(a,classes[last])==table[used,last][0]]
                last=candidates[0];used=before
            sequence=list(reversed(reverse_path))
            if compressed:indices=tuple(grouped[c])
            else:
                queues={a:deque(grouped[a]) for a in classes}
                indices=tuple(queues[a].popleft() for a in sequence)
            paths[c]=prefix[prev]+indices
        previous=current
        if witness:prefix=paths
    if not previous:return (0,0,() if witness else None)
    end=min(previous,key=lambda a:(previous[a][0],-1 if a is None else a))
    return min(v[0] for v in previous.values()),max(v[1] for v in previous.values()),prefix[end] if witness else None


def radius(constrained_lows,timestamp_lows,threshold):
    """Fewest unit-cost case relaxations to allow score <= threshold.

    None means impossible even after relaxing every case. A result of zero
    means already feasible under the base model; it is not a positive certificate.
    """
    if len(constrained_lows)!=len(timestamp_lows):raise ValueError('different case sets')
    losses=[a-t for a,t in zip(constrained_lows,timestamp_lows)]
    if any(v<0 for v in losses):raise ValueError('base model must refine timestamp model')
    selected=sorted(range(len(losses)),key=lambda i:(-losses[i],i))
    value=sum(constrained_lows)
    if value<=threshold:return dict(count=0,indices=[],minimum=value)
    chosen=[]
    for i in selected:
        if not losses[i]:break
        chosen.append(i);value-=losses[i]
        if value<=threshold:return dict(count=len(chosen),indices=chosen,minimum=value)
    return None
