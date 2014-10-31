#! /usr/bin/env python

# works in python 2 or 3
# GPLv3

from sat import *

# todo
# multiplication

def addition(A, B, C):
    "A + B = C, big endian input"
    # little endian makes math easier though
    A = list(reversed(A))
    B = list(reversed(B))
    C = list(reversed(C))
    for clause in window((A[0], B[0], C[0]), 2, 2):
        yield clause
    # fix this to work with different length ints
    # 24 clauses per bit, could be better?
    for i in range(1, min(map(len, (A, B, C)))):
        j = i - 1
        for clause in maybe((A[i], B[i] ,C[i]), 2):
            #yield (-A[j], -B[j], -C[j]) + clause
            #yield (-A[j], -B[j], C[j]) + clause
            yield (-A[j], -B[j]) + clause
            yield (-A[j], B[j], C[j]) + clause
            yield (A[j], -B[j], C[j]) + clause
        for clause in one_or_three((A[i], B[i] ,C[i])):
            yield (-A[j], B[j], -C[j]) + clause
            yield (A[j], -B[j], -C[j]) + clause
            #yield (A[j], B[j], C[j]) + clause
            #yield (A[j], B[j], -C[j]) + clause
            yield (A[j], B[j]) + clause

def one_set_true(*star_cells):
    "combinatorial explosion!  use summary vars instead"
    # sets can be different lengths
    # multiple sets can be true
    # dunno why this works
    # wrote it by listing all bad sequences and eliminating vars
    chop = lambda cells, n: [-c for c in cells[:n]] + [cells[n]]
    for xs in product(*[range(len(sc)) for sc in star_cells]):
        yield tuple(chain.from_iterable(starmap(chop, zip(star_cells, xs))))

def line(cnf, prefix, adj, size, exact=False, closed=False, seed_start=None, seed_end=None, seed_mid=None):
    "a restricted type of flood fill"
    # todo, double conic with seed_end
    if seed_mid and (seed_start or seed_end):
        raise Exception("use only one seed")
    if closed and (seed_start or seed_end):
        raise Exception("loops don't have ends, use seed_mid")
    # place seeds
    seed = None
    if seed_start:
        seed = seed_start
    if seed_mid:
        seed = seed_mid
    base = set(adj.keys())
    if seed is None:
        cells = base
    else:
        cells = set([seed])
    volume = set()
    f = cnf.auto_term
    if seed:
        cnf.write(f(prefix, seed, 0))
    if seed_end:
        cnf.write(f(prefix, seed_end, size-1))
    steps = [(0, None)] + [(i, i-1) for i in range(1, size)]
    if closed:
        steps.append((size-1, 0))
    for layer,target in steps:
        cells2 = [(prefix,c,first) for c in cells]
        volume |= set(cells2)
        # one per layer
        cnf.write(window([f(*c2) for c2 in cells2], 1, 1))
        # single starting point
        if layer == 0:
            cells = expand(adj, cells)
            continue
        # growth
        for c in cells:
            cells3 = expand(adj, [c])
            if exact:
                # no idling
                cells3.discard(c)
            cells3 = set((prefix,c3,target) for c3 in cells3)
            cells3 &= volume
            cells3 = [f(*c3) for c3 in cells3]
            cnf.write([cells3 + [-f(prefix,c,layer)]])
        cells = expand(adj, cells)
    # at most one per column
    columns = defaultdict(set)
    for _,c,l in volume:
        columns[c].add((prefix,c,l))
    for c in columns:
        cells = [f(prefix,c,l) for _,_,l in columns[c]]
        if exact:
            cnf.write(window(cells, 0, 1))
        else:
            cnf.write(window(cells, 1, 1))
    # summarize into a very weird adjacency table
    # unidirectional?  bidirectional?
    for c,links in adj.items():
        for l,t in steps:
            if t is None:
                continue
            for c2 in links:
                first = (prefix,c,t)
                second = (prefix,c2,l)
                if first not in volume or second not in volume:
                    cnf.write_one(-f(prefix, 'summary', c, c2))
                    continue
                cnf.write(if_gen([f(first), f(second)], f(prefix, 'summary', c, c2), modeA=all))
    # also summarize to a flat sheet?
    return


